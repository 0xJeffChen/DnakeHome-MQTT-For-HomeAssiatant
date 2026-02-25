import json
import uuid
import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import callback
from .constant import *

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """设置空调实体"""
    manager = hass.data[DOMAIN][entry.entry_id]
    publish_func = manager.async_publish

    sub_topic = entry.data[CONF_SUB_TOPIC]
    account = entry.data[CONF_ACCOUNT]
    gateway = entry.data[CONF_GATEWAY]

    added_dev_nos = set()

    @callback
    def _add_entity(dev_info):

        dev_no = dev_info["devNo"]
        dev_type = dev_info.get("devType")

        if dev_no in added_dev_nos:
            return

        if dev_type == 1536:
            _LOGGER.info("🛠️ 正在创建空调实体: %s (编号: %s)", dev_info.get("name"), dev_no)
            new_entity = DnakeClimate(
                dev_no=dev_no,
                publish_func=publish_func,
                topic=sub_topic,
                name=dev_info.get("name"),
                unique_id=f"dnake_climate_{dev_no}",
                account=account,
                gateway=gateway
            )
        elif dev_type == 2048:
            _LOGGER.info("🛠️ 正在创建地暖实体: %s (编号: %s)", dev_info.get("name"), dev_no)
            new_entity = DnakeHeater(
                dev_no=dev_no,
                publish_func=publish_func,
                topic=sub_topic,
                name=dev_info.get("name"),
                unique_id=f"dnake_heater_{dev_no}",
                account=account,
                gateway=gateway
            )
        else:
            return

        async_add_entities([new_entity])
        added_dev_nos.add(dev_no)

    # 1. 初始化加载
    devices_in_config = entry.data.get("devices", {})

    for dno_str, info in devices_in_config.items():
        dev_type = info.get("type")
        if dev_type in [1536, 2048]:
            _add_entity({"devNo": int(dno_str), "devType": int(dev_type), "name": info.get("name")})

    # 2. 动态监听
    @callback
    def _handle_discovery(event):
        if event.data.get("platform") == "climate":
            _add_entity(event.data)

    entry.async_on_unload(hass.bus.async_listen(EVENT_NEW_DEVICE, _handle_discovery))


class DnakeClimate(ClimateEntity):
    """空调实体类"""

    def __init__(self, dev_no, publish_func, topic, name, unique_id, account, gateway):
        self._dev_no = dev_no
        self._publish = publish_func
        self._topic = topic
        self._attr_name = name
        self._attr_unique_id = unique_id

        self.account = account
        self.gateway = gateway

        # HA 属性配置
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_target_temperature_step = 0.5
        self._attr_min_temp = 16.0
        self._attr_max_temp = 30.0

        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY]
        self._attr_fan_modes = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]
        self._attr_supported_features = (
                ClimateEntityFeature.TARGET_TEMPERATURE |
                ClimateEntityFeature.FAN_MODE
        )

        # 内部状态定义
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_fan_mode = FAN_AUTO
        self._attr_target_temperature = 26.0
        self._attr_current_temperature = 26.0  # 室内环境温

    def _send_command(self, data_updates: dict):
        """发送 MQTT 指令"""
        payload = {
            "fromDev": self.account,
            "toDev": self.gateway,
            "data": {
                "action": "ctrlDev",
                "devNo": self._dev_no,
                "devCh": 1,
                "devType": 1536,
                "cmd": "AirCondition",  # 假设空调指令名为这个，请根据实际确认
                "uuid": uuid.uuid4().hex
            }
        }
        payload["data"].update(data_updates)
        self.hass.async_create_task(self._publish(self._topic, json.dumps(payload)))

    # --- 控制逻辑 ---

    async def async_turn_on(self):
        """显式开启空调"""
        # 直接调用 set_hvac_mode 逻辑，复用代码
        await self.async_set_hvac_mode(HVACMode.FAN_ONLY)

    async def async_turn_off(self):
        """显式关闭空调"""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """设置模式：关机或切换模式"""
        if hvac_mode == HVACMode.OFF:
            self._send_command({"powerOn": 0})
        else:
            # 映射 HA 模式到 Dnake airMode: 3制冷 4制热 7送风
            mode_map = {HVACMode.COOL: 3, HVACMode.HEAT: 4, HVACMode.FAN_ONLY: 7}
            self._send_command({
                "powerOn": 1,
                "airMode": mode_map.get(hvac_mode, 7)
            })

        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        """设置温度：如果关机则自动开机联动"""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None: return

        ctrl_data = {"temp": int(round(temp * 100))}

        # 联动逻辑：如果空调是关的，调整温度时自动开启并切到制冷模式
        if self._attr_hvac_mode == HVACMode.OFF:
            ctrl_data["powerOn"] = 1
            ctrl_data["airMode"] = 3  # 默认开启制冷
            self._attr_hvac_mode = HVACMode.COOL

        self._send_command(ctrl_data)
        self._attr_target_temperature = temp
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str):
        """设置风速：如果关机则联动开启"""
        fan_map = {FAN_LOW: 1, FAN_MEDIUM: 2, FAN_HIGH: 3, FAN_AUTO: 5}
        ctrl_data = {"windSpeed": fan_map.get(fan_mode, 5)}

        if self._attr_hvac_mode == HVACMode.OFF:
            ctrl_data["powerOn"] = 1
            ctrl_data["airMode"] = 3
            self._attr_hvac_mode = HVACMode.COOL

        self._send_command(ctrl_data)
        self._attr_fan_mode = fan_mode
        self.async_write_ha_state()

    # --- 状态同步 ---

    async def async_added_to_hass(self):
        @callback
        def _handle_status_update(event):
            reports = event.data.get("reports", {})
            changed = False

            # 1. 开关与模式同步
            if "powerOn" in reports:
                if reports["powerOn"] == 0:
                    new_hvac = HVACMode.OFF
                else:
                    # 如果开着，根据 airMode 反推模式
                    mode_rev_map = {3: HVACMode.COOL, 4: HVACMode.HEAT, 7: HVACMode.FAN_ONLY}
                    new_hvac = mode_rev_map.get(reports.get("airMode"), HVACMode.COOL)

                if self._attr_hvac_mode != new_hvac:
                    self._attr_hvac_mode = new_hvac
                    changed = True

            # 2. 温度同步 (1900 -> 19.0)
            if "temp" in reports:
                new_temp = reports["temp"] / 100.0
                if self._attr_target_temperature != new_temp:
                    self._attr_target_temperature = new_temp
                    changed = True

            if "tempIndoor" in reports and reports["tempIndoor"] != 0:
                new_indoor_temp = reports["tempIndoor"] / 100.0
                if self._attr_current_temperature != new_indoor_temp:
                    self._attr_current_temperature = new_indoor_temp
                    changed = True

            # 3. 风速同步
            if "windSpeed" in reports:
                fan_rev_map = {1: FAN_LOW, 2: FAN_MEDIUM, 3: FAN_HIGH, 5: FAN_AUTO}
                new_fan = fan_rev_map.get(reports["windSpeed"], FAN_AUTO)
                if self._attr_fan_mode != new_fan:
                    self._attr_fan_mode = new_fan
                    changed = True

            if changed:
                self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(f"{DOMAIN}_update_{self._dev_no}", _handle_status_update)
        )

