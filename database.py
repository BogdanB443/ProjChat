import sqlite3
from datetime import datetime

class ChatDatabase:
    def __init__(self, db_name="chat.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME NOT NULL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS private_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME NOT NULL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def save_message(self, nickname, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "INSERT INTO messages (nickname, message, timestamp) VALUES (?, ?, ?)",
            (nickname, message, timestamp)
        )
        self.conn.commit()

    def save_private_message(self, sender, recipient, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "INSERT INTO private_messages (sender, recipient, message, timestamp) VALUES (?, ?, ?, ?)",
            (sender, recipient, message, timestamp)
        )
        self.conn.commit()

    def get_history(self, limit=100):
        self.cursor.execute(
            "SELECT nickname, message, timestamp FROM messages ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        return self.cursor.fetchall()

    def get_private_history(self, user1, user2, limit=100):
        self.cursor.execute(
            """
            SELECT sender, recipient, message, timestamp FROM private_messages
            WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?)
            ORDER BY timestamp ASC LIMIT ?
            """,
            (user1, user2, user2, user1, limit)
        )
        return self.cursor.fetchall()

    def register_user(self, nickname, password):
        try:
            self.cursor.execute(
                "INSERT INTO users (nickname, password) VALUES (?, ?)",
                (nickname, password)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def check_credentials(self, nickname, password):
        self.cursor.execute(
            "SELECT * FROM users WHERE nickname = ? AND password = ?",
            (nickname, password)
        )
        return self.cursor.fetchone() is not None

    def close(self):
        self.conn.close()