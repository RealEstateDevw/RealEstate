import os
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.core.google_sheets import get_price_data_for_sheet
from backend.api.complexes.main import extract_price_value
from backend.database import get_db
from backend.database.models import ResidentialComplex

router = APIRouter(prefix="/api/payment-options")

def format_number(num):
    """Форматирует число с пробелами для разделения тысяч"""
    if num is None or num == 0:
        return "0"
    return f"{int(num):,}".replace(",", " ")

async def load_payment_options_for_complex(complex_name: str, floor: str = "5", db: Session = None) -> Dict[str, Any]:
    """
    Загружает данные о способах оплаты для конкретного комплекса из тех же Excel файлов, что и цены
    """
    try:
        # Получаем цены из тех же файлов, что и в apartment-info
        price_keys = {
            "100": f"{complex_name}_5_100",
            "70": f"{complex_name}_5_70",
            "50": f"{complex_name}_5_50",
            "30": f"{complex_name}_5_30"
        }


        prices = {}
        for suffix, key in price_keys.items():
            price_data = await get_price_data_for_sheet(key)
            prices[suffix] = extract_price_value(price_data, key)

        if any(price is None for price in prices.values()):
            raise HTTPException(status_code=404, detail="Не найдены цены для некоторых вариантов оплаты")

        # Берем цену за 30% как базовую для расчетов
        base_price = prices["30"]

        # Вычисляем оставшиеся месяцы (как в apartment-info)
        from datetime import datetime
        from dateutil.relativedelta import relativedelta

        # Получаем настройки рассрочки из базы данных
        if db:
            complex_record = (
                db.query(ResidentialComplex)
                .filter(ResidentialComplex.name == complex_name)
                .first()
            )

            if complex_record and complex_record.installment_start_date:
                start_date = datetime.combine(complex_record.installment_start_date, datetime.min.time())
                installment_months = complex_record.installment_months
            else:
                # Значения по умолчанию
                start_date = datetime(2025, 12, 1)
                installment_months = 36
        else:
            # Если db не передана, используем значения по умолчанию
            start_date = datetime(2025, 12, 1)
            installment_months = 36

        end_date = start_date + relativedelta(months=installment_months)

        # Текущая дата
        today = datetime.today()
        diff_years = end_date.year - today.year
        diff_months = end_date.month - today.month
        total_months_left = diff_years * 12 + diff_months
        if today.day > 1:
            total_months_left -= 1
        total_months_left = max(total_months_left, 0)

        # Примерная площадь квартиры для расчетов (65 м²)
        if complex_name == "ЖК_Бахор":
            example_area = 55.67
        else:
            example_area = 65.38
        example_total_price = base_price * example_area

        # Рассрочка 30%
        installment_30_initial = example_total_price * 0.3
        installment_30_monthly = (example_total_price - installment_30_initial) / installment_months

        # Рассрочка 50%
        installment_50_initial = example_total_price * 0.5
        installment_50_monthly = (example_total_price - installment_50_initial) / installment_months

        # Рассрочка 70%
        installment_70_initial = example_total_price * 0.7
        installment_70_monthly = (example_total_price - installment_70_initial) / installment_months

        # Гибридная рассрочка
        hybrid_initial = example_total_price * 0.3
        hybrid_final = example_total_price * 0.3
        hybrid_middle = example_total_price - hybrid_initial - hybrid_final
        hybrid_monthly = hybrid_middle / 18  # 18 месяцев для гибридной

        # Ипотека
        mortgage_initial = example_total_price * 0.2
        mortgage_amount = example_total_price - mortgage_initial
        mortgage_monthly = mortgage_amount * 0.01  # Примерная ставка

        return {
            "descriptions": {
                "installment": f"До {installment_months} месяцев",
                "hybrid": "С отложенным платежом до 30%",
                "mortgage": "В удобный момент без потерь"
            },
            "details": {
                "installment": {
                    "title": "Рассрочка — удобно и без переплат.",
                    "lines": [
                        "<strong>Варианты:</strong> 70%, 50% или 30%",
                        f"<strong>Первоначальный взнос</strong> — от {format_number(installment_30_initial)} сум",
                        f"<strong>Ежемесячная оплата</strong> — от {format_number(installment_30_monthly)} сум ({installment_months} месяцев, без переплат)"
                    ]
                },
                "hybrid": {
                    "title": "Ваш комфорт в приоритете:",
                    "lines": [
                        f"<strong>Первоначальный взнос</strong> — {format_number(hybrid_initial)} сум",
                        f"<strong>Ежемесячный платёж</strong> — {format_number(hybrid_monthly)} сум",
                        "<strong>До 30% суммы</strong> можно отложить на удобный момент"
                    ]
                },
                "mortgage": {
                    "title": "30% оплачиваются при сдаче объекта.",
                    "lines": [
                        f"<strong>Стоимость квартиры</strong> — от {format_number(example_total_price)} сум",
                        f"<strong>Сумма ипотеки</strong> — от {format_number(mortgage_amount)} сум",
                        "Если к этому моменту будет удобнее — вы сможете оформить ипотеку и рассчитаться комфортно, без лишних забот."
                    ]
                }
            },
            "modals": {
                "installment": f"<h3>Пример рассрочки</h3><p><strong>Стоимость квартиры:</strong> {format_number(example_total_price)} сум</p><p><strong>Первоначальный взнос:</strong> {format_number(installment_30_initial)} сум (30%)</p><p><strong>Ежемесячный платеж:</strong> {format_number(installment_30_monthly)} сум</p><p><strong>Срок рассрочки:</strong> {installment_months} месяцев</p><p><strong>Переплата:</strong> 0 сум</p>",
                "hybrid": f"<h3>Пример гибридной рассрочки</h3><p><strong>Стоимость квартиры:</strong> {format_number(example_total_price)} сум</p><p><strong>Первоначальный взнос (30%):</strong> {format_number(hybrid_initial)} сум</p><p><strong>Ежемесячная оплата (18 мес., 40%):</strong> {format_number(hybrid_monthly)} сум</p><p><strong>Последний платёж (19-й месяц, 30%):</strong> {format_number(hybrid_final)} сум</p>",
                "mortgage": f"<h3>Переход на ипотеку</h3><p><strong>Стоимость квартиры:</strong> {format_number(example_total_price)} сум</p><p><strong>Первоначальный взнос:</strong> {format_number(mortgage_initial)} сум (20%)</p><p><strong>Сумма ипотеки:</strong> {format_number(mortgage_amount)} сум</p><p><strong>Ставка:</strong> от 18% годовых</p><p><strong>Срок:</strong> до 20 лет</p><p><strong>Ежемесячный платеж:</strong> от {format_number(mortgage_monthly)} сум</p>"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки данных: {str(e)}")

@router.get("/")
async def get_payment_options(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Возвращает данные о способах оплаты для всех комплексов из Excel файлов
    """
    result = {}

    # Список комплексов для обработки
    complexes = ["ЖК_Рассвет", "ЖК_Бахор"]

    for complex_name in complexes:
        try:
            result[complex_name] = await load_payment_options_for_complex(complex_name, db=db)
        except HTTPException as e:
            # Если данные не найдены, пропускаем этот комплекс
            if e.status_code == 404:
                continue
            raise e
        except Exception as e:
            # Логируем ошибку, но продолжаем обработку других комплексов
            print(f"Ошибка загрузки данных для {complex_name}: {e}")
            continue

    return result

@router.get("/{complex_name}")
async def get_payment_options_for_complex_endpoint(
    complex_name: str,
    floor: str = Query("5", description="Этаж для расчета цен"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Возвращает данные о способах оплаты для конкретного комплекса
    """
    return await load_payment_options_for_complex(complex_name, floor, db=db)
