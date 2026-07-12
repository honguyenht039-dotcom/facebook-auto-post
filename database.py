import sqlite3
import os
from datetime import datetime
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Bảng lưu trữ cấu hình API
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    
    # Bảng lưu trữ bài viết
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT,
        image_path TEXT,
        status TEXT DEFAULT 'pending',
        error_message TEXT,
        fb_post_id TEXT,
        tg_message_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    
    # Thiết lập giá trị mặc định cho Facebook Page ID nếu chưa tồn tại
    cursor.execute("SELECT value FROM settings WHERE key = 'fb_page_id'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO settings (key, value) VALUES ('fb_page_id', '61590891416912')")
        conn.commit()
        
    conn.close()

def get_setting(key, default=""):
    # HỖ TRỢ STREAMLIT SECRETS (Triển khai trên Cloud):
    # Ưu tiên đọc cấu hình từ st.secrets nếu tồn tại để tránh mất cấu hình khi Cloud reset database SQLite
    try:
        if key in st.secrets:
            val = st.secrets[key]
            if val:
                return str(val)
    except Exception:
        pass
        
    # Nếu không chạy trên Cloud hoặc không cấu hình secrets, đọc từ SQLite cục bộ
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row['value'] if row else default
    except Exception:
        return default

def set_setting(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO settings (key, value)
    VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    ''', (key, value))
    conn.commit()
    conn.close()

def create_post(content, image_path, status='pending'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO posts (content, image_path, status, created_at, updated_at)
    VALUES (?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
    ''', (content, image_path, status))
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return post_id

def get_post(post_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def update_post(post_id, **kwargs):
    if not kwargs:
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Thêm trường updated_at tự động
    kwargs['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    keys = list(kwargs.keys())
    values = list(kwargs.values())
    
    set_clause = ", ".join([f"{k} = ?" for k in keys])
    query = f"UPDATE posts SET {set_clause} WHERE id = ?"
    
    cursor.execute(query, values + [post_id])
    conn.commit()
    conn.close()

def get_posts(limit=50):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posts ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception:
        return []

# Khởi tạo DB khi file này được import lần đầu
init_db()
