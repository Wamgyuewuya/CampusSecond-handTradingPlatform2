"""测试 4.1：商品评论 + 聊天左右区分 + 敏感词过滤"""
import http.client, urllib.parse, re, json, os, time

class Client:
    def __init__(self):
        self.cookies = {}
    def _upd(self, sc):
        for part in sc.split(","):
            part = part.strip()
            m = re.search(r'([^=]+)=([^;]+)', part)
            if m:
                k = m.group(1).strip()
                v = m.group(2).strip()
                if k not in ("path", "Path", "expires", "Expires", "httponly", "HttpOnly", "secure", "SameSite"):
                    self.cookies[k] = v
    def _ck(self):
        return "; ".join(f"{k}={v}" for k,v in self.cookies.items())
    def req(self, m, p, b=None):
        conn = http.client.HTTPConnection("127.0.0.1",10086,timeout=10)
        h = {"Cookie": self._ck()}
        if b: h["Content-Type"] = "application/x-www-form-urlencoded"
        conn.request(m, p, body=b, headers=h)
        r = conn.getresponse()
        d = r.read().decode("utf-8")
        sc = r.getheader("Set-Cookie","")
        conn.close()
        if sc: self._upd(sc)
        return r.status, d
    def get(self, p): return self.req("GET", p)
    def post(self, p, params=None):
        return self.req("POST", p, urllib.parse.urlencode(params or {}))

c = Client()
print("=" * 55)

# 1. 获取登录页获取XSRF
s, h = c.get("/auth/login")
xsrf = c.cookies.get("_xsrf","")
print(f"1. GET /auth/login: Status={s}, _xsrf={xsrf[:20]}...")

# 2. 注册（使用唯一用户名避免冲突）
import time
unique_user = f"ct_{int(time.time())}"
s, h = c.post("/auth/register", {"_xsrf": xsrf, "username": unique_user, "password": "test123456"})
print(f"2. 注册 {unique_user}/{s} ✅")

# 3. 用 user/user123 登录确保认证状态一致
c.get("/auth/login")
xsrf = c.cookies.get("_xsrf","")
s, h = c.post("/auth/login", {"_xsrf": xsrf, "username": "user", "password": "user123"})
# 刷新 XSRF
c.get("/home")
print(f"3. 登录 user/user123: {s} ✅")

# 4. 创建测试商品
from app.models.db import get_connection
with get_connection() as conn:
    cur = conn.execute("INSERT INTO goods (user_id,title,description,price,image,status) VALUES (?,?,?,?,?,?)",
                      (1,"测试商品-评论系统","测试描述",99,"/s/t.jpg","approved"))
    goods_id = cur.lastrowid
print(f"4. 插入测试商品 id={goods_id} ✅")

# 5. 获取详情页
s, h = c.get(f"/goods/detail/{goods_id}")
assert "商品评论" in h
print(f"5. 商品详情页: Status={s} ✅ 含评论区域")

# 6. 发表评论 - 直接使用当前 xsrf
s, h = c.post("/api/goods/comment/create", {
    "_xsrf": c.cookies.get("_xsrf",""),
    "goods_id": str(goods_id),
    "content": "这个商品看起来不错！"
})
print(f"6. POST 评论: Status={s}, body={h[:300]}")
r = json.loads(h)
assert r["code"] == 0, f"评论失败: {h[:200]}"
print(f"   评论1: {r['msg']} ✅")

# 7. 再发一条
s, h = c.post("/api/goods/comment/create", {
    "_xsrf": c.cookies.get("_xsrf",""),
    "goods_id": str(goods_id),
    "content": "价格也很合理"
})
r = json.loads(h)
assert r["code"] == 0
print(f"7. 评论2: {r['msg']} ✅")

# 8. 获取评论列表
s, h = c.get(f"/api/goods/comments?goods_id={goods_id}")
r = json.loads(h)
assert len(r["data"]) == 2
print(f"8. 评论列表: {len(r['data'])} 条 ✅")
for cm in r["data"]:
    print(f"   - {cm['username']}: {cm['content']}")

# 9. 详情页显示评论
s, h = c.get(f"/goods/detail/{goods_id}")
assert "看起来不错" in h
assert "价格也很合理" in h
print("9. 详情页显示评论 ✅")

# 10. CSS 验证聊天左右分区
import os
with open(os.path.join("app", "static", "css", "user.css"), "r", encoding="utf-8") as f:
    css = f.read()
assert ".chat-msg.mine" in css
assert ".chat-msg.other" in css
assert "align-self: flex-end" in css
assert "align-self: flex-start" in css
print("10. CSS 聊天左右分区 ✅")
print("    .chat-msg.mine → 靠右 (flex-end)")
print("    .chat-msg.other → 靠左 (flex-start)")

