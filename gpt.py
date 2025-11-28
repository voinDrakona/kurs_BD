"""
Динамическое tkinter-приложение для работы с PostgreSQL-базой.
- Автоматически создает вкладку для каждой пользовательской таблицы
- Поддерживает CRUD
- Автоматически определяет внешние ключи и отображает их как Combobox (с отображением 'name' или первого текстового поля)

Требования:
- psycopg2-binary
- Python 3.8+

Настройка: укажи строку подключения в DSN переменной внизу файла.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import psycopg2
from psycopg2 import sql
from datetime import datetime


class DBIntrospector:
    def __init__(self, conn):
        self.conn = conn

    def get_tables(self):
        """Вернуть список пользовательских таблиц (исключая системные и представления)."""
        q = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
        with self.conn.cursor() as cur:
            cur.execute(q)
            return [r[0] for r in cur.fetchall()]

    def get_columns(self, table_name):
        q = sql.SQL("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """)
        with self.conn.cursor() as cur:
            cur.execute(q, (table_name,))
            cols = cur.fetchall()
        # return list of dicts
        return [
            {"name": c[0], "type": c[1], "nullable": c[2] == 'YES', "default": c[3]}
            for c in cols
        ]

    def get_primary_key(self, table_name):
        q = """
        SELECT a.attname
        FROM   pg_index i
        JOIN   pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE  i.indrelid = %s::regclass AND i.indisprimary;
        """
        with self.conn.cursor() as cur:
            cur.execute(q, (table_name,))
            rows = cur.fetchall()
        return [r[0] for r in rows]

    def get_foreign_keys(self, table_name):
        q = sql.SQL("""
            SELECT
              kcu.column_name,
              ccu.table_name AS foreign_table_name,
              ccu.column_name AS foreign_column_name
            FROM
              information_schema.key_column_usage AS kcu
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = kcu.constraint_name
            JOIN information_schema.table_constraints AS tc
              ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND kcu.table_schema = 'public'
              AND kcu.table_name = %s;
        """)
        with self.conn.cursor() as cur:
            cur.execute(q, (table_name,))
            return [
                {"column": r[0], "ref_table": r[1], "ref_column": r[2]}
                for r in cur.fetchall()
            ]

    def guess_display_column(self, table_name):
        """Попробовать выбрать столбец для отображения в Combobox при ссылках.
        Предпочтение: name, title, description, любая текстовая колонка, иначе первичный ключ.
        """
        cols = self.get_columns(table_name)
        names_pref = ['name', 'title', 'description']
        for pref in names_pref:
            for c in cols:
                if c['name'].lower() == pref:
                    return c['name']
        for c in cols:
            if c['type'] in ('text', 'character varying', 'varchar'):
                return c['name']
        # fallback to pk
        pks = self.get_primary_key(table_name)
        if pks:
            return pks[0]
        return cols[0]['name'] if cols else None


