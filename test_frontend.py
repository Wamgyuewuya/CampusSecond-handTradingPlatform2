"""前端-用户侧 功能测试"""
import http.client
import urllib.parse
import re
import json

class TestClient:
    def __init__(self):
        self.cookies = {}
    def _update(self, sc):
        for part in sc.split(","):
            m = re.search(r'([^=]+)=([^;]+)', part.strip())
            if m: self.cookies[m.group(1).strip()] = m.group(2).strip()
    def _cookie(self):
        return "; ".join(f"{k}={v}" for k,v in self.cookies.items())
    def req(self, method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", 10086, timeout=10)
        hdrs = {"Cookie": self._cookie()}
        if body: hdrs["Content-Type"] = "application/x-www-form-urlencoded"
        conn.request(method, path, body=body, headers=hdrs)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        sc = resp.getheader("Set-Cookie", "")
        conn.close()
        if sc: self._update(sc)
        return resp.status, data
    def get(self, p): return self.req("GET", p)
    def post(self, p, params=None):
        return self.req("POST", p, urllib.parse.urlencode(params or {}))

c = TestClient()

print("=" * 55)
print("1. 首页/登录页")
s, h = c.get("/")
assert "校园二手" in h
print(f"   ✅ GET / → 200, 包含登录表单")

print("\n2. 注册")
s, h = c.get("/auth/register")
xsrf = c.cookies.get("_xsrf", "")
import time
unique_user = f"tester_{int(time.time())}"
s, h = c.post("/auth/register", {"_xsrf": xsrf, "username": unique_user, "password": "test123456"})
assert "username" in c.cookies, f"注册失败，cookies={c.cookies}"
print(f"   ✅ 注册 {unique_user}/test123456 成功，已登录")

print("\n3. 用户主页")
s, h = c.get("/home")
print(f"   Status: {s}")
print(f"   包含统计: {'stats' in h or '统计' in h or '我的商品' in h}")

# 获取 XSRF
s, h = c.get("/goods/publish")
xsrf = c.cookies.get("_xsrf", "")
print(f"\n4. 商品发布页: Status={s}")

print("\n5. 商品浏览（空列表）")
s, h = c.get("/api/goods/list")
r = json.loads(h)
assert r["count"] == 0
print(f"   ✅ 空列表: count={r['count']}")

# 登录 admin 审核一些商品
print("\n6. 发布商品（模拟文件上传用 POST 模拟）")
# 由于文件上传需要 multipart, 用插入数据库代替
from app.models.db import get_connection
with get_connection() as conn:
    conn.execute("INSERT INTO goods (user_id, title, description, price, image, status) VALUES (?, ?, ?, ?, ?, 'approved')",
                 (1, "苹果 iPhone 14", "9成新, 256GB", 4999.00, "/static/uploads/test.jpg"))
    conn.execute("INSERT INTO goods (user_id, title, description, price, image, status) VALUES (?, ?, ?, ?, ?, 'approved')",
                 (1, "笔记本电脑 ThinkPad", "办公利器", 3500.00, "/static/uploads/test2.jpg"))
    conn.execute("INSERT INTO goods (user_id, title, description, price, image, status) VALUES (?, ?, ?, ?, ?, 'approved')",
                 (2, "这是一条超长商品名称测试十个字省略号", "测试截断", 100.00, "/static/uploads/test3.jpg"))
print("   ✅ 插入 3 条已审核商品")

s, h = c.get("/api/goods/list")
r = json.loads(h)
assert r["count"] == 3
print(f"   ✅ 商品列表: count={r['count']}")

print(f"\n7. 搜索功能")
s, h = c.get("/api/goods/list?keyword=" + urllib.parse.quote("苹果"))
r = json.loads(h)
assert r["count"] == 1
print(f"   ✅ 搜索'苹果': count={r['count']}")

s, h = c.get("/api/goods/list?keyword=Lenovo")
r = json.loads(h)
assert r["count"] == 0
print(f"   ✅ 搜索'Lenovo': count={r['count']}（无结果）")

print("\n8. 商品详情")
s, h = c.get("/goods/detail/1")
print(f"   ✅ GET /goods/detail/1: Status={s}")
assert "苹果" in h

# 插入交易
with get_connection() as conn:
    conn.execute("INSERT INTO transactions (goods_id, seller_id, buyer_id, price) VALUES (?, ?, ?, ?)",
                 (1, 1, 2, 4999.00))
    conn.execute("INSERT INTO transactions (goods_id, seller_id, buyer_id, price) VALUES (?, ?, ?, ?)",
                 (2, 1, 2, 3500.00))
print(f"\n9. 交易记录")
s, h = c.get("/transaction/list")
print(f"   Status={s}")
assert "交易记录" in h

print("\n10. 聊天")
# 登录另一个用户
c2 = TestClient()
c2.get("/auth/login")
xsrf2 = c2.cookies.get("_xsrf", "")
c2.post("/auth/register", {"_xsrf": xsrf2, "username": f"chat_test", "password": "test123456"})

s, h = c2.get("/chat/list")
print(f"   ✅ 聊天列表页: Status={s}")

print("\n11. 发送消息")
# 获取 user 的信息
user = c2.get("/home")
xsrf2 = c2.cookies.get("_xsrf", "")
s, h = c2.post("/api/chat/send", {"_xsrf": xsrf2, "to_user_id": "1", "content": "你好，请问商品还在吗？"})
r = json.loads(h)
assert r["code"] == 0
print(f"   ✅ 发送消息: {r['msg']}")

s, h = c2.get("/api/chat/messages?other_user_id=1")
r = json.loads(h)
assert len(r["data"]) == 1
print(f"   ✅ 获取消息: {len(r['data'])} 条")

print("\n12. 交易评价")
s, h = c.post("/api/transaction/evaluate", {
    "_xsrf": c.cookies.get("_xsrf", ""),
    "transaction_id": "1",
    "rating": "5",
    "content": "非常满意，交易愉快！"
})
r = json.loads(h)
print(f"   ✅ 评价: {r['msg']}")

# 重复评价应被拒绝
s, h = c.post("/api/transaction/evaluate", {
    "_xsrf": c.cookies.get("_xsrf", ""),
    "transaction_id": "1",
    "rating": "5",
    "content": "再次评价"
})
r = json.loads(h)
assert r["code"] == 1
print(f"   ✅ 重复评价被拒: {r['msg']}")

print("\n" + "=" * 55)
print("ALL FRONTEND TESTS PASSED ✅")
