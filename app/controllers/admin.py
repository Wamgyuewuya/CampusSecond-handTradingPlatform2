"""
admin 控制层 — 后台管理
- AdminLoginHandler：管理员登录
- UserManageHandler：用户管理（CRUD + 分页）
"""
import json

import tornado.web
from app.controllers.base import BaseHandler
from app.models.user import UserRepository
from app.models.audit import GoodsRepository, ReportRepository, SensitiveWordRepository


class AdminLoginHandler(BaseHandler):
    """管理员登录页（独立于前台登录）"""

    def get(self):
        # 如果已登录，直接跳转后台
        if self.get_current_user():
            # 验证是否为 admin 角色
            user = UserRepository.get_user_by_username(self.get_current_user())
            if user and user["role"] == "admin":
                return self.redirect("/admin/dashboard")
        self.render("admin_login.html", error=None)

    def post(self):
        username = self.get_body_argument("username", "").strip()
        password = self.get_body_argument("password", "")

        if not username or not password:
            return self.render("admin_login.html", error="请输入用户名和密码")

        # 验证用户是否存在且角色为 admin
        user = UserRepository.get_user_by_username(username)
        if not user or user["role"] != "admin":
            return self.render("admin_login.html", error="管理员账号或密码错误")

        if not UserRepository.verify_user(username, password):
            return self.render("admin_login.html", error="管理员账号或密码错误")

        self.set_secure_cookie("username", username)
        self.redirect("/admin/dashboard")


class AdminLogoutHandler(BaseHandler):
    """管理员退出"""

    def get(self):
        self.clear_cookie("username")
        self.redirect("/admin/login")


