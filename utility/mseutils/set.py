from pathlib import Path
from typing import Any, BinaryIO, Dict, TextIO
from zipfile import ZipFile
from .card import Card, _collect_all_indented_blocks, _cardify_incoming_types, _uncardify_outgoing


class Set:
    """Represents MSE setfile, can load or dump itself to file."""

    def __init__(
        self,
        all_data : Dict[str, Any]
    ) -> None:
        # We need to take all data from the original setfile verbatim, in order -- MSE
        # will often throw a fit if things are rearranged.
        self.all_data = all_data # NEVER SORT THIS DICT
        self.cards = {} # type: Dict[str, Card]
        for k, v in self.all_data.items():
            if isinstance(v, Card):
                self.cards[v.name] = v # Another way to reference SAME card object

    def to_setfile(self, ofile: TextIO) -> None:
        """Dumps to unzipped, plaintext setfile (i.e. file simply named 'set')"""
        _uncardify_outgoing(ofile, self.all_data)

    @classmethod
    def from_setfile(cls, ifile: TextIO) -> "Set":
        """Reads from unzipped, plaintext setfile (i.e. file simply named 'set')"""
        set_fields = {}

        for key, val in _collect_all_indented_blocks(ifile, adaptation_func=_cardify_incoming_types):
            set_fields[key] = val
        return Set(all_data=set_fields)

    @classmethod
    def from_packagefile(cls, filepath: Path, delete_temporaries=True) -> "Set":
        """Reads from zipped .mse-set file, unzips to temporary zip location"""
        temp_folder = filepath.parent / filepath.stem
        with ZipFile(filepath, 'r') as zip_ref:
            zip_ref.extractall(filepath)
        setfile = temp_folder / 'set'
        if not setfile.exists():
            raise ValueError(f"Missing 'set' file! (Are you sure {filepath} is an mse-set?)")
        with open(setfile, 'rt') as ifile:
            s = Set.from_setfile(ifile)
            if delete_temporaries:
                temp_folder.unlink()
            return s
