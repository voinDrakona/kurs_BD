import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import csv
import db
import datetime

class ClientApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Клиент для БД — Договора")
        self.geometry("1000x700")

        # Левое меню: список таблиц
        left = ttk.Frame(self, width=200)
        left.pack(side='left', fill='y')
        ttk.Label(left, text="Таблицы").pack(padx=5, pady=5)
        self.table_list = tk.Listbox(left, height=20)
        self.table_list.pack(fill='y', padx=5)
        self.table_list.bind('<<ListboxSelect>>', self.on_table_select)

        # Кнопки
        btn_frame = ttk.Frame(left)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Обновить список", command=self.load_tables).pack(fill='x')
        ttk.Button(btn_frame, text="Отчёты", command=self.open_reports).pack(fill='x', pady=5)

        # Правый основной фрейм: дерево записей и форма
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
        self.tree.delete(*self.tree.get_children())
        self.tree['columns'] = self.columns
        for c in self.columns:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120, anchor='w')
        rows = db.fetch_rows(table)
        for r in rows:
            self.tree.insert('', tk.END, values=[r[c] for c in self.columns])

    def reload_table(self):
        if self.current_table:
            self.open_table(self.current_table)

    def add_row(self):
        if not self.current_table:
            messagebox.showinfo("Инфо", "Выберите таблицу слева")
            return
        # простая форма: спросим все колонки (кроме PK если serial)
        data = {}
        for col in self.columns:
            val = simpledialog.askstring("Добавить", f"{col}:", parent=self)
            if val is None:
                return
            data[col] = val
        try:
            db.insert_row(self.current_table, data)
            messagebox.showinfo("OK", "Запись добавлена")
            self.reload_table()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def on_edit_row(self, event):
        item = self.tree.focus()
        if not item:
            return
        values = self.tree.item(item)['values']
        pk_col = self.columns[0]  # упрощение: считаем 1-й столбец PK
        pk_val = values[0]
        data = {}
        for idx, col in enumerate(self.columns):
            new = simpledialog.askstring("Редактирование", f"{col}:", initialvalue=str(values[idx]), parent=self)
            if new is None:
                return
            data[col] = new
        try:
            db.update_row(self.current_table, pk_col, pk_val, data)
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
        # Для простоты: фильтр одного поля и сортировка по одному полю
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
        # Форма для добавления договора и сразу нескольких этапов (1:М)
        ContractForm(self)

    def open_reports(self):
        ReportsWindow(self)

class ContractForm(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Форма: Договор и этапы")
        self.geometry("700x500")
        self.parent = parent

        frm = ttk.Frame(self)
        frm.pack(fill='both', expand=True, padx=10, pady=10)

        ttk.Label(frm, text="Код договора:").grid(row=0, column=0, sticky='e')
        self.e_kod = ttk.Entry(frm); self.e_kod.grid(row=0, column=1, sticky='w')

        ttk.Label(frm, text="Тема:").grid(row=1, column=0, sticky='e')
        self.e_tema = ttk.Entry(frm); self.e_tema.grid(row=1, column=1, sticky='w')

        ttk.Label(frm, text="Код заказчика:").grid(row=2, column=0, sticky='e')
        self.e_zak = ttk.Entry(frm); self.e_zak.grid(row=2, column=1, sticky='w')

        ttk.Label(frm, text="Код исполнителя:").grid(row=3, column=0, sticky='e')
        self.e_isp = ttk.Entry(frm); self.e_isp.grid(row=3, column=1, sticky='w')

        # Список этапов
        ttk.Label(frm, text="Этапы (номер,дата,код стадии,сумма,аванс,тема):").grid(row=4, column=0, columnspan=2, sticky='w')
        self.etapy_text = tk.Text(frm, height=10, width=60)
        self.etapy_text.grid(row=5, column=0, columnspan=2, pady=5)

        ttk.Button(frm, text="Сохранить договор + этапы", command=self.save).grid(row=6, column=1, sticky='e', pady=8)

    def save(self):
        kod = self.e_kod.get().strip()
        tema = self.e_tema.get().strip()
        zak = self.e_zak.get().strip()
        isp = self.e_isp.get().strip()
        if not kod:
            messagebox.showerror("Ошибка", "Код договора обязателен")
            return
        # Вставим договор
        data = {
            '_код_договора_': kod,
            'тема': tema,
            'код_заказчика': zak,
            'код_исполнителя': isp,
            'дата_заключения': datetime.date.today()
        }
        try:
            # Если таблица называется иначе — замените ключи под вашу схему
            try:
                db.insert_row('dogovora', data)
            except Exception:
                # Попробуем упрощённый набор колонок (на случай, если schema другая)
                db.insert_row('dogovora', {'_код_договора_': kod, 'тема': tema})
        except Exception as e:
            messagebox.showerror("Ошибка при добавлении договора", str(e))
            return

        # Парсим этапы из текстового поля; каждая строка: номер,дата(YYYY-MM-DD),код_стадии,сумма,аванс,тема
        lines = self.etapy_text.get('1.0', 'end').strip().splitlines()
        for line in lines:
            if not line.strip(): continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 5:
                messagebox.showwarning("Пропуск", f"Строка этапа некорректна: {line}")
                continue
            number = parts[0]
            date_str = parts[1]
            kod_st = parts[2]
            suma = parts[3]
            avans = parts[4]
            tema_et = parts[5] if len(parts) > 5 else ''
            ep = {
                '_код_договора_': kod,
                '_номер_этапа_': number,
                'дата_исполнения_этапа': date_str,
                'код_стадии_исполнения': kod_st,
                'сумма_этапа': suma,
                'сумма_аванса': avans,
                'тема': tema_et
            }
            try:
                db.insert_row('etapy_dogovorov', ep)
            except Exception as e:
                messagebox.showwarning("Ошибка вставки этапа", f"{line}\n{e}")
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
        self.text.insert('end', "contract_id | тема | plan_sum | paid_sum | debt\n")
        for r in rows:
            self.text.insert('end', f"{r['contract_id']} | {r['тема']} | {r['plan_sum']} | {r['paid_sum']} | {r['debt']}\n")
        # экспорт
        if messagebox.askyesno("Экспорт", "Экспортировать результат в CSV?"):
            p = filedialog.asksaveasfilename(defaultextension='.csv')
            if p:
                with open(p, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['contract_id', 'тема', 'plan_sum', 'paid_sum', 'debt'])
                    for r in rows:
                        writer.writerow([r['contract_id'], r['тема'], r['plan_sum'], r['paid_sum'], r['debt']])
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
