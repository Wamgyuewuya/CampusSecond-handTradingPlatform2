"""后台管理功能测试脚本 — 支持 XSRF"""
import http.client
import urllib.parse
import re
import json


class TestClient:
    def __init__(self, host="127.0.0.1", port=10086):
        self.host = host
        self.port = port
        self.cookies = {}

    def _update_cookies(self, set_cookie):
        for part in set_cookie.split(","):
            m = re.search(r'([^=]+)=([^;]+)', part.strip())
            if m:
                self.cookies[m.group(1).strip()] = m.group(2).strip()

    def _cookie_header(self):
        return "; ".join(f"{k}={v}" for k, v in self.cookies.items())

    def request(self, method, path, body=None):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=10)
        headers = {"Cookie": self._cookie_header()}
        if body:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        sc = resp.getheader("Set-Cookie", "")
        conn.close()
        if sc:
            self._update_cookies(sc)
        return resp.status, data

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, params=None):
        body = urllib.parse.urlencode(params or {})
        return self.request("POST", path, body)


client = TestClient()

# 1. 登录
print("=" * 55)
print("1. GET /admin/login → 获取 XSRF")
status, html = client.get("/admin/login")
assert status == 200
assert "login-form" in html
xsrf = client.cookies.get("_xsrf", "")
print(f"   ✅ XSRF token: {xsrf[:25]}...")

# 2. 登录 admin
status, html = client.post("/admin/login", {
    "_xsrf": xsrf, "username": "admin", "password": "admin123"
})
assert status == 302 or status == 200
assert "username" in client.cookies
print("   ✅ admin/admin123 登录成功")

# 3. 访问用户管理页，获取新 XSRF
status, html = client.get("/admin/users")
xsrf = client.cookies.get("_xsrf", "")
print(f"   ✅ 获取用户管理页 XSRF: {xsrf[:25]}...")

# 4. 用户列表 — 应包含 admin
status, data = client.get("/admin/api/users")
result = json.loads(data)
print(f"\n2. 用户列表 API:")
print(f"   Status: {status}, Total: {result['count']}")
items = result["data"]
for u in items:
    print(f"   - ID={u['id']}, {u['username']}, role={u['role']}({u['role_label']})")
assert any(u["username"] == "admin" for u in items), "admin 应在列表中!"
assert any(u["role"] == "admin" for u in items), "应有 admin 角色!"
print("   ✅ 列表中包含管理员账号，且显示角色标签")

# 5. 尝试修改 admin — 应被拒绝
admin_id = [u["id"] for u in items if u["role"] == "admin"][0]
print(f"\n3. 尝试修改 admin (id={admin_id})")
status, data = client.post("/admin/api/user/update", {
    "_xsrf": xsrf, "id": admin_id, "username": "admin_hacked"
})
result = json.loads(data)
assert result["code"] == 1
print(f"   ✅ 被拒绝: {result['msg']}")

# 6. 尝试删除 admin — 应被拒绝
print(f"\n4. 尝试删除 admin (id={admin_id})")
status, data = client.post("/admin/api/user/delete", {
    "_xsrf": xsrf, "id": admin_id
})
result = json.loads(data)
assert result["code"] == 1
print(f"   ✅ 被拒绝: {result['msg']}")

# 7. 创建普通用户 → 修改 → 删除
import time
unique = f"test_{int(time.time())}"
print(f"\n5. 测试普通用户 CRUD (username={unique})")
status, data = client.post("/admin/api/user/create", {
    "_xsrf": xsrf, "username": unique, "password": "123456"
})
result = json.loads(data)
assert result["code"] == 0
print(f"   ✅ 创建: {result['msg']}")

# 获取刚创建的用户 ID
status, data = client.get("/admin/api/users")
items = json.loads(data)["data"]
new_user = [u for u in items if u["username"] == unique][0]
new_id = new_user["id"]

# 修改
status, data = client.post("/admin/api/user/update", {
    "_xsrf": xsrf, "id": new_id, "username": "test_crud_v2"
})
result = json.loads(data)
assert result["code"] == 0
print(f"   ✅ 修改: {result['msg']}")

# 删除
status, data = client.post("/admin/api/user/delete", {
    "_xsrf": xsrf, "id": new_id
})
result = json.loads(data)
assert result["code"] == 0
print(f"   ✅ 删除: {result['msg']}")

print("\n" + "=" * 55)
print("ALL TESTS PASSED ✅")
