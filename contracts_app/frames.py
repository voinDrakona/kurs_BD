import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from .base_table import TableFrame
from .db_config import DatabaseConnection

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

class ContractEditorFrame(tk.Frame):
    """Вкладка Договора с редактированием договора и его этапов в одной форме (1:M)"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.contract_id = None
        self.setup_ui()
        self.load_contracts_list()

    def setup_ui(self):
        # Левая часть — список всех договоров
        left_pane = tk.Frame(self)
        left_pane.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=7)

        tk.Button(left_pane, text="Новый договор", command=self.new_contract).pack(fill=tk.X, pady=2)
        tk.Button(left_pane, text="Обновить список", command=self.load_contracts_list).pack(fill=tk.X, pady=2)
        tk.Button(left_pane, text="Удалить выбранный договор", command=self.delete_current_contract).pack(fill=tk.X, pady=2)

        self.contracts_tree = ttk.Treeview(left_pane, columns=('number', 'date', 'customer'), show='tree headings')
        self.contracts_tree.heading('#0', text='ID')
        self.contracts_tree.heading('number', text='Номер')
        self.contracts_tree.heading('date', text='Дата')
        self.contracts_tree.heading('customer', text='Заказчик')
        self.contracts_tree.column('#0', width=50)
        self.contracts_tree.column('number', width=120)
        self.contracts_tree.column('date', width=100)
        self.contracts_tree.column('customer', width=200)
        self.contracts_tree.pack(fill=tk.BOTH, expand=True)
        self.contracts_tree.bind('<<TreeviewSelect>>', self.on_contract_selected)

        # Правая часть — редактор договора + этапы
        right_pane = tk.Frame(self)
        right_pane.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.detail_editor = ContractDetailEditor(right_pane, self)
        self.detail_editor.pack(fill=tk.BOTH, expand=True)

    def load_contracts_list(self):
        self.contracts_tree.delete(*self.contracts_tree.get_children())
        query = """
            SELECT c.contract_id, c.contract_number, c.contract_date, o.name
            FROM contracts c
            JOIN organizations o ON o.org_id = c.customer_org_id
            ORDER BY c.contract_date DESC, c.contract_number
        """
        data, _ = DatabaseConnection.execute_query(query)
        for cid, num, date, customer in data:
            self.contracts_tree.insert('', tk.END, iid=cid, text=cid,
                                     values=(num, date or '', customer or ''))

    def on_contract_selected(self, event):
        sel = self.contracts_tree.selection()
        if sel:
            self.contract_id = int(sel[0])
            self.detail_editor.load_contract(self.contract_id)

    def new_contract(self):
        self.contract_id = None
        self.detail_editor.clear_form()

    def delete_current_contract(self):
        """Безопасное удаление выбранного договора со всеми связанными данными"""
        selection = self.contracts_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Сначала выберите договор в списке слева")
            return

        contract_id = int(selection[0])
        
        # Получаем номер договора для красивого сообщения
        item = self.contracts_tree.item(selection[0])
        contract_num = item['values'][0] if item['values'] else "без номера"

        # Двойное подтверждение — чтобы случайно не удалить
        if not messagebox.askyesno(
            "Подтверждение удаления",
            f"Вы действительно хотите удалить договор № {contract_num}?\n\n"
            "Будут удалены:\n"
            "• все этапы договора\n"
            "• все связанные оплаты\n"
            "• сам договор\n\n"
            "Операция необратима!",
            icon='warning'
        ):
            return

        try:
            conn = DatabaseConnection.get_connection()
            cur = conn.cursor()

            # Удаляем в правильном порядке из-за внешних ключей
            cur.execute("DELETE FROM payments WHERE contract_id = %s", (contract_id,))
            cur.execute("DELETE FROM contract_milestones WHERE contract_id = %s", (contract_id,))
            cur.execute("DELETE FROM contracts WHERE contract_id = %s", (contract_id,))

            conn.commit()
            conn.close()

            messagebox.showinfo("Успех", f"Договор № {contract_num} успешно удалён из базы данных")
            
            # Обновляем интерфейс
            self.load_contracts_list()
            self.detail_editor.clear_form()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось удалить договор:\n{str(e)}")


class ContractDetailEditor(tk.Frame):
    """Редактор договора и его этапов (1:M в одной форме)"""
    
    def __init__(self, parent, master):
        super().__init__(parent)
        self.master = master
        self.contract_id = None
        self.milestones_data = []
        
        self.load_lookups()    # ← Сначала загружаем справочники
        self.build_ui()        # ← Потом строим интерфейс

    def load_lookups(self):
        # Справочники
        self.orgs = {row[0]: row[1] for row in DatabaseConnection.execute_query("SELECT org_id, name FROM organizations")[0]}
        self.org_ids = {v: k for k, v in self.orgs.items()}
        
        self.types = {row[0]: row[1] for row in DatabaseConnection.execute_query("SELECT contract_type_id, name FROM contract_types")[0]}
        self.type_ids = {v: k for k, v in self.types.items()}
        
        self.stages = {row[0]: row[1] for row in DatabaseConnection.execute_query("SELECT stage_id, name FROM execution_stages")[0]}
        self.stage_ids = {v: k for k, v in self.stages.items()}

    def build_ui(self):
        # === Основная информация ===
        top = tk.LabelFrame(self, text="Договор")
        top.pack(fill=tk.X, padx=5, pady=5)

        row = 0
        tk.Label(top, text="Номер*:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.entry_number = tk.Entry(top, width=30)
        self.entry_number.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        row += 1

        tk.Label(top, text="Дата*:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.entry_date = tk.Entry(top, width=30)
        self.entry_date.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        self.entry_date.insert(0, datetime.today().strftime('%Y-%m-%d'))
        row += 1

        tk.Label(top, text="Заказчик*:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.cb_customer = ttk.Combobox(top, values=list(self.orgs.values()), width=37)
        self.cb_customer.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        row += 1

        tk.Label(top, text="Исполнитель*:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.cb_contractor = ttk.Combobox(top, values=list(self.orgs.values()), width=37)
        self.cb_contractor.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        row += 1

        tk.Label(top, text="Тип договора*:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.cb_type = ttk.Combobox(top, values=list(self.types.values()), width=37)
        self.cb_type.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        row += 1

        # === Этапы ===
        mid = tk.LabelFrame(self, text="Этапы договора (1:M)")
        mid.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        cols = ('no', 'date', 'amount', 'advance', 'subject')
        self.tree_milestones = ttk.Treeview(mid, columns=cols, show='headings', height=12)
        for col, text in zip(cols, ['№ этапа', 'Дата', 'Сумма', 'Аванс', 'Предмет']):
            self.tree_milestones.heading(col, text=text)
            self.tree_milestones.column(col, width=120)
        self.tree_milestones.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        btns = tk.Frame(mid)
        btns.pack(fill=tk.X, pady=5)
        tk.Button(btns, text="+ Добавить этап", command=self.add_milestone).pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="− Удалить выбранный", command=self.delete_milestone).pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="Редактировать", command=self.edit_milestone).pack(side=tk.LEFT, padx=5)

        # === Кнопка сохранения ===
        bottom = tk.Frame(self)
        bottom.pack(fill=tk.X, pady=10)
        tk.Button(bottom, text="Сохранить договор и все этапы", command=self.save_all,
                  font=('Arial', 12, 'bold'), bg="#90ee90").pack(side=tk.RIGHT, padx=20)

    def add_milestone(self):
        self.edit_milestone_dialog()

    def edit_milestone(self):
        sel = self.tree_milestones.selection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите этап для редактирования")
            return
        item = self.tree_milestones.item(sel[0])
        values = item['values']
        self.edit_milestone_dialog(values)

    def edit_milestone_dialog(self, data=None):
        win = tk.Toplevel(self)
        win.title("Этап договора")
        win.geometry("400x350")

        tk.Label(win, text="№ этапа*:").pack(pady=2)
        e_no = tk.Entry(win)
        e_no.pack(pady=2)
        if data: e_no.insert(0, data[0])

        tk.Label(win, text="Дата (YYYY-MM-DD):").pack(pady=2)
        e_date = tk.Entry(win)
        e_date.pack(pady=2)
        if data: e_date.insert(0, data[1])

        tk.Label(win, text="Сумма*:").pack(pady=2)
        e_amount = tk.Entry(win)
        e_amount.pack(pady=2)
        if data: e_amount.insert(0, data[2])

        tk.Label(win, text="Аванс:").pack(pady=2)
        e_advance = tk.Entry(win)
        e_advance.pack(pady=2)
        if data: e_advance.insert(0, data[3])

        tk.Label(win, text="Предмет:").pack(pady=2)
        e_subject = tk.Entry(win, width=50)
        e_subject.pack(pady=2)
        if data: e_subject.insert(0, data[4])

        def save():
            try:
                no = int(e_no.get())
                amount = float(e_amount.get())
                advance = float(e_advance.get() or 0)
                new_row = (no, e_date.get(), amount, advance, e_subject.get())
                if data:
                    # редактируем
                    for i, row in enumerate(self.milestones_data):
                        if row[0] == data[0]:
                            self.milestones_data[i] = new_row
                            break
                else:
                    self.milestones_data.append(new_row)
                self.refresh_milestones_table()
                win.destroy()
            except ValueError:
                messagebox.showerror("Ошибка", "Проверьте числовые поля")

        tk.Button(win, text="Сохранить", command=save).pack(pady=10)

    def delete_milestone(self):
        sel = self.tree_milestones.selection()
        if not sel:
            return
        item = self.tree_milestones.item(sel[0])
        no = item['values'][0]
        self.milestones_data = [r for r in self.milestones_data if r[0] != no]
        self.refresh_milestones_table()

    def refresh_milestones_table(self):
        self.tree_milestones.delete(*self.tree_milestones.get_children())
        for row in sorted(self.milestones_data, key=lambda x: x[0]):
            self.tree_milestones.insert('', tk.END, values=row)

    def clear_form(self):
        """Полная очистка формы для нового договора"""
        self.contract_id = None
        self.entry_number.delete(0, tk.END)
        self.entry_date.delete(0, tk.END)
        self.entry_date.insert(0, datetime.today().strftime('%Y-%m-%d'))
        self.cb_customer.set('')
        self.cb_contractor.set('')
        self.cb_type.set('')
        self.milestones_data = []
        self.refresh_milestones_table()

    def load_contract(self, contract_id):
        self.contract_id = contract_id
        query = "SELECT contract_number, contract_date, customer_org_id, contractor_org_id, contract_type_id FROM contracts WHERE contract_id = %s"
        data, _ = DatabaseConnection.execute_query(query, (contract_id,))
        if not data:
            return
        row = data[0]
        self.entry_number.delete(0, tk.END)
        self.entry_number.insert(0, row[0])
        self.entry_date.delete(0, tk.END)
        self.entry_date.insert(0, str(row[1]) if row[1] else '')
        self.cb_customer.set(self.orgs.get(row[2], ''))
        self.cb_contractor.set(self.orgs.get(row[3], ''))
        self.cb_type.set(self.types.get(row[4], ''))

        # Загружаем этапы
        ms_query = "SELECT milestone_no, milestone_date, amount, advance_amount, subject FROM contract_milestones WHERE contract_id = %s ORDER BY milestone_no"
        ms_data, _ = DatabaseConnection.execute_query(ms_query, (contract_id,))
        self.milestones_data = [(r[0], str(r[1]) if r[1] else '', r[2], r[3], r[4] or '') for r in ms_data]
        self.refresh_milestones_table()

    def save_all(self):
        # Валидация
        if not all([self.entry_number.get().strip(), self.entry_date.get().strip(),
                    self.cb_customer.get(), self.cb_contractor.get(), self.cb_type.get()]):
            messagebox.showerror("Ошибка", "Заполните все обязательные поля договора")
            return

        try:
            contract_date = datetime.strptime(self.entry_date.get().strip(), '%Y-%m-%d').date()
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат даты")
            return

        customer_id = self.org_ids.get(self.cb_customer.get())
        contractor_id = self.org_ids.get(self.cb_contractor.get())
        type_id = self.type_ids.get(self.cb_type.get())
        if not all([customer_id, contractor_id, type_id]):
            messagebox.showerror("Ошибка", "Выберите значения из списков")
            return

        try:
            conn = DatabaseConnection.get_connection()
            cur = conn.cursor()

            if self.contract_id:
                # Обновляем договор
                cur.execute("""UPDATE contracts SET contract_number=%s, contract_date=%s,
                               customer_org_id=%s, contractor_org_id=%s, contract_type_id=%s
                               WHERE contract_id=%s""",
                            (self.entry_number.get().strip(), contract_date, customer_id,
                             contractor_id, type_id, self.contract_id))
            else:
                # Создаём новый
                cur.execute("""INSERT INTO contracts (contract_number, contract_date, customer_org_id,
                               contractor_org_id, contract_type_id)
                               VALUES (%s,%s,%s,%s,%s) RETURNING contract_id""",
                            (self.entry_number.get().strip(), contract_date, customer_id,
                             contractor_id, type_id))
                self.contract_id = cur.fetchone()[0]

            # Удаляем старые этапы
            cur.execute("DELETE FROM contract_milestones WHERE contract_id=%s", (self.contract_id,))

            # Добавляем новые этапы
            for no, mdate_str, amount, advance, subject in self.milestones_data:
                mdate = datetime.strptime(mdate_str, '%Y-%m-%d').date() if mdate_str.strip() else None
                cur.execute("""INSERT INTO contract_milestones
                               (contract_id, milestone_no, milestone_date, amount, advance_amount, subject)
                               VALUES (%s,%s,%s,%s,%s,%s)""",
                            (self.contract_id, no, mdate, float(amount), float(advance), subject or None))

            conn.commit()
            conn.close()

            messagebox.showinfo("Успех", "Договор и все этапы успешно сохранены!")
            self.master.load_contracts_list()
            self.master.on_contract_selected(None)  # обновить правую часть

        except Exception as e:
            messagebox.showerror("Ошибка сохранения", str(e))

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
