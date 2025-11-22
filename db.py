# db.py — слой доступа к PostgreSQL
import psycopg2
import psycopg2.extras

# --- Параметры подключения: замените на свои параметры из docker-compose.yml ---
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'contracts_db',
    'user': 'vladislav',
    'password': '0000'
}

def get_conn():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

# Утилиты
def list_tables():
    sql = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
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
    WHERE table_name = %s
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
    cols_sql = ','.join(cols)
    placeholders = ','.join(['%s']*len(cols))
    sql = f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders}) RETURNING *"
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql, vals)
            conn.commit()
            return cur.fetchone()

def update_row(table, pk_name, pk_value, data: dict):
    sets = ','.join([f"{k} = %s" for k in data.keys()])
    vals = list(data.values()) + [pk_value]
    sql = f"UPDATE {table} SET {sets} WHERE {pk_name} = %s RETURNING *"
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql, vals)
            conn.commit()
            return cur.fetchone()

def delete_row(table, pk_name, pk_value):
    sql = f"DELETE FROM {table} WHERE {pk_name} = %s"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (pk_value,))
            conn.commit()
            return cur.rowcount

# --- Специфичные запросы для вашей предметной области (договора) ---
def get_contracts(filters=None, order_by=''):
    # filters: dict field->value for simple equality filters
    where = []
    params = []
    if filters:
        for k,v in filters.items():
            where.append(f"{k} = %s")
            params.append(v)
    where_clause = ' AND '.join(where)
    return fetch_rows('dogovora', where_clause, tuple(params), order_by)

def get_contract_with_stages_and_payments(contract_id):
    sql = """
    SELECT d.*, o1.naimenovanie as zakazchik, o2.naimenovanie as ispolnitel
    FROM dogovora d
    LEFT JOIN organizacii o1 ON d.kod_zakazchika = o1.kod_organizacii
    LEFT JOIN organizacii o2 ON d.kod_ispolnitelya = o2.kod_organizacii
    WHERE d._kod_dogovora_ = %s
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql, (contract_id,))
            contract = cur.fetchone()
            # stages
            cur.execute("SELECT * FROM etapy_dogovorov WHERE _kod_dogovra_ = %s ORDER BY _номер_этапа_", (contract_id,))
            stages = cur.fetchall()
            # payments
            cur.execute("SELECT * FROM oplata WHERE код_договора = %s ORDER BY дата_оплаты", (contract_id,))
            payments = cur.fetchall()
    return {'contract': contract, 'stages': stages, 'payments': payments}

def report_contracts_summary(filter_params=None, order_by=''):
    # Пример отчёта: договоры + сумма этапов + сумма оплат + дебиторка (план - факт)
    sql = """
    SELECT d._код_договора_ as contract_id,
           d.тема,
           COALESCE(SUM(e.сумма_этапа),0) as plan_sum,
           COALESCE(SUM(o.сумма_оплаты),0) as paid_sum,
           COALESCE(SUM(e.сумма_этапа),0) - COALESCE(SUM(o.сумма_оплаты),0) as debt
    FROM dogovora d
    LEFT JOIN etapy_dogovorov e ON d._код_договора_ = e._код_договора_
    LEFT JOIN oplata o ON d._код_договора_ = o.код_договора
    GROUP BY d._код_договора_, d.тема
    HAVING (%s)
    """
    # Для простоты примера HAVING всегда true если нет фильтров
    having = 'TRUE'
    if filter_params and 'min_debt' in filter_params:
        having = f"(COALESCE(SUM(e.сумма_этапа),0) - COALESCE(SUM(o.сумма_оплаты),0)) >= {int(filter_params['min_debt'])}"
    final_sql = sql % having
    if order_by:
        final_sql += ' ORDER BY ' + order_by
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(final_sql)
            return cur.fetchall()

def report_payment_schedule(start_date=None, end_date=None):
    # Плановая оплаты (этапы) — сгруппировать по месяцу
    sql = """
    SELECT date_trunc('month', e.дата_исполнения_этапа) as month,
           SUM(e.сумма_этапа) as plan_sum
    FROM etapy_dogovorov e
    WHERE (%s)
    GROUP BY month
    ORDER BY month;
    """
    cond = "TRUE"
    if start_date and end_date:
        cond = f"e.дата_исполнения_этапа BETWEEN '{start_date}' AND '{end_date}'"
    final_sql = sql % cond
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(final_sql)
            return cur.fetchall()

def report_actual_receipts(start_date=None, end_date=None):
    sql = """
    SELECT date_trunc('month', o.дата_оплаты) as month,
           SUM(o.сумма_оплаты) as actual_sum
    FROM oplata o
    WHERE (%s)
    GROUP BY month
    ORDER BY month;
    """
    cond = "TRUE"
    if start_date and end_date:
        cond = f"o.дата_оплаты BETWEEN '{start_date}' AND '{end_date}'"
    final_sql = sql % cond
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(final_sql)
            return cur.fetchall()
