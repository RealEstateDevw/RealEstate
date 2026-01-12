import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
import sys

# Configuration
SQLITE_DB_PATH = "data.db.before-restore-20260108-132255"
POSTGRES_DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/realestate")

# Tables in order of dependency (Parents first, Children last)
TABLES = [
    "roles",
    "users",
    "instagram_settings",
    "residential_complexes",
    "draw_users",
    "campaigns",
    "price_history",
    "telegram_miniapp_users",
    "accesses",
    "attendances",
    "instagram_integrations",
    "apartment_units",
    "leads_prototype",
    "telegram_accounts",
    "chat_messages",
    "comments",
    "payments",
    "installment_payments",
    "transactions",
    "contracts",
    "callbacks",
    "client_requests",
    "expenses",
    "check_photos",
    "contract_registry_entries",
    "chessboard_price_entries",
    "apartment_interest_scores",
    "miniapp_lead_requests"
]

def get_sqlite_connection():
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to SQLite: {e}")
        sys.exit(1)

def get_postgres_connection():
    try:
        conn = psycopg2.connect(POSTGRES_DB_URL)
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL: {e}")
        sys.exit(1)

def migrate_table(sqlite_cursor, pg_cursor, table_name):
    print(f"Migrating table: {table_name}...")
    
    # Check if table exists in SQLite
    try:
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()
    except sqlite3.OperationalError:
        print(f"  Table {table_name} not found in SQLite. Skipping.")
        return

    if not rows:
        print(f"  Table {table_name} is empty. Skipping.")
        return

    # Get column names from SQLite
    columns = list(rows[0].keys())
    
    # Define required defaults for missing or null columns
    required_defaults = {
        "residential_complexes": {
            "installment_months": 36,
            "installment_start_date": '2025-12-01',
            "hybrid_installment_enabled": False
        }
    }

    # Define boolean columns that need conversion from 0/1 to False/True
    boolean_columns = {
        "leads_prototype": ["is_active"],
        "instagram_settings": ["is_active"],
        "instagram_integrations": ["is_active"],
        "residential_complexes": ["hybrid_installment_enabled"],
        "callbacks": ["is_completed", "is_missed"],
        "chat_messages": ["is_from_sales"],
        "comments": ["is_internal"],
    }

    # Map invalid enum values
    enum_mappings = {
        "expenses": {
            "category": {"Unknown": "OTHER"}
        }
    }

    # Add missing columns to the list
    if table_name in required_defaults:
        for col_name in required_defaults[table_name]:
            if col_name not in columns:
                columns.append(col_name)

    columns_str = ", ".join(columns)
    
    # Prepare data with defaults and type conversion
    cleaned_data = []
    for row in rows:
        row_dict = dict(row)
        
        if table_name in required_defaults:
            for col_name, default_val in required_defaults[table_name].items():
                # If column missing or value is None, use default
                if col_name not in row_dict or row_dict[col_name] is None:
                    row_dict[col_name] = default_val
        
        # Convert booleans
        if table_name in boolean_columns:
            for col in boolean_columns[table_name]:
                val = row_dict.get(col)
                if val is not None:
                    # Convert 0/1 to False/True
                    if val == 1:
                        row_dict[col] = True
                    elif val == 0:
                        row_dict[col] = False
                    # If it's already bool, leave it.

        # Map enum values
        if table_name in enum_mappings:
            for col, mapping in enum_mappings[table_name].items():
                val = row_dict.get(col)
                if val in mapping:
                    row_dict[col] = mapping[val]
        
        # Construct the tuple in the correct order
        cleaned_row = tuple(row_dict.get(col) for col in columns)
        cleaned_data.append(cleaned_row)
    
    data = cleaned_data
    
    # Insert into Postgres
    query = f"INSERT INTO {table_name} ({columns_str}) VALUES %s ON CONFLICT DO NOTHING"
    
    try:
        execute_values(pg_cursor, query, data)
        print(f"  Migrated {len(data)} rows.")
    except psycopg2.Error as e:
        print(f"  Error migrating {table_name}: {e}")
        raise e

def reset_sequences(pg_cursor):
    print("Resetting sequences...")
    # This query finds all sequences and resets them to the max value of their id column
    query = """
    SELECT 'SELECT setval(' || quote_literal(quote_ident(S.relname)) || ', MAX(id) ) FROM ' || quote_ident(T.relname) || ';'
    FROM pg_class AS S, pg_depend AS D, pg_class AS T, pg_attribute AS A
    WHERE S.relkind = 'S'
    AND S.oid = D.objid
    AND D.refobjid = T.oid
    AND D.refobjsubid = A.attnum
    ORDER BY S.relname;
    """
    pg_cursor.execute(query)
    reset_queries = pg_cursor.fetchall()
    
    for q in reset_queries:
        try:
            pg_cursor.execute(q[0])
        except psycopg2.Error as e:
            print(f"  Error resetting sequence: {e} (might be empty table)")
            # Continue even if one fails (e.g. empty table)
            pass

def main():
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"SQLite database file not found: {SQLITE_DB_PATH}")
        sys.exit(1)

    sqlite_conn = get_sqlite_connection()
    pg_conn = get_postgres_connection()
    
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    try:
        # Disable constraints temporarily? No, better to insert in correct order.
        # But we can defer them if needed. For now, relying on order.
        
        for table in TABLES:
            migrate_table(sqlite_cursor, pg_cursor, table)
        
        # Reset sequences
        reset_sequences(pg_cursor)
        
        pg_conn.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        pg_conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    main()
