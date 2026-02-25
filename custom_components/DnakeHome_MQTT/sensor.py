import logging
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
)
from homeassistant.core import callback
from .constant import *

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):

    """设置空气质量传感器实体"""
    manager = hass.data[DOMAIN][entry.entry_id]
    added_dev_nos = set()

    # 定义要创建的传感器类型
    sensor_types = [
        ("temp", "温度", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, 100),
        ("relativeHumid", "湿度", PERCENTAGE, SensorDeviceClass.HUMIDITY, 100),
        ("concnPM2Dot5", "PM2.5", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, SensorDeviceClass.PM25, 1),
        ("concnPM1Dot0", "PM1.0", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, SensorDeviceClass.PM1, 1),
        ("concnPM10", "PM10", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, SensorDeviceClass.PM10, 1),
    ]

    @callback
    def _add_sensor_entity(dev_info):
        """核心：真正将实体添加到 Home Assistant 的函数"""
        dev_no = dev_info["devNo"]

        # 幂等性检查：如果已经添加过了，直接跳过
        if dev_no in added_dev_nos:
            return

        _LOGGER.info("🛠️ 正在创建空气盒子实体: %s (编号: %s)", dev_info.get("name"), dev_no)

        entities = []
        for key, name, unit, device_class, factor in sensor_types:
            entities.append(
                DnakeAirSensor(entry, dev_no, key, name, unit, device_class, factor)
            )

        # 真正注册到 HA
        async_add_entities(entities)
        added_dev_nos.add(dev_no)
        return

    devices_in_config = entry.data.get("devices", {})
    for dno_str, info in devices_in_config.items():
        # 根据 type 过滤出空气盒子 (3077)
        if info.get("type") == 3077:
            _add_sensor_entity({
                "devNo": int(dno_str),
                "name": info.get("name")
            })

    @callback
    def _handle_discovery_event(event):
        """处理来自 Manager 的 EVENT_NEW_DEVICE 信号"""
        data = event.data
        # 校验：只处理属于本平台的设备
        if data.get("platform") == "sensor":
            _LOGGER.info("📡 监听到新传感器上线信号: %s", data.get("devNo"))
            _add_sensor_entity(data)

    # 注册监听器，并确保在插件卸载时自动取消订阅
    entry.async_on_unload(
        hass.bus.async_listen(EVENT_NEW_DEVICE, _handle_discovery_event)
    )

    return True

class DnakeAirSensor(SensorEntity):
    """空气质量传感器实体类"""

    def __init__(self, entry, dev_no, key, name, unit, device_class, factor):
        self._entry = entry
        self._dev_no = dev_no
        self._key = key
        self._factor = factor

        self._attr_name = f"空气质量 {name}"
        self._attr_unique_id = f"dnake_air_sensor_{dev_no}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_value = None

    # --- 状态同步逻辑 (sensor.py) ---

    async def async_added_to_hass(self):
        """当传感器实体添加到 HA 时，监听对应的事件"""

        @callback
        def _handle_status_update(event):
            """处理已经提取好的 reports 数据"""
            # 这里的 event.data 直接就是 reports 字典
            reports = event.data.get("reports", {})

            # 检查这个传感器关注的字段（如 temp, concnPM2Dot5 等）是否在本次上报中
            if self._key in reports:
                raw_value = reports[self._key]

                # 数值转换：raw_value / factor (100 或 1)
                # 例如：temp: 1676 / 100 -> 16.76
                new_value = round(raw_value / self._factor, 2)

                if self._attr_native_value != new_value:
                    self._attr_native_value = new_value

                    # 立即将新状态写入 HA 状态机
                    self.async_write_ha_state()

        # 订阅事件：例如 dnake_home_mqtt_update_60
        self.async_on_remove(
            self.hass.bus.async_listen(
                f"{DOMAIN}_update_{self._dev_no}",
                _handle_status_update
            )
        )