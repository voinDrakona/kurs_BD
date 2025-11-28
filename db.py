# db.py — корректная версия под вашу БД
import psycopg2
import psycopg2.extras

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'contracts_db',
    'user': 'vladislav',
    'password': '0000'
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)


# ---------------------------------------------------------
# Универсальные операции
# ---------------------------------------------------------

def list_tables():
    sql = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema='public'
      AND table_type='BASE TABLE'
    ORDER BY table_name;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return [r[0] for r in cur.fetchall()]


def get_columns(table):
    sql = """
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name=%s
    ORDER BY ordinal_position;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (table,))
            return cur.fetchall()


def fetch_rows(table, where_clause='', params=(), order_by=''):
    sql = f"SELECT * FROM {table} "
    if where_clause:
        sql += " WHERE " + where_clause
    if order_by:
        sql += " ORDER BY " + order_by
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def insert_row(table, data: dict):
    cols = list(data.keys())
    vals = [data[c] for c in cols]
    col_sql = ','.join(cols)
    placeholders = ','.join(['%s'] * len(cols))
    sql = f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders}) RETURNING *"

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql, vals)
            conn.commit()
            return cur.fetchone()


def update_row(table, pk_col, pk_val, data: dict):
    sets = ','.join([f"{k}=%s" for k in data.keys()])
    vals = list(data.values()) + [pk_val]
    sql = f"UPDATE {table} SET {sets} WHERE {pk_col}=%s RETURNING *"

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql, vals)
            conn.commit()
            return cur.fetchone()


def delete_row(table, pk_col, pk_val):
    sql = f"DELETE FROM {table} WHERE {pk_col}=%s"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (pk_val,))
            conn.commit()
            return cur.rowcount


# ---------------------------------------------------------
# Специализированные функции под ВАШУ БД
# ---------------------------------------------------------

# ---------- контракты ----------

def get_contract(contract_id):
    sql = """
    SELECT *
    FROM contracts
    WHERE contract_id=%s
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql, (contract_id,))
            return cur.fetchone()


def get_contract_full(contract_id):
    """Договор + заказчик + исполнитель + тип + стадия + vat"""
    sql = """
    SELECT *
    FROM view_contract_full
    WHERE contract_id=%s
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql, (contract_id,))
            return cur.fetchone()


def get_contract_milestones(contract_id):
    sql = """
    SELECT *
    FROM contract_milestones
    WHERE contract_id=%s
    ORDER BY milestone_no
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql, (contract_id,))
            return cur.fetchall()


def get_payments(contract_id):
    sql = """
    SELECT *
    FROM payments
    WHERE contract_id=%s
    ORDER BY payment_date
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql, (contract_id,))
            return cur.fetchall()


def create_contract_with_milestones(contract_data, milestones):
    """
    Полноценная транзакция 1:М для формы "Договор + этапы"
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # 1. создаём договор
            cols = list(contract_data.keys())
            vals = [contract_data[c] for c in cols]
            col_sql = ','.join(cols)
            placeholders = ','.join(['%s'] * len(cols))

            sql_contract = f"""
            INSERT INTO contracts ({col_sql})
            VALUES ({placeholders})
            RETURNING contract_id
            """

            cur.execute(sql_contract, vals)
            new_contract_id = cur.fetchone()['contract_id']

            # 2. создаём много этапов (1:М)
            for m in milestones:
                m['contract_id'] = new_contract_id
                cols = list(m.keys())
                vals = [m[c] for c in cols]
                col_sql = ','.join(cols)
                placeholders = ','.join(['%s'] * len(cols))

                sql_m = f"""
                INSERT INTO contract_milestones ({col_sql})
                VALUES ({placeholders})
                """
                cur.execute(sql_m, vals)

            # триггеры сами пересчитают total_amount и debt
            conn.commit()

            return new_contract_id


# ---------------------------------------------------------
# Отчёты
# ---------------------------------------------------------

def report_contract_details():
    """
    Отчёт: этапы + оплаты (многотабличный VIEW)
    """
    sql = "SELECT * FROM view_contract_details ORDER BY contract_id, milestone_no"
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql)
            return cur.fetchall()


def report_milestones_summary():
    sql = "SELECT * FROM view_milestones_summary_per_contract ORDER BY contract_id"
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql)
            return cur.fetchall()


def report_payments_summary():
    sql = "SELECT * FROM view_payments_summary_per_contract ORDER BY contract_id"
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql)
            return cur.fetchall()
