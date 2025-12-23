import shutil
from datetime import datetime

from fastapi import APIRouter, Query, Depends, HTTPException, Body, Form, UploadFile, File, Response
from typing import List, Optional
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import FileResponse

from backend.api.leads.schemas import LeadSearchResponse, LeadInDB, LeadUpdate, LeadState, LeadStatus, LeadCreate, \
    CommentCreate, CommentResponse, ContractCreate, ContractResponse, CallbackRequest
from backend.core.deps import get_current_user_from_cookie
from backend.database import get_db
from backend.database.models import Comment, User, Contract, Lead, Callback
from backend.database.sales_service.crud import LeadCRUD, LeadStatisticsService, InactiveLeadsService, LeadFilterService ,UnassignedLeadsService
from config import logger
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

router = APIRouter(prefix="/api/leads")

lead_crud = LeadCRUD()


@router.get("/search", response_model=List[LeadSearchResponse])
async def search_leads(
        query: str = Query(..., min_length=0, description="Search query for leads"),
        limit: int = Query(10, ge=1, le=50, description="Maximum number of results to return"),
        db: Session = Depends(get_db)
):
    """
    Search leads by name, phone number, or region.
    Returns a list of matching leads with basic information.
    """
    results = lead_crud.search_leads(db, query, limit)
    return results


@router.get("/inactive")
async def get_inactive_leads(db: Session = Depends(get_db)):
    service = InactiveLeadsService(db)
    return service.get_inactive_leads()


@router.get("/unassigned")
async def get_unassigned_leads(db: Session = Depends(get_db)):
    """
    Returns leads that are active but not assigned to any salesperson.
    """
    service = UnassignedLeadsService(db)
    return service.get_unassigned_leads()


@router.get("/filter")
async def filter_leads(
        user_id: Optional[int] = Query(None),
        db: Session = Depends(get_db)
):
    service = LeadFilterService(db)
    return service.get_filtered_leads(user_id)


@router.post("/", response_model=LeadInDB)
async def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    return lead_crud.create_lead(db, lead)


@router.get("/{lead_id}", response_model=LeadInDB)
async def get_lead(response: Response, lead_id: int, db: Session = Depends(get_db)):
    # Отключаем кеширование для real-time данных
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    db_lead = lead_crud.get_lead(db, lead_id)
    if not db_lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return db_lead


@router.get("/", response_model=List[LeadInDB])
async def get_leads(
        response: Response,
        skip: int = 0,
        limit: int = 100,
        status: Optional[LeadStatus] = None,
        state: Optional[LeadState] = None,
        region: Optional[str] = None,
        payment_type: Optional[str] = None,
        db: Session = Depends(get_db)
):
    # Отключаем кеширование для real-time данных
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return lead_crud.get_leads(db, skip, limit, status, state, region, payment_type)


@router.put("/{lead_id}")
async def update_lead(lead_id: int, lead_update: LeadUpdate, db: Session = Depends(get_db)):
    db_lead = lead_crud.update_lead(db, lead_id, lead_update)
    if not db_lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return db_lead


