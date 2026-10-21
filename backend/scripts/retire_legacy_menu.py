"""Retire every menu item that is NOT part of the Spice Hub catalog (migration 0011).

Why: older seeds / experiments left ~80 extra dishes (e.g. "pork biriyani", "Boiled Eggs (2 pcs)")
next to the 90 real dishes. This script removes them safely.

What it does to each legacy item
  * never ordered      -> deleted completely (item + its price variants)
  * has order history  -> ARCHIVED (is_active = false, is_available = false) so old bills and
                          reports keep working; archived items no longer show to customers/admin.
Legacy categories left with no dishes are deleted (or deactivated if archived dishes remain).

It is a DRY RUN by default. Nothing is changed unless you pass --apply.

Usage (from backend/, with the virtualenv active and DATABASE_URL pointing at the target DB):
    python scripts/retire_legacy_menu.py                      # preview only
    python scripts/retire_legacy_menu.py --apply              # really do it
    python scripts/retire_legacy_menu.py --apply --keep PB,M081   # keep specific item codes
    python scripts/retire_legacy_menu.py --apply --restore-catalog   # also mark all 90 catalog
                                                                     # dishes active + in stock
"""

# ruff: noqa: E402, E501

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.menu import MenuCategory, MenuItem, MenuPriceVariant
from app.models.orders import OrderItem

_MIGRATION = (
    backend_dir / "alembic" / "versions" / "20261018_1700_0011_spice_hub_shortlisted_menu.py"
)


def load_catalog() -> list[dict]:
    spec = importlib.util.spec_from_file_location("m0011_catalog", _MIGRATION)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load {_MIGRATION}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.MENU_CATALOG


async def run(apply: bool, keep: set[str], restore_catalog: bool) -> int:
    catalog = load_catalog()
    keep_codes = {item[0].upper() for cat in catalog for item in cat["items"]} | keep
    keep_categories = {cat["category"].strip().lower() for cat in catalog}

    settings = get_settings()
    target = (
        settings.database_url.split("@")[-1]
        if "@" in settings.database_url
        else settings.database_url
    )
    print(f"Database target : {target}")
    print(
        f"Mode            : {'APPLY (changes will be committed)' if apply else 'DRY RUN (no changes)'}"
    )
    print(
        f"Keeping         : {len(keep_codes)} item codes (90 catalog dishes{' + ' + ', '.join(sorted(keep)) if keep else ''})\n"
    )

    engine = create_async_engine(settings.database_url, echo=False)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async with maker() as session:
        async with session.begin():
            items = list((await session.execute(select(MenuItem))).scalars().all())
            legacy = [i for i in items if i.item_code.strip().upper() not in keep_codes]

            ordered_ids = set(
                (await session.execute(select(OrderItem.menu_item_id).distinct())).scalars().all()
            )

            to_delete = [i for i in legacy if i.id not in ordered_ids]
            to_archive = [
                i for i in legacy if i.id in ordered_ids and (i.is_active or i.is_available)
            ]
            already = [
                i for i in legacy if i.id in ordered_ids and not (i.is_active or i.is_available)
            ]

            print(f"Total items in database : {len(items)}")
            print(f"Catalog items kept      : {len(items) - len(legacy)}")
            print(f"Legacy items found      : {len(legacy)}")
            print(f"  -> delete (never ordered)        : {len(to_delete)}")
            print(f"  -> archive (has order history)   : {len(to_archive)}")
            print(f"  -> already archived              : {len(already)}\n")

            catalog_codes = keep_codes - keep
            catalog_items = [i for i in items if i.item_code.strip().upper() in catalog_codes]
            unavailable = [i for i in catalog_items if not (i.is_active and i.is_available)]
            print(f"Catalog dishes present  : {len(catalog_items)} of 90")
            print(f"Catalog dishes sold out / inactive : {len(unavailable)}")
            if unavailable and not restore_catalog:
                print("  (re-run with --restore-catalog to mark them active and in stock)")
            print()

            for label, group in (("DELETE", to_delete), ("ARCHIVE", to_archive)):
                for i in sorted(group, key=lambda x: x.item_code):
                    print(f"  [{label}] {i.item_code:<10} {i.name}")

            if apply:
                if to_delete:
                    ids = [i.id for i in to_delete]
                    await session.execute(
                        delete(MenuPriceVariant).where(MenuPriceVariant.menu_item_id.in_(ids))
                    )
                    await session.execute(delete(MenuItem).where(MenuItem.id.in_(ids)))
                for i in to_archive:
                    i.is_active = False
                    i.is_available = False
                    variants = (
                        (
                            await session.execute(
                                select(MenuPriceVariant).where(
                                    MenuPriceVariant.menu_item_id == i.id
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    for v in variants:
                        v.is_active = False
                        v.is_available = False
                if restore_catalog:
                    for i in catalog_items:
                        i.is_active = True
                        i.is_available = True
                    cat_ids = [i.id for i in catalog_items]
                    for v in (
                        (
                            await session.execute(
                                select(MenuPriceVariant).where(
                                    MenuPriceVariant.menu_item_id.in_(cat_ids)
                                )
                            )
                        )
                        .scalars()
                        .all()
                    ):
                        v.is_active = True
                        v.is_available = True
                    for c in (
                        (
                            await session.execute(
                                select(MenuCategory).where(
                                    func.lower(MenuCategory.name).in_(keep_categories)
                                )
                            )
                        )
                        .scalars()
                        .all()
                    ):
                        c.is_active = True
                    print(
                        f"Restored {len(catalog_items)} catalog dishes (+ their portions and categories) to active / in stock."
                    )
                await session.flush()

            # ---- legacy categories -------------------------------------------------------
            cats = list((await session.execute(select(MenuCategory))).scalars().all())
            print("\nLegacy categories:")
            changed_cats = 0
            for cat in cats:
                if cat.name.strip().lower() in keep_categories:
                    continue
                remaining = (
                    await session.execute(
                        select(func.count())
                        .select_from(MenuItem)
                        .where(MenuItem.category_id == cat.id)
                    )
                ).scalar_one()
                if not apply:  # the real deletes have not run yet - account for them
                    remaining -= sum(1 for i in to_delete if i.category_id == cat.id)
                if remaining == 0:
                    print(f"  [DELETE]  {cat.name}  (empty)")
                    if apply:
                        await session.delete(cat)
                    changed_cats += 1
                elif cat.is_active:
                    print(f"  [HIDE]    {cat.name}  ({remaining} archived/kept dishes remain)")
                    if apply:
                        cat.is_active = False
                    changed_cats += 1
            if changed_cats == 0:
                print("  none")

            if not apply:
                print(
                    "\nDRY RUN finished - nothing was changed. Re-run with --apply to perform this."
                )
                await session.rollback()
            else:
                print("\nDone. Changes committed.")

    await engine.dispose()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Retire legacy (non-catalog) menu items safely.")
    parser.add_argument(
        "--apply", action="store_true", help="Actually change the database (default: dry run)."
    )
    parser.add_argument(
        "--restore-catalog",
        action="store_true",
        help="Also mark all catalog dishes, portions and categories active and in stock.",
    )
    parser.add_argument(
        "--keep", default="", help="Comma-separated item codes to keep, e.g. PB,M081."
    )
    args = parser.parse_args()
    keep = {c.strip().upper() for c in args.keep.split(",") if c.strip()}
    raise SystemExit(asyncio.run(run(args.apply, keep, args.restore_catalog)))


if __name__ == "__main__":
    main()
