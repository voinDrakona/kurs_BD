import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import csv
import db
import datetime

def is_required(table, column):
    req_fields = {
        'contract_types': ['name'],
        'execution_stages': ['name'],
        'vat_rates': ['percent'],
        'payment_methods': ['name'],
        'organizations': ['name'],
        'contracts': ['contract_number', 'customer_org_id', 'contractor_org_id', 'contract_type_id', 'current_stage_id', 'vat_id'],
        'contract_milestones': ['contract_id', 'milestone_no', 'stage_id', 'amount', 'advance_amount'],
        'payments': ['contract_id', 'amount', 'payment_method_id']
    }
    if column is None:
        return req_fields.get(table, [])  # возвращаем список всех обязательных полей
    return column in req_fields.get(table, [])  # True/False для одного поля


def check_required_fields(table, data):
    req = is_required(table, None)  # присвоение отдельной строкой
    for f in req:
        if f not in data or data[f] in (None, '', []):
            raise ValueError(f"Обязательное поле '{f}' не заполнено")

def convert_data(table, data):
    new_data = {}
    for k, v in data.items():
        if v in ('', None):
            # не передавать колонку с пустым значением, если есть DEFAULT в БД
            continue
        elif k.endswith('_id') or k in ('milestone_no', 'contract_id', 'payment_id', 'stage_id'):
            new_data[k] = int(v)
        elif k in ('amount', 'advance_amount', 'total_amount', 'paid_amount', 'debt_amount'):
            new_data[k] = float(v)
        else:
            new_data[k] = v
    return new_data


def insert_row_safe(table, data):
    data = convert_data(table, data)
    check_required_fields(table, data)
    return db.insert_row(table, data)  # или insert_row_return_id если нужно получить PK

def update_row_safe(table, pk_col, pk_val, data):
    data = convert_data(table, data)
    check_required_fields(table, data)
    db.update_row(table, pk_col, pk_val, data)

class ClientApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Клиент для БД — Договора")
        self.geometry("1000x700")

        # ===== Левое меню =====
        left = ttk.Frame(self, width=200)
        left.pack(side='left', fill='y')
        ttk.Label(left, text="Таблицы").pack(padx=5, pady=5)
        self.table_list = tk.Listbox(left, height=20)
        self.table_list.pack(fill='y', padx=5)
        self.table_list.bind('<<ListboxSelect>>', self.on_table_select)

        btn_frame = ttk.Frame(left)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Обновить список", command=self.load_tables).pack(fill='x')
        ttk.Button(btn_frame, text="Отчёты", command=self.open_reports).pack(fill='x', pady=5)

        # ===== Правый фрейм =====
        right = ttk.Frame(self)
        right.pack(side='right', fill='both', expand=True)
        self.tree = ttk.Treeview(right, show='headings')
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<Double-1>', self.on_edit_row)

        control = ttk.Frame(right)
        control.pack(fill='x')
        ttk.Button(control, text="Добавить", command=self.add_row).pack(side='left', padx=4)
        ttk.Button(control, text="Удалить", command=self.delete_row).pack(side='left', padx=4)
        ttk.Button(control, text="Обновить", command=self.reload_table).pack(side='left', padx=4)
        ttk.Button(control, text="Поиск", command=self.search_dialog).pack(side='left', padx=4)
        ttk.Button(control, text="Фильтр/Сортировка", command=self.filter_sort_dialog).pack(side='left', padx=4)
        ttk.Button(control, text="Форма: Договор + Этапы (1:М)", command=self.open_contract_form).pack(side='right', padx=4)

        self.current_table = None
        self.current_pk = None
        self.columns = []

        self.load_tables()

    def load_tables(self):
        self.table_list.delete(0, tk.END)
        try:
            tables = db.list_tables()
        except Exception as e:
            messagebox.showerror("Ошибка подключения", str(e))
            return
        for t in tables:
            self.table_list.insert(tk.END, t)

    def on_table_select(self, evt):
        sel = self.table_list.curselection()
        if not sel: return
        table = self.table_list.get(sel[0])
        self.open_table(table)

    def open_table(self, table):
        self.current_table = table
        cols = db.get_columns(table)
        self.columns = [c[0] for c in cols]

        # скрываем PK
        pk_fields = ('contract_id','payment_id','stage_id')
        self.columns = [c for c in self.columns if c not in pk_fields]

        self.tree.delete(*self.tree.get_children())
        self.tree['columns'] = self.columns
        for c in self.columns:
            self.tree.heading(c, text=c + (' *' if is_required(table, c) else ''))
            self.tree.column(c, width=120, anchor='w')
        rows = db.fetch_rows(table)
        for r in rows:
            self.tree.insert('', tk.END, values=[r.get(c) for c in self.columns])

    def reload_table(self):
        if self.current_table:
            self.open_table(self.current_table)

    def add_row(self):
        if not self.current_table:
            messagebox.showinfo("Инфо", "Выберите таблицу слева")
            return

        data = {}

        # Обязательные поля
        required_cols = is_required(self.current_table, None)  # список обязательных колонок
        for col in required_cols:
            val = simpledialog.askstring("Добавить", f"{col} *:", parent=self)
            if val is None:
                return
            data[col] = val

        # Необязательные поля (спрашиваем отдельно, можно пропустить)
        for col in self.columns:
            if col not in required_cols:
                val = simpledialog.askstring("Добавить", f"{col} (необязательное):", parent=self)
                data[col] = val if val else None


        try:
            insert_row_safe(self.current_table, data)
            messagebox.showinfo("OK", "Запись добавлена")
            self.reload_table()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


    def on_edit_row(self, event):
        item = self.tree.focus()
        if not item: return
        values = self.tree.item(item)['values']

        pk_col = self.columns[0]
        pk_val = values[0]
        data = {}

        # Обязательные поля
        required_cols = is_required(self.current_table, None)  # список обязательных колонок
        for col in required_cols:
            val = simpledialog.askstring("Добавить", f"{col} *:", parent=self)
            if val is None:
                return
            data[col] = val


        # Необязательные поля
        for col in self.columns:
            if col not in required_cols:
                val = simpledialog.askstring("Добавить", f"{col} (необязательное):", parent=self)
                data[col] = val if val else None


        try:
            update_row_safe(self.current_table, pk_col, pk_val, data)
            messagebox.showinfo("OK", "Запись обновлена")
            self.reload_table()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def delete_row(self):
        item = self.tree.focus()
        if not item:
            messagebox.showinfo("Инфо", "Выберите запись в таблице")
            return
        values = self.tree.item(item)['values']
        pk_col = self.columns[0]
        pk_val = values[0]
        if messagebox.askyesno("Удалить?", f"Удалить запись {pk_val}?"):
            try:
                db.delete_row(self.current_table, pk_col, pk_val)
                self.reload_table()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

    def search_dialog(self):
        if not self.current_table:
            messagebox.showinfo("Инфо", "Выберите таблицу")
            return
        field = simpledialog.askstring("Поиск", f"Поле для поиска (из {', '.join(self.columns)}):", parent=self)
        if not field or field not in self.columns:
            messagebox.showerror("Ошибка", "Неверное поле")
            return
        term = simpledialog.askstring("Поиск", f"Искомое значение для {field} (равно):", parent=self)
        if term is None:
            return
        rows = db.fetch_rows(self.current_table, where_clause=f"{field} = %s", params=(term,))
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert('', tk.END, values=[r[c] for c in self.columns])

    def filter_sort_dialog(self):
        if not self.current_table:
            messagebox.showinfo("Инфо", "Выберите таблицу")
            return
        field = simpledialog.askstring("Фильтр", f"Поле для фильтра (или пусто):", parent=self)
        cond = ''
        params = ()
        if field:
            val = simpledialog.askstring("Фильтр", f"Значение для {field} (равно):", parent=self)
            if val is None: return
            cond = f"{field} = %s"
            params = (val,)
        order = simpledialog.askstring("Сортировка", f"Поле для сортировки (или пусто):", parent=self)
        rows = db.fetch_rows(self.current_table, where_clause=cond, params=params, order_by=order or '')
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert('', tk.END, values=[r[c] for c in self.columns])

    def open_contract_form(self):
        ContractForm(self)

    def open_reports(self):
        ReportsWindow(self)



