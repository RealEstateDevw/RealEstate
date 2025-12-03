"""Генератор актов выполненных работ на основе данных из реестра договоров.

Сервис подбирает шаблон Word по названию ЖК, подтягивает данные контракта
из БД и формирует готовый документ в `media/acts`. Основная точка входа —
функция `reg_act`, которую вызывает админский эндпоинт.
"""

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Final, Iterable, Optional

from docxtpl import DocxTemplate
from num2words import num2words
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.database.models import ContractRegistryEntry, ResidentialComplex

BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR: Final[Path] = BASE_DIR / "static" / "acts"
OUTPUT_DIR: Final[Path] = Path("media") / "acts"


def _format_decimal(value: float) -> str:
    """Return formatted value with spaces as thousand separators."""
    return f"{value:,}".replace(",", " ")


def _normalize_key(value: str) -> str:
    """Convert identifier to a normalized lookup key."""
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _build_alias_map() -> Dict[str, str]:
    """Map various ЖК aliases to their canonical DB names."""
    aliases: Dict[str, list[str]] = {
        "ЖК_Бахор": [
            "ЖК_Бахор",
            "ЖК-Бахор",
            "ЖК Бахор",
            "Бахор",
            "baxor",
            "zhk-baxor",
            "zhk_baxor",
        ],
        "ЖК_Рассвет": [
            "ЖК_Рассвет",
            "ЖК-Рассвет",
            "ЖК Рассвет",
            "Рассвет",
            "rassvet",
            "zhk-rassvet",
            "zhk_rassvet",
        ],
    }
    alias_map: Dict[str, str] = {}
    for canonical, items in aliases.items():
        for item in items:
            alias_map[_normalize_key(item)] = canonical
    return alias_map


JK_ALIAS_MAP: Final[Dict[str, str]] = _build_alias_map()


def _resolve_complex(session: Session, jk_name: str) -> Optional[ResidentialComplex]:
    """Resolve ЖК by alias, slug, or display name."""
    normalized = _normalize_key(jk_name)
    canonical_name = JK_ALIAS_MAP.get(normalized)

    if canonical_name:
        complex_obj = (
            session.query(ResidentialComplex)
            .filter(ResidentialComplex.name == canonical_name)
            .first()
        )
        if complex_obj:
            return complex_obj

    lower_value = jk_name.lower()
    complex_obj = (
        session.query(ResidentialComplex)
        .filter(ResidentialComplex.name.ilike(lower_value))
        .first()
    )
    if complex_obj:
        return complex_obj

    complex_obj = (
        session.query(ResidentialComplex)
        .filter(ResidentialComplex.slug.ilike(lower_value))
        .first()
    )
    if complex_obj:
        return complex_obj

    for candidate in session.query(ResidentialComplex).all():
        if _normalize_key(candidate.name or "") == normalized:
            return candidate
        if candidate.slug and _normalize_key(candidate.slug) == normalized:
            return candidate

    return None


def _resolve_template_candidates(jk_name: str, complex_obj: Optional[ResidentialComplex]) -> Iterable[str]:
    """Prepare ordered template suffixes to probe."""
    candidates = [jk_name]
    if complex_obj:
        candidates.extend(
            filter(
                None,
                [
                    complex_obj.slug,
                    complex_obj.name,
                    _normalize_key(complex_obj.name or ""),
                    _normalize_key(complex_obj.slug or ""),
                ],
            )
        )
    # dict.fromkeys preserves order while removing duplicates
    return dict.fromkeys(candidates).keys()


def _resolve_template_path(jk_name: str, complex_obj: Optional[ResidentialComplex]) -> Path:
    """Pick the first existing template matching provided identifiers."""
    for candidate in _resolve_template_candidates(jk_name, complex_obj):
        template_path = TEMPLATES_DIR / f"act_{candidate}.docx"
        if template_path.exists():
            return template_path

    raise FileNotFoundError(
        f"Шаблон Word для `{jk_name}` не найден. Проверьте наличие файла `act_{jk_name}.docx` в каталоге `{TEMPLATES_DIR}`."
    )