class DashboardHandler(BaseHandler):
    """后台主页 — 含左侧菜单的主框架"""

    @tornado.web.authenticated
    def get(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        if not user or user["role"] != "admin":
            self.redirect("/admin/login")
            return
        self.render("admin_dashboard.html", title="后台首页",
                     username=self.get_current_user())


class DashboardHomeHandler(BaseHandler):
    """后台主页 — iframe 内嵌欢迎页"""

    @tornado.web.authenticated
    def get(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        if not user or user["role"] != "admin":
            self.redirect("/admin/login")
            return
        self.render("admin_dashboard_home.html", title="后台首页",
                     username=self.get_current_user())


class UserManageHandler(BaseHandler):
    """用户管理 — JSON API"""

    @tornado.web.authenticated
    def get(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        if not user or user["role"] != "admin":
            self.redirect("/admin/login")
            return
        self.render("admin_users.html", title="用户管理",
                     username=self.get_current_user())


class UserListApiHandler(BaseHandler):
    """用户列表 API（分页 JSON）"""

    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", "1"))
        page_size = int(self.get_argument("limit", "20"))
        result = UserRepository.list_users(page=page, page_size=page_size)
        self.write({
            "code": 0,
            "msg": "",
            "count": result["total"],
            "data": result["items"]
        })


class UserCreateApiHandler(BaseHandler):
    """新增用户 API"""

    @tornado.web.authenticated
    def post(self):
        username = self.get_body_argument("username", "").strip()
        password = self.get_body_argument("password", "").strip()
        if not username or not password:
            return self.write({"code": 1, "msg": "用户名和密码不能为空"})
        if UserRepository.create_user(username, password, role="user"):
            self.write({"code": 0, "msg": "创建成功"})
        else:
            self.write({"code": 1, "msg": "用户名已存在"})


class UserUpdateApiHandler(BaseHandler):
    """修改用户 API — 不可修改管理员"""

    @tornado.web.authenticated
    def post(self):
        user_id = int(self.get_body_argument("id", "0"))
        # 检查是否为管理员
        user = UserRepository.get_user_by_id(user_id)
        if not user:
            return self.write({"code": 1, "msg": "用户不存在"})
        if user["role"] == "admin":
            return self.write({"code": 1, "msg": "管理员账号不可修改"})

        username = self.get_body_argument("username", "").strip()
        password = self.get_body_argument("password", "").strip()
        kwargs = {}
        if username:
            kwargs["username"] = username
        if password:
            kwargs["password"] = password
        if not kwargs:
            return self.write({"code": 1, "msg": "没有需要修改的内容"})
        ok = UserRepository.update_user(user_id, **kwargs)
        if username and not ok:
            return self.write({"code": 1, "msg": "用户名已存在"})
        self.write({"code": 0, "msg": "修改成功"})


class UserDeleteApiHandler(BaseHandler):
    """删除用户 API — 不可删除管理员"""

    @tornado.web.authenticated
    def post(self):
        user_id = int(self.get_body_argument("id", "0"))
        # 检查是否为管理员
        user = UserRepository.get_user_by_id(user_id)
        if not user:
            return self.write({"code": 1, "msg": "用户不存在"})
        if user["role"] == "admin":
            return self.write({"code": 1, "msg": "管理员账号不可删除"})
        ok = UserRepository.delete_user(user_id)
        self.write({"code": 0 if ok else 1, "msg": "删除成功" if ok else "删除失败"})


# ============================================================
# 审核管理 v0.5
# ============================================================

class _AdminCheckMixin:
    """检查是否为 admin 角色的混入方法"""

    def _check_admin(self):
        user = UserRepository.get_user_by_username(self.get_current_user())
        if not user or user["role"] != "admin":
            self.redirect("/admin/login")
            return None
        return user


class GoodsManageHandler(BaseHandler, _AdminCheckMixin):
    """商品审核页面"""

    @tornado.web.authenticated
    def get(self):
        if not self._check_admin():
            return
        self.render("admin_goods.html", title="违规商品审核",
                     username=self.get_current_user())


class GoodsListApiHandler(BaseHandler):
    """商品列表 API"""

    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", "1"))
        page_size = int(self.get_argument("limit", "20"))
        status = self.get_argument("status", "") or None
        result = GoodsRepository.list_goods(page=page, page_size=page_size, status=status)
        self.write({
            "code": 0, "msg": "", "count": result["total"], "data": result["items"]
        })


class GoodsAuditApiHandler(BaseHandler):
    """商品审核 API"""

    @tornado.web.authenticated
    def post(self):
        goods_id = int(self.get_body_argument("id", "0"))
        action = self.get_body_argument("action", "")
        if action not in ("approved", "rejected"):
            return self.write({"code": 1, "msg": "无效的审核操作"})
        ok = GoodsRepository.audit_goods(goods_id, action)
        label = "已审核" if action == "approved" else "已拒绝"
        self.write({"code": 0 if ok else 1, "msg": label if ok else "审核失败"})


class ReportManageHandler(BaseHandler, _AdminCheckMixin):
    """举报信息处理页面"""

    @tornado.web.authenticated
    def get(self):
        if not self._check_admin():
            return
        self.render("admin_reports.html", title="举报信息处理",
                     username=self.get_current_user())


class ReportListApiHandler(BaseHandler):
    """举报列表 API"""

    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", "1"))
        page_size = int(self.get_argument("limit", "20"))
        status = self.get_argument("status", "") or None
        result = ReportRepository.list_reports(page=page, page_size=page_size, status=status)
        self.write({
            "code": 0, "msg": "", "count": result["total"], "data": result["items"]
        })


class ReportHandleApiHandler(BaseHandler):
    """处理举报 API"""

    @tornado.web.authenticated
    def post(self):
        report_id = int(self.get_body_argument("id", "0"))
        handle_note = self.get_body_argument("handle_note", "").strip()
        if not handle_note:
            return self.write({"code": 1, "msg": "请填写处理意见"})
        user = UserRepository.get_user_by_username(self.get_current_user())
        ok = ReportRepository.handle_report(report_id, user["id"], handle_note)
        self.write({"code": 0 if ok else 1, "msg": "处理成功" if ok else "处理失败"})


class SensitiveWordManageHandler(BaseHandler, _AdminCheckMixin):
    """敏感词管理页面"""

    @tornado.web.authenticated
    def get(self):
        if not self._check_admin():
            return
        self.render("admin_sensitive_words.html", title="敏感词管理",
                     username=self.get_current_user())


class SensitiveWordListApiHandler(BaseHandler):
    """敏感词列表 API"""

    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", "1"))
        page_size = int(self.get_argument("limit", "20"))
        result = SensitiveWordRepository.list_words(page=page, page_size=page_size)
        self.write({
            "code": 0, "msg": "", "count": result["total"], "data": result["items"]
        })


class SensitiveWordCreateApiHandler(BaseHandler):
    """新增敏感词 API"""

    @tornado.web.authenticated
    def post(self):
        word = self.get_body_argument("word", "").strip()
        replacement = self.get_body_argument("replacement", "***").strip()
        if not word:
            return self.write({"code": 1, "msg": "敏感词不能为空"})
        ok = SensitiveWordRepository.add_word(word, replacement)
        self.write({"code": 0 if ok else 1, "msg": "添加成功" if ok else "敏感词已存在"})


class SensitiveWordUpdateApiHandler(BaseHandler):
    """修改敏感词 API"""

    @tornado.web.authenticated
    def post(self):
        word_id = int(self.get_body_argument("id", "0"))
        word = self.get_body_argument("word", "").strip()
        replacement = self.get_body_argument("replacement", "").strip()
        kwargs = {}
        if word:
            kwargs["word"] = word
        if replacement:
            kwargs["replacement"] = replacement
        if not kwargs:
            return self.write({"code": 1, "msg": "没有需要修改的内容"})
        ok = SensitiveWordRepository.update_word(word_id, **kwargs)
        self.write({"code": 0 if ok else 1, "msg": "修改成功" if ok else "修改失败"})


class SensitiveWordDeleteApiHandler(BaseHandler):
    """删除敏感词 API"""

    @tornado.web.authenticated
    def post(self):
        word_id = int(self.get_body_argument("id", "0"))
        ok = SensitiveWordRepository.delete_word(word_id)
        self.write({"code": 0 if ok else 1, "msg": "删除成功" if ok else "删除失败"})
