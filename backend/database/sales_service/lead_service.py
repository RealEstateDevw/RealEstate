from backend.database.sales_service import get_db, Lead


def create_lead_db(full_name, phone, source, city):
    with next(get_db()) as db:
        try:
            new_lead = Lead(full_name=full_name, phone=phone,
                            source=source, city=city)
            db.add(new_lead)
            db.commit()
            return True
        except Exception as e:
            raise e


def get_all_or_exact_lead_db(lid=0):
    with next(get_db()) as db:
        try:
            if lid == 0:
                all_leads = db.query(Lead).all()
                return all_leads
            exact_lead = db.query(Lead).filter_by(id=lid).first()
            return exact_lead
        except Exception as e:
            raise e


def update_lead_db(lid, change_info, new_info):
    with next(get_db()) as db:
        try:
            update_lead = db.query(Lead).filter_by(id=lid).first()
            if update_lead:
                if change_info == "full_name":
                    update_lead.full_name = new_info
                elif change_info == "phone":
                    update_lead.phone = new_info
                elif change_info == "source":
                    update_lead.source = new_info
                elif change_info == "city":
                    update_lead.city = new_info
                db.commit()
                return True
            return False
        except Exception as e:
            raise e


def delete_lead_db(lid):
    with next(get_db()) as db:
        try:
            to_delete_lead = db.query(Lead).filter_by(id=lid).first()
            if to_delete_lead:
                db.delete(to_delete_lead)
                db.commit()
                return True
            return False
        except Exception as e:
            raise e
