"""
前端-用户侧 控制层
- UserHandler：用户主页
- GoodsPublishHandler：商品发布
- GoodsBrowseHandler / GoodsDetailHandler：商品浏览 / 详情
- GoodsSearchApiHandler：搜索 API
- ChatListHandler / ChatRoomHandler / ChatApiHandler：聊天
- TransactionListHandler / EvaluateApiHandler：交易评价
"""
import os
import json
import datetime

import tornado.web
import tornado.gen
from app.controllers.base import BaseHandler
from app.models.user import UserRepository
from app.models.frontend import GoodsFrontend, ChatRepository, TransactionRepository, EvaluationRepository

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")


class RegisterHandler(BaseHandler):
    """用户注册"""

    def get(self):
        self.render("register.html", title="注册", error=None)

    def post(self):
        username = self.get_body_argument("username", "").strip()
        password = self.get_body_argument("password", "").strip()
        if not username or not password:
            return self.render("register.html", title="注册", error="用户名和密码不能为空")
        if len(username) < 2 or len(username) > 20:
            return self.render("register.html", title="注册", error="用户名长度需在 2-20 个字符")
        if len(password) < 6:
            return self.render("register.html", title="注册", error="密码长度至少 6 位")

        # 敏感词过滤（用户名涉及敏感词的禁止注册）
        filtered = GoodsFrontend.filter_sensitive(username)
        if filtered != username:
            return self.render("register.html", title="注册", error="用户名包含敏感词，请重新输入")

        if UserRepository.create_user(username, password, role="user"):
            self.set_secure_cookie("username", username)
            self.redirect("/home")
        else:
            self.render("register.html", title="注册", error="用户名已存在")


class LoginHandler(BaseHandler):
    """用户登录"""

    def get(self):
        if self.get_current_user():
            return self.redirect("/home")
        self.render("user_login.html", title="登录", error=None)

    def post(self):
        username = self.get_body_argument("username", "").strip()
        password = self.get_body_argument("password", "")

        if not username or not password:
            return self.render("user_login.html", title="登录", error="请输入用户名或密码")

        if not UserRepository.verify_user(username, password):
            return self.render("user_login.html", title="登录", error="用户名或密码错误")

        self.set_secure_cookie("username", username)
        self.redirect("/home")


class LogoutHandler(BaseHandler):
    """用户退出"""

    def get(self):
        self.clear_cookie("username")
        self.redirect("/auth/login")

    def post(self):
        self.clear_cookie("username")
        self.redirect("/auth/login")


class UserHomeHandler(BaseHandler):
    """用户主页"""

    @tornado.web.authenticated
    def get(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        if not user:
            self.redirect("/auth/login")
            return
        uid = user["id"]

        # 统计数据
        from app.models.db import get_connection
        with get_connection() as conn:
            goods_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM goods WHERE user_id = ?", (uid,)
            ).fetchone()["cnt"]
            buy_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM transactions WHERE buyer_id = ?", (uid,)
            ).fetchone()["cnt"]
            sell_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM transactions WHERE seller_id = ?", (uid,)
            ).fetchone()["cnt"]

        # 用户发布的商品
        goods_result = GoodsFrontend.list_by_user(uid)
        # 交易记录
        txn_result = TransactionRepository.list_by_user(uid)

        self.render("user_home.html", title="我的主页",
                     username=user["username"],
                     current_user_id=uid,
                     stats={"goods_count": goods_count, "buy_count": buy_count, "sell_count": sell_count, "user_id": uid},
                     goods_list=goods_result["items"],
                     txn_list=txn_result["items"])