@router.delete("/{lead_id}")
async def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    success = lead_crud.unassign_lead(db, lead_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": "Lead successfully deleted"}


@router.get("/user/{user_id}")
async def get_user_leads(
        response: Response,
        user_id: int,
        include_callbacks: bool = False,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    # Отключаем кеширование для real-time данных
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    leads = lead_crud.get_leads_by_user(db, user_id, include_callbacks, skip, limit)
    
    # Если лидов нет, возвращаем пустой массив вместо ошибки 404
    if not leads:
        return []

    result = []
    for lead in leads:
        lead_dict = {
            "id": lead.id,
            "full_name": lead.full_name,
            "phone": lead.phone,
            "region": lead.region,
            "contact_source": lead.contact_source,
            "status": lead.status,
            "state": lead.state,
            "square_meters": lead.square_meters,
            "rooms": lead.rooms,
            "floor": lead.floor,
            "total_price": lead.total_price,
            "currency": lead.currency,
            "payment_type": lead.payment_type,
            "monthly_payment": lead.monthly_payment,
            "installment_period": lead.installment_period,
            "installment_markup": lead.installment_markup,
            "square_meters_price": lead.square_meters_price,
            "down_payment": lead.down_payment,
            "hybrid_final_payment": getattr(lead, "hybrid_final_payment", None),
            "notes": lead.notes,
            "next_contact_date": lead.next_contact_date,
            "user_id": lead.user_id,
            "created_at": lead.created_at,
            "updated_at": lead.updated_at,
            "callbacks": [callback.callback_time for callback in
                          lead.callbacks] if include_callbacks and lead.callbacks else []
        }
        result.append(lead_dict)

    return result


@router.get("/comments/{lead_id}", response_model=List[CommentResponse])
async def get_comments(lead_id: int, db: Session = Depends(get_db)):
    comments = (
        db.query(Comment)
        .filter(Comment.lead_id == lead_id)
        .order_by(Comment.created_at)
        .all()
    )

    # Add author name to each comment
    for comment in comments:
        comment.author_name = comment.author.first_name

    return comments


@router.post("/comments", response_model=CommentResponse)
async def create_comment(comment: CommentCreate, db: Session = Depends(get_db),
                         current_user_id=Depends(get_current_user_from_cookie)):
    db_comment = Comment(
        text=comment.text,
        is_internal=comment.is_internal,
        lead_id=comment.lead_id,
        author_id=current_user_id.id
    )

    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    # Add author name for response
    db_comment.author_name = db_comment.author.first_name

    return db_comment


@router.get("/lead-statistics/daily")
async def get_daily_statistics(db: Session = Depends(get_db)):
    service = LeadStatisticsService(db)
    return service.get_daily_statistics()


@router.post("/contracts/", response_model=ContractResponse)
async def create_contract(
        contract_data: ContractCreate,
        db: Session = Depends(get_db)
):
    """
    Создание договора и генерация Excel-файла.
    Принимает данные из формы.
    """
    try:
        # Проверка существования лида
        lead = db.query(Lead).filter(Lead.id == contract_data.lead_id).first()
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Лид не найден"
            )

        # Здесь реализуйте сохранение договора в БД.
        # В этом примере мы предполагаем, что договор успешно сохранён и используем contract_data как объект договора.
        # Например, contract = create_contract_in_db(contract_data) – ваша логика сохранения.
        contract = contract_data  # Для демонстрации

        # Подготовка данных для Excel-файла
        excel_data = {
            "Номер договора": contract.contract_number,
            "Дата договора": contract.contractDate.strftime("%Y-%m-%d"),
            "Блок": contract.block,
            "Этаж": contract.floor,
            "Номер квартиры": contract.apartmentNumber,
            "Кол-во комнат": contract.rooms,
            "Площадь (м²)": contract.size,
            "Общая стоимость": contract.totalPrice,
            "Стоимость 1 м²": contract.pricePerM2,
            "Выбор оплаты": contract.paymentChoice,
            "Сумма первоначального взноса": contract.initialPayment,
            "Ф/И/О": contract.fullName,
            "Серия паспорта": contract.passportSeries,
            "ПИНФЛ": contract.pinfl,
            "Кем выдан": contract.issuedBy,
            "Адрес прописки": contract.registrationAddress,
            "Номер телефона": contract.phone,
            "Отдел продаж": contract.salesDepartment,
            "Статус договора": "Создан"
        }

        # Создание Excel-файла
        filename =  f"contract_{contract.contract_number}.xlsx"
        df = pd.DataFrame([excel_data])
        df.to_excel(filename, index=False)
        print(f"Excel-файл создан: {filename}")
        logger.info(f"Договор {contract.contract_number} успешно создан")

        # Возврат файла в виде ответа
        return FileResponse(
            path=str(filename),
            filename=filename.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        logger.error(f"Ошибка при создании договора: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании договора: {str(e)}"
        )


@router.post("/{lead_id}/schedule-callback")
async def schedule_callback(lead_id: int, callback: CallbackRequest, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Create a new callback entry
    new_callback = Callback(
        lead_id=lead_id,
        callback_time=callback.callbackTime,
        is_completed=False
    )
    db.add(new_callback)
    db.commit()
    return {"message": "Callback scheduled"}


# Attach apartment details to a lead
@router.post("/{lead_id}/attach-apartment", response_model=LeadInDB)
async def attach_apartment(
    lead_id: int,
    apartment: dict = Body(..., description="Apartment details to attach to lead"),
    db: Session = Depends(get_db)
):
    """
    Attach apartment details to lead. Expects JSON with keys:
      square_meters, rooms, floor, total_price, currency,
      payment_type, monthly_payment, installment_period, installment_markup
    """
    db_lead = lead_crud.get_lead(db, lead_id)
    if not db_lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    # Update specified fields on the lead
    for field in [
        "square_meters", "rooms", "floor", "total_price", "currency",
        "payment_type", "monthly_payment", "installment_period", "complex_name", "number_apartments", "block", "down_payment",
        "square_meters_price", "down_payment_percent"
    ]:
        if field in apartment:
            setattr(db_lead, field, apartment[field])
    db.commit()
    db.refresh(db_lead)
    return db_lead


@router.post("/import")
async def import_leads(
        salesperson: int = Form(...),
        lead_file: UploadFile = File(None),
        google_sheet_url: Optional[str] = Form(None),
        db: Session = Depends(get_db)
):
    # Validate salesperson
    user = db.query(User).filter(User.id == salesperson).first()
    if not user:
        raise HTTPException(status_code=404, detail="Salesperson not found")

    # Process the leads
    try:
        if lead_file and lead_file.size > 0:
            # Process Excel file with explicit engine
            try:
                # Use 'openpyxl' for .xlsx files; you can switch to 'xlrd' for .xls files if needed
                df = pd.read_excel(lead_file.file, engine='openpyxl')
            except ValueError as e:
                # If openpyxl fails, try xlrd for older .xls files
                if 'Excel file format cannot be determined' in str(e):
                    df = pd.read_excel(lead_file.file, engine='xlrd')
                else:
                    raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")
        elif google_sheet_url:
            # Process Google Sheets
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_file("google_credentials.json", scopes=scopes)
            client = gspread.authorize(creds)
            sheet = client.open_by_url(google_sheet_url).sheet1
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
        else:
            raise HTTPException(status_code=400, detail="Either lead_file or google_sheet_url must be provided")

        # Map the DataFrame to Lead objects
        for _, row in df.iterrows():
            created_at = datetime.strptime(row.get('Дата', datetime.utcnow().strftime('%Y-%m-%d')),
                                           '%Y-%m-%d') if row.get('Дата') else datetime.utcnow()
            lead = Lead(
                full_name=row.get('Имя', 'Unknown'),
                phone=row.get('Номер телефона', ''),
                region=row.get('Город', 'Unknown'),
                contact_source="Unknown",
                status="COLD",
                state="NEW",
                total_price=float(row.get('Тариф', 0.0)) if row.get('Тариф') else 0.0,
                currency="UZS",
                payment_type=row.get('Тариф', 'Unknown') if isinstance(row.get('Тариф'), str) else 'Unknown',
                user_id=salesperson,
                created_at=created_at,
                updated_at=created_at
            )
            db.add(lead)
        db.commit()

        return {"message": "Leads imported successfully", "imported_count": len(df)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error importing leads: {str(e)}")


