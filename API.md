# Dnake Home MQTT Plugin API Documentation

This document describes the internal architecture and API interfaces for the Dnake Home MQTT plugin.

## Architecture Overview

The plugin follows a modular architecture:

- **Core**: Handles MQTT connection (`core/mqtt.py`) and Device Management (`core/device_manager.py`).
- **Devices**: Contains device implementations (`devices/`).
- **Config Flow**: Handles user configuration (`config_flow.py`).

### Key Components

#### `DnakeMqttClient` (`core/mqtt.py`)

Handles the connection to the MQTT broker using `paho-mqtt`.

- `async_start()`: Connects to the broker and starts the loop.
- `async_stop()`: Disconnects and stops the loop.
- `async_publish(payload: dict)`: Publishes a JSON payload to the configured topic.

#### `DeviceManager` (`core/device_manager.py`)

Manages device discovery and state updates.

- `async_setup()`: Starts listening for MQTT messages and initiates heartbeat.
- `_handle_mqtt_message(event)`: Processes incoming MQTT messages.
- `_register_new_device(dev_no, dev_type, data)`: Registers a new device and fires `dnake_home_mqtt_device_discovered`.

#### `DnakeBaseEntity` (`devices/base.py`)

Base class for all entities.

- `_handle_update(data)`: Abstract method to handle state updates.
- `async_send_command(payload)`: Helper to send commands via MQTT.

## Events

### `dnake_home_mqtt_device_discovered`

Fired when a new device is discovered via MQTT.

**Payload:**
```json
{
  "platform": "climate",
  "dev_no": 1,
  "dev_type": 1536,
  "name": "Dnake_Air Conditioner_1",
  "device_info": { ... }
}
```

### `dnake_home_mqtt_device_state_update_{device_id}`

Internal event dispatched via `async_dispatcher_send` when a device state update is received.

## Device Types

Supported device types (mapped in `const.py`):

- **1536**: Climate (Air Conditioner)
- **2048**: Heater (Floor Heating)
- **1792**: Fan (Fresh Air System)
- **3077**: Sensor (Air Quality Monitor)

## Configuration

Configuration is handled via `config_flow.py` and validated using `voluptuous` schemas defined in `schemas.py`.

### YAML Configuration (Optional)

Although Config Flow is preferred, `configuration.yaml` support can be added using the schema in `schemas.py`.

```yaml
dnake_home_mqtt:
  broker: "192.168.1.100"
  port: 1883
  account: "101"
  gateway: "10101"
```

## Extension Guide

To add a new device type:

1.  Add the type ID and mapping to `const.py`.
2.  Create a new class in `devices/` inheriting from `DnakeBaseEntity`.
3.  Implement `_handle_update` to parse state.
4.  Implement control methods (e.g., `async_turn_on`) using `async_send_command`.
5.  Update the corresponding platform file (e.g., `light.py`) to instantiate the new class.
