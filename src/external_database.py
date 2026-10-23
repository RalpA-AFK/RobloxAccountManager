import sqlite3
import os
import time

TEMP_DB_Name = "roblox_external_ephemeral.db"

class ExternalDatabaseManager:
    def __init__(self, db_path=TEMP_DB_Name):
        self.db_path = db_path
        self._create_tables()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS external_instances (
                    pid INTEGER PRIMARY KEY,
                    custom_label TEXT,
                    claimed_time TEXT,
                    first_seen REAL
                )
            """)
            try:
                conn.execute("ALTER TABLE external_instances ADD COLUMN first_seen REAL")
            except sqlite3.OperationalError:
                pass  # Column already exists
            conn.commit()

    def register_or_get_instance(self, pid: int, current_time: float):
        existing = self.get_external_instance(pid)
        if existing:
            return existing
        
        default_label = "Manually Launched / Xbox"
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO external_instances (pid, custom_label, claimed_time, first_seen)
                VALUES (?, ?, datetime('now'), ?)
            """, (pid, default_label, current_time))
            conn.commit()
        return self.get_external_instance(pid) or {
            "pid": pid,
            "custom_label": default_label,
            "first_seen": current_time
        }

    def get_all_external_instances(self):
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM external_instances").fetchall()
            return [dict(row) for row in rows]

    def update_custom_label(self, pid: int, custom_label: str):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO external_instances (pid, custom_label, claimed_time, first_seen)
                VALUES (?, ?, datetime('now'), ?)
                ON CONFLICT(pid) DO UPDATE SET custom_label=excluded.custom_label
            """, (pid, custom_label, time.time()))
            conn.commit()

    def add_external_instance(self, pid: int, custom_label: str = "Manually Launched / Xbox"):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO external_instances (pid, custom_label, claimed_time, first_seen)
                VALUES (?, ?, datetime('now'), ?)
            """, (pid, custom_label, time.time()))
            conn.commit()

    def remove_external_instance(self, pid: int):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM external_instances WHERE pid = ?", (pid,))
            conn.commit()

    def get_external_instance(self, pid: int):
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM external_instances WHERE pid = ?", (pid,)).fetchone()
            return dict(row) if row else None

    def clear_all(self):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM external_instances")
            conn.commit()