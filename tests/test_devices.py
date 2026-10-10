from datetime import datetime, timedelta, timezone

from app.service import utc_now

import pytest
from fastapi.testclient import TestClient

from app.main import app, device_service
from app.service import utc_now

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_devices():
    device_service.devices.clear()
    yield
    device_service.devices.clear()


def register_device(device_id="device-01", name="Lab Device 01"):
    return client.post(
        "/devices",
        json={"id": device_id, "name": name},
    )


def test_register_device():
    response = register_device()

    assert response.status_code == 201
    assert response.json()["id"] == "device-01"
    assert response.json()["status"] == "OFFLINE"


def test_duplicate_registration():
    register_device()
    response = register_device()

    assert response.status_code == 409


def test_heartbeat_updates_device():
    register_device()

    response = client.post(
        "/devices/device-01/heartbeat",
        json={"status": "OK", "cpu_usage": 42},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ONLINE"
    assert response.json()["last_heartbeat"] is not None


def test_heartbeat_for_unknown_device():
    response = client.post(
        "/devices/unknown/heartbeat",
        json={"status": "OK"},
    )

    assert response.status_code == 404


def test_device_is_offline_without_heartbeat():
    register_device()

    response = client.get("/devices/device-01")

    assert response.status_code == 200
    assert response.json()["status"] == "OFFLINE"



def test_device_status_timeout_boundary(monkeypatch):
    register_device()

    device = device_service.devices["device-01"]

    # Freeze the clock so the test is deterministic.
    fixed_now = datetime(
        2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc
    )

    monkeypatch.setattr(
        "app.service.utc_now", lambda: fixed_now
    )

    # Exactly 30 seconds old: still ONLINE.
    device.last_heartbeat = fixed_now - timedelta(seconds=30)
    assert device_service.get_status(device) == "ONLINE"

    # 31 seconds old: OFFLINE.
    device.last_heartbeat = fixed_now - timedelta(seconds=31)
    assert device_service.get_status(device) == "OFFLINE"


def test_fleet_summary():
    register_device("device-01", "Lab Device 01")
    register_device("device-02", "Lab Device 02")

    client.post(
        "/devices/device-01/heartbeat",
        json={"status": "OK"},
    )

    response = client.get("/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total": 2,
        "online": 1,
        "offline": 1,
    }
