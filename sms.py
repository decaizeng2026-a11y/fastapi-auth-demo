import random
from datetime import timedelta
import redis
from logger import get_request_id,logger


# 链接数据库
r = redis.Redis(host="localhost", port=6379, decode_responses=True)


# 发送短信
def send_sms(phone: str, code: str):
    logger.bind(request_id=get_request_id()).info(f"发送短信到{phone}，验证码{code}")
    return True


# 生成验证码
def generate_code():
    return str(random.randint(100000, 999999))


# 存储验证码 + 频控标记
def save_code(phone: str, code: str):
    r.setex(f"sms:code:{phone}", timedelta(seconds=300), code)
    r.setex(f"sms:limit:{phone}", timedelta(seconds=60), "1")


# 检查能不能发（频控）
def can_send(phone: str):
    return not r.exists(f"sms:limit:{phone}")


# 校验验证码
def verify_code(phone: str, code: str):
    stored_code = r.get(f"sms:code:{phone}")
    if stored_code and stored_code == code:
        r.delete(f"sms:code:{phone}")
        return True
    return False
