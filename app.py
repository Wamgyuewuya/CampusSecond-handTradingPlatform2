import os
import tornado.ioloop 
import tornado.web
from tornado.httpserver import HTTPServer

# v0.3 加载动态登录业务
from app.controllers.auth import LoginHandler, LogoutHandler
from app.controllers.home import AdminHandler
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
		(r"/", LoginHandler),                # 首页
		(r"/auth/login", LoginHandler),      # 登录
		(r"/auth/logout", LogoutHandler),    # 退出
		(r"/admin", AdminHandler),           # 后台
	],**settings)

if __name__ == "__main__":
	init_db()
	app = make_app()
	server = HTTPServer(app)
	server.listen(10086)
	print("Server Start At http://127.0.0.1:10086")
	tornado.ioloop.IOLoop.current().start()