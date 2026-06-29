from celery import Celery


# 创建Celery实例
# "tasks"是当前应用的名称，随便取
# broker:任务中转站，用redis
# backend:结果储存柜，也用Redis
celery_app = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
)