class DnakeHeater(ClimateEntity):
    """地暖实体类 (devType: 2048)"""
    def __init__(self, dev_no, publish_func, topic, name, unique_id, account, gateway):
        self._dev_no = dev_no
        self._publish = publish_func
        self._topic = topic
        self._attr_name = name
        self._attr_unique_id = unique_id
        self.account = account
        self.gateway = gateway

        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_target_temperature_step = 1.0
        self._attr_min_temp = 5.0
        self._attr_max_temp = 35.0
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = 25.0
        self._attr_current_temperature = 26.0

    def _send_command(self, data_updates: dict):
        payload = {
            "fromDev": self.account,
            "toDev": self.gateway,
            "data": {
                "action": "ctrlDev",
                "devNo": self._dev_no,
                "devCh": 3,
                "devType": 2048,
                "cmd": "AirHeater",
                "uuid": uuid.uuid4().hex
            }
        }
        payload["data"].update(data_updates)
        self.hass.async_create_task(self._publish(self._topic, json.dumps(payload)))

    async def async_set_hvac_mode(self, hvac_mode):
        self._send_command({"powerOn": 1 if hvac_mode == HVACMode.HEAT else 0})
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None: return
        self._send_command({"temp": int(round(temp * 100))})
        self._attr_target_temperature = temp
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        @callback
        def _handle_status_update(event):
            reports = event.data.get("reports", {})
            changed = False
            if "powerOn" in reports:
                new_mode = HVACMode.HEAT if reports["powerOn"] == 1 else HVACMode.OFF
                if self._attr_hvac_mode != new_mode:
                    self._attr_hvac_mode = new_mode
                    changed = True
            if "temp" in reports:
                new_temp = reports["temp"] / 100.0
                if self._attr_target_temperature != new_temp:
                    self._attr_target_temperature = new_temp
                    changed = True
            if "tempIndoor" in reports and reports["tempIndoor"] != 0:
                new_indoor = reports["tempIndoor"] / 100.0
                if self._attr_current_temperature != new_indoor:
                    self._attr_current_temperature = new_indoor
                    changed = True
            if changed:
                self.async_write_ha_state()
        self.async_on_remove(self.hass.bus.async_listen(f"{DOMAIN}_update_{self._dev_no}", _handle_status_update))