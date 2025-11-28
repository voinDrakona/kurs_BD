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

class ContractTypesFrame(TableFrame):
    """Фрейм для работы с типами договоров"""
    
    def __init__(self, parent):
        columns = [
            {'name': 'contract_type_id', 'display': 'ID', 'db_field': 'contract_type_id', 'width': 50},
            {'name': 'name', 'display': 'Наименование', 'db_field': 'name', 'width': 200},
        ]
        super().__init__(parent, 'contract_types', columns)
    
    def add_record(self):
        self.edit_dialog()
    
    def edit_record(self):
        record = self.get_selected_record()
        if record:
            self.edit_dialog(record)
        else:
            messagebox.showwarning("Предупреждение", "Выберите запись для редактирования")
    
    def edit_dialog(self, record=None):
        dialog = tk.Toplevel(self)
        dialog.title("Тип договора" if not record else "Редактирование типа договора")
        dialog.geometry("400x200")
        
        fields = {}
        row = 0
        
        if record:
            tk.Label(dialog, text="ID:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
            tk.Label(dialog, text=str(record[0])).grid(row=row, column=1, padx=5, pady=5, sticky=tk.W)
            row += 1
        
        tk.Label(dialog, text="*Наименование:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['name'] = tk.Entry(dialog, width=30)
        fields['name'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if record: fields['name'].insert(0, record[1] or '')
        row += 1
        
        dialog.columnconfigure(1, weight=1)
        
        def save():
            name = fields['name'].get().strip()
            if not name:
                messagebox.showerror("Ошибка", "Заполните обязательные поля (*)")
                return
            
            try:
                if record:
                    query = "UPDATE contract_types SET name=%s WHERE contract_type_id=%s"
                    params = (name, record[0])
                else:
                    query = "INSERT INTO contract_types (name) VALUES (%s)"
                    params = (name,)
                
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
        
        if messagebox.askyesno("Подтверждение", f"Удалить тип договора '{record[1]}'?"):
            try:
                query = "DELETE FROM contract_types WHERE contract_type_id=%s"
                DatabaseConnection.execute_query(query, (record[0],), fetch=False)
                messagebox.showinfo("Успех", "Запись удалена")
                self.load_data()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить:\n{str(e)}")

class ExecutionStagesFrame(TableFrame):
    """Фрейм для работы с этапами исполнения"""
    
    def __init__(self, parent):
        columns = [
            {'name': 'stage_id', 'display': 'ID', 'db_field': 'stage_id', 'width': 50},
            {'name': 'name', 'display': 'Наименование', 'db_field': 'name', 'width': 200},
        ]
        super().__init__(parent, 'execution_stages', columns)
    
    def add_record(self):
        self.edit_dialog()
    
    def edit_record(self):
        record = self.get_selected_record()
        if record:
            self.edit_dialog(record)
        else:
            messagebox.showwarning("Предупреждение", "Выберите запись для редактирования")
    
    def edit_dialog(self, record=None):
        dialog = tk.Toplevel(self)
        dialog.title("Этап исполнения" if not record else "Редактирование этапа исполнения")
        dialog.geometry("400x200")
        
        fields = {}
        row = 0
        
        if record:
            tk.Label(dialog, text="ID:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
            tk.Label(dialog, text=str(record[0])).grid(row=row, column=1, padx=5, pady=5, sticky=tk.W)
            row += 1
        
        tk.Label(dialog, text="*Наименование:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['name'] = tk.Entry(dialog, width=30)
        fields['name'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if record: fields['name'].insert(0, record[1] or '')
        row += 1
        
        dialog.columnconfigure(1, weight=1)
        
        def save():
            name = fields['name'].get().strip()
            if not name:
                messagebox.showerror("Ошибка", "Заполните обязательные поля (*)")
                return
            
            try:
                if record:
                    query = "UPDATE execution_stages SET name=%s WHERE stage_id=%s"
                    params = (name, record[0])
                else:
                    query = "INSERT INTO execution_stages (name) VALUES (%s)"
                    params = (name,)
                
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
        
        if messagebox.askyesno("Подтверждение", f"Удалить этап исполнения '{record[1]}'?"):
            try:
                query = "DELETE FROM execution_stages WHERE stage_id=%s"
                DatabaseConnection.execute_query(query, (record[0],), fetch=False)
                messagebox.showinfo("Успех", "Запись удалена")
                self.load_data()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить:\n{str(e)}")

class VatRatesFrame(TableFrame):
    """Фрейм для работы со ставками НДС"""
    
    def __init__(self, parent):
        columns = [
            {'name': 'vat_id', 'display': 'ID', 'db_field': 'vat_id', 'width': 50},
            {'name': 'percent', 'display': 'Процент', 'db_field': 'percent', 'width': 200},
        ]
        super().__init__(parent, 'vat_rates', columns)
    
    def add_record(self):
        self.edit_dialog()
    
    def edit_record(self):
        record = self.get_selected_record()
        if record:
            self.edit_dialog(record)
        else:
            messagebox.showwarning("Предупреждение", "Выберите запись для редактирования")
    
    def edit_dialog(self, record=None):
        dialog = tk.Toplevel(self)
        dialog.title("Ставка НДС" if not record else "Редактирование ставки НДС")
        dialog.geometry("400x200")
        
        fields = {}
        row = 0
        
        if record:
            tk.Label(dialog, text="ID:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
            tk.Label(dialog, text=str(record[0])).grid(row=row, column=1, padx=5, pady=5, sticky=tk.W)
            row += 1
        
        tk.Label(dialog, text="*Процент:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['percent'] = tk.Entry(dialog, width=30)
        fields['percent'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if record: fields['percent'].insert(0, str(record[1]) if record[1] is not None else '')
        row += 1
        
        dialog.columnconfigure(1, weight=1)
        
        def save():
            percent_str = fields['percent'].get().strip()
            if not percent_str:
                messagebox.showerror("Ошибка", "Заполните обязательные поля (*)")
                return
            try:
                percent = float(percent_str)
            except ValueError:
                messagebox.showerror("Ошибка", "Процент должен быть числом")
                return
            
            try:
                if record:
                    query = "UPDATE vat_rates SET percent=%s WHERE vat_id=%s"
                    params = (percent, record[0])
                else:
                    query = "INSERT INTO vat_rates (percent) VALUES (%s)"
                    params = (percent,)
                
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
        
        if messagebox.askyesno("Подтверждение", f"Удалить ставку НДС '{record[1]}'?"):
            try:
                query = "DELETE FROM vat_rates WHERE vat_id=%s"
                DatabaseConnection.execute_query(query, (record[0],), fetch=False)
                messagebox.showinfo("Успех", "Запись удалена")
                self.load_data()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить:\n{str(e)}")

class PaymentMethodsFrame(TableFrame):
    """Фрейм для работы со способами оплаты"""
    
    def __init__(self, parent):
        columns = [
            {'name': 'payment_method_id', 'display': 'ID', 'db_field': 'payment_method_id', 'width': 50},
            {'name': 'name', 'display': 'Наименование', 'db_field': 'name', 'width': 200},
        ]
        super().__init__(parent, 'payment_methods', columns)
    
    def add_record(self):
        self.edit_dialog()
    
    def edit_record(self):
        record = self.get_selected_record()
        if record:
            self.edit_dialog(record)
        else:
            messagebox.showwarning("Предупреждение", "Выберите запись для редактирования")
    
    def edit_dialog(self, record=None):
        dialog = tk.Toplevel(self)
        dialog.title("Способ оплаты" if not record else "Редактирование способа оплаты")
        dialog.geometry("400x200")
        
        fields = {}
        row = 0
        
        if record:
            tk.Label(dialog, text="ID:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
            tk.Label(dialog, text=str(record[0])).grid(row=row, column=1, padx=5, pady=5, sticky=tk.W)
            row += 1
        
        tk.Label(dialog, text="*Наименование:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['name'] = tk.Entry(dialog, width=30)
        fields['name'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if record: fields['name'].insert(0, record[1] or '')
        row += 1
        
        dialog.columnconfigure(1, weight=1)
        
        def save():
            name = fields['name'].get().strip()
            if not name:
                messagebox.showerror("Ошибка", "Заполните обязательные поля (*)")
                return
            
            try:
                if record:
                    query = "UPDATE payment_methods SET name=%s WHERE payment_method_id=%s"
                    params = (name, record[0])
                else:
                    query = "INSERT INTO payment_methods (name) VALUES (%s)"
                    params = (name,)
                
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
        
        if messagebox.askyesno("Подтверждение", f"Удалить способ оплаты '{record[1]}'?"):
            try:
                query = "DELETE FROM payment_methods WHERE payment_method_id=%s"
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
    
    def add_record(self):
        self.edit_dialog()
    
    def edit_record(self):
        record = self.get_selected_record()
        if record:
            self.edit_dialog(record)
        else:
            messagebox.showwarning("Предупреждение", "Выберите запись для редактирования")
    
    def edit_dialog(self, record=None):
        dialog = tk.Toplevel(self)
        dialog.title("Договор" if not record else "Редактирование договора")
        dialog.geometry("600x600")
        
        edit_data = None
        if record:
            contract_id = record[0]
            query = """
                SELECT contract_number, contract_date, customer_org_id, contractor_org_id, 
                       contract_type_id, current_stage_id, vat_id, execution_date, 
                       subject, note, is_active
                FROM contracts WHERE contract_id = %s
            """
            data, _ = DatabaseConnection.execute_query(query, (contract_id,))
            if data:
                edit_data = data[0]
        
        # Fetch lookups
        orgs_data, _ = DatabaseConnection.execute_query("SELECT org_id, name FROM organizations ORDER BY name")
        org_names = [name for _, name in orgs_data]
        org_id_to_name = {org_id: name for org_id, name in orgs_data}
        org_name_to_id = {name: org_id for org_id, name in orgs_data}
        
        types_data, _ = DatabaseConnection.execute_query("SELECT contract_type_id, name FROM contract_types ORDER BY name")
        type_names = [name for _, name in types_data]
        type_id_to_name = {tid: name for tid, name in types_data}
        type_name_to_id = {name: tid for tid, name in types_data}
        
        stages_data, _ = DatabaseConnection.execute_query("SELECT stage_id, name FROM execution_stages ORDER BY name")
        stage_names = [name for _, name in stages_data]
        stage_id_to_name = {sid: name for sid, name in stages_data}
        stage_name_to_id = {name: sid for sid, name in stages_data}
        
        vats_data, _ = DatabaseConnection.execute_query("SELECT vat_id, percent FROM vat_rates ORDER BY percent")
        vat_names = [str(percent) for _, percent in vats_data]
        vat_id_to_name = {vid: str(percent) for vid, percent in vats_data}
        vat_name_to_id = {str(percent): vid for vid, percent in vats_data}
        
        fields = {}
        vars = {}
        row = 0
        
        if record:
            tk.Label(dialog, text="ID:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
            tk.Label(dialog, text=str(record[0])).grid(row=row, column=1, padx=5, pady=5, sticky=tk.W)
            row += 1
        
        # Номер
        tk.Label(dialog, text="*Номер:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['contract_number'] = tk.Entry(dialog, width=40)
        fields['contract_number'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if edit_data: fields['contract_number'].insert(0, edit_data[0] or '')
        row += 1
        
        # Дата
        tk.Label(dialog, text="*Дата (YYYY-MM-DD):").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['contract_date'] = tk.Entry(dialog, width=40)
        fields['contract_date'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if edit_data: fields['contract_date'].insert(0, str(edit_data[1]) if edit_data[1] else '')
        row += 1
        
        # Заказчик
        tk.Label(dialog, text="*Заказчик:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        vars['customer'] = tk.StringVar(value=org_id_to_name.get(edit_data[2] if edit_data else None, ''))
        ttk.Combobox(dialog, textvariable=vars['customer'], values=org_names, width=37).grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        row += 1
        
        # Исполнитель
        tk.Label(dialog, text="*Исполнитель:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        vars['contractor'] = tk.StringVar(value=org_id_to_name.get(edit_data[3] if edit_data else None, ''))
        ttk.Combobox(dialog, textvariable=vars['contractor'], values=org_names, width=37).grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        row += 1
        
        # Тип договора
        tk.Label(dialog, text="*Тип договора:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        vars['contract_type'] = tk.StringVar(value=type_id_to_name.get(edit_data[4] if edit_data else None, ''))
        ttk.Combobox(dialog, textvariable=vars['contract_type'], values=type_names, width=37).grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        row += 1
        
        # Текущий этап
        tk.Label(dialog, text="Текущий этап:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        vars['current_stage'] = tk.StringVar(value=stage_id_to_name.get(edit_data[5] if edit_data else None, ''))
        ttk.Combobox(dialog, textvariable=vars['current_stage'], values=stage_names, width=37).grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        row += 1
        
        # НДС
        tk.Label(dialog, text="НДС (%):").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        vars['vat'] = tk.StringVar(value=vat_id_to_name.get(edit_data[6] if edit_data else None, ''))
        ttk.Combobox(dialog, textvariable=vars['vat'], values=vat_names, width=37).grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        row += 1
        
        # Дата исполнения
        tk.Label(dialog, text="Дата исполнения (YYYY-MM-DD):").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['execution_date'] = tk.Entry(dialog, width=40)
        fields['execution_date'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if edit_data: fields['execution_date'].insert(0, str(edit_data[7]) if edit_data[7] else '')
        row += 1
        
        # Предмет
        tk.Label(dialog, text="Предмет:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.NW)
        fields['subject'] = tk.Text(dialog, width=40, height=3)
        fields['subject'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if edit_data: fields['subject'].insert(1.0, edit_data[8] or '')
        row += 1
        
        # Примечание
        tk.Label(dialog, text="Примечание:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.NW)
        fields['note'] = tk.Text(dialog, width=40, height=3)
        fields['note'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if edit_data: fields['note'].insert(1.0, edit_data[9] or '')
        row += 1
        
        # Активен
        vars['is_active'] = tk.BooleanVar(value=edit_data[10] if edit_data else True)
        tk.Checkbutton(dialog, text="Активен", variable=vars['is_active']).grid(row=row, column=0, columnspan=2, pady=5)
        row += 1
        
        dialog.columnconfigure(1, weight=1)
        
        def save():
            number = fields['contract_number'].get().strip()
            date_str = fields['contract_date'].get().strip()
            customer_name = vars['customer'].get()
            contractor_name = vars['contractor'].get()
            type_name = vars['contract_type'].get()
            stage_name = vars['current_stage'].get()
            vat_name = vars['vat'].get()
            execution_date_str = fields['execution_date'].get().strip()
            subject = fields['subject'].get(1.0, tk.END).strip() or None
            note = fields['note'].get(1.0, tk.END).strip() or None
            is_active = vars['is_active'].get()
            
            if not all([number, date_str, customer_name, contractor_name, type_name]):
                messagebox.showerror("Ошибка", "Заполните обязательные поля (*)")
                return
            
            try:
                contract_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                execution_date = datetime.strptime(execution_date_str, '%Y-%m-%d').date() if execution_date_str else None
            except ValueError:
                messagebox.showerror("Ошибка", "Неверный формат даты (YYYY-MM-DD)")
                return
            
            customer_id = org_name_to_id.get(customer_name)
            contractor_id = org_name_to_id.get(contractor_name)
            type_id = type_name_to_id.get(type_name)
            stage_id = stage_name_to_id.get(stage_name) if stage_name else None
            vat_id = vat_name_to_id.get(vat_name) if vat_name else None
            
            if not all([customer_id, contractor_id, type_id]):
                messagebox.showerror("Ошибка", "Неверные значения списков")
                return
            
            try:
                if record:
                    query = """
                        UPDATE contracts SET contract_number=%s, contract_date=%s, customer_org_id=%s, 
                                             contractor_org_id=%s, contract_type_id=%s, current_stage_id=%s, 
                                             vat_id=%s, execution_date=%s, subject=%s, note=%s, is_active=%s 
                        WHERE contract_id=%s
                    """
                    params = (number, contract_date, customer_id, contractor_id, type_id, stage_id, 
                              vat_id, execution_date, subject, note, is_active, record[0])
                else:
                    query = """
                        INSERT INTO contracts (contract_number, contract_date, customer_org_id, 
                                               contractor_org_id, contract_type_id, current_stage_id, 
                                               vat_id, execution_date, subject, note, is_active) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    params = (number, contract_date, customer_id, contractor_id, type_id, stage_id, 
                              vat_id, execution_date, subject, note, is_active)
                
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
        
        if messagebox.askyesno("Подтверждение", f"Удалить договор '{record[1]}'?"):
            try:
                query = "DELETE FROM contracts WHERE contract_id=%s"
                DatabaseConnection.execute_query(query, (record[0],), fetch=False)
                messagebox.showinfo("Успех", "Запись удалена")
                self.load_data()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить:\n{str(e)}")

class ContractMilestonesFrame(TableFrame):
    """Фрейм для работы с этапами договоров"""
    
    def __init__(self, parent):
        columns = [
            {'name': 'contract_id', 'display': 'ID договора', 'db_field': 'cm.contract_id', 'width': 80},
            {'name': 'milestone_no', 'display': '№ этапа', 'db_field': 'cm.milestone_no', 'width': 80},
            {'name': 'contract_number', 'display': 'Номер договора', 'db_field': 'c.contract_number', 'width': 120},
            {'name': 'milestone_date', 'display': 'Дата', 'db_field': 'cm.milestone_date', 'width': 100},
            {'name': 'stage_name', 'display': 'Этап', 'db_field': 'es.name', 'width': 150},
            {'name': 'amount', 'display': 'Сумма', 'db_field': 'cm.amount', 'width': 100},
            {'name': 'advance_amount', 'display': 'Аванс', 'db_field': 'cm.advance_amount', 'width': 100},
            {'name': 'subject', 'display': 'Предмет', 'db_field': 'cm.subject', 'width': 200},
        ]
        super().__init__(parent, 'contract_milestones', columns)
    
    def get_select_query(self):
        return """
            SELECT cm.contract_id, cm.milestone_no, c.contract_number, cm.milestone_date, 
                   es.name as stage_name, cm.amount, cm.advance_amount, cm.subject 
            FROM contract_milestones cm 
            JOIN contracts c ON c.contract_id = cm.contract_id 
            LEFT JOIN execution_stages es ON es.stage_id = cm.stage_id 
            ORDER BY cm.contract_id, cm.milestone_no
        """
    
    def add_record(self):
        self.edit_dialog()
    
    def edit_record(self):
        record = self.get_selected_record()
        if record:
            self.edit_dialog(record)
        else:
            messagebox.showwarning("Предупреждение", "Выберите запись для редактирования")
    
    def edit_dialog(self, record=None):
        dialog = tk.Toplevel(self)
        dialog.title("Этап договора" if not record else "Редактирование этапа договора")
        dialog.geometry("500x500")
        
        # Fetch lookups
        contracts_data, _ = DatabaseConnection.execute_query("SELECT contract_id, contract_number FROM contracts ORDER BY contract_number")
        contract_numbers = [number for _, number in contracts_data]
        contract_id_to_number = {cid: number for cid, number in contracts_data}
        contract_number_to_id = {number: cid for cid, number in contracts_data}
        
        stages_data, _ = DatabaseConnection.execute_query("SELECT stage_id, name FROM execution_stages ORDER BY name")
        stage_names = [name for _, name in stages_data]
        stage_id_to_name = {sid: name for sid, name in stages_data}
        stage_name_to_id = {name: sid for sid, name in stages_data}
        
        fields = {}
        vars = {}
        row = 0
        
        if record:
            tk.Label(dialog, text="ID договора:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
            tk.Label(dialog, text=str(record[0])).grid(row=row, column=1, padx=5, pady=5, sticky=tk.W)
            row += 1
            
            tk.Label(dialog, text="№ этапа:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
            tk.Label(dialog, text=str(record[1])).grid(row=row, column=1, padx=5, pady=5, sticky=tk.W)
            row += 1
        
        # Договор
        tk.Label(dialog, text="*Договор:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        vars['contract'] = tk.StringVar(value=contract_id_to_number.get(record[0] if record else None, ''))
        ttk.Combobox(dialog, textvariable=vars['contract'], values=contract_numbers, width=37).grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        row += 1
        
        # № этапа
        if not record:
            tk.Label(dialog, text="*№ этапа:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
            fields['milestone_no'] = tk.Entry(dialog, width=40)
            fields['milestone_no'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
            row += 1
        
        # Дата
        tk.Label(dialog, text="Дата (YYYY-MM-DD):").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['milestone_date'] = tk.Entry(dialog, width=40)
        fields['milestone_date'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if record: fields['milestone_date'].insert(0, str(record[3]) if record[3] else '')
        row += 1
        
        # Этап
        tk.Label(dialog, text="Этап:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        vars['stage'] = tk.StringVar(value=record[4] if record else '')
        ttk.Combobox(dialog, textvariable=vars['stage'], values=stage_names, width=37).grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        row += 1
        
        # Сумма
        tk.Label(dialog, text="*Сумма:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['amount'] = tk.Entry(dialog, width=40)
        fields['amount'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if record: fields['amount'].insert(0, str(record[5]) if record[5] is not None else '0')
        row += 1
        
        # Аванс
        tk.Label(dialog, text="Аванс:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['advance_amount'] = tk.Entry(dialog, width=40)
        fields['advance_amount'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if record: fields['advance_amount'].insert(0, str(record[6]) if record[6] is not None else '0')
        row += 1
        
        # Предмет
        tk.Label(dialog, text="Предмет:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.NW)
        fields['subject'] = tk.Text(dialog, width=40, height=3)
        fields['subject'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if record: fields['subject'].insert(1.0, record[7] or '')
        row += 1
        
        dialog.columnconfigure(1, weight=1)
        
        def save():
            contract_name = vars['contract'].get()
            if not contract_name:
                messagebox.showerror("Ошибка", "Выберите договор")
                return
            contract_id_val = contract_number_to_id[contract_name]
            
            if record:
                milestone_no_val = record[1]
            else:
                milestone_no_str = fields['milestone_no'].get().strip()
                if not milestone_no_str:
                    messagebox.showerror("Ошибка", "Заполните № этапа")
                    return
                try:
                    milestone_no_val = int(milestone_no_str)
                except ValueError:
                    messagebox.showerror("Ошибка", "№ этапа должен быть числом")
                    return
            
            date_str = fields['milestone_date'].get().strip()
            milestone_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
            
            stage_name = vars['stage'].get()
            stage_id = stage_name_to_id.get(stage_name) if stage_name else None
            
            amount_str = fields['amount'].get().strip()
            if not amount_str:
                messagebox.showerror("Ошибка", "Заполните сумму")
                return
            try:
                amount = float(amount_str)
            except ValueError:
                messagebox.showerror("Ошибка", "Сумма должна быть числом")
                return
            
            advance_str = fields['advance_amount'].get().strip()
            try:
                advance_amount = float(advance_str) if advance_str else 0.0
            except ValueError:
                messagebox.showerror("Ошибка", "Аванс должен быть числом")
                return
            
            subject = fields['subject'].get(1.0, tk.END).strip() or None
            
            try:
                if record:
                    query = """
                        UPDATE contract_milestones SET milestone_date=%s, stage_id=%s, amount=%s, 
                                                       advance_amount=%s, subject=%s 
                        WHERE contract_id=%s AND milestone_no=%s
                    """
                    params = (milestone_date, stage_id, amount, advance_amount, subject, 
                              contract_id_val, milestone_no_val)
                else:
                    query = """
                        INSERT INTO contract_milestones (contract_id, milestone_no, milestone_date, 
                                                         stage_id, amount, advance_amount, subject) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    params = (contract_id_val, milestone_no_val, milestone_date, stage_id, 
                              amount, advance_amount, subject)
                
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
        
        if messagebox.askyesno("Подтверждение", f"Удалить этап №{record[1]} договора {record[2]}?"):
            try:
                query = "DELETE FROM contract_milestones WHERE contract_id=%s AND milestone_no=%s"
                DatabaseConnection.execute_query(query, (record[0], record[1]), fetch=False)
                messagebox.showinfo("Успех", "Запись удалена")
                self.load_data()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить:\n{str(e)}")

class PaymentsFrame(TableFrame):
    """Фрейм для работы с оплатами"""
    
    def __init__(self, parent):
        columns = [
            {'name': 'payment_id', 'display': 'ID', 'db_field': 'p.payment_id', 'width': 50},
            {'name': 'contract_id', 'display': 'ID договора', 'db_field': 'p.contract_id', 'width': 80},
            {'name': 'contract_number', 'display': 'Номер договора', 'db_field': 'c.contract_number', 'width': 120},
            {'name': 'payment_date', 'display': 'Дата', 'db_field': 'p.payment_date', 'width': 100},
            {'name': 'amount', 'display': 'Сумма', 'db_field': 'p.amount', 'width': 100},
            {'name': 'payment_method_name', 'display': 'Способ оплаты', 'db_field': 'pm.name', 'width': 150},
            {'name': 'payment_doc_number', 'display': '№ документа', 'db_field': 'p.payment_doc_number', 'width': 150},
        ]
        super().__init__(parent, 'payments', columns)
    
    def get_select_query(self):
        return """
            SELECT p.payment_id, p.contract_id, c.contract_number, p.payment_date, 
                   p.amount, pm.name as payment_method_name, p.payment_doc_number 
            FROM payments p 
            JOIN contracts c ON c.contract_id = p.contract_id 
            LEFT JOIN payment_methods pm ON pm.payment_method_id = p.payment_method_id 
            ORDER BY p.payment_id
        """
    
    def add_record(self):
        self.edit_dialog()
    
    def edit_record(self):
        record = self.get_selected_record()
        if record:
            self.edit_dialog(record)
        else:
            messagebox.showwarning("Предупреждение", "Выберите запись для редактирования")
    
    def edit_dialog(self, record=None):
        dialog = tk.Toplevel(self)
        dialog.title("Оплата" if not record else "Редактирование оплаты")
        dialog.geometry("500x400")
        
        # Fetch lookups
        contracts_data, _ = DatabaseConnection.execute_query("SELECT contract_id, contract_number FROM contracts ORDER BY contract_number")
        contract_numbers = [number for _, number in contracts_data]
        contract_id_to_number = {cid: number for cid, number in contracts_data}
        contract_number_to_id = {number: cid for cid, number in contracts_data}
        
        methods_data, _ = DatabaseConnection.execute_query("SELECT payment_method_id, name FROM payment_methods ORDER BY name")
        method_names = [name for _, name in methods_data]
        method_id_to_name = {mid: name for mid, name in methods_data}
        method_name_to_id = {name: mid for mid, name in methods_data}
        
        fields = {}
        vars = {}
        row = 0
        
        if record:
            tk.Label(dialog, text="ID:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
            tk.Label(dialog, text=str(record[0])).grid(row=row, column=1, padx=5, pady=5, sticky=tk.W)
            row += 1
        
        # Договор
        tk.Label(dialog, text="*Договор:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        vars['contract'] = tk.StringVar(value=contract_id_to_number.get(record[1] if record else None, ''))
        ttk.Combobox(dialog, textvariable=vars['contract'], values=contract_numbers, width=37).grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        row += 1
        
        # Дата
        tk.Label(dialog, text="*Дата (YYYY-MM-DD):").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['payment_date'] = tk.Entry(dialog, width=40)
        fields['payment_date'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if record: fields['payment_date'].insert(0, str(record[3]) if record[3] else '')
        row += 1
        
        # Сумма
        tk.Label(dialog, text="*Сумма:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['amount'] = tk.Entry(dialog, width=40)
        fields['amount'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if record: fields['amount'].insert(0, str(record[4]) if record[4] is not None else '')
        row += 1
        
        # Способ оплаты
        tk.Label(dialog, text="Способ оплаты:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        vars['payment_method'] = tk.StringVar(value=record[5] if record else '')
        ttk.Combobox(dialog, textvariable=vars['payment_method'], values=method_names, width=37).grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        row += 1
        
        # № документа
        tk.Label(dialog, text="№ документа:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        fields['payment_doc_number'] = tk.Entry(dialog, width=40)
        fields['payment_doc_number'].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        if record: fields['payment_doc_number'].insert(0, record[6] or '')
        row += 1
        
        dialog.columnconfigure(1, weight=1)
        
        def save():
            contract_name = vars['contract'].get()
            if not contract_name:
                messagebox.showerror("Ошибка", "Выберите договор")
                return
            contract_id_val = contract_number_to_id[contract_name]
            
            date_str = fields['payment_date'].get().strip()
            if not date_str:
                messagebox.showerror("Ошибка", "Заполните дату")
                return
            try:
                payment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                messagebox.showerror("Ошибка", "Неверный формат даты (YYYY-MM-DD)")
                return
            
            amount_str = fields['amount'].get().strip()
            if not amount_str:
                messagebox.showerror("Ошибка", "Заполните сумму")
                return
            try:
                amount = float(amount_str)
                if amount <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Ошибка", "Сумма должна быть положительным числом")
                return
            
            method_name = vars['payment_method'].get()
            method_id = method_name_to_id.get(method_name) if method_name else None
            
            doc_number = fields['payment_doc_number'].get().strip() or None
            
            try:
                if record:
                    query = """
                        UPDATE payments SET contract_id=%s, payment_date=%s, amount=%s, 
                                            payment_method_id=%s, payment_doc_number=%s 
                        WHERE payment_id=%s
                    """
                    params = (contract_id_val, payment_date, amount, method_id, doc_number, record[0])
                else:
                    query = """
                        INSERT INTO payments (contract_id, payment_date, amount, 
                                              payment_method_id, payment_doc_number) 
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    params = (contract_id_val, payment_date, amount, method_id, doc_number)
                
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
        
        if messagebox.askyesno("Подтверждение", f"Удалить оплату ID {record[0]}?"):
            try:
                query = "DELETE FROM payments WHERE payment_id=%s"
                DatabaseConnection.execute_query(query, (record[0],), fetch=False)
                messagebox.showinfo("Успех", "Запись удалена")
                self.load_data()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить:\n{str(e)}")

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
        self.notebook.add(ContractTypesFrame(self.notebook), text="Типы договоров")
        self.notebook.add(ExecutionStagesFrame(self.notebook), text="Этапы исполнения")
        self.notebook.add(VatRatesFrame(self.notebook), text="Ставки НДС")
        self.notebook.add(PaymentMethodsFrame(self.notebook), text="Способы оплаты")
        self.notebook.add(ContractsFrame(self.notebook), text="Договора")
        self.notebook.add(ContractMilestonesFrame(self.notebook), text="Этапы договоров")
        self.notebook.add(PaymentsFrame(self.notebook), text="Оплаты")
        
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