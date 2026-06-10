# 数据库连接与建表
import os
import sqlite3
import hashlib
import secrets

def _project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

DB_PATH = os.path.join(_project_root(), "database", "app.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _hash_password(password: str, salt: bytes) -> str:
    """对密码进行 PBKDF2-SHA256 加盐哈希"""
    dk = hashlib.pbkdf2_hmac("sha256", password.encode('utf-8'), salt, 100_000)
    return dk.hex()

def init_db():
    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                create_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        ''')

        # 迁移：为已有表添加 role 列（如果不存在）
        try:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        except sqlite3.OperationalError:
            pass  # 列已存在

        # ---- 商品表 ----
        conn.execute('''
            CREATE TABLE IF NOT EXISTS goods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                price REAL NOT NULL DEFAULT 0,
                image TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                create_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # ---- 举报信息表 ----
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER NOT NULL,
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                handler_id INTEGER,
                handle_note TEXT NOT NULL DEFAULT '',
                create_at TEXT NOT NULL DEFAULT (datetime('now')),
                handle_at TEXT,
                FOREIGN KEY (reporter_id) REFERENCES users(id),
                FOREIGN KEY (handler_id) REFERENCES users(id)
            )
        ''')

        # ---- 敏感词表 ----
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sensitive_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL UNIQUE,
                replacement TEXT NOT NULL DEFAULT '***',
                create_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        ''')

        # ---- 私信/聊天表 ----
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                create_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (from_user_id) REFERENCES users(id),
                FOREIGN KEY (to_user_id) REFERENCES users(id)
            )
        ''')

        # ---- 交易记录表 ----
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goods_id INTEGER NOT NULL,
                seller_id INTEGER NOT NULL,
                buyer_id INTEGER NOT NULL,
                price REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'completed',
                create_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (goods_id) REFERENCES goods(id),
                FOREIGN KEY (seller_id) REFERENCES users(id),
                FOREIGN KEY (buyer_id) REFERENCES users(id)
            )
        ''')

        # ---- 评价表 ----
        conn.execute('''
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                content TEXT NOT NULL DEFAULT '',
                create_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (transaction_id) REFERENCES transactions(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # ---- 商品评论表 ----
        conn.execute('''
            CREATE TABLE IF NOT EXISTS goods_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goods_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                create_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (goods_id) REFERENCES goods(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # 种子：创建默认 admin 用户（如果尚未存在）
        admin = conn.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
        if not admin:
            salt = secrets.token_bytes(16)
            pw_hash = _hash_password("admin123", salt)
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
                ("admin", pw_hash, salt.hex(), "admin")
            )

        # 种子：创建默认普通用户 user/user123（如果尚未存在）
        user = conn.execute("SELECT id FROM users WHERE username = ?", ("user",)).fetchone()
        if not user:
            salt = secrets.token_bytes(16)
            pw_hash = _hash_password("user123", salt)
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
                ("user", pw_hash, salt.hex(), "user")
            )

        # 种子：创建默认敏感词（如果不存在）
        existing = conn.execute("SELECT COUNT(*) as cnt FROM sensitive_words").fetchone()["cnt"]
        if existing == 0:
            default_words = [
                ("暴力", "***"),
                ("色情", "***"),
                ("赌博", "***"),
                ("毒品", "***"),
                ("诈骗", "***"),
                ("反动", "***"),
                ("枪支", "***"),
                ("违禁品", "***"),
                ("代考", "***"),
                ("作弊", "***"),
            ]
            conn.executemany(
                "INSERT INTO sensitive_words (word, replacement) VALUES (?, ?)",
                default_words
            )