class GoodsPublishHandler(BaseHandler):
    """商品发布"""

    @tornado.web.authenticated
    def get(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        self.render("goods_publish.html", title="发布商品", error=None,
                     username=user["username"] if user else "")

    @tornado.web.authenticated
    def post(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        if not user:
            return self.redirect("/auth/login")

        title = self.get_body_argument("title", "").strip()
        description = self.get_body_argument("description", "").strip()
        price_str = self.get_body_argument("price", "").strip()

        if not title or not price_str:
            return self.render("goods_publish.html", title="发布商品",
                                error="商品名称和价格不能为空")

        try:
            price = float(price_str)
            if price <= 0:
                raise ValueError
        except ValueError:
            return self.render("goods_publish.html", title="发布商品",
                                error="价格必须为正数")

        # 处理图片上传
        image_path = ""
        file_info = self.request.files.get("image", [])
        if file_info:
            file_data = file_info[0]
            ext = os.path.splitext(file_data["filename"])[1] or ".jpg"
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            filename = f"goods_{user['id']}_{int(datetime.datetime.now().timestamp())}{ext}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(file_data["body"])
            image_path = f"/static/uploads/{filename}"
        else:
            return self.render("goods_publish.html", title="发布商品",
                                error="请上传商品图片")

        # 敏感词过滤
        description = GoodsFrontend.filter_sensitive(description)
        GoodsFrontend.publish(user["id"], title, description, price, image_path)
        self.redirect("/home")


class GoodsBrowseHandler(BaseHandler):
    """商品浏览页"""

    def get(self):
        self.render("goods_browse.html", title="商品浏览")


class GoodsBrowseListApiHandler(BaseHandler):
    """商品列表 API（已审核）"""

    def get(self):
        page = int(self.get_argument("page", "1"))
        page_size = int(self.get_argument("limit", "20"))
        keyword = self.get_argument("keyword", "").strip() or None
        result = GoodsFrontend.list_approved(page=page, page_size=page_size, keyword=keyword)
        self.write({
            "code": 0, "msg": "", "count": result["total"], "data": result["items"]
        })


class GoodsDetailHandler(BaseHandler):
    """商品详情页"""

    def get(self, goods_id):
        goods = GoodsFrontend.get_by_id(goods_id)
        if not goods:
            self.redirect("/goods/browse")
            return
        # 获取评论
        comments = GoodsFrontend.get_comments(goods_id)
        # 获取当前用户信息
        user = None
        current_user_name = self.get_current_user()
        is_purchased = False
        is_owner = False
        if current_user_name:
            user = UserRepository.get_user_by_username(current_user_name)
            if user:
                is_purchased = TransactionRepository.check_purchased(goods_id, user["id"])
                is_owner = (goods["user_id"] == user["id"])
        self.render("goods_detail.html", title=goods["title"], goods=goods,
                     current_user=current_user_name,
                     current_user_id=user["id"] if user else 0,
                     comments=comments,
                     is_purchased=is_purchased, is_owner=is_owner)


class ChatListHandler(BaseHandler):
    """消息列表页"""

    @tornado.web.authenticated
    def get(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        if not user:
            return self.redirect("/auth/login")
        conversations = ChatRepository.get_conversation_list(user["id"])
        self.render("chat_list.html", title="消息列表",
                     username=user["username"],
                     current_user_id=user["id"],
                     conversations=conversations)


class ChatRoomHandler(BaseHandler):
    """聊天室页面"""

    @tornado.web.authenticated
    def get(self, other_user_id):
        user = UserRepository.get_user_by_username(self.get_current_user())
        other = UserRepository.get_user_by_id(other_user_id)
        if not user or not other:
            return self.redirect("/home")

        # 标记已读
        ChatRepository.mark_as_read(other["id"], user["id"])

        messages = ChatRepository.get_conversation(user["id"], other["id"])
        self.render("chat_room.html", title=f"与 {other['username']} 聊天",
                     username=user["username"],
                     current_user_id=user["id"],
                     other_user=other,
                     messages=messages)


class ChatSendApiHandler(BaseHandler):
    """发送消息 API"""

    @tornado.web.authenticated
    def post(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        if not user:
            return self.write({"code": 1, "msg": "未登录"})
        to_user_id = int(self.get_body_argument("to_user_id", "0"))
        content = self.get_body_argument("content", "").strip()
        if not content:
            return self.write({"code": 1, "msg": "消息不能为空"})
        # 敏感词过滤
        content = GoodsFrontend.filter_sensitive(content)
        ChatRepository.send_message(user["id"], to_user_id, content)
        self.write({"code": 0, "msg": "发送成功"})


class ChatMessagesApiHandler(BaseHandler):
    """获取聊天消息 API"""

    @tornado.web.authenticated
    def get(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        if not user:
            return self.write({"code": 1, "msg": "未登录", "data": []})
        other_user_id = int(self.get_argument("other_user_id", "0"))
        messages = ChatRepository.get_conversation(user["id"], other_user_id)
        self.write({"code": 0, "data": messages})


class TransactionListHandler(BaseHandler):
    """交易记录页面"""

    @tornado.web.authenticated
    def get(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        if not user:
            return self.redirect("/auth/login")
        result = TransactionRepository.list_by_user(user["id"])
        self.render("transaction_list.html", title="交易记录",
                     username=user["username"],
                     transactions=result["items"],
                     user_id=user["id"])


class EvaluateApiHandler(BaseHandler):
    """提交评价 API"""

    @tornado.web.authenticated
    def post(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        if not user:
            return self.write({"code": 1, "msg": "未登录"})

        transaction_id = int(self.get_body_argument("transaction_id", "0"))
        rating = int(self.get_body_argument("rating", "0"))
        content = self.get_body_argument("content", "").strip()

        if rating < 1 or rating > 5:
            return self.write({"code": 1, "msg": "评分需在 1-5 之间"})

        # 验证交易属于该用户
        from app.models.db import get_connection
        with get_connection() as conn:
            txn = conn.execute(
                "SELECT * FROM transactions WHERE id = ? AND (buyer_id = ? OR seller_id = ?)",
                (transaction_id, user["id"], user["id"])
            ).fetchone()
            if not txn:
                return self.write({"code": 1, "msg": "交易记录不存在"})

        ok = EvaluationRepository.evaluate(transaction_id, user["id"], rating, content)
        self.write({"code": 0 if ok else 1, "msg": "评价成功" if ok else "评价失败或已评价"})


class CommentListApiHandler(BaseHandler):
    """获取商品评论 API"""

    def get(self):
        goods_id = int(self.get_argument("goods_id", "0"))
        comments = GoodsFrontend.get_comments(goods_id)
        self.write({"code": 0, "data": comments})


class CommentCreateApiHandler(BaseHandler):
    """发表评论 API"""

    @tornado.web.authenticated
    def post(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        if not user:
            return self.write({"code": 1, "msg": "未登录"})
        goods_id = int(self.get_body_argument("goods_id", "0"))
        content = self.get_body_argument("content", "").strip()
        if not content:
            return self.write({"code": 1, "msg": "评论内容不能为空"})
        # 敏感词过滤
        content = GoodsFrontend.filter_sensitive(content)
        # 验证商品存在
        goods = GoodsFrontend.get_by_id(goods_id)
        if not goods:
            return self.write({"code": 1, "msg": "商品不存在"})
        GoodsFrontend.add_comment(goods_id, user["id"], content)
        self.write({"code": 0, "msg": "评论成功"})


class BuyApiHandler(BaseHandler):
    """购买商品 API"""

    @tornado.web.authenticated
    def post(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        if not user:
            return self.write({"code": 1, "msg": "未登录"})
        goods_id = int(self.get_body_argument("goods_id", "0"))
        goods = GoodsFrontend.get_by_id(goods_id)
        if not goods:
            return self.write({"code": 1, "msg": "商品不存在"})
        if goods["status"] != "approved":
            return self.write({"code": 1, "msg": "该商品尚未上架"})
        if goods["user_id"] == user["id"]:
            return self.write({"code": 1, "msg": "不能购买自己的商品"})
        if TransactionRepository.check_purchased(goods_id, user["id"]):
            return self.write({"code": 1, "msg": "您已购买过该商品"})
        TransactionRepository.create_transaction(goods_id, goods["user_id"], user["id"], goods["price"])
        self.write({"code": 0, "msg": "购买成功"})


class ReportCreateApiHandler(BaseHandler):
    """用户提交举报 API"""

    @tornado.web.authenticated
    def post(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        if not user:
            return self.write({"code": 1, "msg": "未登录"})
        target_type = self.get_body_argument("target_type", "").strip()
        target_id = int(self.get_body_argument("target_id", "0"))
        reason = self.get_body_argument("reason", "").strip()
        detail = self.get_body_argument("detail", "").strip()
        if not target_type or not target_id or not reason:
            return self.write({"code": 1, "msg": "举报信息不完整"})
        if target_type not in ("goods", "user"):
            return self.write({"code": 1, "msg": "举报类型无效"})
        from app.models.audit import ReportRepository
        ReportRepository.create_report(user["id"], target_type, target_id, reason, detail)
        self.write({"code": 0, "msg": "举报提交成功，等待管理员处理"})


class ReportListHandler(BaseHandler):
    """用户举报记录页"""

    @tornado.web.authenticated
    def get(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        self.render("user_report_list.html", title="我的举报",
                     username=user["username"] if user else "",
                     current_user_id=user["id"] if user else 0)


class UserReportListApiHandler(BaseHandler):
    """用户自己的举报列表 API"""

    @tornado.web.authenticated
    def get(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        if not user:
            return self.write({"code": 1, "msg": "未登录", "data": [], "total": 0})
        page = int(self.get_argument("page", "1"))
        page_size = int(self.get_argument("page_size", "20"))
        from app.models.audit import ReportRepository
        result = ReportRepository.list_by_reporter(user["id"], page, page_size)
        self.write({"code": 0, "data": result["items"], "total": result["total"]})
