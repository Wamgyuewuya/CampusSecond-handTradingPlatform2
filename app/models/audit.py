"""
审核管理 模型层
- GoodsRepository：商品审核
- ReportRepository：举报信息处理
- SensitiveWordRepository：敏感词管理
"""
import sqlite3
from app.models.db import get_connection


class GoodsRepository:
    """商品审核"""

    @staticmethod
    def list_goods(page: int = 1, page_size: int = 20, status: str = None):
        """分页查询商品，可按状态筛选"""
        offset = (page - 1) * page_size
        where = ""
        params = []
        if status:
            where = "WHERE g.status = ?"
            params.append(status)
        with get_connection() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) as cnt FROM goods g {where}", params
            ).fetchone()["cnt"]
            rows = conn.execute(
                f"""SELECT g.id, g.user_id, g.title, g.description, g.price,
                           g.image, g.status, g.create_at, u.username
                    FROM goods g LEFT JOIN users u ON g.user_id = u.id
                    {where}
                    ORDER BY g.id DESC LIMIT ? OFFSET ?""",
                params + [page_size, offset]
            ).fetchall()
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": [dict(r) for r in rows]
            }

    @staticmethod
    def audit_goods(goods_id: int, status: str) -> bool:
        """审核商品：approved / rejected"""
        with get_connection() as conn:
            cur = conn.execute(
                "UPDATE goods SET status = ? WHERE id = ?",
                (status, goods_id)
            )
            return cur.rowcount > 0


class ReportRepository:
    """举报信息处理"""

    @staticmethod
    def create_report(reporter_id: int, target_type: str, target_id: int, reason: str, detail: str = "") -> int:
        """用户提交举报，返回举报ID"""
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO reports (reporter_id, target_type, target_id, reason, detail) VALUES (?, ?, ?, ?, ?)",
                (reporter_id, target_type, target_id, reason, detail)
            )
            return cur.lastrowid

    @staticmethod
    def list_reports(page: int = 1, page_size: int = 20, status: str = None):
        """分页查询举报信息"""
        offset = (page - 1) * page_size
        where = ""
        params = []
        if status:
            where = "WHERE r.status = ?"
            params.append(status)
        with get_connection() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) as cnt FROM reports r {where}", params
            ).fetchone()["cnt"]
            rows = conn.execute(
                f"""SELECT r.id, r.reporter_id, r.target_type, r.target_id,
                           r.reason, r.detail, r.status,
                           r.handler_id, r.handle_note, r.create_at, r.handle_at,
                           ru.username as reporter_name
                    FROM reports r
                    LEFT JOIN users ru ON r.reporter_id = ru.id
                    {where}
                    ORDER BY r.id DESC LIMIT ? OFFSET ?""",
                params + [page_size, offset]
            ).fetchall()
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": [dict(r) for r in rows]
            }

    @staticmethod
    def handle_report(report_id: int, handler_id: int, handle_note: str) -> bool:
        """处理举报"""
        with get_connection() as conn:
            cur = conn.execute(
                """UPDATE reports
                   SET status = 'resolved', handler_id = ?, handle_note = ?,
                       handle_at = datetime('now')
                   WHERE id = ? AND status = 'pending'""",
                (handler_id, handle_note, report_id)
            )
            return cur.rowcount > 0

    @staticmethod
    def list_by_reporter(reporter_id: int, page: int = 1, page_size: int = 20):
        """查询某个用户提交的举报记录"""
        offset = (page - 1) * page_size
        with get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM reports WHERE reporter_id = ?", (reporter_id,)
            ).fetchone()["cnt"]
            rows = conn.execute(
                """SELECT r.*, u.username as handler_name
                   FROM reports r
                   LEFT JOIN users u ON r.handler_id = u.id
                   WHERE r.reporter_id = ?
                   ORDER BY r.id DESC LIMIT ? OFFSET ?""",
                (reporter_id, page_size, offset)
            ).fetchall()
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": [dict(r) for r in rows]
            }


class SensitiveWordRepository:
    """敏感词管理"""

    @staticmethod
    def list_words(page: int = 1, page_size: int = 20):
        """分页查询敏感词"""
        offset = (page - 1) * page_size
        with get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM sensitive_words"
            ).fetchone()["cnt"]
            rows = conn.execute(
                "SELECT id, word, replacement, create_at FROM sensitive_words ORDER BY id DESC LIMIT ? OFFSET ?",
                (page_size, offset)
            ).fetchall()
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": [dict(r) for r in rows]
            }

    @staticmethod
    def add_word(word: str, replacement: str = "***") -> bool:
        """添加敏感词"""
        try:
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO sensitive_words (word, replacement) VALUES (?, ?)",
                    (word, replacement)
                )
            return True
        except sqlite3.IntegrityError:
            return False

    @staticmethod
    def update_word(word_id: int, word: str = None, replacement: str = None) -> bool:
        """修改敏感词"""
        sets = []
        params = []
        if word:
            sets.append("word = ?")
            params.append(word)
        if replacement:
            sets.append("replacement = ?")
            params.append(replacement)
        if not sets:
            return True
        params.append(word_id)
        with get_connection() as conn:
            try:
                conn.execute(
                    f"UPDATE sensitive_words SET {', '.join(sets)} WHERE id = ?",
                    params
                )
                return True
            except sqlite3.IntegrityError:
                return False

    @staticmethod
    def delete_word(word_id: int) -> bool:
        """删除敏感词"""
        with get_connection() as conn:
            cur = conn.execute("DELETE FROM sensitive_words WHERE id = ?", (word_id,))
            return cur.rowcount > 0
