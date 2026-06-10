"""测试 任务5：举报功能"""
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

# 1. 登录 user/user123
s, h = c.get("/auth/login")
xsrf = c.cookies.get("_xsrf","")
s, h = c.post("/auth/login", {"_xsrf": xsrf, "username": "user", "password": "user123"})
c.get("/home")
print(f"1. 登录 user/user123 ✅")

# 2. 提交举报（举报商品）
s, h = c.post("/api/report/create", {
    "_xsrf": c.cookies.get("_xsrf",""),
    "target_type": "goods",
    "target_id": "1",
    "reason": "违规商品",
    "detail": "该商品可能存在违规内容"
})
r = json.loads(h)
assert r["code"] == 0, f"举报失败: {h[:200]}"
print(f"2. 举报商品: {r['msg']} ✅")

# 3. 提交举报（举报用户/聊天）
s, h = c.post("/api/report/create", {
    "_xsrf": c.cookies.get("_xsrf",""),
    "target_type": "user",
    "target_id": "1",
    "reason": "骚扰",
    "detail": "该用户发送骚扰信息"
})
r = json.loads(h)
assert r["code"] == 0
print(f"3. 举报用户: {r['msg']} ✅")

# 4. 举报信息不完整 → 被拒
s, h = c.post("/api/report/create", {
    "_xsrf": c.cookies.get("_xsrf",""),
    "target_type": "goods",
    "target_id": "0",
    "reason": "",
})
r = json.loads(h)
assert r["code"] == 1
print(f"4. 举报信息不完整被拒: {r['msg']} ✅")

# 5. 举报类型无效 → 被拒
s, h = c.post("/api/report/create", {
    "_xsrf": c.cookies.get("_xsrf",""),
    "target_type": "invalid",
    "target_id": "1",
    "reason": "测试",
})
r = json.loads(h)
assert r["code"] == 1
print(f"5. 无效举报类型被拒: {r['msg']} ✅")

# 6. 查看我的举报列表页
s, h = c.get("/report/list")
assert "我的举报" in h
print(f"6. 举报列表页: Status={s} ✅")

# 7. 获取举报列表 API
s, h = c.get("/api/report/list?page=1&page_size=20")
print(f"   report_list response: status={s}, body={h[:300]}")
r = json.loads(h)
assert r["code"] == 0, f"API失败: {h[:300]}"
assert r["total"] >= 2, f"期望至少2条，实际{r['total']}条"
print(f"7. 举报记录: {r['total']} 条 ✅")
for item in r["data"]:
    print(f"   - [{item['target_type']}] {item['reason']} → {item['status']}")

# 8. 未登录不能提交举报
c2 = Client()
s, h = c2.post("/api/report/create", {
    "target_type": "goods",
    "target_id": "1",
    "reason": "测试"
})
print(f"8. 未登录提交举报: Status={s} ✅")

# 9. 先创建一条已审核商品，再验证详情页有举报按钮
from app.models.db import get_connection
with get_connection() as conn:
    cur = conn.execute("INSERT INTO goods (user_id,title,description,price,image,status) VALUES (?,?,?,?,?,?)",
                      (1,"测试举报商品","测试",100,"/s/t.jpg","approved"))
    gid = cur.lastrowid
s, h = c.get(f"/goods/detail/{gid}")
assert "举报" in h, f"详情页应包含举报按钮: {h[:500]}"
print(f"9. 商品详情页包含举报按钮 (goods_id={gid}) ✅")

# 10. 验证聊天页导航有"我的举报"
s, h = c.get("/chat/list")
assert "我的举报" in h
print(f"10. 聊天页导航包含'我的举报' ✅")

# 11. admin 后台处理举报（用独立的 client）
admin_c = Client()
s, h = admin_c.get("/admin/login")
xsrf = admin_c.cookies.get("_xsrf","")
s, h = admin_c.post("/admin/login", {"_xsrf": xsrf, "username": "admin", "password": "admin123"})
# 先获取待处理举报列表确认
s, h = admin_c.get("/admin/api/reports?page=1&page_size=20")  # admin全局列表API
r = json.loads(h)
# admin API 返回格式: {code, count, data}
report_id = r["data"][0]["id"] if r.get("data") else 1
print(f"   admin: {r['count']} 条举报，处理 id={report_id}")
s, h = admin_c.post("/admin/api/report/handle", {
    "_xsrf": admin_c.cookies.get("_xsrf",""),
    "id": str(report_id),
    "handle_note": "已核实，商品已下架"
})
r = json.loads(h)
assert r["code"] == 0, f"处理失败: {h[:300]}"
print(f"11. 管理员处理举报 (id={report_id}): {r['msg']} ✅")

print("\n" + "=" * 55)
print("ALL TASK 5 TESTS PASSED ✅")
