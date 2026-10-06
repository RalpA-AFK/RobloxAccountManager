import sqlite3
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

DB_NAME = "roblox_manager.db"

class DatabaseManager:
    def __init__(self, db_path=DB_NAME):
        self.db_path = db_path
        self._init_encryption_key()
        self._create_tables()

    def _init_encryption_key(self):
        salt = b"RobloxAccountManagerSecureVaultSalt2026"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        seed = os.environ.get("COMPUTERNAME", "RobloxManagerDefaultDevice").encode()
        key = base64.urlsafe_b64encode(kdf.derive(seed))
        self.cipher = Fernet(key)

    def _encrypt_cookie(self, raw_cookie: str) -> str:
        if not raw_cookie:
            return ""
        return self.cipher.encrypt(raw_cookie.encode()).decode()

    def _decrypt_cookie(self, encrypted_cookie: str) -> str:
        if not encrypted_cookie:
            return ""
        try:
            return self.cipher.decrypt(encrypted_cookie.encode()).decode()
        except Exception:
            return ""

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    slot_index INTEGER PRIMARY KEY,
                    username TEXT,
                    display_name TEXT,
                    encrypted_cookie TEXT,
                    custom_label TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()

    def save_account(self, slot_index: int, username: str, display_name: str, cookie: str, custom_label: str = ""):
        encrypted = self._encrypt_cookie(cookie)
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO accounts (slot_index, username, display_name, encrypted_cookie, custom_label)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(slot_index) DO UPDATE SET
                    username=excluded.username,
                    display_name=excluded.display_name,
                    encrypted_cookie=excluded.encrypted_cookie,
                    custom_label=COALESCE(NULLIF(excluded.custom_label, ''), accounts.custom_label)
            """, (slot_index, username, display_name, encrypted, custom_label))
            conn.commit()

    def get_account(self, slot_index: int):
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM accounts WHERE slot_index = ?", (slot_index,)).fetchone()
            if row:
                acc = dict(row)
                acc["cookie"] = self._decrypt_cookie(acc["encrypted_cookie"])
                return acc
            return None

    def fetch_all_accounts(self):
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM accounts ORDER BY slot_index ASC").fetchall()
            accounts = []
            for row in rows:
                acc = dict(row)
                acc["cookie"] = self._decrypt_cookie(acc["encrypted_cookie"])
                accounts.append(acc)
            return accounts

    def get_all_accounts(self):
        return self.fetch_all_accounts()

    def update_custom_label(self, slot_index: int, custom_label: str):
        with self._get_connection() as conn:
            conn.execute("UPDATE accounts SET custom_label = ? WHERE slot_index = ?", (custom_label, slot_index))
            conn.commit()

    def delete_account(self, slot_index: int):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM accounts WHERE slot_index = ?", (slot_index,))
            conn.commit()

    def set_preference(self, key: str, value: str):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO preferences (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (key, value))
            conn.commit()

    def get_preference(self, key: str, default=None):
        with self._get_connection() as conn:
            row = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default