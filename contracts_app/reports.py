import tkinter as tk
from tkinter import ttk, messagebox
from .db_config import DatabaseConnection

class ReportsWindow(tk.Toplevel):
    """Окно отчетов"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Отчеты")
        self.geometry("900x650")

        # === Левая панель — список отчётов ===
        reports_frame = tk.Frame(self, width=250)
        reports_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        reports_frame.pack_propagate(False)

        tk.Label(reports_frame, text="Доступные отчёты:", font=('Arial', 12, 'bold')).pack(pady=10)

        tk.Button(reports_frame, text="Сведения по договорам", 
                command=self.report_contract_details, width=28, height=2).pack(pady=4)
        tk.Button(reports_frame, text="Договора с долгом > 10000", 
                command=self.report_contracts_with_debt, width=28, height=2).pack(pady=4)
        tk.Button(reports_frame, text="Сводка по оплатам", 
                command=self.report_payments_summary, width=28, height=2).pack(pady=4)

        # === Правая часть — таблица отчёта ===
        report_frame = tk.Frame(self)
        report_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 1. Сначала создаём Treeview с привязкой скроллбаров
        self.report_tree = ttk.Treeview(report_frame, show="headings")

        # 2. Создаём скроллбары
        vsb = ttk.Scrollbar(report_frame, orient="vertical", command=self.report_tree.yview)
        hsb = ttk.Scrollbar(report_frame, orient="horizontal", command=self.report_tree.xview)  # ← xview, а не xscrollcommand!

        # 3. Привязываем скроллбары к Treeview
        self.report_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # 4. Упаковываем всё
        self.report_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
    
    def report_contract_details(self):
        """Отчет: Сведения по договорам + фильтры"""
        dlg = SimpleReportFilterDialog(self)
        self.wait_window(dlg)
        if not dlg.result: 
            return
        f = dlg.result

        query = """
            SELECT
                c.contract_number AS "Номер договора",
                c.contract_date AS "Дата",
                cust.name AS "Заказчик",
                contr.name AS "Исполнитель",
                c.total_amount AS "Сумма договора",
                c.paid_amount AS "Оплачено",
                c.debt_amount AS "Задолженность",
                COUNT(DISTINCT cm.milestone_no) AS "Этапов",
                COUNT(DISTINCT p.payment_id) AS "Платежей"
            FROM contracts c
            LEFT JOIN organizations cust ON cust.org_id = c.customer_org_id
            LEFT JOIN organizations contr ON contr.org_id = c.contractor_org_id
            LEFT JOIN contract_milestones cm ON cm.contract_id = c.contract_id
            LEFT JOIN payments p ON p.contract_id = c.contract_id
            WHERE 1=1
        """
        params = []
        if f['date_from']:
            query += " AND c.contract_date >= %s"; params.append(f['date_from'])
        if f['date_to']:
            query += " AND c.contract_date <= %s"; params.append(f['date_to'])
        if f['customer']:
            query += " AND cust.name ILIKE %s"; params.append(f"%{f['customer']}%")
        if f['min_debt'] > 0:
            query += " HAVING c.debt_amount >= %s"; params.append(f['min_debt'])

        query += f"""
            GROUP BY c.contract_id, c.contract_number, c.contract_date, cust.name, contr.name,
                     c.total_amount, c.paid_amount, c.debt_amount
            ORDER BY {f['sort']} {f['order']}
        """

        try:
            data, columns = DatabaseConnection.execute_query(query, params)
            self.display_report(data, columns, title="Сведения по договорам")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сформировать отчёт:\n{str(e)}")

    def report_contracts_with_debt(self):
        """Отчет: Договора с долгом + фильтры"""
        dlg = SimpleReportFilterDialog(self)
        self.wait_window(dlg)
        if not dlg.result: return
        f = dlg.result

        query = """
            SELECT
                c.contract_number AS "Номер",
                cust.name AS "Заказчик",
                c.total_amount AS "Сумма",
                c.paid_amount AS "Оплачено",
                c.debt_amount AS "Долг"
            FROM contracts c
            JOIN organizations cust ON cust.org_id = c.customer_org_id
            WHERE c.debt_amount > 10000
        """
        params = []
        if f['min_debt'] > 10000:
            query += " AND c.debt_amount >= %s"; params.append(f['min_debt'])
        if f['customer']:
            query += " AND cust.name ILIKE %s"; params.append(f"%{f['customer']}%")

        query += f" ORDER BY {f['sort']} {f['order']}"

        try:
            data, columns = DatabaseConnection.execute_query(query, params)
            self.display_report(data, columns, title="Договора с задолженностью")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сформировать отчёт:\n{str(e)}")

    def report_payments_summary(self):
        """Отчет: Сводка по оплатам + фильтры"""
        dlg = SimpleReportFilterDialog(self)
        self.wait_window(dlg)
        if not dlg.result: return
        f = dlg.result

        query = """
            SELECT
                c.contract_number AS "Номер договора",
                cust.name AS "Заказчик",
                COUNT(p.payment_id) AS "Кол-во платежей",
                SUM(p.amount) AS "Сумма оплат",
                MAX(p.payment_date) AS "Последняя оплата"
            FROM contracts c
            LEFT JOIN organizations cust ON cust.org_id = c.customer_org_id
            LEFT JOIN payments p ON p.contract_id = c.contract_id
            WHERE 1=1
        """
        params = []
        if f['date_from']:
            query += " AND p.payment_date >= %s"; params.append(f['date_from'])
        if f['date_to']:
            query += " AND p.payment_date <= %s"; params.append(f['date_to'])
        if f['customer']:
            query += " AND cust.name ILIKE %s"; params.append(f"%{f['customer']}%")

        query += """
            GROUP BY c.contract_id, c.contract_number, cust.name
            HAVING COUNT(p.payment_id) > 0
            ORDER BY SUM(p.amount) DESC
        """

        try:
            data, columns = DatabaseConnection.execute_query(query, params)
            self.display_report(data, columns, title="Сводка по оплатам")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сформировать отчёт:\n{str(e)}")
    
    def display_report(self, data, columns, title="Отчёт"):
        """Отображение отчета"""
        self.report_tree.delete(*self.report_tree.get_children())
        
        self.report_tree['columns'] = columns
        self.report_tree['show'] = 'headings'
        
        for col in columns:
            self.report_tree.heading(col, text=col)
            self.report_tree.column(col, width=120)
        
        for row in data:
            self.report_tree.insert('', tk.END, values=row)


class SimpleReportFilterDialog(tk.Toplevel):
    def __init__(self, parent, title="Фильтры и сортировка"):
        super().__init__(parent)
        self.title(title)
        self.geometry("380x520")
        self.resizable(False, False)
        self.result = None

        tk.Label(self, text="Параметры отчёта", font=("Arial", 14, "bold")).pack(pady=10)

        # Период договора
        tk.Label(self, text="Дата договора от:").pack(anchor="w", padx=20)
        self.e_from = tk.Entry(self, width=20)
        self.e_from.pack(pady=2, padx=20)

        tk.Label(self, text="Дата договора до:").pack(anchor="w", padx=20)
        self.e_to = tk.Entry(self, width=20)
        self.e_to.pack(pady=2, padx=20)

        # Заказчик (по части названия)
        tk.Label(self, text="Заказчик (содержит):").pack(anchor="w", padx=20)
        self.e_customer = tk.Entry(self, width=40)
        self.e_customer.pack(pady=2, padx=20)

        # Минимальный долг (только для отчётов с долгом)
        tk.Label(self, text="Минимальный долг:").pack(anchor="w", padx=20)
        self.e_min_debt = tk.Entry(self, width=20)
        self.e_min_debt.insert(0, "0")
        self.e_min_debt.pack(pady=2, padx=20)

        # Сортировка
        tk.Label(self, text="Сортировать по:", font=("Arial", 10, "bold")).pack(pady=(15,5), anchor="w", padx=20)
        self.sort_var = tk.StringVar(value="debt_amount")
        options = [
            ("debt_amount", "Задолженность"),
            ("contract_date", "Дата договора"),
            ("contract_number", "Номер договора"),
            ("customer", "Заказчик"),
            ("total_amount", "Сумма договора")
        ]
        for val, text in options:
            tk.Radiobutton(self, text=text, variable=self.sort_var, value=val).pack(anchor="w", padx=40)

        self.order_var = tk.StringVar(value="DESC")
        frame_order = tk.Frame(self)
        frame_order.pack(pady=10)
        tk.Radiobutton(frame_order, text="По убыванию", variable=self.order_var, value="DESC").pack(side=tk.LEFT, padx=20)
        tk.Radiobutton(frame_order, text="По возрастанию", variable=self.order_var, value="ASC").pack(side=tk.LEFT, padx=20)

        btns = tk.Frame(self)
        btns.pack(pady=20)
        tk.Button(btns, text="Сформировать", command=self.ok, bg="#90ee90", width=15).pack(side=tk.LEFT, padx=10)
        tk.Button(btns, text="Отмена", command=self.destroy, width=15).pack(side=tk.LEFT, padx=10)

    def ok(self):
        try:
            min_debt = float(self.e_min_debt.get() or 0)
        except:
            min_debt = 0

        self.result = {
            'date_from': self.e_from.get().strip() or None,
            'date_to': self.e_to.get().strip() or None,
            'customer': self.e_customer.get().strip() or None,
            'min_debt': min_debt,
            'sort': self.sort_var.get(),
            'order': self.order_var.get()
        }
        self.destroy()