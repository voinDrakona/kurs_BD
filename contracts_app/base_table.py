import tkinter as tk
from tkinter import ttk, messagebox
from .db_config import DatabaseConnection

class TableFrame(tk.Frame):
    """Базовый фрейм для работы с таблицами"""
    
    def __init__(self, parent, table_name, columns_config, id_field='id'):
        super().__init__(parent)
        self.table_name = table_name
        self.columns_config = columns_config
        self.id_field = id_field  # Имя поля ID (org_id, contract_id и т.д.)
        self.current_data = []
        self.filtered_data = []
        self.sort_column = None
        self.sort_reverse = False
        
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Создание интерфейса"""
        toolbar = tk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(toolbar, text="Обновить", command=self.load_data).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Добавить", command=self.add_record).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Редактировать", command=self.edit_record).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Удалить", command=self.delete_record).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Поиск", command=self.search_dialog).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Фильтр", command=self.filter_dialog).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Сброс", command=self.reset_filter).pack(side=tk.LEFT, padx=2)
        
        tree_frame = tk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        visible_columns = [col['name'] for col in self.columns_config if not col['name'].endswith('_id') and col['name'] != self.id_field]
        self.tree = ttk.Treeview(tree_frame, columns=visible_columns, show='tree headings',
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
            if col['name'].endswith('_id') or col['name'] == self.id_field:
                continue  # Скрываем ID
            self.tree.column(col['name'], width=col.get('width', 100))
            self.tree.heading(col['name'], text=col['display'], 
                              command=lambda c=col['name']: self.sort_by_column(c))
            
        for col in self.columns_config:
            col_name = col['name']
            width = col.get('width', 100)
            
            if width == 0:
                # Полностью скрываем колонку (даже заголовок не показываем)
                self.tree.column(col_name, width=0, stretch=False, minwidth=0)
                self.tree.heading(col_name, text="")
            else:
                self.tree.column(col_name, width=width)
                self.tree.heading(col_name, text=col['display'], 
                                command=lambda c=col_name: self.sort_by_column(c))
        
        self.tree.bind('<Double-1>', lambda e: self.edit_record())
    
    def get_select_query(self):
        """Всегда запрашиваем ID первым, даже если он не в columns_config"""
        visible_fields = ', '.join([col['db_field'] for col in self.columns_config])
        id_field = getattr(self, 'id_field', self.columns_config[0]['db_field'] if self.columns_config else 'id')
        return f"SELECT {id_field}, {visible_fields} FROM {self.table_name} ORDER BY {id_field} DESC"

    def load_data(self):
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
            id_value = row[0]  # ID всегда первый в SELECT
            visible_values = row[1:]  # Остальные — видимые
            item = self.tree.insert('', tk.END, text=str(idx), values=visible_values)
            self.tree.item(item, tags=(id_value,))  # Сохраняем ID в tags
    
    def get_selected_record(self):
        """Получить выбранную запись"""
        selection = self.tree.selection()
        if not selection:
            return None
        
        item = self.tree.item(selection[0])
        id_value = item['tags'][0] if item['tags'] else None
        visible_values = item['values']
        return (id_value, *visible_values)  # ID + видимые поля

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
        self.search_dialog()
    
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
