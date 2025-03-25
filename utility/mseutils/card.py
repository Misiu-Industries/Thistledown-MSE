from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Dict, Iterator, List, Optional, TextIO, Tuple
import re


def _parse_datetime_if_str(o: Any) -> datetime:
    if isinstance(o, datetime):
        return o
    elif isinstance(o, str):
        return datetime.strptime(o.strip(), Card.time_format)
    return datetime.now()


_re_setfile_scanner = re.compile(
    r"^(?P<indent>\s*)(?:(?:(?P<group_tag>.*?):$)|(?:(?P<key_tag>.*?): (?P<value>.*)$))",
    re.MULTILINE,
)


@contextmanager
def _restore_file_pos(file: TextIO):
    """Seeks file back to initial position at end of block."""
    init_pos = file.tell()
    try:
        yield file
    finally:
        file.seek(init_pos)

def peek_line(file: TextIO):
    pos = file.tell()
    line = file.readline()
    file.seek(pos)
    return line


def _collect_indented_block(
    ifile: TextIO, adaptation_func: Optional[Callable] = None
) -> Tuple[str, Any]:
    """Attempts to extract indented blocks of data from a setfile, perhaps recursively.
    Expects ifile to be on a line BEFORE the the indent (e.g. an opening 'card:' tag),
    collects all lines beginning with an additional layer of indent after that tag into
    a dict (e.g. '\tnotes: ' will be given back as {'notes' : ''}), and if it returns
    nominally ifile will be on the line AFTER that layer of indent (e.g. perhaps the
    opening 'card:' tag of the next card).

    If adaptation_func is not None, it will be passed key / value pairs of the data to
    allow you to make them into different types on the fly -- for example, your func
    could take a pair like "time_modified": "2025-03-19 17:00:13" and parse the value
    into a datetime.

    Can raise IndentationError or ValueError for bad blocks or bad tags.
    """
    global _re_setfile_scanner

    l = ifile.readline()
    m = _re_setfile_scanner.match(l)
    if m is None:
        raise ValueError(
            f"Expected opening tag at line {l} in {ifile.name}"
        )

    if m["key_tag"] is not None:
        # Single line data, we can return right away
        k, v = m["key_tag"], m["value"]
        if adaptation_func is not None:
            k, v = adaptation_func(k, v)
        return (k, v)

    # Otherwise, we're looking at an indented block.
    # Remember this initial indent, we'll return if we get back to this level
    init_indent = m["indent"]
    init_tag = m["group_tag"]
    fields = {}  # type: Dict[str, Any] | List[str]

    while True:
        # Get next line and decide what it is
        l = peek_line(ifile)
        if l == "":
            # If we run out of lines with readline, l will be the empty string
            break
        if init_tag.endswith(" text"):
            # Special case... rules text ironically does not follow regex rules very well
            stripped = l.lstrip()
            curr_indent = l.replace(stripped, '')
            if len(curr_indent) <= len(init_indent):
                # We're done! Great. The next guy can start on this line
                break
            if isinstance(fields, dict):
                fields = []
            fields.append(stripped)
            ifile.readline() # to pop
        else:
            m = _re_setfile_scanner.match(peek_line(ifile))
            if m is None:
                raise ValueError(
                    f"Unparseable line {l} in {ifile.name})"
                )
            if len(m["indent"]) <= len(init_indent):
                # We're done! Great. The next guy can start on this line
                break

            if m["group_tag"] is not None:
                # Opening of a new multi-line thing; recurse
                gt, dat = _collect_indented_block(ifile)
                if adaptation_func is not None:
                    gt, dat = adaptation_func(gt, dat)
                fields[gt] = dat
            elif m["key_tag"] is not None:
                k = m["key_tag"]
                v = m["value"]
                if adaptation_func is not None:
                    k, v = adaptation_func(k, v)
                fields[k] = v
                ifile.readline() # to pop

    if adaptation_func is not None:
        init_tag, fields = adaptation_func(init_tag, fields)
    return (init_tag, fields)


def _collect_all_indented_blocks(ifile : TextIO, **kwargs) -> Iterator[Tuple[str, Dict[str, Any]]]:
    """Repeatedly call _collect_indented_block until file is empty."""
    while True:
        if peek_line(ifile) == "":
            return
        yield _collect_indented_block(ifile, **kwargs)


