"""
基类：
- tornado.web.RequestHandler
- 处理cookie / seedion /token
- @authenticated

"""
import tornado.web 
class BaseHandler(tornado.web.RequestHandler):
	def get_current_user(self):
		username = self.get_secure_cookie("username")
		if not username:
			return None
		return username.decode('utf-8')