class TableFrame(tk.Frame):
    def __init__(self, parent, conn, introspector, table_name):
        super().__init__(parent)
        self.conn = conn
        self.introspector = introspector
        self.table_name = table_name
        self.columns = self.introspector.get_columns(table_name)
        self.fks = {fk['column']: fk for fk in self.introspector.get_foreign_keys(table_name)}
        self.pk = self.introspector.get_primary_key(table_name)
        self.display_cols_cache = {}

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        toolbar = tk.Frame(self)
        toolbar.pack(fill=tk.X)
        btn_add = tk.Button(toolbar, text='Добавить', command=self.add_record)
        btn_edit = tk.Button(toolbar, text='Редактировать', command=self.edit_record)
        btn_del = tk.Button(toolbar, text='Удалить', command=self.delete_record)
        btn_refresh = tk.Button(toolbar, text='Обновить', command=self.load_data)
        btn_add.pack(side=tk.LEFT, padx=4, pady=4)
        btn_edit.pack(side=tk.LEFT, padx=4, pady=4)
        btn_del.pack(side=tk.LEFT, padx=4, pady=4)
        btn_refresh.pack(side=tk.LEFT, padx=4, pady=4)

        self.tree = ttk.Treeview(self, columns=[c['name'] for c in self.columns], show='headings')
        for c in self.columns:
            self.tree.heading(c['name'], text=c['name'])
            self.tree.column(c['name'], width=120)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind('<Double-1>', lambda e: self.edit_record())

    def fetch_fk_options(self, ref_table, ref_col):
        # try cached
        key = (ref_table, ref_col)
        if key in self.display_cols_cache:
            return self.display_cols_cache[key]
        disp_col = self.introspector.guess_display_column(ref_table)
        q = sql.SQL('SELECT {id}, {disp} FROM {tbl} ORDER BY {disp}').format(
            id=sql.Identifier(ref_col),
            disp=sql.Identifier(disp_col),
            tbl=sql.Identifier(ref_table)
        )
        with self.conn.cursor() as cur:
            try:
                cur.execute(q)
                rows = cur.fetchall()
            except Exception:
                # fallback to id only
                cur.execute(sql.SQL('SELECT {id} FROM {tbl}').format(id=sql.Identifier(ref_col), tbl=sql.Identifier(ref_table)))
                rows = cur.fetchall()
        options = [(r[0], str(r[1]) if len(r) > 1 else str(r[0])) for r in rows]
        self.display_cols_cache[key] = (disp_col, options)
        return disp_col, options

    def load_data(self):
        cols = [c['name'] for c in self.columns]
        q = sql.SQL('SELECT {fields} FROM {tbl} ORDER BY 1').format(
            fields=sql.SQL(', ').join(sql.Identifier(c) for c in cols),
            tbl=sql.Identifier(self.table_name)
        )
        with self.conn.cursor() as cur:
            cur.execute(q)
            rows = cur.fetchall()
        # clear
        for r in self.tree.get_children():
            self.tree.delete(r)
        for row in rows:
            values = []
            for i, v in enumerate(row):
                col = cols[i]
                if col in self.fks and v is not None:
                    # replace id with display value
                    fk = self.fks[col]
                    disp_col, options = self.fetch_fk_options(fk['ref_table'], fk['ref_column'])
                    display = next((opt[1] for opt in options if opt[0] == v), str(v))
                    values.append(display)
                else:
                    values.append(v)
            self.tree.insert('', tk.END, values=values)

    def get_selected_pk(self):
        sel = self.tree.selection()
        if not sel:
            return None
        item = self.tree.item(sel[0])['values']
        # find pk value by matching tree columns to pk name
        if not self.pk:
            return None
        pk_index = None
        for i, c in enumerate(self.columns):
            if c['name'] == self.pk[0]:
                pk_index = i
                break
        if pk_index is None:
            return None
        return item[pk_index]

    def add_record(self):
        self._open_editor()

    def edit_record(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Внимание', 'Нет выбранной записи')
            return
        # get row values and open editor with defaults
        vals = self.tree.item(sel[0])['values']
        defaults = {}
        for i, c in enumerate(self.columns):
            defaults[c['name']] = vals[i]
        self._open_editor(defaults=defaults, editing=True)

    def delete_record(self):
        pk_val = self.get_selected_pk()
        if pk_val is None:
            messagebox.showwarning('Внимание', 'Не найден PK для выбранной записи')
            return
        if not messagebox.askyesno('Подтвердите', 'Удалить запись?'):
            return
        # delete
        q = sql.SQL('DELETE FROM {tbl} WHERE {pk} = %s').format(
            tbl=sql.Identifier(self.table_name),
            pk=sql.Identifier(self.pk[0])
        )
        with self.conn.cursor() as cur:
            try:
                cur.execute(q, (pk_val,))
                self.conn.commit()
                self.load_data()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror('Ошибка', str(e))

    def _open_editor(self, defaults=None, editing=False):
        defaults = defaults or {}
        dlg = tk.Toplevel(self)
        dlg.title(('Редактирование' if editing else 'Добавление') + f' — {self.table_name}')
        entries = {}

        for i, col in enumerate(self.columns):
            name = col['name']
            lbl = tk.Label(dlg, text=name)
            lbl.grid(row=i, column=0, sticky='w', padx=4, pady=2)
            if name in self.fks:
                fk = self.fks[name]
                disp_col, options = self.fetch_fk_options(fk['ref_table'], fk['ref_column'])
                cb = ttk.Combobox(dlg, values=[o[1] for o in options])
                # map display -> id via dict
                id_map = {o[1]: o[0] for o in options}
                entries[name] = (cb, id_map)
                # set default if present
                if name in defaults and defaults[name] is not None:
                    # defaults[name] contains display value in tree; try to set combobox by display
                    cb.set(defaults[name])
                cb.grid(row=i, column=1, sticky='we', padx=4, pady=2)
            else:
                ent = tk.Entry(dlg)
                entries[name] = ent
                if name in defaults and defaults[name] is not None:
                    ent.insert(0, str(defaults[name]))
                ent.grid(row=i, column=1, sticky='we', padx=4, pady=2)

        def on_save():
            data = {}
            for name, w in entries.items():
                if isinstance(w, tuple):
                    cb, id_map = w
                    val_display = cb.get().strip()
                    val = id_map.get(val_display, None)
                    data[name] = val
                else:
                    v = w.get().strip()
                    data[name] = v if v != '' else None
            try:
                if editing and self.pk:
                    # update by PK
                    pk_col = self.pk[0]
                    pk_value = None
                    # try to extract pk from defaults
                    if pk_col in defaults:
                        pk_value = defaults[pk_col]
                    else:
                        pk_value = self.get_selected_pk()
                    # build set clause
                    set_clause = sql.SQL(', ').join(
                        sql.SQL('{} = %s').format(sql.Identifier(k)) for k in data.keys() if k != pk_col
                    )
                    q = sql.SQL('UPDATE {tbl} SET {set} WHERE {pk} = %s').format(
                        tbl=sql.Identifier(self.table_name),
                        set=set_clause,
                        pk=sql.Identifier(pk_col)
                    )
                    params = [v for k, v in data.items() if k != pk_col]
                    params.append(pk_value)
                    with self.conn.cursor() as cur:
                        cur.execute(q, params)
                        self.conn.commit()
                else:
                    cols = [k for k in data.keys() if not (k == self.pk[0] and col_default_is_serial(self.columns, k))]
                    q = sql.SQL('INSERT INTO {tbl} ({fields}) VALUES ({vals})').format(
                        tbl=sql.Identifier(self.table_name),
                        fields=sql.SQL(', ').join(sql.Identifier(c) for c in cols),
                        vals=sql.SQL(', ').join(sql.Placeholder() * len(cols))
                    )
                    params = [data[c] for c in cols]
                    with self.conn.cursor() as cur:
                        cur.execute(q, params)
                        self.conn.commit()
                dlg.destroy()
                self.load_data()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror('Ошибка', str(e))

        btn_save = tk.Button(dlg, text='Сохранить', command=on_save)
        btn_save.grid(row=len(self.columns), column=0, columnspan=2, pady=8)


def col_default_is_serial(columns, colname):
    for c in columns:
        if c['name'] == colname:
            d = c.get('default')
            if d and ('nextval' in str(d) or 'nextval' in str(d).lower()):
                return True
    return False


class MainApplication(tk.Tk):
    def __init__(self, dsn):
        super().__init__()
        self.title('DB Admin — dynamic')
        self.geometry('1000x600')
        try:
            self.conn = psycopg2.connect(dsn)
        except Exception as e:
            messagebox.showerror('DB connection error', str(e))
            self.destroy()
            return
        self.intro = DBIntrospector(self.conn)
        self.setup_ui()

    def setup_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)
        tables = self.intro.get_tables()
        for t in tables:
            frame = TableFrame(nb, self.conn, self.intro, t)
            nb.add(frame, text=t)

        # status bar
        status = tk.Label(self, text=f'Connected to DB — {datetime.now().isoformat()}', bd=1, relief=tk.SUNKEN, anchor='w')
        status.pack(side=tk.BOTTOM, fill=tk.X)


if __name__ == '__main__':
    # Поменяй DSN на свою БД
    DSN = "dbname=contracts_db user=vladislav password=0000 host=localhost port=5432"
    app = MainApplication(DSN)
    app.mainloop()