def _fetch_contract(session: Session, complex_id: int, contract_id: str) -> Optional[ContractRegistryEntry]:
    """Load a contract registry entry scoped to the resolved ЖК."""
    return (
        session.query(ContractRegistryEntry)
        .filter(ContractRegistryEntry.complex_id == complex_id)
        .filter(ContractRegistryEntry.contract_number == contract_id)
        .first()
    )


def _build_base_data(entry: ContractRegistryEntry) -> Dict[str, Any]:
    """Prepare base context matching legacy column names used in templates."""
    contract_date_value = (
        entry.contract_date.strftime("%Y-%m-%d") if entry.contract_date else ""
    )
    data: Dict[str, Any] = {
        "№ Договора": entry.contract_number,
        "Дата Договора": contract_date_value,
        "Блок": entry.block_name,
        "Этаж": entry.floor,
        "№ КВ": entry.apartment_number,
        "Кол-во ком": entry.rooms,
        "Квадратура Квартиры": entry.area_sqm,
        "Общ Стоимость Договора": entry.total_price or 0,
        "Стоимость 1 кв.м": entry.price_per_sqm,
        "Процент 1 Взноса": entry.down_payment_percent or 0,
        "Сумма 1 Взноса": entry.down_payment_amount or 0,
        "Ф/И/О": entry.buyer_full_name,
        "Серия Паспорта": entry.buyer_passport_series,
        "ПИНФЛ": entry.buyer_pinfl,
        "Кем выдан": entry.issued_by,
        "Адрес прописки": entry.registration_address,
        "Номер тел": entry.phone_number,
        "Отдел Продаж": entry.sales_department,
    }

    if entry.extra_data and isinstance(entry.extra_data, dict):
        data.update(entry.extra_data)

    return data


def _safe_filename_component(value: str, fallback: str = "act") -> str:
    """Sanitize user-provided input for safe file names."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned or fallback


def reg_act(jk_name: str, contract_id: str, act_number: str, date_act: date) -> Path:
    """
    Generate an act document for the given contract and return the path to the generated file.

    Raises:
        FileNotFoundError: when the Word template is missing.
        ValueError: when the contract or ЖК cannot be found.
    """
    with SessionLocal() as session:
        complex_obj = _resolve_complex(session, jk_name)
        if not complex_obj:
            raise ValueError(f"ЖК `{jk_name}` не найден в системе.")

        template_path = _resolve_template_path(jk_name, complex_obj)
        entry = _fetch_contract(session, complex_obj.id, contract_id)

    if not entry:
        raise ValueError(f"Договор с номером `{contract_id}` не найден в ЖК `{jk_name}`.")

    data = _build_base_data(entry)
    total_cost_value = float(data["Общ Стоимость Договора"] or 0)
    pv_sum_value = float(data["Сумма 1 Взноса"] or 0)
    payment_amount = round(total_cost_value * 0.03)

    contract_date_raw = data.get("Дата Договора")
    contract_date_formatted = ""
    if contract_date_raw:
        try:
            contract_date_formatted = datetime.strptime(contract_date_raw, "%Y-%m-%d").strftime("%d-%m-%Y")
        except ValueError:
            contract_date_formatted = contract_date_raw

    data.update(
        {
            "act_number": act_number,
            "date_act": date_act.strftime("%d-%m-%Y"),
            "contract_number": data["№ Договора"],
            "contract_date": contract_date_formatted,
            "fio": data.get("Ф/И/О", ""),
            "total_cost": _format_decimal(total_cost_value),
            "total_cost_in_words": num2words(int(round(total_cost_value)), lang="ru"),
            "pv_percent": data.get("Процент 1 Взноса", 0),
            "pv_sum": _format_decimal(pv_sum_value),
            "pv_sum_in_words": num2words(int(round(pv_sum_value)), lang="ru"),
            "payment_amount": _format_decimal(payment_amount),
            "payment_amount_in_words": num2words(payment_amount, lang="ru"),
        }
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_suffix = _safe_filename_component(act_number)
    output_path = OUTPUT_DIR / f"act_{safe_suffix}.docx"

    doc = DocxTemplate(template_path)
    doc.render(data)
    doc.save(output_path)

    return output_path.resolve()
