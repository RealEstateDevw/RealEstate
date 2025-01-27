from backend.database.sales_service import get_db, Salesperson


def create_sales_person_db(full_name, phone, email):
    with next(get_db()) as db:
        try:
            new_sales_person = Salesperson(full_name=full_name, phone=phone, email=email)
            db.add(new_sales_person)
            db.commit()
            return True
        except Exception as e:
            raise e


def get_all_or_exact_sales_person(sid=0):
    with next(get_db()) as db:
        try:
            if sid == 0:
                all_speople = db.query(Salesperson).all()
                return all_speople
            exact_sperson = db.query(Salesperson).filter_by(id=sid).first()
            return exact_sperson
        except Exception as e:
            raise e


def update_sperson_db(sid, change_info, new_info):
    with next(get_db()) as db:
        try:
            update_sperson = db.query(Salesperson).filter_by(id=sid).first()
            if update_sperson:
                if change_info == "full_name":
                    update_sperson.full_name = new_info
                elif change_info == "phone":
                    update_sperson.phone = new_info
                elif change_info == "email":
                    update_sperson.email = new_info
                db.commit()
                return True
            return False
        except Exception as e:
            raise e


def delete_sperson_db(sid):
    with next(get_db()) as db:
        try:
            to_delete_sperson = db.query(Salesperson).filter_by(id=sid).first()
            if to_delete_sperson:
                db.delete(to_delete_sperson)
                db.commit()
                return True
            return False
        except Exception as e:
            raise e
