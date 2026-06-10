# admin 控制层
import tornado.web
from app.controllers.base import BaseHandler

# 修复：类名大写开头
class AdminHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		# 修复：cookie 是 bytes，需要 decode 显示正常
		username = self.current_user.decode("utf-8") if self.current_user else ""
		self.render("admin.html", title="后台首页", username=username)