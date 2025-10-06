from __future__ import annotations

from pathlib import Path

from backend.database import SessionLocal
from backend.database.models import ResidentialComplex
from backend.core.excel_importer import (
    import_chess_from_excel,
    import_price_from_excel,
    import_contract_registry_from_excel,
)

BASE_DIR = Path('static') / 'Жилые_Комплексы'


def slugify(name: str) -> str | None:
    slug = ''.join(ch.lower() if ch.isalnum() else '-' for ch in name)
    slug = '-'.join(filter(None, slug.split('-')))
    return slug or None


def main() -> None:
    if not BASE_DIR.exists():
        raise SystemExit(f"Base directory '{BASE_DIR}' not found")

    session = SessionLocal()
    try:
        for complex_dir in sorted(p for p in BASE_DIR.iterdir() if p.is_dir()):
            name = complex_dir.name
            complex_obj = (
                session.query(ResidentialComplex)
                .filter(ResidentialComplex.name == name)
                .first()
            )
            if complex_obj:
                complex_obj.slug = slugify(name)
            else:
                complex_obj = ResidentialComplex(name=name, slug=slugify(name))
                session.add(complex_obj)
                session.flush()

            summary: dict[str, int] = {}

            chess_path = complex_dir / 'jk_data.xlsx'
            if chess_path.exists():
                summary['apartments'] = import_chess_from_excel(session, complex_obj, str(chess_path))

            price_path = complex_dir / 'price_shaxamtka.xlsx'
            if price_path.exists():
                summary['prices'] = import_price_from_excel(session, complex_obj, str(price_path))

            registry_path = complex_dir / 'contract_registry.xlsx'
            if registry_path.exists():
                summary['contracts'] = import_contract_registry_from_excel(session, complex_obj, str(registry_path))

            session.commit()
            print(f"Imported {name}: {summary}")
    finally:
        session.close()


if __name__ == '__main__':
    main()
