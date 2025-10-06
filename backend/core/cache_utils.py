from __future__ import annotations

from typing import Iterable, Sequence

from fastapi_cache import FastAPICache

from backend.core.google_sheets import get_price_data_for_sheet_all, get_shaxmatka_data
from backend.core.plan_cache import prewarm_plan_cache
from backend.database import SessionLocal
from backend.database.models import ApartmentUnit, ResidentialComplex

DEFAULT_COMPLEX_CACHE_NAMESPACES: Sequence[str] = (
    "complexes:list",
    "complexes:jk",
    "complexes:blocks",
    "complexes:apartment-info",
    "complexes:price-by-key",
    "complexes:price-all",
    "complexes:price-all-full",
    "complexes:shaxmatka",
    "complexes:aggregate",
    "complexes:plan-image",
    "complexes:floor-plan",
    "shaxmatka",
)


async def invalidate_complex_cache(namespaces: Iterable[str] | None = None) -> None:
    """Safely clears FastAPI cache namespaces used for complex data."""
    targets = list(namespaces) if namespaces is not None else list(DEFAULT_COMPLEX_CACHE_NAMESPACES)

    if not targets:
        return

    for namespace in targets:
        try:
            await FastAPICache.clear(namespace=namespace)
        except Exception as exc:  # noqa: BLE001 - best effort cache bust
            print(f"[cache] Failed to clear namespace '{namespace}': {exc}")


async def warmup_complex_caches() -> None:
    """Loads shaxmatka, price data, and plan previews into cache for all complexes."""
    session = SessionLocal()
    try:
        complexes = session.query(ResidentialComplex).all()
        if not complexes:
            return

        for complex_obj in complexes:
            jk_name = complex_obj.name
            try:
                await get_shaxmatka_data(jk_name)
            except Exception as exc:  # noqa: BLE001
                print(f"[cache] Failed shaxmatka warmup for {jk_name}: {exc}")

            try:
                await get_price_data_for_sheet_all(jk_name)
            except Exception as exc:  # noqa: BLE001
                print(f"[cache] Failed price warmup for {jk_name}: {exc}")

            # Pre-cache plan images for unique block/size combinations.
            units = (
                session.query(ApartmentUnit.block_name, ApartmentUnit.area_sqm)
                .filter(ApartmentUnit.complex_id == complex_obj.id)
                .all()
            )
            unique_pairs = {
                (block_name or "", f"{area:.2f}")
                for block_name, area in units
                if block_name and area is not None
            }
            if unique_pairs:
                prewarm_plan_cache(jk_name, unique_pairs)
    finally:
        session.close()
