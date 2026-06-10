import os
import tornado.ioloop 
import tornado.web
from tornado.httpserver import HTTPServer

# v0.3 加载动态登录业务
from app.controllers.auth import LogoutHandler
from app.controllers.home import AdminHandler
# v0.4 加载后台管理业务
from app.controllers.admin import (
    AdminLoginHandler, AdminLogoutHandler,
    DashboardHandler, DashboardHomeHandler,
    UserManageHandler,
    UserListApiHandler, UserCreateApiHandler,
    UserUpdateApiHandler, UserDeleteApiHandler,
    # v0.5 审核管理
    GoodsManageHandler, GoodsListApiHandler, GoodsAuditApiHandler,
    ReportManageHandler, ReportListApiHandler, ReportHandleApiHandler,
    SensitiveWordManageHandler, SensitiveWordListApiHandler,
    SensitiveWordCreateApiHandler, SensitiveWordUpdateApiHandler,
    SensitiveWordDeleteApiHandler,
)
# v0.6 前端-用户侧
from app.controllers.frontend import (
    LoginHandler, RegisterHandler, UserHomeHandler,
    GoodsPublishHandler, GoodsBrowseHandler, GoodsDetailHandler,
    GoodsBrowseListApiHandler,
    ChatListHandler, ChatRoomHandler, ChatSendApiHandler,
    ChatMessagesApiHandler, TransactionListHandler, EvaluateApiHandler,
    CommentListApiHandler, CommentCreateApiHandler,
    ReportCreateApiHandler, ReportListHandler, UserReportListApiHandler,
    BuyApiHandler,
)
from app.models.db import init_db

def make_app():
	base_dir = os.path.dirname(os.path.abspath(__file__))

	settings = dict(
		template_path=os.path.join(base_dir,"app","templates"),
		static_path=os.path.join(base_dir,"app","static"),
		cookie_secret="demo-cookie-secrete-change-me",
		login_url="/auth/login",
		xsrf_cookies=True,
		debug=True,
		auto_reload=True
	)

	return tornado.web.Application([
		(r"/", LoginHandler),                      # 首页（指向用户登录）
		(r"/auth/login", LoginHandler),            # 用户登录
		(r"/auth/register", RegisterHandler),      # 用户注册
		(r"/auth/logout", LogoutHandler),          # 用户退出
		(r"/admin", AdminHandler),                 # 后台（旧）

		# ---- 后台管理路由（v0.4） ----
		(r"/admin/login", AdminLoginHandler),       # 后台登录
		(r"/admin/logout", AdminLogoutHandler),     # 后台退出
		(r"/admin/dashboard", DashboardHandler),    # 后台主页
		(r"/admin/dashboard/home", DashboardHomeHandler),  # 后台欢迎页
		(r"/admin/users", UserManageHandler),       # 用户管理页

		# ---- 用户管理 API ----
		(r"/admin/api/users", UserListApiHandler),
		(r"/admin/api/user/create", UserCreateApiHandler),
		(r"/admin/api/user/update", UserUpdateApiHandler),
		(r"/admin/api/user/delete", UserDeleteApiHandler),

		# ---- 审核管理路由（v0.5） ----
		(r"/admin/goods", GoodsManageHandler),                   # 商品审核页
		(r"/admin/reports", ReportManageHandler),                 # 举报处理页
		(r"/admin/sensitive-words", SensitiveWordManageHandler),  # 敏感词管理页

		# ---- 审核管理 API ----
		(r"/admin/api/goods", GoodsListApiHandler),
		(r"/admin/api/goods/audit", GoodsAuditApiHandler),
		(r"/admin/api/reports", ReportListApiHandler),
		(r"/admin/api/report/handle", ReportHandleApiHandler),
		(r"/admin/api/sensitive-words", SensitiveWordListApiHandler),
		(r"/admin/api/sensitive-word/create", SensitiveWordCreateApiHandler),
		(r"/admin/api/sensitive-word/update", SensitiveWordUpdateApiHandler),
		(r"/admin/api/sensitive-word/delete", SensitiveWordDeleteApiHandler),

		# ---- 前端-用户侧路由（v0.6） ----
		(r"/home", UserHomeHandler),                       # 用户主页
		(r"/goods/publish", GoodsPublishHandler),           # 商品发布
		(r"/goods/browse", GoodsBrowseHandler),             # 商品浏览
		(r"/goods/detail/(\d+)", GoodsDetailHandler),       # 商品详情

		# ---- 前端 API ----
		(r"/api/goods/list", GoodsBrowseListApiHandler),    # 商品列表API

		# ---- 聊天 ----
		(r"/chat/list", ChatListHandler),                   # 消息列表
		(r"/chat/(\d+)", ChatRoomHandler),                  # 聊天室
		(r"/api/chat/send", ChatSendApiHandler),            # 发送消息
		(r"/api/chat/messages", ChatMessagesApiHandler),    # 获取消息

		# ---- 交易评价 ----
		(r"/transaction/list", TransactionListHandler),     # 交易记录
		(r"/api/transaction/evaluate", EvaluateApiHandler), # 提交评价

		# ---- 商品评论 ----
		(r"/api/goods/comments", CommentListApiHandler),     # 获取评论
		(r"/api/goods/comment/create", CommentCreateApiHandler),  # 发表评论

		# ---- 购买商品 ----
		(r"/api/goods/buy", BuyApiHandler),                  # 购买商品

		# ---- 举报功能（用户侧） ----
		(r"/api/report/create", ReportCreateApiHandler),     # 提交举报
		(r"/report/list", ReportListHandler),                # 我的举报页
		(r"/api/report/list", UserReportListApiHandler),     # 我的举报列表API
	],**settings)

if __name__ == "__main__":
	init_db()
	app = make_app()
	server = HTTPServer(app)
	server.listen(10086)
	print("Server Start At http://127.0.0.1:10086")
	tornado.ioloop.IOLoop.current().start()