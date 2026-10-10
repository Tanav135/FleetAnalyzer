
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models import (
    DeviceRegistration,
    DeviceResponse,
    FleetSummary,
    HeartbeatRequest,
)

OFFLINE_TIMEOUT_SECONDS = 30


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Device:
    id: str
    name: str
    registered_at: datetime
    last_heartbeat: datetime | None = None
    heartbeat_status: str = "OK"
    cpu_usage: float | None = None
    signal_strength: int | None = None


class DeviceService:
    def __init__(self):
        self.devices: dict[str, Device] = {}

    def register_device(self, request: DeviceRegistration) -> Device:
        if request.id in self.devices:
            raise ValueError("Device already exists")

        device = Device(
            id=request.id,
            name=request.name,
            registered_at=utc_now(),
        )
        self.devices[device.id] = device
        return device

    def receive_heartbeat(
        self, device_id: str, request: HeartbeatRequest
    ) -> Device:
        device = self.devices.get(device_id)
        if device is None:
            raise KeyError("Device not found")

        # Receipt time is authoritative for timeout calculation.
        device.last_heartbeat = utc_now()
        device.heartbeat_status = request.status
        device.cpu_usage = request.cpu_usage
        device.signal_strength = request.signal_strength

        return device

    def get_status(self, device: Device) -> str:
        if device.last_heartbeat is None:
            return "OFFLINE"

        elapsed = (
            utc_now() - device.last_heartbeat
        ).total_seconds()

        if elapsed < 0:
            return "OFFLINE"

        return (
            "ONLINE"
            if elapsed <= OFFLINE_TIMEOUT_SECONDS
            else "OFFLINE"
        )

    def to_response(self, device: Device) -> DeviceResponse:
        return DeviceResponse(
            id=device.id,
            name=device.name,
            status=self.get_status(device),
            last_heartbeat=device.last_heartbeat,
            registered_at=device.registered_at,
        )

    def list_devices(self) -> list[DeviceResponse]:
        return [
            self.to_response(device)
            for device in self.devices.values()
        ]

    def get_device(self, device_id: str) -> DeviceResponse:
        device = self.devices.get(device_id)
        if device is None:
            raise KeyError("Device not found")
        return self.to_response(device)

    def get_summary(self) -> FleetSummary:
        devices = self.list_devices()
        online = sum(
            device.status == "ONLINE" for device in devices
        )
        total = len(devices)

        return FleetSummary(
            total=total,
            online=online,
            offline=total - online,
        )
