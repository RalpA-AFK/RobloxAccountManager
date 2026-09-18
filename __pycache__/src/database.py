import sqlite3
import os

DB_NAME = "roblox_accounts.db"

def init_db():
    """Initializes the SQLite database and creates the accounts table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            display_name TEXT,
            cookie TEXT NOT NULL,
            build_label TEXT,
            is_active INTEGER DEFAULT 0,
            is_afk INTEGER DEFAULT 1
        )
    """)
    
    conn.commit()
    conn.close()

def add_account(username, display_name, cookie, build_label="Default"):
    """Adds a new Roblox account or updates it if it already exists."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO accounts (username, display_name, cookie, build_label, is_active, is_afk)
        VALUES (?, ?, ?, ?, 0, 1)
    """, (username, display_name, cookie, build_label))
    
    conn.commit()
    conn.close()

def get_all_accounts():
    """Retrieves all stored accounts from the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, username, display_name, build_label, is_active, is_afk FROM accounts")
    rows = cursor.fetchall()
    
    conn.close()
    return rows

def update_account_state(account_id, is_active, is_afk):
    """Updates whether an account instance is actively on-screen or in an AFK state."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE accounts 
        SET is_active = ?, is_afk = ? 
        WHERE id = ?
    """, (is_active, is_afk, account_id))
    
    conn.commit()
    conn.close()

def delete_account(account_id):
    """Deletes an account from the database by its ID."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("[+] Database initialized successfully.")