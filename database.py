import sqlite3
import logging

class DBManager:
    def __init__(self, db_name="nandabot.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)')
            cursor.execute('CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, type TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
            cursor.execute('''CREATE TABLE IF NOT EXISTS products 
                             (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, type TEXT, price REAL, 
                              server_key TEXT, p_type TEXT, gb INTEGER, days INTEGER)''')
            cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
            
            defaults = [
                ('welcome_msg', "👋 မင်္ဂလာပါ {name}\nNanda VPN Bot မှ ကြိုဆိုပါတယ်။\n💰 လက်ရှိ Credit: {balance} Ks"),
                ('payment_info', "💳 **ငွေလွှဲရန် အချက်အလက်များ**\n\n📞 **09682115890** (Myo Nanda Kyaw)\nလွှဲပြီးလျှင် ပြေစာပို့ပေးပါဗျ။"),
                ('atom_msg', "📢 Atom VIP များ ပြန်ရလျှင် Free လဲပေးပါမည်။")
            ]
            cursor.executemany('INSERT OR IGNORE INTO settings VALUES (?, ?)', defaults)
            conn.commit()

    def get_setting(self, key):
        with sqlite3.connect(self.db_name) as conn:
            res = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return res[0] if res else ""

    def update_setting(self, key, value):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
            conn.commit()

    def get_products(self):
        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute("SELECT * FROM products").fetchall()]

    def add_product(self, name, p_type, price, server, proto, gb, days):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute("INSERT INTO products (name, type, price, server_key, p_type, gb, days) VALUES (?,?,?,?,?,?,?)",
                         (name, p_type, price, server, proto, gb, days))
            conn.commit()

    def update_balance(self, user_id, amount, t_type):
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0.0)", (user_id,))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
                cursor.execute("INSERT INTO transactions (user_id, amount, type) VALUES (?, ?, ?)", (user_id, amount, t_type))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"DB Update Balance Error: {e}")
            return False

    def get_balance(self, user_id):
        with sqlite3.connect(self.db_name) as conn:
            res = conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return res[0] if res else 0.0

    def get_history(self, user_id):
        with sqlite3.connect(self.db_name) as conn:
            return conn.execute("SELECT amount, type, timestamp FROM transactions WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5", (user_id,)).fetchall()
