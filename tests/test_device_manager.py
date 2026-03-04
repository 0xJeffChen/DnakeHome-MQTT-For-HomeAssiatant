"""Tests for the Device Manager."""
import pytest
from unittest.mock import MagicMock, patch
from homeassistant.core import HomeAssistant
from custom_components.DnakeHome_MQTT.core.device_manager import DeviceManager
from custom_components.DnakeHome_MQTT.const import (
    EVENT_MQTT_MESSAGE_RECEIVED,
    EVENT_DEVICE_DISCOVERED,
    DEVICE_TYPE_CLIMATE,
)

@pytest.fixture
def mock_hass():
    hass = MagicMock(spec=HomeAssistant)
    hass.bus = MagicMock()
    hass.config_entries = MagicMock()
    return hass

@pytest.fixture
def mock_mqtt_client():
    client = MagicMock()
    client.async_publish = MagicMock()
    return client

@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.data = {
        "account": "test_account",
        "gateway": "test_gateway",
        "devices": {}
    }
    return entry

async def test_device_discovery(mock_hass, mock_config_entry, mock_mqtt_client):
    """Test that a new device is discovered and event is fired."""
    manager = DeviceManager(mock_hass, mock_config_entry, mock_mqtt_client)
    await manager.async_setup()

    # Simulate MQTT message
    payload = {
        "data": {
            "action": "cmtDevInfo",
            "devList": [
                {
                    "devNo": 1,
                    "devType": DEVICE_TYPE_CLIMATE,
                    "reports": {"powerOn": 1}
                }
            ]
        }
    }
    
    # Mock the event object
    event = MagicMock()
    event.data = {"payload": payload} # In real code payload is string, but let's mock json load or adjust test
    
    # Since we mock json.loads in test or adjust implementation?
    # Our implementation does json.loads(event.data.get("payload"))
    # So we should pass a JSON string.
    import json
    event.data = {"payload": json.dumps(payload)}

    # Call the handler directly or simulate bus fire
    # Here we call the handler directly since it's a callback registered
    # manager._handle_mqtt_message(event) 
    # But _handle_mqtt_message is private. We can access it or trigger via bus mock?
    # Better to access it via manager._handle_mqtt_message
    
    manager._handle_mqtt_message(event)
    
    # Check if EVENT_DEVICE_DISCOVERED was fired
    assert mock_hass.bus.async_fire.called
    args, kwargs = mock_hass.bus.async_fire.call_args
    assert args[0] == EVENT_DEVICE_DISCOVERED
    assert args[1]["dev_no"] == 1
    assert args[1]["dev_type"] == DEVICE_TYPE_CLIMATE

async def test_heartbeat(mock_hass, mock_config_entry, mock_mqtt_client):
    """Test heartbeat sends correct payload."""
    manager = DeviceManager(mock_hass, mock_config_entry, mock_mqtt_client)
    
    # Add a known device to config
    mock_config_entry.data["devices"] = {
        "1": {"type": DEVICE_TYPE_CLIMATE, "name": "Test Climate"}
    }
    
    await manager._async_heartbeat(None)
    
    mock_mqtt_client.async_publish.assert_called_once()
    call_args = mock_mqtt_client.async_publish.call_args
    payload = call_args[0][0]
    
    assert payload["data"]["action"] == "readDev"
    assert len(payload["data"]["devList"]) == 1
    assert payload["data"]["devList"][0]["devNo"] == 1
