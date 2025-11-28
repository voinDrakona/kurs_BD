import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import psycopg2
from psycopg2 import sql
from datetime import datetime
import traceback

class DatabaseConfig:
    """Конфигурация подключения к БД"""
    HOST = "localhost"
    PORT = "5432"
    DATABASE = "contracts_db"
    USER = "vladislav"
    PASSWORD = "0000"

class DatabaseConnection:
    """Менеджер подключения к базе данных"""
    
    @staticmethod
    def get_connection():
        return psycopg2.connect(
            host=DatabaseConfig.HOST,
            port=DatabaseConfig.PORT,
            database=DatabaseConfig.DATABASE,
            user=DatabaseConfig.USER,
            password=DatabaseConfig.PASSWORD
        )
    
    @staticmethod
    def execute_query(query, params=None, fetch=True):
        """Выполнение SQL запроса"""
        conn = None
        try:
            conn = DatabaseConnection.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch:
                result = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                return result, columns
            else:
                conn.commit()
                return None, None
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

class TableFrame(tk.Frame):
    """Базовый фрейм для работы с таблицами"""
    
    def __init__(self, parent, table_name, columns_config):
        super().__init__(parent)
        self.table_name = table_name
        self.columns_config = columns_config
        self.current_data = []
        self.filtered_data = []
        self.sort_column = None
        self.sort_reverse = False
        
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Создание интерфейса"""
        # Toolbar
        toolbar = tk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(toolbar, text="Обновить", command=self.load_data).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Добавить", command=self.add_record).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Редактировать", command=self.edit_record).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Удалить", command=self.delete_record).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Поиск", command=self.search_dialog).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Фильтр", command=self.filter_dialog).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Сброс", command=self.reset_filter).pack(side=tk.LEFT, padx=2)
        
        # Treeview
        tree_frame = tk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        columns = [col['name'] for col in self.columns_config]
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings',
                                 yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure columns
        self.tree.column('#0', width=50, minwidth=50)
        self.tree.heading('#0', text='№')
        
        for col in self.columns_config:
            self.tree.column(col['name'], width=col.get('width', 100))
            self.tree.heading(col['name'], text=col['display'], 
                            command=lambda c=col['name']: self.sort_by_column(c))
        
        self.tree.bind('<Double-1>', lambda e: self.edit_record())
    
    def get_select_query(self):
        """Получить SELECT запрос для таблицы"""
        columns = ', '.join([col['db_field'] for col in self.columns_config])
        return f"SELECT {columns} FROM {self.table_name} ORDER BY {self.columns_config[0]['db_field']}"
    
    def load_data(self):
        """Загрузка данных из БД"""
        try:
            query = self.get_select_query()
            data, _ = DatabaseConnection.execute_query(query)
            self.current_data = data
            self.filtered_data = data
            self.display_data()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить данные:\n{str(e)}")
    
    def display_data(self):
        """Отображение данных в таблице"""
        self.tree.delete(*self.tree.get_children())
        
        for idx, row in enumerate(self.filtered_data, 1):
            self.tree.insert('', tk.END, text=str(idx), values=row)
    
    def sort_by_column(self, col):
        """Сортировка по столбцу"""
        col_idx = [c['name'] for c in self.columns_config].index(col)
        
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = False
        
        self.filtered_data = sorted(self.filtered_data, 
                                    key=lambda x: x[col_idx] if x[col_idx] is not None else '',
                                    reverse=self.sort_reverse)
        self.display_data()
    
    def get_selected_record(self):
        """Получить выбранную запись"""
        selection = self.tree.selection()
        if not selection:
            return None
        
        item = self.tree.item(selection[0])
        return item['values']
    
    def search_dialog(self):
        """Диалог поиска"""
        dialog = tk.Toplevel(self)
        dialog.title("Поиск")
        dialog.geometry("400x150")
        
        tk.Label(dialog, text="Поле:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        field_var = tk.StringVar()
        field_combo = ttk.Combobox(dialog, textvariable=field_var, 
                                   values=[col['display'] for col in self.columns_config])
        field_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        field_combo.current(0)
        
        tk.Label(dialog, text="Значение:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        value_var = tk.StringVar()
        tk.Entry(dialog, textvariable=value_var).grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        
        dialog.columnconfigure(1, weight=1)
        
        def do_search():
            field_idx = [col['display'] for col in self.columns_config].index(field_var.get())
            search_value = value_var.get().lower()
            
            self.filtered_data = [row for row in self.current_data 
                                 if search_value in str(row[field_idx]).lower()]
            self.display_data()
            dialog.destroy()
        
        tk.Button(dialog, text="Найти", command=do_search).grid(row=2, column=0, columnspan=2, pady=10)
    
    def filter_dialog(self):
        """Диалог фильтрации"""
        self.search_dialog()  # Используем тот же диалог
    
    def reset_filter(self):
        """Сброс фильтра"""
        self.filtered_data = self.current_data
        self.display_data()
    
    def add_record(self):
        """Добавление записи"""
        messagebox.showinfo("Информация", "Реализуйте в подклассе")
    
    def edit_record(self):
        """Редактирование записи"""
        messagebox.showinfo("Информация", "Реализуйте в подклассе")
    
    def delete_record(self):
        """Удаление записи"""
        messagebox.showinfo("Информация", "Реализуйте в подклассе")

class OrganizationsFrame(TableFrame):
    """Фрейм для работы с организациями"""
    
    def __init__(self, parent):
        columns = [
            {'name': 'org_id', 'display': 'ID', 'db_field': 'org_id', 'width': 50},
            {'name': 'name', 'display': 'Наименование', 'db_field': 'name', 'width': 200},
            {'name': 'inn', 'display': 'ИНН', 'db_field': 'inn', 'width': 120},
            {'name': 'address', 'display': 'Адрес', 'db_field': 'address', 'width': 250},
            {'name': 'phone', 'display': 'Телефон', 'db_field': 'phone', 'width': 120},
        ]
        super().__init__(parent, 'organizations', columns)
    
    def add_record(self):
        self.edit_dialog()
    
    def edit_record(self):
        record = self.get_selected_record()
        if record:
            self.edit_dialog(record)
        else:
            messagebox.showwarning("Предупреждение", "Выберите запись для редактирования")
    
    def edit_dialog(self, record=None):
        """Диалог добавления/редактирования"""
        dialog = tk.Toplevel(self)
        dialog.title("Организация" if not record else "Редактирование организации")
        dialog.geometry("500x400")
        
        fields = {}
        row = 0
        
        # ID (только для редактирования)
        if record:
            tk.Label(dialog, text="ID:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
            tk.Label(dialog, text=str(record[0])).grid(row=row, column=1, padx=5, pady=5, sticky=tk.W)
            row += 1
        
        # Наименование
        tk.Label(dialog, text="*Наименование:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['name'] = tk.Entry(dialog, width=40)
        fields['name'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if record: fields['name'].insert(0, record[1] or '')
        row += 1
        
        # ИНН
        tk.Label(dialog, text="ИНН:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['inn'] = tk.Entry(dialog, width=40)
        fields['inn'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if record: fields['inn'].insert(0, record[2] or '')
        row += 1
        
        # Адрес
        tk.Label(dialog, text="Адрес:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.NW)
        fields['address'] = tk.Text(dialog, width=40, height=3)
        fields['address'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if record: fields['address'].insert(1.0, record[3] or '')
        row += 1
        
        # Телефон
        tk.Label(dialog, text="Телефон:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['phone'] = tk.Entry(dialog, width=40)
        fields['phone'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if record: fields['phone'].insert(0, record[4] or '')
        row += 1
        
        dialog.columnconfigure(1, weight=1)
        
        def save():
            name = fields['name'].get().strip()
            if not name:
                messagebox.showerror("Ошибка", "Заполните обязательные поля (*)")
                return
            
            try:
                if record:
                    query = """UPDATE organizations 
                              SET name=%s, inn=%s, address=%s, phone=%s 
                              WHERE org_id=%s"""
                    params = (name, fields['inn'].get().strip() or None,
                             fields['address'].get(1.0, tk.END).strip() or None,
                             fields['phone'].get().strip() or None,
                             record[0])
                else:
                    query = """INSERT INTO organizations (name, inn, address, phone) 
                              VALUES (%s, %s, %s, %s)"""
                    params = (name, fields['inn'].get().strip() or None,
                             fields['address'].get(1.0, tk.END).strip() or None,
                             fields['phone'].get().strip() or None)
                
                DatabaseConnection.execute_query(query, params, fetch=False)
                messagebox.showinfo("Успех", "Данные сохранены")
                self.load_data()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить:\n{str(e)}")
        
        tk.Button(dialog, text="Сохранить", command=save).grid(row=row, column=0, columnspan=2, pady=10)
    
    def delete_record(self):
        record = self.get_selected_record()
        if not record:
            messagebox.showwarning("Предупреждение", "Выберите запись для удаления")
            return
        
        if messagebox.askyesno("Подтверждение", f"Удалить организацию '{record[1]}'?"):
            try:
                query = "DELETE FROM organizations WHERE org_id=%s"
                DatabaseConnection.execute_query(query, (record[0],), fetch=False)
                messagebox.showinfo("Успех", "Запись удалена")
                self.load_data()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить:\n{str(e)}")

class ContractsFrame(TableFrame):
    """Фрейм для работы с договорами"""
    
    def __init__(self, parent):
        columns = [
            {'name': 'contract_id', 'display': 'ID', 'db_field': 'contract_id', 'width': 50},
            {'name': 'contract_number', 'display': 'Номер', 'db_field': 'contract_number', 'width': 120},
            {'name': 'contract_date', 'display': 'Дата', 'db_field': 'contract_date', 'width': 100},
            {'name': 'customer_name', 'display': 'Заказчик', 'db_field': 'customer_name', 'width': 200},
            {'name': 'contractor_name', 'display': 'Исполнитель', 'db_field': 'contractor_name', 'width': 200},
            {'name': 'total_amount', 'display': 'Сумма', 'db_field': 'total_amount', 'width': 100},
            {'name': 'paid_amount', 'display': 'Оплачено', 'db_field': 'paid_amount', 'width': 100},
            {'name': 'debt_amount', 'display': 'Долг', 'db_field': 'debt_amount', 'width': 100},
        ]
        super().__init__(parent, 'view_contract_full', columns)
    
    def get_select_query(self):
        return "SELECT contract_id, contract_number, contract_date, customer_name, contractor_name, total_amount, paid_amount, debt_amount FROM view_contract_full ORDER BY contract_id"

class ReportsWindow(tk.Toplevel):
    """Окно отчетов"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Отчеты")
        self.geometry("900x600")
        
        # Список отчетов
        reports_frame = tk.Frame(self)
        reports_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        tk.Label(reports_frame, text="Выберите отчет:", font=('Arial', 12, 'bold')).pack(pady=5)
        
        tk.Button(reports_frame, text="Сведения по договорам", 
                 command=self.report_contract_details, width=25).pack(pady=2)
        tk.Button(reports_frame, text="Договора с долгом > 10000", 
                 command=self.report_contracts_with_debt, width=25).pack(pady=2)
        tk.Button(reports_frame, text="Сводка по оплатам", 
                 command=self.report_payments_summary, width=25).pack(pady=2)
        
        # Область отчета
        report_frame = tk.Frame(self)
        report_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        vsb = ttk.Scrollbar(report_frame, orient="vertical")
        hsb = ttk.Scrollbar(report_frame, orient="horizontal")
        
        self.report_tree = ttk.Treeview(report_frame, yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.config(command=self.report_tree.yview)
        hsb.config(command=self.report_tree.xscrollcommand)
        
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.report_tree.pack(fill=tk.BOTH, expand=True)
    
    def report_contract_details(self):
        """Отчет: Сведения по договорам"""
        try:
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
            GROUP BY c.contract_id, c.contract_number, c.contract_date, cust.name, contr.name,
                     c.total_amount, c.paid_amount, c.debt_amount
            ORDER BY c.contract_date DESC
            """
            
            data, columns = DatabaseConnection.execute_query(query)
            self.display_report(data, columns)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сформировать отчет:\n{str(e)}")
    
    def report_contracts_with_debt(self):
        """Отчет: Договора с долгом > 10000"""
        try:
            query = """
            SELECT 
                contract_number AS "Номер",
                customer_name AS "Заказчик",
                total_amount AS "Сумма",
                paid_amount AS "Оплачено",
                debt_amount AS "Долг"
            FROM view_contracts_with_debt_over_10000
            ORDER BY debt_amount DESC
            """
            
            data, columns = DatabaseConnection.execute_query(query)
            self.display_report(data, columns)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сформировать отчет:\n{str(e)}")
    
    def report_payments_summary(self):
        """Отчет: Сводка по оплатам"""
        try:
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
            GROUP BY c.contract_id, c.contract_number, cust.name
            HAVING COUNT(p.payment_id) > 0
            ORDER BY SUM(p.amount) DESC
            """
            
            data, columns = DatabaseConnection.execute_query(query)
            self.display_report(data, columns)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сформировать отчет:\n{str(e)}")
    
    def display_report(self, data, columns):
        """Отображение отчета"""
        self.report_tree.delete(*self.report_tree.get_children())
        
        self.report_tree['columns'] = columns
        self.report_tree['show'] = 'headings'
        
        for col in columns:
            self.report_tree.heading(col, text=col)
            self.report_tree.column(col, width=120)
        
        for row in data:
            self.report_tree.insert('', tk.END, values=row)

class MainApplication(tk.Tk):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Система управления договорами")
        self.geometry("1200x700")
        
        # Проверка подключения
        try:
            DatabaseConnection.get_connection().close()
        except Exception as e:
            messagebox.showerror("Ошибка подключения", 
                               f"Не удалось подключиться к базе данных:\n{str(e)}")
            self.destroy()
            return
        
        self.setup_menu()
        self.setup_ui()
    
    def setup_menu(self):
        """Создание меню"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # Меню Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Выход", command=self.quit)
        
        # Меню Отчеты
        reports_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Отчеты", menu=reports_menu)
        reports_menu.add_command(label="Открыть отчеты", command=self.open_reports)
        
        # Меню Справка
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)
    
    def setup_ui(self):
        """Создание интерфейса"""
        # Notebook для вкладок
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Вкладки
        self.notebook.add(OrganizationsFrame(self.notebook), text="Организации")
        self.notebook.add(ContractsFrame(self.notebook), text="Договора")
        
        # Строка состояния
        status_bar = tk.Label(self, text="Готов", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def open_reports(self):
        """Открыть окно отчетов"""
        ReportsWindow(self)
    
    def show_about(self):
        """О программе"""
        messagebox.showinfo("О программе", 
                          "Система управления договорами\nВерсия 1.0\n\nКурсовая работа по БД")

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()