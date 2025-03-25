from datetime import datetime
from pathlib import Path
from mseutils import Card, Set

_parrot_args = {
    "has_styling": "true",
    "notes": "Parrot has passed on.",
    "name": "Dead Parrot",
    "time_modified": datetime(1941, 12, 7, 7, 48, 0),
    "time_created": "1776-07-04 13:02:03",
    "animal_type": "Bird",
}

_parrot_setfile_strs = [
    "card:",
    "\thas_styling: true",
    "\tnotes: Parrot has passed on.",
    "\ttime_created: 1776-07-04 13:02:03",
    "\ttime_modified: 1941-12-07 07:48:00",
    "\tname: Dead Parrot",
    "\tanimal_type: Bird",
]

_hepcat_args = {
    "notes": "Cat has hepatitus.",
    "name": "Hep Cat",
    "time_modified": datetime(1969, 7, 14, 20, 15, 33),
    "time_created": "1969-07-14 20:15:33",
    "animal_type": "Mammal",
    "mass_g": 4000,
}

_hepcat_setfile_strs = [
    "card:",
    "\thas_styling: false",
    "\tnotes: Cat has hepatitus.",
    "\ttime_created: 1969-07-14 20:15:33",
    "\ttime_modified: 1969-07-14 20:15:33",
    "\tname: Hep Cat",
    "\tanimal_type: Mammal",
    "\tmass_g: 4000",
]

_indented_card_1 = (
    "card",
    {
        "has_styling": "false",
        "notes": "",
        "time_created": "2025-03-19 17:00:13",
        "poop": {"nugget": "true"},
        "time_modified": "2025-03-19 17:00:13",
        "name": "American Crow",
        "sciencename": "Corvus brachyrhynchos",
        "animal_type": "Bird",
        "mass_g": "450",
        "art": "",
    },
)

_testdir = Path(__file__).parent


