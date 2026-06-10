# 用于登录/注册/退出 有关的控制层方法
import tornado.web
from app.controllers.base import BaseHandler
from app.models.user import UserRepository

class LoginHandler(BaseHandler):
	def get(self):
		self.render("login.html",title="登录",error=None)

	def post(self):
		username = self.get_body_argument("username","").strip()
		password = self.get_body_argument("password","")

		if not username or not password:
			self.set_status(400)
			return self.render("login.html",title="登录",error="请输入用户名或密码")

		if not UserRepository.verify_user(username,password):
			self.set_status(401)
			return self.render("login.html",title="登录",error="输入的用户名或密码错误")

		self.set_secure_cookie("username",username)
		self.redirect("/admin")

# 修复：大写开头 + 支持GET退出
class LogoutHandler(BaseHandler):
	def get(self):
		self.clear_cookie("username")
		self.redirect("/")

	def post(self):
		self.clear_cookie("username")
		self.redirect("/")