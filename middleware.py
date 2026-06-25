from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from logger import set_request_id, logger, get_request_id


class RequestLogMiddleware(BaseHTTPMiddleware):
    """请求日志中间件：为每个请求生成request_id,记录请求入站和出站"""

    async def dispatch(
            self, request: Request, call_next):
        # 1.生成唯一request_id,存入上下文
        set_request_id()

        # 2.记录请求入站日志
        logger.bind(request_id=get_request_id()).info(
            f"请求入站：{request.method} {request.url.path}"
        )

        # 3.执行真正的业务逻辑
        response = await call_next(request)

        # 4.记录请求出站日志
        logger.bind(request_id=get_request_id()).info(
            f"请求出站：{response.status_code}"
        )
        return response
