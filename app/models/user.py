import hashlib
import secrets
import sqlite3

from app.models.db import get_connection

def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode('utf-8'), salt, 100_000)
    return dk.hex()


class UserRepository:
    @staticmethod
    def create_user(username: str, password: str, role: str = "user") -> bool:
        salt = secrets.token_bytes(16)
        password_hash = _hash_password(password, salt)
        try:
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
                    (username, password_hash, salt.hex(), role)
                )
            return True
        except sqlite3.IntegrityError:
            return False

    @staticmethod
    def get_user_by_username(username: str):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, username, password_hash, salt, role FROM users WHERE username = ?",
                (username,)
            ).fetchone()
            return row

    @staticmethod
    def verify_user(username: str, password: str) -> bool:
        row = UserRepository.get_user_by_username(username)
        if not row:
            return False
        salt = bytes.fromhex(row['salt'])
        return _hash_password(password, salt) == row["password_hash"]

    # ---- 用户管理（admin 专用） ----

    @staticmethod
    def list_users(page: int = 1, page_size: int = 20):
        """分页查询所有用户列表（含管理员），按角色排序"""
        offset = (page - 1) * page_size
        with get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM users"
            ).fetchone()["cnt"]
            rows = conn.execute(
                "SELECT id, username, role, create_at FROM users ORDER BY role DESC, id DESC LIMIT ? OFFSET ?",
                (page_size, offset)
            ).fetchall()
            items = []
            for r in rows:
                d = dict(r)
                d["role_label"] = "管理员" if d["role"] == "admin" else "普通用户"
                items.append(d)
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": items
            }

    @staticmethod
    def update_user(user_id: int, username: str = None, password: str = None) -> bool:
        """修改用户信息（用户名/密码）"""
        with get_connection() as conn:
            if username:
                try:
                    conn.execute("UPDATE users SET username = ? WHERE id = ? AND role = 'user'",
                                 (username, user_id))
                except sqlite3.IntegrityError:
                    return False
            if password:
                salt = secrets.token_bytes(16)
                pw_hash = _hash_password(password, salt)
                conn.execute(
                    "UPDATE users SET password_hash = ?, salt = ? WHERE id = ? AND role = 'user'",
                    (pw_hash, salt.hex(), user_id)
                )
            return True

    @staticmethod
    def delete_user(user_id: int) -> bool:
        """删除普通用户"""
        with get_connection() as conn:
            cur = conn.execute("DELETE FROM users WHERE id = ? AND role = 'user'", (user_id,))
            return cur.rowcount > 0

    @staticmethod
    def get_user_by_id(user_id: int):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, username, role, create_at FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            return dict(row) if row else None