class TestCard:
    def test_module_init_py_isnt_screwy(self):
        c = Card()
        assert True

    def test_init_defaults(self):
        c = Card()
        assert c.has_styling == "false"
        assert c.notes == ""
        assert isinstance(c.time_created, datetime)
        assert c.name == ""

    def test_init_kwargs(self):
        c = Card(**_parrot_args)
        assert c.has_styling == "true"
        assert c.notes == "Parrot has passed on."
        assert c.name == "Dead Parrot"
        assert c.remaining_keys["animal_type"] == "Bird"
        assert c.time_modified == datetime(1941, 12, 7, 7, 48, 0)
        assert c.time_created == datetime(1776, 7, 4, 13, 2, 3)

    def test_eq(self):
        c1 = Card(name="Hep Cat")
        c2 = Card(name="Hep Cat", notes="Cat has hepatitus.")
        assert c1 == c2

    def test_identical_to(self):
        c1 = Card(name="Hep Cat")
        c2 = Card(name="Hep Cat", notes="Cat has hepatitus.")
        assert not c1.is_identical_to(c2)

    def test_im_not_crazy_with_dicts(self):
        c = Card(name="Hep Cat")
        d1 = {"ref1" : c}
        d2 = {"ref2" : c}
        assert id(d1["ref1"]) == id(d2["ref2"]) == id(c)

    def test_to_setfile_strs(self):
        c = Card(**_parrot_args)
        assert c.to_setfile_strs() == _parrot_setfile_strs

    def test_to_setfile(self):
        parrot = Card(**_parrot_args)
        cat = Card(**_hepcat_args)
        with open(_testdir / "cards", "wt") as ofile:
            parrot.to_setfile(ofile)
            cat.to_setfile(ofile)
        with open(_testdir / "cards", "rt") as ifile:
            cpos = 0
            for parrot_str in _parrot_setfile_strs:
                line = next(ifile)
                cpos += len(line)
                assert line == f"{parrot_str}\n"
            assert cpos == 164
            for cat_str in _hepcat_setfile_strs:
                line = next(ifile)
                assert line == f"{cat_str}\n"

    def test_restore_filepos(self):
        from mseutils.card import _restore_file_pos

        with open(_testdir / "indented_blocks", "rt") as ifile:
            assert ifile.tell() == 0
            with _restore_file_pos(ifile) as ifile:
                ifile.readline()
                ifile.readline()
                assert ifile.tell() == 28
            assert ifile.tell() == 0

    def test_setfile_regex(self):
        from mseutils.card import _re_setfile_scanner

        m = _re_setfile_scanner.match("card:")
        assert m is not None
        m_dict = m.groupdict()
        assert m_dict["indent"] == ""
        assert m_dict["group_tag"] == "card"
        assert m_dict["key_tag"] == None
        assert m_dict["value"] == None
        m = _re_setfile_scanner.match("	food: Eats shoots and leaves")
        assert m is not None
        m_dict = m.groupdict()
        assert m_dict["indent"] == "	"
        assert m_dict["group_tag"] == None
        assert m_dict["key_tag"] == "food"
        assert m_dict["value"] == "Eats shoots and leaves"

    def test_collect_indented_block(self):
        from mseutils.card import _collect_indented_block

        data2 = (
            "card",
            {
                "has_styling": "false",
            },
        )
        with open(_testdir / "indented_blocks", "rt", encoding="utf-8-sig") as ifile:
            data = _collect_indented_block(ifile)
            assert data == _indented_card_1
            data = _collect_indented_block(ifile)
            assert data == data2

    def test_collect_first_key_unindented(self):
        from mseutils.card import _collect_indented_block

        with open(_testdir / "notindented_blocks", "rt", encoding="utf-8-sig") as ifile:
            data = _collect_indented_block(ifile)
            assert data == ("set_key", "something")
            data = _collect_indented_block(ifile)
            assert data == _indented_card_1

    def test_collect_all_blocks(self):
        from mseutils.card import _collect_all_indented_blocks

        data2 = (
            "card",
            {
                "has_styling": "false",
            },
        )
        with open(_testdir / "indented_blocks", "rt", encoding="utf-8-sig") as ifile:
            data = [d for d in _collect_all_indented_blocks(ifile)]
            assert len(data) == 2
            assert data[0] == _indented_card_1
            assert data[1] == data2

    def test_rules_text_special_case(self):
        from mseutils.card import _collect_all_indented_blocks

        with open(_testdir / "notindented_blocks", "rt", encoding="utf-8-sig") as ifile:
            data = [d for d in _collect_all_indented_blocks(ifile)]
            l = data[3][1]["rule text"]
            assert len(l) == 3
            assert l[-1] == "At the beginning of your end step, if you control less than three Spirits, create a 1/1 white and black Spirit creature token with <kw-a><nospellcheck>flying</nospellcheck></kw-a>.\n"


    def test_adapt_indented_block(self):
        from mseutils.card import _collect_indented_block, _cardify_incoming_types

        card_args = {
            "has_styling": "false",
            "notes": "",
            "time_created": "2025-03-19 17:00:13",
            "poop": {"nugget": "true"},
            "time_modified": "2025-03-19 17:00:13",
            "name": "American Crow",
            "sciencename": "Corvus brachyrhynchos",
            "animal_type": "Bird",
            "mass_g": "450",
            "art": "",
        }
        data1 = ("American Crow", Card(**card_args))
        with open(_testdir / "indented_blocks", "rt", encoding="utf-8-sig") as ifile:
            data = _collect_indented_block(ifile, adaptation_func=_cardify_incoming_types)
            assert data == data1

    def test_from_setfile(self):
        with open(_testdir / "cardfile_valid", "rt") as ifile:
            parrot = Card.from_setfile(ifile)
            assert parrot.to_setfile_strs() == _parrot_setfile_strs
            cat = Card.from_setfile(ifile)
            assert cat.to_setfile_strs() == _hepcat_setfile_strs


class TestSet:
    def test_from_setfile(self):
        s = None
        with open(_testdir / "setfile_valid", "rt", encoding="utf-8-sig") as ifile:
            s = Set.from_setfile(ifile)
        assert s is not None
        assert len(s.cards) == 7
        assert s.all_data["game"] == "Thistledown"
        assert s.all_data["version_control"] == {"type" : "none"}
        assert s.all_data["apprentice_code"] == ""

    def test_round_trip(self):
        import filecmp
        s = None
        with open(_testdir / "setfile_valid", "rt", encoding="utf-8-sig") as ifile:
            s = Set.from_setfile(ifile)
        with open(_testdir / "setfile_out", "wt", encoding="utf-8-sig", newline='\n') as ofile:
            s.to_setfile(ofile)
        assert filecmp.cmp(_testdir / "setfile_valid", _testdir / "setfile_out", shallow=False)

    def test_really_thorny_round_trip(self):
        import filecmp
        s = None
        with open(_testdir / "complicatedsetfile", "rt", encoding="utf-8-sig") as ifile:
            s = Set.from_setfile(ifile)
        with open(_testdir / "complicatedsetfile_out", "wt", encoding="utf-8-sig", newline='\n') as ofile:
            s.to_setfile(ofile)
        assert filecmp.cmp(_testdir / "complicatedsetfile", _testdir / "complicatedsetfile_out", shallow=False)