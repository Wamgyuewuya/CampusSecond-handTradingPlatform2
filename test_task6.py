"""测试 任务6：购买商品"""
import http.client, urllib.parse, re, json

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
                if k not in ("path","Path","expires","Expires","httponly","HttpOnly","secure","SameSite"):
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

# 0. 插入一条已审核商品（owner=admin id=1）
from app.models.db import get_connection
with get_connection() as conn:
    cur = conn.execute(
        "INSERT INTO goods (user_id,title,description,price,image,status) VALUES (?,?,?,?,?,?)",
        (1, "测试购买商品", "测试用", 199.0, "/s/t.jpg", "approved")
    )
    goods_id = cur.lastrowid
print(f"0. 创建测试商品 id={goods_id} ✅")

# 1. 登录 user/user123
s, h = c.get("/auth/login")
xsrf = c.cookies.get("_xsrf","")
s, h = c.post("/auth/login", {"_xsrf": xsrf, "username": "user", "password": "user123"})
c.get("/home")
print("1. 登录 user/user123 ✅")

# 2. 购买商品
s, h = c.post("/api/goods/buy", {
    "_xsrf": c.cookies.get("_xsrf",""),
    "goods_id": str(goods_id)
})
r = json.loads(h)
assert r["code"] == 0, f"购买失败: {h[:200]}"
print(f"2. 购买商品: {r['msg']} ✅")

# 3. 重复购买 → 被拒
s, h = c.post("/api/goods/buy", {
    "_xsrf": c.cookies.get("_xsrf",""),
    "goods_id": str(goods_id)
})
r = json.loads(h)
assert r["code"] == 1
print(f"3. 重复购买被拒: {r['msg']} ✅")

# 4. 购买不存在的商品 → 被拒
s, h = c.post("/api/goods/buy", {
    "_xsrf": c.cookies.get("_xsrf",""),
    "goods_id": "99999"
})
r = json.loads(h)
assert r["code"] == 1
print(f"4. 不存在的商品被拒: {r['msg']} ✅")

# 5. 购买未审核的商品 → 被拒
with get_connection() as conn:
    cur = conn.execute(
        "INSERT INTO goods (user_id,title,description,price,image,status) VALUES (?,?,?,?,?,?)",
        (1, "待审核商品", "测试", 99, "/s/t.jpg", "pending")
    )
    pend_id = cur.lastrowid
s, h = c.post("/api/goods/buy", {
    "_xsrf": c.cookies.get("_xsrf",""),
    "goods_id": str(pend_id)
})
r = json.loads(h)
assert r["code"] == 1
print(f"5. 未审核商品被拒: {r['msg']} ✅")

# 6. 购买自己的商品 → 被拒（用 admin 登录）
admin_c = Client()
s, h = admin_c.get("/admin/login")
xsrf = admin_c.cookies.get("_xsrf","")
s, h = admin_c.post("/admin/login", {"_xsrf": xsrf, "username": "admin", "password": "admin123"})
s, h = admin_c.post("/api/goods/buy", {
    "_xsrf": admin_c.cookies.get("_xsrf",""),
    "goods_id": str(goods_id)
})
r = json.loads(h)
assert r["code"] == 1
print(f"6. 购买自己的商品被拒: {r['msg']} ✅")

# 7. 验证交易记录已生成
s, h = c.get("/transaction/list")
assert "交易记录" in h
print(f"7. 交易记录页: Status={s} ✅")

# 8. 验证商品详情页显示"已购买"
s, h = c.get(f"/goods/detail/{goods_id}")
assert "已购买" in h
print(f"8. 详情页显示'已购买' ✅")

# 9. 验证商品浏览页有购买按钮
s, h = c.get("/goods/browse")
assert "btn-success" in h
print(f"9. 浏览页有购买按钮 ✅")

# 10. 未登录不能购买
c2 = Client()
s, h = c2.post("/api/goods/buy", {"goods_id": str(goods_id)})
assert s == 403
print(f"10. 未登录购买被拒: Status={s} ✅")

print("\n" + "=" * 55)
print("ALL TASK 6 TESTS PASSED ✅")
