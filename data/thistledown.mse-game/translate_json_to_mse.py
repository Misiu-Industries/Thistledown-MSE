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
from pathlib import Path
from typing import Any, Dict, List

_legal_tagnames = [
    "name",
    "sciencename"
]

def _mseify_values(o: Any) -> str:
    """Given value, escapes it appropriately for an MSE script."""
    if isinstance(o, int) or isinstance(o, float):
        return(str(o))
    return(f'"{str(o)}"') # Default just add wrapping ""

def _extract_legal_tags(d : Dict[str, Any]) -> str:
    """Expects dict holding card data, returns all legal card tags within that data as
    a single string of 'tag' : 'value' pairs separated by commas."""
    legal_data = {k: _mseify_values(v) for k, v in d.items() if k in _legal_tagnames}
    return ", ".join([f"{k}: {v}" for k, v in legal_data.items()])

# Main script:

cards = []  # type: List[Dict[str, Any]]
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

with open('cards_to_import', 'wt') as out:
    # First line is different, opens brackets
    out.write(f"[ new_card([{_extract_legal_tags(cards[0])}])\n")
    if len(cards) > 1:
        for card in cards[1:]:
            out.write(f", new_card([{_extract_legal_tags(card)}])\n")
    # Close brackets
    out.write("]")