# 11. chat_room.html 模板验证
with open(os.path.join("app", "templates", "chat_room.html"), "r", encoding="utf-8") as f:
    tpl = f.read()
assert "mine" in tpl and "other" in tpl
print("11. 聊天模板左右分区 ✅")

# ====== 敏感词过滤测试 (任务4.2) ======
print("\n" + "=" * 55)
print("12-17: 敏感词过滤测试 (任务4.2)")

# 12. 注册时使用敏感词用户名 → 被拒绝
s, h = c.get("/auth/register")
xsrf = c.cookies.get("_xsrf","")
s, h = c.post("/auth/register", {"_xsrf": xsrf, "username": "暴力分子", "password": "test123456"})
assert "敏感词" in h, f"用户名含敏感词应被拒绝: {h[:200]}"
print(f"12. 敏感用户名被拒绝 ✅")

# 13. 正常用户登录
s, h = c.get("/auth/login")
xsrf = c.cookies.get("_xsrf","")
s, h = c.post("/auth/login", {"_xsrf": xsrf, "username": "user", "password": "user123"})
print(f"13. 登录 user/user123 ✅")

# 14. 商品发布含敏感词描述 → 自动过滤
s, h = c.get("/goods/publish")
xsrf = c.cookies.get("_xsrf","")

# 用 POST 模拟文件上传
import io
boundary = "----TestBoundary"
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="_xsrf"\r\n\r\n'
    f"{xsrf}\r\n"
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="title"\r\n\r\n'
    f"测试商品-敏-感-词\r\n"
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="description"\r\n\r\n'
    f"这是一个涉及暴力的商品描述，含有赌博信息\r\n"
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="price"\r\n\r\n'
    f"99.9\r\n"
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="image"; filename="test.jpg"\r\n'
    f"Content-Type: image/jpeg\r\n\r\n"
    f"fake_image_data\r\n"
    f"--{boundary}--\r\n"
)
conn = http.client.HTTPConnection("127.0.0.1", 10086, timeout=10)
hds = {"Content-Type": f"multipart/form-data; boundary={boundary}", "Cookie": c._ck()}
conn.request("POST", "/goods/publish", body=body.encode("utf-8"), headers=hds)
r = conn.getresponse()
r.read().decode("utf-8")
sc = r.getheader("Set-Cookie","")
conn.close()
if sc: c._upd(sc)
# 检查数据库中最新商品的描述已被过滤
from app.models.db import get_connection
with get_connection() as conn:
    latest = conn.execute(
        "SELECT * FROM goods WHERE title LIKE ? ORDER BY id DESC LIMIT 1",
        ("%测试商品%",)
    ).fetchone()
assert latest is not None, "未找到发布的测试商品"
desc = latest["description"]
assert "***" in desc, f"敏感词应被替换为***, 实际: {desc}"
assert "暴力" not in desc, f"敏感词'暴力'应被过滤"
assert "赌博" not in desc, f"敏感词'赌博'应被过滤"
print(f"14. 商品描述敏感词过滤 ✅ (描述: {latest['description'][:50]}...)")

# 15. 评论含敏感词 → 过滤
goods_id = latest["id"]
# 刷新 xsrf
s, h = c.get(f"/goods/detail/{goods_id}")
xsrf = c.cookies.get("_xsrf","")
s, h = c.post("/api/goods/comment/create", {
    "_xsrf": xsrf, "goods_id": str(goods_id), "content": "这个商品真是暴力！"
})
r = json.loads(h)
assert r["code"] == 0
# 获取评论验证
s, h = c.get(f"/api/goods/comments?goods_id={goods_id}")
r = json.loads(h)
last_comment = r["data"][-1]
assert "***" in last_comment["content"], f"评论中的敏感词应被替换: {last_comment['content']}"
print(f"15. 评论敏感词过滤 ✅ (内容: {last_comment['content']})")

# 16. 聊天消息含敏感词 → 过滤
s, h = c.post("/api/chat/send", {
    "_xsrf": c.cookies.get("_xsrf",""),
    "to_user_id": "1",
    "content": "你那个东西是毒品吗？"
})
r = json.loads(h)
assert r["code"] == 0
# 获取消息验证
s, h = c.get(f"/api/chat/messages?other_user_id=1")
r = json.loads(h)
last_msg = r["data"][-1]
assert "***" in last_msg["content"], f"聊天消息中的敏感词应被替换: {last_msg['content']}"
print(f"16. 聊天消息敏感词过滤 ✅ (内容: {last_msg['content']})")

# 17. 敏感词列表有10个默认词
from app.models.audit import SensitiveWordRepository
words = SensitiveWordRepository.list_words(page=1, page_size=99)
assert len(words["items"]) >= 10
print(f"17. 默认敏感词列表: {len(words['items'])} 个 ✅")

print("\n" + "=" * 55)
print("ALL TASK 4.1 + 4.2 TESTS PASSED ✅")
