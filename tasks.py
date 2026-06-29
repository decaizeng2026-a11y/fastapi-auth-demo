import random
from celery_app import celery_app
from crud import get_order_by_id,update_order_status
from database import SessionLocal

# 模拟开箱可获得的奖品列表
PRIZE_LIST = [
    {"name": "AK-47 | 红线", "rarity": "隐秘"},
    {"name": "M4A4 | 咆哮", "rarity": "违禁"},
    {"name": "AWP | 巨龙传说", "rarity": "隐秘"},
    {"name": "格洛克 | 渐变之色", "rarity": "受限"},
    {"name": "P250 | 沙尘", "rarity": "军规"},
    {"name": "印花 | Natus Vincere", "rarity": "普通"},
]

@celery_app.task(bind=True,max_retries=3,default_retry_delay=5)
def open_blind_box(self,order_id:int,user_id:int):
    """
       异步执行开箱任务，真实查数据库防重复消费
       """
    # 自己创建数据库会话（Celery 任务不在 FastAPI 请求里，不能依赖注入）
    db = SessionLocal()
    try:
        # ====== 第1步：防重复消费（查数据库确认订单状态）======
        order = get_order_by_id(db,order_id)
        if not order:
            return {"status":"error","msg":f"订单{order_id}不存在"}

        if order.status != "pending":
            print(f"[开箱任务]订单{order_id}状态为{order.status},跳过重复执行")
            return {"status":"skipped","msg":f"订单已处理过","order_id":order_id}

        # 标记为处理中
        update_order_status(db,order_id,"processing")


        # ========第2步：模拟开箱算法========
        import time
        time.sleep(1)   # 模拟开箱算法
        prize = random.choice(PRIZE_LIST)
        print(f"[开箱任务]用户{user_id}开出了：{prize['name']} ({prize['rarity']})")

        # ========第3步：更新库存和用户资产（Day6先模拟，Day9整合时连真实表）========
        print(f"[开箱任务]扣减库存：{prize['name']}")
        print(f"[开箱任务] 更新用户 {user_id} 资产: +{prize['name']}")

        # ====== 第4步：标记订单完成 ======
        update_order_status(db, order_id, "done")

        return {
            "status": "success",
            "prize": prize["name"],
            "rarity": prize["rarity"],
            "user_id": user_id,
            "order_id": order_id
        }

    except Exception as exc:
        # 标记订单失败
        update_order_status(db, order_id, "failed")
        print(f"[开箱任务] 任务失败: {exc}")
        raise self.retry(exc=exc)

    finally:
        db.close()  # 记得关闭会话