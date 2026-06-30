# mock_drone.py
import json
import time
import random
import paho.mqtt.client as mqtt

# 使用 EMQX 免费公共 Broker（和你的后端订阅的是同一个）
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "drone/hydrology/data"

client = mqtt.Client(client_id=f"mock_drone_{random.randint(1000, 9999)}")
client.connect(MQTT_BROKER, MQTT_PORT)

seq = 1
try:
    while True:
        # 模拟水文数据
        data = {
            "water_level": round(random.uniform(10.0, 15.0), 2),  # 水位 10-15 米
            "flow_speed": round(random.uniform(2.0, 5.0), 2),  # 流速 2-5 米/秒
            "seq_num": seq
        }
        payload = json.dumps(data)
        client.publish(MQTT_TOPIC, payload)
        print(f"[模拟无人机] 已发送: {payload}")

        seq += 1
        time.sleep(5)  # 每 5 秒发一条

except KeyboardInterrupt:
    print("\n[模拟无人机] 停止发送")
    client.disconnect()