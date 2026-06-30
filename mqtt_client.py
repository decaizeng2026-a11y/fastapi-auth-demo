import json
import time
import random
import threading
from database import datetime
import paho.mqtt.client as mqtt
from database import SessionLocal
from logger import logger,get_request_id
import redis


# ==============配置==============
MQTT_BROKER = "broker.emqx.io"      # EMQX 免费公共 Broker
MQTT_PORT = 1883                     # MQTT 默认端口
MQTT_TOPIC = "drone/hydrology/data"  # 无人机上传水文数据的主题
CLIENT_ID = f"backend_subscriber_{random.randint(1000, 9999)}"


# 用 Redis 做消息去重（你 Day2 已经用了 Redis）
r = redis.Redis(host='localhost', port=6379, decode_responses=True)


# ==================== 回调函数 ====================
def on_connect(client,userdata,flags,rc):
    """链接成功时的回调"""
    if rc == 0:
        print(f"[MQTT]链接成功，订阅主题：{MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"[MQTT]链接失败，错误码：{rc}")


def on_disconnect(client,userdata,rc):
    """链接断开时的回调（断线重连在这里触发）"""
    if rc != 0:
        print(f"[MQTT]意外断开，错误码{rc}，正在尝试重连...")
        # paho-mqtt 会自动重连，我们也可以手动调用 connect
    try:
        client.reconnect()
    except Exception as e:
        print(f"[MQTT]重连失败：{e}")


def on_message(client,userdata,msg):
    """收到消息时的回调：解析 JSON —> 去重 ->存入MYSQL"""
    try:
        # 1. 解析 JSON
        payload = json.loads(msg.payload.decode("utf-8"))
        print(f"[MQTT]收到消息：{payload}")

        # 2. 消息去重（根据 seq_num）
        seq_num = payload.get("seq_num")
        if seq_num:
            if r.exists(f"mqtt:seq:{seq_num}"):
                print(f"[MQTT]重复消息，跳过：seq_num={seq_num}")
                return
            # 标记为已处理，2 小时过期（防止 Redis 无限增长）
            r.setex(f"mqtt:seq:{seq_num}",7200,"1")

        # 3. 存入 MySQ
        db = SessionLocal()
        try:
            from crud import create_hydrology_record
            create_hydrology_record(
                db=db,
                water_level=payload.get("water_level",0.0),
                flow_speed=payload.get("flow_seqed",0.0)
            )
            print(f"[MQTT]数据已存入数据库")
        finally:
            db.close()
    except json.JSONDecodeError:
        print(f"[MQTT]JSON 解析失败：{msg.payload}")
    except Exception as e:
        print(f"[MQTT]处理消息异常：{e}")


# ===============启动客户端================
def start_mqtt_client():
    """在独立线程中启动MQTT客户端"""
    client = mqtt.Client(client_id=CLIENT_ID)

    # 绑定回调
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # 设置心跳保活（60 秒内没消息，自动发心跳包）
    client.connect(MQTT_BROKER,MQTT_PORT,keepalive=60)

    # 启动网络循环（阻塞式，所以放在独立线程里）
    client.loop_forever()


# 在独立线程中启动，不阻塞Fastapi 主进程
mqtt_thread = threading.Thread(target=start_mqtt_client,daemon=True)
mqtt_thread.start()
print("[MQTT]客户端已在后台线程启动")