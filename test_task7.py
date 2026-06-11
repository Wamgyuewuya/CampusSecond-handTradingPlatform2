"""测试 任务7：交易评价显示在商品详情页评论区"""
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

# 0. 创建数据：商品 + 交易 + 评价
from app.models.db import get_connection
with get_connection() as conn:
    # 商品（user_id=1）
    cur = conn.execute("INSERT INTO goods (user_id,title,description,price,image,status) VALUES (?,?,?,?,?,?)",
                      (1, "评价测试商品", "测试评价显示", 299, "/s/t.jpg", "approved"))
    goods_id = cur.lastrowid
    # 交易（buyer_id=2 即 user）
    cur2 = conn.execute("INSERT INTO transactions (goods_id, seller_id, buyer_id, price) VALUES (?,?,?,?)",
                       (goods_id, 1, 2, 299))
    txn_id = cur2.lastrowid
    # 评价
    cur3 = conn.execute("INSERT INTO evaluations (transaction_id, user_id, rating, content) VALUES (?,?,?,?)",
                       (txn_id, 2, 5, "商品非常好，卖家很诚信！"))
    ev_id = cur3.lastrowid
print(f"0. 创建测试数据: goods={goods_id}, txn={txn_id}, eval={ev_id} ✅")

# 1. 登录 user
s, h = c.get("/auth/login")
xsrf = c.cookies.get("_xsrf","")
s, h = c.post("/auth/login", {"_xsrf": xsrf, "username": "user", "password": "user123"})
c.get("/home")
print("1. 登录 user/user123 ✅")

# 2. 获取商品详情页 — 验证评价出现在评论区
s, h = c.get(f"/goods/detail/{goods_id}")
assert "交易评价" in h, f"详情页应包含'交易评价'标签: {h[500:1000]}"
assert "商品非常好" in h, f"详情页应包含评价内容"
assert "★★★★★" in h, f"详情页应包含5星评价"
print(f"2. 商品详情页显示交易评价 ✅ (含5星+标签+内容)")

# 3. 发一条普通评论验证同时显示
s, h = c.post("/api/goods/comment/create", {
    "_xsrf": c.cookies.get("_xsrf",""),
    "goods_id": str(goods_id),
    "content": "普通评论测试"
})
r = json.loads(h)
assert r["code"] == 0

# 4. 验证评论区同时包含评价和评论
s, h = c.get(f"/goods/detail/{goods_id}")
assert "交易评价" in h
assert "普通评论测试" in h
assert "商品非常好" in h
print(f"3+4. 评论区同时显示评价和普通评论 ✅")

# 5. API 验证
s, h = c.get(f"/api/goods/comments?goods_id={goods_id}")
r = json.loads(h)
assert len(r["data"]) == 2
types = [item["src_type"] for item in r["data"]]
assert "evaluation" in types
assert "comment" in types
print(f"5. API返回2条记录(评价+评论) ✅")

# 6. 评价未填写内容
with get_connection() as conn:
    cur = conn.execute("INSERT INTO goods (user_id,title,description,price,image,status) VALUES (?,?,?,?,?,?)",
                      (1, "评价测试2", "测试", 99, "/s/t.jpg", "approved"))
    g2 = cur.lastrowid
    cur = conn.execute("INSERT INTO transactions (goods_id, seller_id, buyer_id, price) VALUES (?,?,?,?)",
                      (g2, 1, 2, 99))
    cur = conn.execute("INSERT INTO evaluations (transaction_id, user_id, rating, content) VALUES (?,?,?,?)",
                      (cur.lastrowid, 2, 3, ""))
s, h = c.get(f"/goods/detail/{g2}")
assert "未填写评价内容" in h
print(f"6. 空评价显示'未填写评价内容' ✅")

print("\n" + "=" * 55)
print("ALL TASK 7 TESTS PASSED ✅")
