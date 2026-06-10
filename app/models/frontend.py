"""
前端-用户侧 模型层
- GoodsFrontend：商品发布/浏览/搜索/详情
- ChatRepository：聊天消息
- TransactionRepository：交易记录
- EvaluationRepository：交易评价
"""
import sqlite3
import os
from app.models.db import get_connection

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "app", "static", "uploads")


class GoodsFrontend:
    """用户侧商品操作"""

    @staticmethod
    def _load_sensitive_words():
        """加载所有敏感词"""
        from app.models.audit import SensitiveWordRepository
        words = SensitiveWordRepository.list_words(page=1, page_size=9999)
        return words.get("items", [])

    @staticmethod
    def filter_sensitive(text: str) -> str:
        """过滤文本中的敏感词，返回替换后的文本"""
        if not text:
            return text
        words = GoodsFrontend._load_sensitive_words()
        for w in words:
            text = text.replace(w["word"], w["replacement"])
        return text

    @staticmethod
    def publish(user_id: int, title: str, description: str, price: float, image: str) -> int:
        """发布商品，返回商品ID"""
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO goods (user_id, title, description, price, image) VALUES (?, ?, ?, ?, ?)",
                (user_id, title, description, price, image)
            )
            return cur.lastrowid

    @staticmethod
    def list_approved(page: int = 1, page_size: int = 20, keyword: str = None):
        """分页查询已审核商品"""
        offset = (page - 1) * page_size
        where = "WHERE g.status = 'approved'"
        params = []
        if keyword:
            where += " AND g.title LIKE ?"
            params.append(f"%{keyword}%")
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
    def get_by_id(goods_id: int):
        """获取商品详情"""
        with get_connection() as conn:
            row = conn.execute(
                """SELECT g.*, u.username
                   FROM goods g LEFT JOIN users u ON g.user_id = u.id
                   WHERE g.id = ?""",
                (goods_id,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def list_by_user(user_id: int, page: int = 1, page_size: int = 20):
        """查询用户发布的商品"""
        offset = (page - 1) * page_size
        with get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM goods WHERE user_id = ?", (user_id,)
            ).fetchone()["cnt"]
            rows = conn.execute(
                "SELECT * FROM goods WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (user_id, page_size, offset)
            ).fetchall()
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": [dict(r) for r in rows]
            }

    # ---- 商品评论 ----

    @staticmethod
    def get_comments(goods_id: int):
        """获取某商品的所有评论"""
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT gc.*, u.username
                   FROM goods_comments gc LEFT JOIN users u ON gc.user_id = u.id
                   WHERE gc.goods_id = ?
                   ORDER BY gc.id ASC""",
                (goods_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def add_comment(goods_id: int, user_id: int, content: str) -> int:
        """添加评论"""
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO goods_comments (goods_id, user_id, content) VALUES (?, ?, ?)",
                (goods_id, user_id, content)
            )
            return cur.lastrowid


class ChatRepository:
    """聊天消息"""

    @staticmethod
    def send_message(from_user_id: int, to_user_id: int, content: str) -> int:
        """发送消息"""
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO messages (from_user_id, to_user_id, content) VALUES (?, ?, ?)",
                (from_user_id, to_user_id, content)
            )
            return cur.lastrowid

    @staticmethod
    def get_conversation(user_id_1: int, user_id_2: int, page: int = 1, page_size: int = 50):
        """获取两个用户之间的聊天记录"""
        offset = (page - 1) * page_size
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT m.*, u.username as from_username
                   FROM messages m LEFT JOIN users u ON m.from_user_id = u.id
                   WHERE (m.from_user_id = ? AND m.to_user_id = ?)
                      OR (m.from_user_id = ? AND m.to_user_id = ?)
                   ORDER BY m.id DESC LIMIT ? OFFSET ?""",
                (user_id_1, user_id_2, user_id_2, user_id_1, page_size, offset)
            ).fetchall()
            return [dict(r) for r in reversed(rows)]

    @staticmethod
    def get_conversation_list(user_id: int):
        """获取用户的所有会话列表（含最后一条消息）"""
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT
                    CASE WHEN m.from_user_id = ? THEN m.to_user_id ELSE m.from_user_id END as other_user_id,
                    u.username as other_username,
                    m.content as last_message,
                    m.create_at as last_time,
                    m.from_user_id,
                    SUM(CASE WHEN m.to_user_id = ? AND m.is_read = 0 THEN 1 ELSE 0 END) as unread
                   FROM messages m
                   LEFT JOIN users u ON (CASE WHEN m.from_user_id = ? THEN m.to_user_id ELSE m.from_user_id END) = u.id
                   WHERE m.from_user_id = ? OR m.to_user_id = ?
                   GROUP BY other_user_id
                   ORDER BY m.id DESC""",
                (user_id, user_id, user_id, user_id, user_id)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def mark_as_read(from_user_id: int, to_user_id: int):
        """标记消息为已读"""
        with get_connection() as conn:
            conn.execute(
                "UPDATE messages SET is_read = 1 WHERE from_user_id = ? AND to_user_id = ?",
                (from_user_id, to_user_id)
            )


class TransactionRepository:
    """交易记录"""

    @staticmethod
    def create_transaction(goods_id: int, seller_id: int, buyer_id: int, price: float) -> int:
        """创建交易记录"""
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO transactions (goods_id, seller_id, buyer_id, price) VALUES (?, ?, ?, ?)",
                (goods_id, seller_id, buyer_id, price)
            )
            return cur.lastrowid

    @staticmethod
    def check_purchased(goods_id: int, user_id: int) -> bool:
        """检查用户是否已购买某商品"""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM transactions WHERE goods_id = ? AND buyer_id = ?",
                (goods_id, user_id)
            ).fetchone()
            return row is not None

    @staticmethod
    def list_by_user(user_id: int, page: int = 1, page_size: int = 20):
        """查询用户的交易记录（作为买家或卖家）"""
        offset = (page - 1) * page_size
        with get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM transactions WHERE seller_id = ? OR buyer_id = ?",
                (user_id, user_id)
            ).fetchone()["cnt"]
            rows = conn.execute(
                """SELECT t.*, g.title as goods_title, g.image as goods_image,
                          s.username as seller_name, b.username as buyer_name
                   FROM transactions t
                   LEFT JOIN goods g ON t.goods_id = g.id
                   LEFT JOIN users s ON t.seller_id = s.id
                   LEFT JOIN users b ON t.buyer_id = b.id
                   WHERE t.seller_id = ? OR t.buyer_id = ?
                   ORDER BY t.id DESC LIMIT ? OFFSET ?""",
                (user_id, user_id, page_size, offset)
            ).fetchall()
            items = []
            for r in rows:
                d = dict(r)
                # 检查是否已评价
                ev = conn.execute(
                    "SELECT id FROM evaluations WHERE transaction_id = ? AND user_id = ?",
                    (d["id"], user_id)
                ).fetchone()
                d["evaluated"] = ev is not None
                items.append(d)
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": items
            }


class EvaluationRepository:
    """交易评价"""

    @staticmethod
    def evaluate(transaction_id: int, user_id: int, rating: int, content: str = "") -> bool:
        """提交评价"""
        try:
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO evaluations (transaction_id, user_id, rating, content) VALUES (?, ?, ?, ?)",
                    (transaction_id, user_id, rating, content)
                )
            return True
        except sqlite3.IntegrityError:
            return False

    @staticmethod
    def get_by_transaction(transaction_id: int):
        """获取某条交易的评价"""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM evaluations WHERE transaction_id = ?", (transaction_id,)
            ).fetchall()
            return [dict(r) for r in rows]
