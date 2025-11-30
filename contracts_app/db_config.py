import psycopg2

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