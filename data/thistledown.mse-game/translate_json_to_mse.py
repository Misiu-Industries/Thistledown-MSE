print("Script for converting json files of card data into MSE script, which allows you")
print("to maintain card data in a collaborative area (like Google Sheets) but still")
print("quickly use MSE for formatting and printing the cards.")
print()
print("Inputs:")
print("  - one or more files with the .json extension in this folder")
print("Outputs:")
print("  - file named 'cards_to_import' to this folder, which can be used natively")
print("    in MSE from Cards > Add Multiple Cards > Update cards from autogen")
print()

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO


def _parse_datetime_if_str(o: Any) -> datetime:
    if isinstance(o, datetime):
        return o
    elif isinstance(o, str):
        return datetime.strptime(o, Card.time_format)
    return datetime.now()


class Card:
    """Represents MSE card, can load from json or setfile and dump itself to setfile."""

    time_format = r"%Y-%m-%d %H:%M:%S"

    def __init__(self, **kwargs) -> None:
        self.has_styling = kwargs.pop("has_styling", False)
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

    def to_setfile_strs(self) -> List[str]:
        """Return representation of self as lines ready to be written to setfile."""
        ret = ["card:"]
        ret.append(f"\thas_styling: {'true' if self.has_styling else 'false'}")
        ret.append(f"\tnotes: {self.notes}")
        ret.append(f"\ttime_created: {self.time_created.strftime(Card.time_format)}")
        ret.append(f"\ttime_modified: {self.time_created.strftime(Card.time_format)}")
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
        if not l.endswith("card:"):
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
            k, v = l.strip().split(": ")
            card_fields[k] = v
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


class Set:
    """Represents MSE setfile, can load or dump itself to file."""
    def __init__(self, *, mse_version: str, game: str, stylesheet: str, **kwargs) -> None:
        self.mse_version = mse_version
        self.short_name = kwargs.pop("short_name", None)
        self.depends_on = kwargs.pop("depends_on", [])
        self.game = game
        self.stylesheet = stylesheet
        self.cards = kwargs.pop("cards", [])
        self.set_info = kwargs.pop("set_info", [])

    def to_setfile(self, ofile: TextIO) -> None:
        ofile.write(f"mse_version: {self.mse_version}")
        if self.short_name is not None:
            ofile.write(f"short_name: {self.short_name}")
        if len(self.depends_on) > 0:
            ofile.writelines("\t".join(self.depends_on))
        ofile.write(f"game: {self.game}")
        ofile.write(f"stylesheet: {self.stylesheet}")
        if len(self.set_info) > 0:
            ofile.writelines("\t".join(self.depends_on))

_legal_tagnames = ["name", "sciencename", "animal_type", "mass_g"]


def _mseify_values(o: Any) -> str:
    """Given value, escapes it appropriately for an MSE script."""
    if isinstance(o, int) or isinstance(o, float):
        return str(o)
    return f'"{str(o)}"'  # Default just add wrapping ""


def _extract_legal_tags(d: Dict[str, Any]) -> str:
    """Expects dict holding card data, returns all legal card tags within that data as
    a single string of 'tag' : 'value' pairs separated by commas."""
    legal_data = {k: _mseify_values(v) for k, v in d.items() if k in _legal_tagnames}
    return ", ".join([f"{k}: {v}" for k, v in legal_data.items()])


# Main script:

cards = []  # type: List[Dict[str, Any]]
cardcards = [] # type: List[Card]
jsons = Path.cwd().glob("*.json")

for json_path in jsons:
    with open(json_path, "rt") as fp:
        data = json.load(fp)
        if (
            not isinstance(data, list)
            or len(data) == 0
            or not isinstance(data[0], dict)
        ):
            raise ValueError(
                "Expects a non-empty list of dicts of {tag_name : value}, e.g. {'name', 'Carolina Wren'}"
            )
        for carddata in data:
            cards.append(carddata)
            cardcards.append(Card(**carddata))

with open("cards_to_import", "wt") as out:
    # First line is different, opens brackets
    out.write(f"import_list := [ new_card([{_extract_legal_tags(cards[0])}])\n")
    if len(cards) > 1:
        for card in cards[1:]:
            tag_str = _extract_legal_tags(card)
            if len(tag_str) == 0:
                continue  # don't write blank cards
            out.write(f", new_card([{tag_str}])\n")
    # Close brackets
    out.write("]")
