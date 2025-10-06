from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Iterable, Optional

import fitz  # type: ignore

PLAN_CACHE_ROOT = Path("backend/static/floorplans")
PLAN_SOURCE_ROOT = Path("static/Жилые_Комплексы")


def _ensure_directory(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)


def _slugify_segment(value: str) -> str:
    """Creates a filesystem-safe slug while preserving Cyrillic characters."""
    cleaned = value.strip().lower()
    slug = re.sub(r"[^\w\-]+", "-", cleaned, flags=re.UNICODE)
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-") or "unknown"


def _normalize_apartment_size(value: str | float | int) -> str:
    text = str(value).strip()
    text = text.replace(",", ".")
    try:
        # keep two decimals for stability when rendering floats
        return f"{float(text):.2f}"
    except (TypeError, ValueError):
        return text or "unknown"


def _build_cached_path(jk_name: str, block_name: str, apartment_size: str | float | int) -> Path:
    jk_dir = PLAN_CACHE_ROOT / jk_name
    _ensure_directory(jk_dir)
    filename = f"{_slugify_segment(block_name)}__{_normalize_apartment_size(apartment_size).replace('.', '_')}.png"
    return jk_dir / filename


def _candidate_plan_files(jk_name: str, apartment_size: str | float | int) -> Iterable[Path]:
    base_dir = PLAN_SOURCE_ROOT / jk_name / "Planirovki"
    if not base_dir.exists():
        return []

    apartment_size = str(apartment_size)
    potential_files: list[Path] = []
    for ext in ("jpg", "jpeg", "png", "svg"):
        potential = base_dir / f"{apartment_size}.{ext}"
        if potential.exists():
            potential_files.append(potential)
    return potential_files


def _generate_from_pdf(
    pdf_path: Path,
    apartment_size: str | float | int,
    cache_path: Path,
) -> Optional[Path]:
    if not pdf_path.exists():
        return None

    doc = None
    try:
        doc = fitz.open(pdf_path)
        target_size = float(str(apartment_size).replace(",", "."))

        for page in doc:
            try:
                text = page.get_text() or ""
            except Exception:
                text = ""

            # direct text match first
            if str(apartment_size) in text:
                pix = page.get_pixmap()
                pix.save(cache_path)
                return cache_path

            # fallback using regex for numeric patterns with tolerance
            size_patterns = [
                r"(\d+[\.,]?\d*)\s*м²",
                r"(\d+[\.,]?\d*)\s*м2",
                r"(\d+[\.,]?\d*)\s*м",
            ]
            for pattern in size_patterns:
                for match in re.findall(pattern, text):
                    try:
                        found_size = float(str(match).replace(",", "."))
                    except ValueError:
                        continue
                    if abs(found_size - target_size) <= 0.15:
                        pix = page.get_pixmap()
                        pix.save(cache_path)
                        return cache_path
    except Exception as exc:  # noqa: BLE001
        print(f"[plan-cache] Failed to render '{pdf_path}': {exc}")
    finally:
        if doc is not None:
            doc.close()
    return None


def ensure_plan_image_cached(
    jk_name: str,
    block_name: str,
    apartment_size: str | float | int,
) -> Path:
    """
    Ensures that a plan image for the specified apartment is cached locally.

    Returns the cached file path or raises FileNotFoundError if no plan can be located.
    """
    cache_path = _build_cached_path(jk_name, block_name, apartment_size)
    if cache_path.exists():
        return cache_path

    candidate_files = list(_candidate_plan_files(jk_name, apartment_size))
    base_dir = PLAN_SOURCE_ROOT / jk_name / "Planirovki"

    # include block-based PDFs as fallbacks
    normalized_block = block_name.strip()
    normalized_variants = {
        normalized_block,
        normalized_block.replace(" ", ""),
        normalized_block.replace(" ", "_"),
        normalized_block.replace(" ", "-"),
        normalized_block.replace(",", ""),
        normalized_block.replace(".", ""),
        normalized_block.replace(",", "_"),
        normalized_block.replace(".", "_"),
    }
    if normalized_block.startswith("Блок"):
        suffix = normalized_block.split(" ", 1)[-1]
        normalized_variants.update({
            suffix,
            suffix.replace(" ", ""),
            suffix.replace(" ", "_"),
            suffix.replace(" ", "-"),
        })

    pdf_candidates = [base_dir / f"{variant}.pdf" for variant in normalized_variants]
    if base_dir.exists():
        for file in base_dir.iterdir():
            if file.suffix.lower() == ".pdf":
                pdf_candidates.append(file)

    if candidate_files:
        source_file = candidate_files[0]
        shutil.copyfile(source_file, cache_path)
        return cache_path

    for pdf_path in pdf_candidates:
        cached = _generate_from_pdf(pdf_path, apartment_size, cache_path)
        if cached:
            return cached

    raise FileNotFoundError(f"Plan not found for {jk_name}, block '{block_name}', size={apartment_size}")


def prewarm_plan_cache(
    jk_name: str,
    block_sizes: Iterable[tuple[str, str | float | int]],
) -> None:
    """Pre-populates cached plan images for the provided block/size pairs."""
    for block_name, apartment_size in block_sizes:
        if not block_name or apartment_size in (None, ""):
            continue
        try:
            ensure_plan_image_cached(jk_name, block_name, apartment_size)
        except FileNotFoundError:
            # Missing individual plans are acceptable; continue warming others.
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"[plan-cache] Warmup error for {jk_name}/{block_name}/{apartment_size}: {exc}")

