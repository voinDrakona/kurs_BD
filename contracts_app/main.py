import tkinter as tk
from tkinter import ttk, messagebox
from .frames import (OrganizationsFrame, ContractTypesFrame, ExecutionStagesFrame,
                     VatRatesFrame, PaymentMethodsFrame, ContractEditorFrame,
                     ContractMilestonesFrame, PaymentsFrame)
from .reports import ReportsWindow
from .db_config import DatabaseConnection

class MainApplication(tk.Tk):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Система управления договорами")
        self.geometry("1200x700")
        
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
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Выход", command=self.quit)
        
        reports_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Отчеты", menu=reports_menu)
        reports_menu.add_command(label="Открыть отчеты", command=self.open_reports)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)
    
    def setup_ui(self):
        """Создание интерфейса"""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.notebook.add(OrganizationsFrame(self.notebook), text="Организации")
        self.notebook.add(ContractTypesFrame(self.notebook), text="Типы договоров")
        self.notebook.add(ExecutionStagesFrame(self.notebook), text="Этапы исполнения")
        self.notebook.add(VatRatesFrame(self.notebook), text="Ставки НДС")
        self.notebook.add(PaymentMethodsFrame(self.notebook), text="Способы оплаты")
        self.notebook.add(ContractEditorFrame(self.notebook), text="Договора")
        self.notebook.add(ContractMilestonesFrame(self.notebook), text="Этапы договоров")
        self.notebook.add(PaymentsFrame(self.notebook), text="Оплаты")
        
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