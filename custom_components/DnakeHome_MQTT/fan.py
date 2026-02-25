import json
import uuid
import logging
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import callback
from .constant import *

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """设置新风实体"""

    manager = hass.data[DOMAIN][entry.entry_id]
    publish_func = manager.async_publish  # 获取类的方法引用

    sub_topic = entry.data[CONF_SUB_TOPIC]
    account = entry.data[CONF_ACCOUNT]
    gateway = entry.data[CONF_GATEWAY]

    # 2. 内部维护一个集合，防止在当前生命周期内重复添加同一个 devNo
    added_dev_nos = set()

    @callback
    def _add_fan_entity(dev_info):
        """核心：真正将实体添加到 Home Assistant 的函数"""
        dev_no = dev_info["devNo"]

        # 幂等性检查：如果已经添加过了，直接跳过
        if dev_no in added_dev_nos:
            return

        _LOGGER.info("🛠️ 正在创建新风实体: %s (编号: %s)", dev_info.get("name"), dev_no)

        # 创建实体实例
        # 注意：publish_func 直接传递 manager 的方法
        new_fan = FreshAirFan(
            dev_no=dev_no,
            publish_func=publish_func,
            topic=sub_topic,
            name=dev_info.get("name"),
            unique_id=f"dnake_air_fresh_{dev_no}",
            account=account,
            gateway=gateway
        )

        # 真正注册到 HA
        async_add_entities([new_fan])
        added_dev_nos.add(dev_no)

    # --- 阶段 A: 初始化加载 (重启 HA 时触发) ---
    # 从 entry.data["devices"] 字典里读取之前持久化过的设备
    devices_in_config = entry.data.get("devices", {})

    for dno_str, info in devices_in_config.items():
        # 根据 type 过滤出新风设备 (1792)
        if info.get("type") == 1792:
            _add_fan_entity({
                "devNo": int(dno_str),
                "name": info.get("name")
            })

    # --- 阶段 B: 动态监听 (插件运行中发现新设备时触发) ---
    @callback
    def _handle_discovery_event(event):
        """处理来自 Manager 的 EVENT_NEW_DEVICE 信号"""
        data = event.data
        # 校验：只处理属于本平台的设备
        if data.get("platform") == "fan":
            _LOGGER.info("📡 监听到新设备上线信号: %s", data.get("devNo"))
            _add_fan_entity(data)

    # 注册监听器，并确保在插件卸载时自动取消订阅
    entry.async_on_unload(
        hass.bus.async_listen(EVENT_NEW_DEVICE, _handle_discovery_event)
    )

    return True


