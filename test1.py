# 单元测试
from app.models.db import init_db
from app.models.user import UserRepository

init_db()
print("Create:",UserRepository.create_user("rexyang","123456"))
print("verify right:",UserRepository.verify_user("rexyang","123456"))
print("verify wrong 1:",UserRepository.verify_user("rexyang","123457"))
print("verify wrong 2:",UserRepository.verify_user("rexyang1","123456"))
