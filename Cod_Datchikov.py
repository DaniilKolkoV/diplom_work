import sqlite3
from datetime import datetime
import hashlib

class DatabaseManager:
    def __init__(self, db_name="aes_monitor.db"):
        self.db_name = db_name
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_type TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_type TEXT NOT NULL,
                value REAL NOT NULL,
                threshold REAL NOT NULL,
                severity TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, username, password, role):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        try:
            cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', 
                          (username, hashed_password, role))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def authenticate_user(self, username, password):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute('SELECT * FROM users WHERE username=? AND password=?', 
                      (username, hashed_password))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def add_sensor_data(self, sensor_type, value):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sensor_data (sensor_type, value) VALUES (?, ?)', 
                      (sensor_type, value))
        conn.commit()
        conn.close()
    
    def get_current_sensor_data(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT sensor_type, value FROM sensor_data 
            WHERE timestamp = (SELECT MAX(timestamp) FROM sensor_data sd WHERE sd.sensor_type = sensor_data.sensor_type)
        ''')
        data = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in data}
    
    def add_alert(self, sensor_type, value, threshold, severity):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO alerts (sensor_type, value, threshold, severity) VALUES (?, ?, ?, ?)', 
                      (sensor_type, value, threshold, severity))
        conn.commit()
        conn.close()

class AuthManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.current_user = None
    
    def register(self, username, password, role="operator"):
        return self.db_manager.add_user(username, password, role)
    
    def login(self, username, password):
        user = self.db_manager.authenticate_user(username, password)
        if user:
            self.current_user = {
                'id': user[0],
                'username': user[1],
                'role': user[3]
            }
            return True
        return False
    
    def logout(self):
        self.current_user = None

class MainActivity:
    def __init__(self, db_manager, auth_manager):
        self.db_manager = db_manager
        self.auth_manager = auth_manager
        self.thresholds = {
            'temperature': 300.0,
            'pressure': 150.0,
            'vibration': 5.0
        }
    
    def display_dashboard(self):
        if not self.auth_manager.current_user:
            print("Пожалуйста, войдите в систему")
            return
        
        sensor_data = self.db_manager.get_current_sensor_data()
        
        print("\n=== АЭС МОНИТОР - ГЛАВНЫЙ ЭКРАН ===")
        print(f"Пользователь: {self.auth_manager.current_user['username']}")
        print(f"Роль: {self.auth_manager.current_user['role']}")
        print("\nТЕКУЩИЕ ПОКАЗАНИЯ:")
        
        for sensor_type, value in sensor_data.items():
            status = self.get_status_indicator(sensor_type, value)
            print(f"{sensor_type.upper()}: {value:.2f} {status}")
        
        print("\nБЫСТРЫЙ ДОСТУП:")
        print("1. Детальный мониторинг")
        print("2. История данных")
        print("3. Оповещения")
        print("4. Настройки")
        print("5. Выход")
    
    def get_status_indicator(self, sensor_type, value):
        threshold = self.thresholds.get(sensor_type, 0)
        if value <= threshold * 0.8:
            return "🟢 НОРМА"
        elif value <= threshold * 0.9:
            return "🟡 ВНИМАНИЕ"
        else:
            return "🔴 КРИТИЧЕСКИЙ"
    
    def generate_sample_data(self):
        import random
        sensors = ['temperature', 'pressure', 'vibration']
        
        for sensor in sensors:
            base_value = random.uniform(50, 400) if sensor == 'temperature' else random.uniform(50, 200) if sensor == 'pressure' else random.uniform(1, 10)
            self.db_manager.add_sensor_data(sensor, base_value)
            
            value = base_value
            threshold = self.thresholds[sensor]
            
            if value > threshold * 0.9:
                severity = "critical" if value > threshold else "warning"
                self.db_manager.add_alert(sensor, value, threshold, severity)

def main():
    db_manager = DatabaseManager()
    auth_manager = AuthManager(db_manager)
    main_activity = MainActivity(db_manager, auth_manager)
    
    db_manager.add_user("admin", "admin123", "administrator")
    db_manager.add_user("operator", "operator123", "operator")
    db_manager.add_user("engineer", "engineer123", "engineer")
    
    main_activity.generate_sample_data()
    
    while True:
        print("\n=== АЭС МОНИТОР ===")
        print("1. Вход")
        print("2. Регистрация")
        print("3. Выход")
        
        choice = input("Выберите действие: ")
        
        if choice == "1":
            username = input("Логин: ")
            password = input("Пароль: ")
            if auth_manager.login(username, password):
                print(f"Успешный вход! Добро пожаловать, {username}!")
                while auth_manager.current_user:
                    main_activity.display_dashboard()
                    action = input("\nВыберите действие: ")
                    if action == "5":
                        auth_manager.logout()
                        print("Выход выполнен")
            else:
                print("Ошибка входа! Проверьте логин и пароль.")
        
        elif choice == "2":
            username = input("Введите логин: ")
            password = input("Введите пароль: ")
            role = input("Введите роль (operator/engineer/administrator): ")
            if auth_manager.register(username, password, role):
                print("Регистрация успешна!")
            else:
                print("Ошибка регистрации! Пользователь уже существует.")
        
        elif choice == "3":
            print("До свидания!")
            break
        
        else:
            print("Неверный выбор!")

if __name__ == "__main__":
    main()
