# database.py
import sqlite3

class DBManager:
    def __init__(self, db_name="nandabot.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                             (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS transactions 
                             (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                              amount REAL, type TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            conn.commit()

    def get_balance(self, user_id):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            res = cursor.fetchone()
            return res[0] if res else 0.0

    def update_balance(self, user_id, amount, t_type):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0.0)", (user_id,))
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            cursor.execute("INSERT INTO transactions (user_id, amount, type) VALUES (?, ?, ?)", 
                          (user_id, amount, t_type))
            conn.commit()
