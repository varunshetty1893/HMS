"""Generate one dedicated illustration per Spice Hub menu item.

Usage (from repo root):
    python scripts/dish_art/build.py

Reads the canonical catalog from Alembic migration 0011 and writes
`customer-web/public/dishes/<ITEM_CODE>.svg`.  The build FAILS if

  * a catalog item has no artwork spec,
  * a spec points at a code that is not in the catalog, or
  * two items would end up with identical artwork

so a "Coca-Cola shows a Sprite picture" style mistake cannot slip in again.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import food_a as A  # noqa: E402
import food_b as B  # noqa: E402
from prims import rng_for, wrap_svg  # noqa: E402

ROOT = HERE.parent.parent
OUT = ROOT / "customer-web" / "public" / "dishes"
MIGRATION = ROOT / "backend" / "alembic" / "versions" / "20261018_1700_0011_spice_hub_shortlisted_menu.py"

# Soft backgrounds per family (centre colour, edge colour)
WARM = ("#fff4e0", "#f6dcb8")
GREEN = ("#f1f7e4", "#d9e8bd")
ROSE = ("#fff0f0", "#f8d4d4")
COOL = ("#eef6fb", "#cfe3f1")
SAND = ("#fbf3e6", "#ecd9b8")
CREAM = ("#fffaf0", "#f3e5c8")

# code -> (renderer, kwargs, background)
SPECS: dict = {
    # Breakfast
    "BF-IDL": (A.breakfast_idli, {}, GREEN),
    "BF-PD": (A.breakfast_dosa, {"kind": "plain"}, WARM),
    "BF-MD": (A.breakfast_dosa, {"kind": "masala"}, WARM),
    "BF-SD": (A.breakfast_dosa, {"kind": "set"}, SAND),
    "BF-PB": (A.breakfast_poori, {}, WARM),
    # Meals
    "LM-VM": (A.lunch_meals, {"kind": "veg"}, SAND),
    "LM-SVM": (A.lunch_meals, {"kind": "special"}, WARM),
    "LM-SIM": (A.lunch_meals, {"kind": "south"}, GREEN),
    "LM-CM": (A.lunch_meals, {"kind": "chicken"}, WARM),
    "LM-FM": (A.lunch_meals, {"kind": "fish"}, COOL),
    # Rice
    "LR-SR": (A.rice_dish, {"kind": "steamed"}, CREAM),
    "LR-JR": (A.rice_dish, {"kind": "jeera"}, SAND),
    "LR-GR": (A.rice_dish, {"kind": "ghee"}, WARM),
    "LR-VP": (A.rice_dish, {"kind": "pulao"}, GREEN),
    "LR-EFR": (A.rice_dish, {"kind": "egg", "style": "steel"}, WARM),
    # Biryani
    "BY-VB": (A.biryani, {"kind": "veg"}, GREEN),
    "BY-EB": (A.biryani, {"kind": "egg"}, WARM),
    "CB": (A.biryani, {"kind": "chicken"}, WARM),
    "BY-CDB": (A.biryani, {"kind": "dum"}, SAND),
    "BY-MB": (A.biryani, {"kind": "mutton"}, ROSE),
    # Breads
    "BR-KP": (A.breads, {"kind": "parotta"}, WARM),
    "BR-CH": (A.breads, {"kind": "chapati"}, SAND),
    "BR-TR": (A.breads, {"kind": "roti"}, SAND),
    "BR-PN": (A.breads, {"kind": "naan"}, CREAM),
    "BR-BN": (A.breads, {"kind": "butter"}, WARM),
    # Veg curries
    "VC-PBM": (A.veg_curry, {"kind": "paneer_butter"}, WARM),
    "VC-KP": (A.veg_curry, {"kind": "kadai"}, ROSE),
    "VC-DF": (A.veg_curry, {"kind": "dal"}, SAND),
    "VC-VK": (A.veg_curry, {"kind": "kurma"}, GREEN),
    "VC-CM": (A.veg_curry, {"kind": "chana"}, WARM),
    # Non-veg curries
    "NC-CC": (A.nonveg_curry, {"kind": "chicken_curry"}, WARM),
    "NC-BC": (A.nonveg_curry, {"kind": "butter_chicken"}, CREAM),
    "NC-CCN": (A.nonveg_curry, {"kind": "chettinad"}, ROSE),
    "NC-MC": (A.nonveg_curry, {"kind": "mutton"}, SAND),
    "NC-EC": (A.nonveg_curry, {"kind": "egg"}, WARM),
    # Mandi & grill
    "MD-AFM": (B.mandi, {"kind": "alfaham_mandi"}, SAND),
    "MD-BQM": (B.mandi, {"kind": "bbq_mandi"}, WARM),
    "MD-TDM": (B.mandi, {"kind": "tandoori_mandi"}, ROSE),
    "MD-AFC": (B.mandi, {"kind": "alfaham_chicken"}, CREAM),
    "MD-GC": (B.mandi, {"kind": "grilled"}, WARM),
    # Snacks - veg
    "SV-GM": (B.snack_veg, {"kind": "gobi"}, ROSE),
    "SV-P65": (B.snack_veg, {"kind": "paneer65"}, WARM),
    "SV-CP": (B.snack_veg, {"kind": "chilli_paneer"}, GREEN),
    "SV-FF": (B.snack_veg, {"kind": "fries"}, SAND),
    "SV-VM": (B.momos, {}, COOL),
    # Snacks - chicken
    "SC-C65": (B.snack_chicken, {"kind": "c65"}, ROSE),
    "SC-CC": (B.snack_chicken, {"kind": "chilli"}, WARM),
    "SC-CLL": (B.snack_chicken, {"kind": "lollipop"}, ROSE),
    "SC-CKB": (B.snack_chicken, {"kind": "kebab"}, SAND),
    "SC-CTK": (B.snack_chicken, {"kind": "tikka"}, WARM),
    # Seafood
    "SF-FF": (B.seafood, {"kind": "fish_fry"}, COOL),
    "SF-ATF": (B.seafood, {"kind": "tawa"}, SAND),
    "SF-PRF": (B.seafood, {"kind": "prawns"}, ROSE),
    "SF-FFG": (B.seafood, {"kind": "fingers"}, WARM),
    "SF-GFP": (B.seafood, {"kind": "golden"}, WARM),
    # Rolls & quick bites
    "RK-VRL": (B.roll, {"kind": "veg"}, GREEN),
    "RK-ERL": (B.roll, {"kind": "egg"}, WARM),
    "RK-CRL": (B.roll, {"kind": "chicken"}, SAND),
    "RK-CSH": (B.roll, {"kind": "shawarma"}, WARM),
    "RK-CBG": (B.roll, {"kind": "burger"}, CREAM),
    # Soups
    "SP-TOM": (B.soup, {"kind": "tomato"}, ROSE),
    "SP-CRN": (B.soup, {"kind": "corn"}, CREAM),
    "SP-VCL": (B.soup, {"kind": "veg_clear"}, GREEN),
    "SP-CCL": (B.soup, {"kind": "chicken_clear"}, SAND),
    "SP-MCW": (B.soup, {"kind": "manchow"}, WARM),
    # Fresh juice
    "BJ-LIM": (B.juice, {"kind": "lime"}, GREEN),
    "BJ-ORG": (B.juice, {"kind": "orange"}, WARM),
    "BJ-WML": (B.juice, {"kind": "watermelon"}, ROSE),
    "BJ-MSB": (B.juice, {"kind": "mosambi"}, CREAM),
    "BJ-MXF": (B.juice, {"kind": "mixed"}, ROSE),
    # Shakes & lassi
    "BM-CHK": (B.shake, {"kind": "choco"}, SAND),
    "BM-ORO": (B.shake, {"kind": "oreo"}, COOL),
    "BM-MNG": (B.shake, {"kind": "mango"}, WARM),
    "BM-COF": (B.shake, {"kind": "coffee"}, SAND),
    "BM-LSS": (B.shake, {"kind": "lassi"}, CREAM),
    # Cold & hot drinks
    "BD-SPR": (B.can_drink, {"kind": "sprite"}, GREEN),
    "BD-COL": (B.can_drink, {"kind": "cola"}, ROSE),
    "BD-THM": (B.can_drink, {"kind": "thums"}, SAND),
    "BD-TEA": (B.hot_drink, {"kind": "tea"}, WARM),
    "BD-COF": (B.hot_drink, {"kind": "coffee"}, SAND),
    # Desserts
    "DS-VAN": (B.dessert, {"kind": "vanilla"}, CREAM),
    "DS-CHO": (B.dessert, {"kind": "chocolate"}, SAND),
    "DS-BRW": (B.dessert, {"kind": "brownie"}, WARM),
    "DS-GJM": (B.dessert, {"kind": "jamun"}, WARM),
    "DS-FAL": (B.dessert, {"kind": "falooda"}, ROSE),
    # Chinese
    "CH-VFR": (A.rice_dish, {"kind": "veg", "style": "black"}, GREEN),
    "CH-EFR": (A.rice_dish, {"kind": "egg", "style": "black"}, WARM),
    "CH-CFR": (A.rice_dish, {"kind": "chicken", "style": "black"}, SAND),
    "CH-CHN": (B.chinese, {"kind": "noodles"}, WARM),
    "CH-CMD": (B.chinese, {"kind": "manchurian"}, ROSE),
}


def load_catalog():
    spec = importlib.util.spec_from_file_location("m0011_catalog", MIGRATION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.MENU_CATALOG


def main() -> int:
    catalog = load_catalog()
    names = {item[0]: item[1] for cat in catalog for item in cat["items"]}

    missing = sorted(set(names) - set(SPECS))
    unknown = sorted(set(SPECS) - set(names))
    if missing or unknown:
        print("ERROR  items without art:", missing, " specs for unknown codes:", unknown)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()

    seen: dict[str, str] = {}
    for code, (fn, kwargs, (bg_a, bg_b)) in SPECS.items():
        body = fn(code, rng_for(code), **kwargs)
        svg = wrap_svg(body, bg_a, bg_b, names[code])
        digest = hashlib.sha1(svg.encode()).hexdigest()
        if digest in seen:
            print(f"ERROR  {code} and {seen[digest]} produced identical art")
            return 1
        seen[digest] = code
        (OUT / f"{code}.svg").write_text(svg, encoding="utf-8")

    print(f"OK  wrote {len(SPECS)} dish illustrations to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