class FreshAirFan(FanEntity):
    """新风实体类"""

    def __init__(self, dev_no, publish_func, topic, name, unique_id, account, gateway):
        self._dev_no = dev_no
        self._publish = publish_func
        self._topic = topic
        self._attr_name = name
        self._attr_unique_id = unique_id

        self.account = account
        self.gateway = gateway

        self._attr_supported_features = (
                FanEntityFeature.SET_SPEED |
                FanEntityFeature.TURN_OFF |
                FanEntityFeature.TURN_ON |
                FanEntityFeature.PRESET_MODE
        )

        # 初始内部属性
        self._attr_is_on = False
        self._attr_percentage = 33  # 初始设为一档

    @property
    def speed_count(self) -> int:
        return 3

    # --- 核心状态映射 ---
    @property
    def is_on(self) -> bool:
        """显式返回开关状态，不依赖风速百分比"""
        return self._attr_is_on

    @property
    def percentage(self) -> int:
        """显式返回百分比"""
        return self._attr_percentage

    @property
    def preset_modes(self) -> list:
        """定义下拉框里显示的选项名称"""
        return ["关闭", "低速", "中速", "高速"]

    @property
    def preset_mode(self) -> str:
        """告诉 HA 当前下拉框应该勾选哪一个"""
        if not self._attr_is_on:
            return "关闭"
        if self._attr_percentage <= 33: return "低速"
        if self._attr_percentage <= 66: return "中速"
        return "高速"

    async def async_set_preset_mode(self, preset_mode: str):
        if preset_mode == "低速":
            await self.async_set_percentage(33)
        elif preset_mode == "中速":
            await self.async_set_percentage(66)
        elif preset_mode == "高速":
            await self.async_set_percentage(100)
        elif preset_mode == "关闭":
            await self.async_set_percentage(0)

    def _send_command(self, data_updates: dict):
        """
        核心方法：动态构建报文。
        每次调用都会创建一个全新的字典，彻底避免浅拷贝导致的字段污染。
        """
        # 构建纯净的基础报文
        payload = {
            "fromDev": self.account,
            "toDev": self.gateway,
            "data": {
                "action": "ctrlDev",
                "devNo": self._dev_no,
                "devCh": 1,
                "devType": 1792,
                "cmd": "AirFresh",
                "uuid": uuid.uuid4().hex
            }
        }

        # 将本次操作特有的字段（如 powerOn 或 windSpeed）合并进去
        payload["data"].update(data_updates)

        # 异步下发
        self.hass.async_create_task(
            self._publish(self._topic, json.dumps(payload))
        )
        _LOGGER.debug("已动态构建并下发报文: %s", payload)

    # --- 开关控制 ---

    async def async_turn_on(self, percentage: int = None, preset_mode: str = None, **kwargs):
        """开启逻辑"""

        ctrl_data = {"powerOn": 1}

        # 如果开启时带了风速请求，则继续处理
        if percentage:
            wind_speed = self._percentage_to_wind_speed(percentage)
            ctrl_data["windSpeed"] = wind_speed
            self._attr_percentage = percentage
            # _LOGGER.info("🚀 开启设备并同步设置风速为 %s 档", wind_speed)

        self._send_command(ctrl_data)
        self._attr_is_on = True
        self.async_write_ha_state()

    def _percentage_to_wind_speed(self, percentage: int) -> int:
        """百分比转档位工具函数"""
        if percentage <= 33: return 1
        if percentage <= 66: return 2
        return 3

    async def async_turn_off(self, **kwargs):
        """仅发送关闭报文"""
        ctrl_data = {
            "powerOn": 0,
            "windSpeed": 1
        }
        self._send_command(ctrl_data)
        self._attr_is_on = False
        self._attr_percentage = 33
        self.async_write_ha_state()

    # --- 风速控制 ---
    async def async_set_percentage(self, percentage: int):
        """根据百分比计算档位，并仅下发风速报文"""

        if percentage == 0:
            await self.async_turn_off()
            return

        # 映射逻辑
        wind_speed = 1
        if percentage <= 33:
            wind_speed = 1
        elif percentage <= 66:
            wind_speed = 2
        else:
            wind_speed = 3

        # 2. 构建报文数据
        ctrl_data = {"windSpeed": wind_speed}

        # 3. 核心改进：如果当前是关闭状态，额外添加 powerOn 字段
        if not self._attr_is_on:
            # _LOGGER.info("📢 设备 [%s] 处于关闭状态，调节风速时将同步发送开启指令", self._attr_name)
            ctrl_data["powerOn"] = 1
            self._attr_is_on = True  # 同步更新内部开关状态

        # 4. 下发组合报文
        self._send_command(ctrl_data)

        self._attr_percentage = percentage
        self.async_write_ha_state()

    # --- 状态上报同步 ---

    async def async_added_to_hass(self):
        """订阅 __init__.py 分发的内部事件以更新状态"""

        @callback
        def _handle_status_update(event):

            reports = event.data.get("reports", {})
            changed = False

            # 更新开关状态
            if "powerOn" in reports:
                new_on = (reports["powerOn"] == 1)
                if self._attr_is_on != new_on:
                    self._attr_is_on = new_on
                    changed = True

            # 更新风速状态
            if "windSpeed" in reports:
                new_speed = reports["windSpeed"]
                # 转换回百分比 (1->33, 2->66, 3->100)
                new_percentage = int((new_speed / self.speed_count) * 100)
                if self._attr_percentage != new_percentage:
                    self._attr_percentage = new_percentage
                    changed = True

            if changed:
                self.async_write_ha_state()

        event_name = f"{DOMAIN}_update_{self._dev_no}"
        # 监听事件总线中关于本设备 ID 的消息
        self.async_on_remove(
            self.hass.bus.async_listen(event_name, _handle_status_update)
        )