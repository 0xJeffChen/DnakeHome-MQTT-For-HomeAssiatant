DOMAIN = "dnake_home_mqtt"

CONF_BROKER = "broker"
CONF_PORT = "port"
CONF_PUB_TOPIC = "pub_topic"
CONF_SUB_TOPIC = "sub_topic"
CONF_ACCOUNT = "account"
CONF_GATEWAY = "gateway"
CONF_DISPLAY = "display"

# 你可以根据需要修改这些默认值
DEFAULT_HOST = "192.168.5.100"
DEFAULT_PORT = 1883
DEFAULT_PUBLISH_TOPIC = "pub_topic"
DEFAULT_SUBSCRIBE_TOPIC = "sub_topic"
DEFAULT_ACCOUNT = "account"
DEFAULT_GATEWAY = "gateway"
DEFAULT_DISPLAY = "display"

# 设备类型映射表
DEVICE_TYPE_MAP = {
    1792: {"platform": "fan", "name": "新风"},
    1536: {"platform": "climate", "name": "空调"},
    3077: {"platform": "sensor", "name": "空气盒子"},
    2048: {"platform": "climate", "name": "地暖"}
}

# 自定义事件名称
EVENT_NEW_DEVICE = f"{DOMAIN}_new_device_discovered"