class ContractForm(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Форма: Договор и этапы")
        self.geometry("800x600")
        self.parent = parent

        frm = ttk.Frame(self)
        frm.pack(fill='both', expand=True, padx=10, pady=10)

        # ===== Договор =====
        ttk.Label(frm, text="Номер договора *:").grid(row=0, column=0, sticky='e')
        self.e_number = ttk.Entry(frm); self.e_number.grid(row=0, column=1, sticky='w')

        ttk.Label(frm, text="Тема:").grid(row=1, column=0, sticky='e')
        self.e_subject = ttk.Entry(frm); self.e_subject.grid(row=1, column=1, sticky='w')

        # Combobox для заказчика
        ttk.Label(frm, text="Заказчик *:").grid(row=2, column=0, sticky='e')
        customers = [(str(r['org_id']), r['name']) for r in db.fetch_rows('organizations')]
        self.customer_map = {name: oid for oid, name in customers}
        self.e_customer = ttk.Combobox(frm, values=list(self.customer_map.keys()))
        self.e_customer.grid(row=2, column=1, sticky='w')

        # Combobox для исполнителя
        ttk.Label(frm, text="Исполнитель *:").grid(row=3, column=0, sticky='e')
        contractors = [(str(r['org_id']), r['name']) for r in db.fetch_rows('organizations')]
        self.contractor_map = {name: oid for oid, name in contractors}
        self.e_contractor = ttk.Combobox(frm, values=list(self.contractor_map.keys()))
        self.e_contractor.grid(row=3, column=1, sticky='w')

        # Тип договора
        ttk.Label(frm, text="Тип договора:").grid(row=4, column=0, sticky='e')
        types = [(str(r['contract_type_id']), r['name']) for r in db.fetch_rows('contract_types')]
        self.type_map = {name: tid for tid, name in types}
        self.e_contract_type = ttk.Combobox(frm, values=list(self.type_map.keys()))
        self.e_contract_type.grid(row=4, column=1, sticky='w')

        # Ставка НДС
        ttk.Label(frm, text="НДС:").grid(row=5, column=0, sticky='e')
        vats = [(str(r['vat_id']), str(r['percent'])) for r in db.fetch_rows('vat_rates')]
        self.vat_map = {percent: vid for vid, percent in vats}
        self.e_vat = ttk.Combobox(frm, values=list(self.vat_map.keys()))
        self.e_vat.grid(row=5, column=1, sticky='w')

        # ===== Этапы =====
        ttk.Label(frm, text="Этапы договора:").grid(row=6, column=0, columnspan=2, sticky='w')
        self.milestones_frame = ttk.Frame(frm)
        self.milestones_frame.grid(row=7, column=0, columnspan=2, sticky='w', pady=5)
        self.milestones_rows = []

        ttk.Button(frm, text="Добавить этап", command=self.add_milestone_row).grid(row=8, column=1, sticky='e', pady=5)
        ttk.Button(frm, text="Сохранить договор + этапы", command=self.save).grid(row=9, column=1, sticky='e', pady=8)

    def add_milestone_row(self):
        row_idx = len(self.milestones_rows)
        entries = []

        # Номер этапа
        e_no = ttk.Entry(self.milestones_frame, width=5)
        e_no.grid(row=row_idx, column=0)
        entries.append(e_no)

        # Дата этапа
        e_date = ttk.Entry(self.milestones_frame, width=12)
        e_date.grid(row=row_idx, column=1)
        entries.append(e_date)

        # Стадия выполнения
        stages = [(str(r['stage_id']), r['name']) for r in db.fetch_rows('execution_stages')]
        self.stage_map = {name: sid for sid, name in stages}
        e_stage = ttk.Combobox(self.milestones_frame, values=list(self.stage_map.keys()), width=15)
        e_stage.grid(row=row_idx, column=2)
        entries.append(e_stage)

        # Сумма этапа
        e_amount = ttk.Entry(self.milestones_frame, width=10)
        e_amount.grid(row=row_idx, column=3)
        entries.append(e_amount)

        # Аванс
        e_advance = ttk.Entry(self.milestones_frame, width=10)
        e_advance.grid(row=row_idx, column=4)
        entries.append(e_advance)

        # Тема этапа
        e_subject = ttk.Entry(self.milestones_frame, width=20)
        e_subject.grid(row=row_idx, column=5)
        entries.append(e_subject)

        self.milestones_rows.append(entries)

    def save(self):
        # ===== Проверка договора =====
        number = self.e_number.get().strip()
        subject = self.e_subject.get().strip()
        customer_name = self.e_customer.get().strip()
        contractor_name = self.e_contractor.get().strip()
        contract_type_name = self.e_contract_type.get().strip()
        vat_percent = self.e_vat.get().strip()

        if not contract_type_name:
            messagebox.showerror("Ошибка", "Тип договора обязателен")
            return

        if not vat_percent:
            messagebox.showerror("Ошибка", "Ставка НДС обязательна")
            return

        if not number or not customer_name or not contractor_name:
            messagebox.showerror("Ошибка", "Пожалуйста, заполните все обязательные поля договора (*)")
            return

        try:
            contract_data = {
                'contract_number': number,
                'subject': subject or None,
                'customer_org_id': self.customer_map[customer_name],
                'contractor_org_id': self.contractor_map[contractor_name],
                'contract_type_id': self.type_map.get(contract_type_name),
                'vat_id': self.vat_map.get(vat_percent),
                'contract_date': datetime.date.today()
            }
            new_contract_id = db.insert_row_return_id('contracts', contract_data)
        except Exception as e:
            messagebox.showerror("Ошибка при добавлении договора", str(e))
            return

        # ===== Этапы =====
        for idx, entries in enumerate(self.milestones_rows, 1):
            no = entries[0].get().strip()
            date = entries[1].get().strip()
            stage_name = entries[2].get().strip()
            amount = entries[3].get().strip()
            advance = entries[4].get().strip()
            tema = entries[5].get().strip()

            if not no and not date and not amount:
                continue  # пустая строка пропускается

            if not no or not date or not amount:
                messagebox.showerror("Ошибка", f"Строка {idx} этапа: не заполнены обязательные поля (*)")
                return

            try:
                milestone_data = {
                    'contract_id': new_contract_id,
                    'milestone_no': int(no),
                    'milestone_date': date,
                    'stage_id': self.stage_map.get(stage_name),
                    'amount': float(amount),
                    'advance_amount': float(advance) if advance else 0,
                    'subject': tema or None
                }
                db.insert_row('contract_milestones', milestone_data)
            except Exception as e:
                messagebox.showwarning("Ошибка вставки этапа", f"Этап {idx}: {e}")

        messagebox.showinfo("Готово", "Договор и этапы сохранены")
        self.destroy()
        self.parent.reload_table()



class ReportsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Отчёты")
        self.geometry("800x600")
        frm = ttk.Frame(self)
        frm.pack(fill='both', expand=True, padx=10, pady=10)

        ttk.Button(frm, text="Отчёт: Сведения по договорам (план/факт/дебиторка)",
                   command=self.run_report_contracts).pack(fill='x', pady=5)
        ttk.Button(frm, text="Отчёт: График плановой оплаты (по месяцам)",
                   command=self.run_report_plan).pack(fill='x', pady=5)
        ttk.Button(frm, text="Отчёт: График поступлений (факт, по месяцам)",
                   command=self.run_report_actual).pack(fill='x', pady=5)

        self.text = tk.Text(frm)
        self.text.pack(fill='both', expand=True)

    def run_report_contracts(self):
        min_debt = simpledialog.askinteger("Фильтр", "Минимальная дебиторская задолженность (или пусто):", parent=self)
        filters = {}
        if min_debt is not None:
            filters['min_debt'] = min_debt
        rows = db.report_contracts_summary(filters)
        self.text.delete('1.0', 'end')
        self.text.insert('end', "contract_id | subject | total_amount | paid_amount | debt_amount\n")
        for r in rows:
            self.text.insert('end', f"{r['contract_id']} | {r['subject']} | {r['total_amount']} | {r['paid_amount']} | {r['debt_amount']}\n")
        if messagebox.askyesno("Экспорт", "Экспортировать результат в CSV?"):
            p = filedialog.asksaveasfilename(defaultextension='.csv')
            if p:
                with open(p, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['contract_id', 'subject', 'total_amount', 'paid_amount', 'debt_amount'])
                    for r in rows:
                        writer.writerow([r['contract_id'], r['subject'], r['total_amount'], r['paid_amount'], r['debt_amount']])
                messagebox.showinfo("OK", f"Сохранено в {p}")

    def run_report_plan(self):
        start = simpledialog.askstring("Период", "Начальная дата YYYY-MM-DD (или пусто):", parent=self)
        end = simpledialog.askstring("Период", "Конечная дата YYYY-MM-DD (или пусто):", parent=self)
        rows = db.report_payment_schedule(start, end)
        self.text.delete('1.0', 'end')
        for r in rows:
            self.text.insert('end', f"{r['month'].date()} : {r['plan_sum']}\n")
        if messagebox.askyesno("Экспорт", "Экспортировать результат в CSV?"):
            p = filedialog.asksaveasfilename(defaultextension='.csv')
            if p:
                with open(p, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['month', 'plan_sum'])
                    for r in rows:
                        writer.writerow([r['month'].date(), r['plan_sum']])
                messagebox.showinfo("OK", f"Сохранено в {p}")

    def run_report_actual(self):
        start = simpledialog.askstring("Период", "Начальная дата YYYY-MM-DD (или пусто):", parent=self)
        end = simpledialog.askstring("Период", "Конечная дата YYYY-MM-DD (или пусто):", parent=self)
        rows = db.report_actual_receipts(start, end)
        self.text.delete('1.0', 'end')
        for r in rows:
            self.text.insert('end', f"{r['month'].date()} : {r['actual_sum']}\n")
        if messagebox.askyesno("Экспорт", "Экспортировать результат в CSV?"):
            p = filedialog.asksaveasfilename(defaultextension='.csv')
            if p:
                with open(p, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['month', 'actual_sum'])
                    for r in rows:
                        writer.writerow([r['month'].date(), r['actual_sum']])
                messagebox.showinfo("OK", f"Сохранено в {p}")

if __name__ == '__main__':
    app = ClientApp()
    app.mainloop()
