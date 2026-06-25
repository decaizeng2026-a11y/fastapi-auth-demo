import sys
import uuid
from contextvars import ContextVar
from loguru import logger

# 1.先移除默认控制台输出，我们完全自定义
logger.remove()

# 2.添加控制台输出(开发环境用，彩色格式更易读)
logger.add(
    sys.stdout,
    level="DEBUG",
    format="<green>{time:YYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level>"
           "| <cyan>{extra[request_id]}</cyan> | <level>{message}</level>",
)

# 3.添加INFO级别文件输出（正常业务日志）
logger.add(
    "logs/info.log",
    level="INFO",
    rotation="10MB",
    retention="30 days",
    encoding="utf-8",
    format="{time:YYY-MM-DD HH:mm:ss} | {level: <8} | {extra[request_id]} | {message}",
)

# 4.添加ERROR级别文件输出（错误日志单独存储）
logger.add(
    "logs/error.log",
    level="ERROR",
    rotation="10 MB",
    retention="30days",
    encoding="utf-8",
    format="{time:YYY-MM-DD HH:mm:ss} | {level: <8} | {extra[request_id]} | {message}",
)

# 5.用ContextVar 存储每个请求的request_id,线程/协程安全
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def set_request_id():
    """为当前请求生成唯一的request_id，并存入上下文变量"""
    request_id_var.set(uuid.uuid4().hex[:12])  # 取前12位方便阅读


def get_request_id():
    """获取当前请求的request_id"""
    return request_id_var.get()
