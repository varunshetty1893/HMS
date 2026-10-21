"""Menu content integrity: every dish has its own description and its own picture.

Guards against the bug where Coca-Cola showed a Sprite photo and every dish said
"Freshly prepared <name>." (the seed's image map used item codes that did not exist).
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent
VERSIONS = BACKEND_DIR / "alembic" / "versions"
DISHES_DIR = REPO_DIR / "customer-web" / "public" / "dishes"


def _load(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, VERSIONS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_catalog_mod = _load("20261018_1700_0011_spice_hub_shortlisted_menu.py", "m0011_for_test")
_desc_mod = _load("20261020_1000_0014_menu_item_descriptions_and_images.py", "m0014_for_test")

CATALOG = _catalog_mod.MENU_CATALOG
DESCRIPTIONS: dict[str, str] = _desc_mod.ITEM_DESCRIPTIONS
# (code, name, dietary_type)
ITEMS = [(i[0], i[1], i[3]) for cat in CATALOG for i in cat["items"]]
CODES = {code for code, _, _ in ITEMS}


def test_catalog_still_has_90_unique_item_codes() -> None:
    assert len(ITEMS) == 90
    assert len(CODES) == 90


def test_every_item_has_exactly_one_description_and_no_extras() -> None:
    assert set(DESCRIPTIONS) == CODES


def test_descriptions_are_specific_not_placeholders() -> None:
    for code, text in DESCRIPTIONS.items():
        assert not text.lower().startswith("freshly prepared"), code
        assert 20 <= len(text) <= 110, f"{code}: description length {len(text)}"
        assert text.endswith((".", ")")), f"{code}: should end with a full stop"


def test_descriptions_are_unique() -> None:
    seen: dict[str, str] = {}
    for code, text in DESCRIPTIONS.items():
        assert text not in seen, f"{code} repeats the description of {seen[text]}"
        seen[text] = code


def test_veg_dishes_never_mention_meat_fish_or_egg() -> None:
    forbidden = re.compile(r"\b(chicken|mutton|fish|prawns?|egg|eggs|meat|anjal)\b", re.I)
    for code, _name, dietary in ITEMS:
        if dietary == "VEG":
            assert not forbidden.search(DESCRIPTIONS[code]), f"{code}: {DESCRIPTIONS[code]}"


def test_soft_drinks_describe_themselves_not_each_other() -> None:
    assert "Coca-Cola" in DESCRIPTIONS["BD-COL"]
    assert "Sprite" not in DESCRIPTIONS["BD-COL"]
    assert "Sprite" in DESCRIPTIONS["BD-SPR"]
    assert "Thums Up" in DESCRIPTIONS["BD-THM"]
    assert "Coca-Cola" not in DESCRIPTIONS["BD-THM"]
    assert "tea" in DESCRIPTIONS["BD-TEA"].lower()
    assert "coffee" in DESCRIPTIONS["BD-COF"].lower()


def test_dish_name_appears_in_its_own_description_when_it_is_a_brand_or_drink() -> None:
    for code in ("BD-SPR", "BD-COL", "BD-THM"):
        name = next(n for c, n, _ in ITEMS if c == code)
        assert name.lower() in DESCRIPTIONS[code].lower()


def test_every_item_has_its_own_illustration() -> None:
    files = {p.stem for p in DISHES_DIR.glob("*.svg")}
    assert files == CODES, f"missing={sorted(CODES - files)} extra={sorted(files - CODES)}"


def test_no_two_items_share_the_same_illustration() -> None:
    seen: dict[str, str] = {}
    for path in sorted(DISHES_DIR.glob("*.svg")):
        digest = hashlib.sha1(path.read_bytes()).hexdigest()
        assert digest not in seen, f"{path.stem} is identical to {seen[digest]}"
        seen[digest] = path.stem


def test_illustration_title_matches_the_item_name() -> None:
    for code, name, _ in ITEMS:
        svg = (DISHES_DIR / f"{code}.svg").read_text(encoding="utf-8")
        assert f"<title>{name}</title>" in svg, f"{code}: artwork is not labelled '{name}'"
