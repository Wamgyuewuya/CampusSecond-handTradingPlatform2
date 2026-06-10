"""审核管理功能测试脚本"""
import http.client
import urllib.parse
import re
import json


class TestClient:
    def __init__(self, host="127.0.0.1", port=10086):
        self.host = host
        self.port = port
        self.cookies = {}

    def _update_cookies(self, sc):
        for part in sc.split(","):
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
        return self.request("POST", path, urllib.parse.urlencode(params or {}))


client = TestClient()

# 登录
client.get("/admin/login")
xsrf = client.cookies.get("_xsrf", "")
client.post("/admin/login", {"_xsrf": xsrf, "username": "admin", "password": "admin123"})
assert "username" in client.cookies

# 获取页面的 XSRF
client.get("/admin/goods")
xsrf = client.cookies.get("_xsrf", "")

print("=" * 55)
print("1. 商品审核测试")
print("-" * 40)

# 创建测试商品（模拟用户发布，直接插入数据库）
from app.models.db import get_connection
with get_connection() as conn:
    conn.execute(
        "INSERT INTO goods (user_id, title, description, price) VALUES (?, ?, ?, ?)",
        (1, "测试商品A", "这是一个测试商品", 99.99)
    )
    conn.execute(
        "INSERT INTO goods (user_id, title, description, price) VALUES (?, ?, ?, ?)",
        (1, "测试商品B", "另一个测试商品", 199.00)
    )
print("   ✅ 插入 2 条测试商品")

# 查询商品列表
status, data = client.get("/admin/api/goods")
result = json.loads(data)
assert result["count"] == 2
print(f"   ✅ 商品列表: count={result['count']}")

goods_id = result["data"][0]["id"]
print(f"   商品 #{goods_id} 状态: {result['data'][0]['status']} (应为 pending)")

# 审核通过
status, data = client.post("/admin/api/goods/audit", {
    "_xsrf": xsrf, "id": goods_id, "action": "approved"
})
result = json.loads(data)
assert result["code"] == 0
print(f"   ✅ 审核通过: {result['msg']}")

# 审核拒绝第二个
goods_id2 = result["data"][0]["id"] if False else (goods_id + 1)
# Get the other goods
status, data = client.get("/admin/api/goods")
other = [g for g in json.loads(data)["data"] if g["status"] == "pending"][0]
status, data = client.post("/admin/api/goods/audit", {
    "_xsrf": xsrf, "id": other["id"], "action": "rejected"
})
result = json.loads(data)
assert result["code"] == 0
print(f"   ✅ 审核拒绝商品 #{other['id']}: {result['msg']}")

# 按状态筛选
status, data = client.get("/admin/api/goods?status=approved")
assert json.loads(data)["count"] == 1
print(f"   ✅ 状态筛选(approved): count={json.loads(data)['count']}")

print("\n2. 敏感词管理测试")
print("-" * 40)

# 新增
status, data = client.post("/admin/api/sensitive-word/create", {
    "_xsrf": xsrf, "word": "赌博", "replacement": "***"
})
assert json.loads(data)["code"] == 0
print(f"   ✅ 新增敏感词: 赌博")

status, data = client.post("/admin/api/sensitive-word/create", {
    "_xsrf": xsrf, "word": "色情", "replacement": "***"
})
assert json.loads(data)["code"] == 0
print(f"   ✅ 新增敏感词: 色情")

status, data = client.post("/admin/api/sensitive-word/create", {
    "_xsrf": xsrf, "word": "暴力", "replacement": "**"
})
s = json.loads(data)
assert s["code"] == 0
print(f"   ✅ 新增敏感词: 暴力→{s['data']['replacement'] if 'data' in s else '**'}")

# 查询列表
status, data = client.get("/admin/api/sensitive-words")
result = json.loads(data)
assert result["count"] == 3
words = [w["word"] for w in result["data"]]
print(f"   ✅ 敏感词列表: {', '.join(words)}")

# 修改
word_id = result["data"][0]["id"]
status, data = client.post("/admin/api/sensitive-word/update", {
    "_xsrf": xsrf, "id": word_id, "word": "赌博赌博"
})
assert json.loads(data)["code"] == 0
print(f"   ✅ 修改敏感词: ID={word_id}")

# 删除
status, data = client.post("/admin/api/sensitive-word/delete", {
    "_xsrf": xsrf, "id": word_id
})
assert json.loads(data)["code"] == 0
print(f"   ✅ 删除敏感词: ID={word_id}")

status, data = client.get("/admin/api/sensitive-words")
assert json.loads(data)["count"] == 2
print(f"   ✅ 删除后列表: count={json.loads(data)['count']}")

print("\n3. 举报信息处理测试")
print("-" * 40)

# 模拟插入举报
with get_connection() as conn:
    conn.execute(
        "INSERT INTO reports (reporter_id, target_type, target_id, reason, detail) VALUES (?, ?, ?, ?, ?)",
        (1, "商品", 1, "虚假信息", "描述与实际不符")
    )
    conn.execute(
        "INSERT INTO reports (reporter_id, target_type, target_id, reason, detail) VALUES (?, ?, ?, ?, ?)",
        (1, "用户", 2, "恶意行为", "辱骂其他用户")
    )
print("   ✅ 插入 2 条测试举报")

# 查询
status, data = client.get("/admin/api/reports")
result = json.loads(data)
assert result["count"] == 2
print(f"   ✅ 举报列表: count={result['count']}")

# 处理第一条
report_id = result["data"][0]["id"]
status, data = client.post("/admin/api/report/handle", {
    "_xsrf": xsrf, "id": report_id, "handle_note": "经核实，已下架违规商品"
})
assert json.loads(data)["code"] == 0
print(f"   ✅ 处理举报 #{report_id}: {json.loads(data)['msg']}")

# 空处理意见应被拒绝
report_id2 = result["data"][1]["id"]
status, data = client.post("/admin/api/report/handle", {
    "_xsrf": xsrf, "id": report_id2, "handle_note": ""
})
assert json.loads(data)["code"] == 1
print(f"   ✅ 空处理意见被拒绝: {json.loads(data)['msg']}")

# 按状态筛选
status, data = client.get("/admin/api/reports?status=resolved")
assert json.loads(data)["count"] == 1
print(f"   ✅ 状态筛选(resolved): count={json.loads(data)['count']}")

print("\n" + "=" * 55)
print("ALL AUDIT TESTS PASSED ✅")