class Card:
    """Represents MSE card, can load from json or setfile and dump itself to setfile."""

    time_format = r"%Y-%m-%d %H:%M:%S"
    date_format = r"%Y-%m-%d"

    def __init__(self, **kwargs) -> None:
        self.has_styling = kwargs.pop("has_styling", "false")
        self.notes = kwargs.pop("notes", "")
        # Time is tricky; it might be coming in as a string
        self.time_created = _parse_datetime_if_str(kwargs.pop("time_created", None))
        self.time_modified = _parse_datetime_if_str(kwargs.pop("time_modified", None))
        self.name = kwargs.pop("name", "")
        self.remaining_keys = kwargs  # type: Dict[str, Any]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Card):
            return self.name == other.name  # This works well for "if card in set:"
        return False

    def is_identical_to(self, other: "Card") -> bool:
        """Deep comparison of two Cards."""
        return (
            self.has_styling == other.has_styling
            and self.notes == other.notes
            and self.time_created == other.time_created
            and self.time_modified == other.time_modified
            and self.name == other.name
            and self.remaining_keys == other.remaining_keys
        )

    def to_setfile_strs(self) -> List[str]:
        """Return representation of self as lines ready to be written to setfile."""
        ret = ["card:"]
        ret.append(
            f"\thas_styling: {'true' if self.has_styling == "true" else 'false'}"
        )
        ret.append(f"\tnotes: {self.notes}")
        ret.append(f"\ttime_created: {self.time_created.strftime(Card.time_format)}")
        ret.append(f"\ttime_modified: {self.time_modified.strftime(Card.time_format)}")
        ret.append(f"\tname: {self.name}")
        for k, v in self.remaining_keys.items():
            ret.append(f"\t{str(k)}: {str(v)}")
        return ret

    def to_setfile(self, ofile: TextIO, indent: Optional[str] = "") -> None:
        """Writes self as lines to output text file, optionally with indent."""
        for s in self.to_setfile_strs():
            ofile.write(f"{indent}{s}\n")

    @classmethod
    def from_setfile(cls, ifile: TextIO) -> "Card":
        """Attempts to construct a card from input file.
        Restores ifile position to where it was at the start of the function and raises
        ValueError or IndentationError upon failure.
        Returns Card and leaves ifile position just after the end of the card data upon
        success.
        """
        init_pos = ifile.tell()
        l = ifile.readline()
        if not l.endswith("card:\n"):
            ifile.seek(init_pos)
            raise ValueError(
                f"Missing 'card:' tag at line {l} (position {init_pos}) in {ifile.name}"
            )
        c = Card()
        # We lock on to the indentation level of the following line
        prev_pos = ifile.tell()
        l = ifile.readline()
        indent = l.replace(l.lstrip(), "")
        if len(indent) == 0:
            err_pos = ifile.tell()
            ifile.seek(init_pos)
            raise IndentationError(
                f"Expected indented block at line {l} (position {err_pos}) in {ifile.name}"
            )
        card_fields = {  # all of these are required
            "has_styling": None,
            "notes": None,
            "time_created": None,
            "time_modified": None,
            "name": None,
        }  # type: dict[str, Any]
        while l != "" and l.startswith(indent):
            # If we run out of lines with readline, l will be the empty string
            try:
                k, v = l.lstrip().split(": ")
            except ValueError:
                raise ValueError(f"Bad or blank tag {l}")
            card_fields[k.strip()] = v.strip()
            prev_pos = ifile.tell()
            l = ifile.readline()
        # Here we are out of the indented block. Did we get all our required fields?
        if None in card_fields.values():
            ifile.seek(init_pos)
            raise ValueError(
                f"Card candidate is missing one or more required fields (has_styling, notes, time_created, time_modified, name)"
            )
        # If we made it down here... finally, we have a card!
        ifile.seek(prev_pos)
        return Card(**card_fields)

def _cardify_incoming_types(k: Any, v: Any) -> Tuple[Any, Any]:
    if k == "card":
        c = Card(**v)
        return (c.name, c)
    elif isinstance(k, str):
        if "time" in k:
            return(k, datetime.strptime(v, Card.time_format))
        elif k == "game_version" or k == "stylesheet_version":
            return(k, datetime.strptime(v, Card.date_format))
    return (k, v)

def _uncardify_outgoing(ofile: TextIO, data: dict[str, Any], curr_indent: str="") -> None:
    for k, v in data.items():
        if isinstance(v, dict):
            ofile.write(f"{curr_indent}{k}:\n")
            _uncardify_outgoing(ofile, v, curr_indent + "\t")
        elif isinstance(v, datetime):
            if v.hour == 0 and v.minute == 0:
                ofile.write(f"{curr_indent}{k}: {v.strftime(Card.date_format)}\n")
            else:
                ofile.write(f"{curr_indent}{k}: {v.strftime(Card.time_format)}\n")
        elif isinstance(v, Card):
            v.to_setfile(ofile)
        else:
            ofile.write(f"{curr_indent}{k}: {v}\n")