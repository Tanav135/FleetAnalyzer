
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

        # Control-plane state is deliberately separate from Device.
        # Values: RUNNING, STOPPED, REMOVED.
        self.simulator_commands: dict[str, str] = {}

        # device_id -> idempotency_key -> payload fingerprint
        self.processed_heartbeats: dict[
            str, dict[str, tuple]
        ] = {}

    def register_device(
        self, request: DeviceRegistration
    ) -> Device:
        existing = self.devices.get(request.id)

        if existing is not None:
            if existing.name == request.name:
                # Identical registration is idempotent.
                return existing
            raise ValueError(
                "Device ID already exists with different details"
            )

        device = Device(
            id=request.id,
            name=request.name,
            registered_at=utc_now(),
        )
        self.devices[device.id] = device
        self.simulator_commands[device.id] = "RUNNING"
        self.processed_heartbeats[device.id] = {}
        return device

    def receive_heartbeat(
        self,
        device_id: str,
        request: HeartbeatRequest,
        idempotency_key: str,
    ) -> Device:
        device = self.devices.get(device_id)

        if device is None:
            raise KeyError("Device not found")

        fingerprint = (
            request.status,
            request.cpu_usage,
            request.signal_strength,
        )
        processed = self.processed_heartbeats[device_id]

        # A retry must not refresh last_heartbeat a second time.
        if idempotency_key in processed:
            if processed[idempotency_key] != fingerprint:
                raise ValueError(
                    "Idempotency key reused with different payload"
                )
            return device

        if self.simulator_commands[device_id] != "RUNNING":
            raise RuntimeError("Device simulator is not running")

        # Record the event only when it is accepted.
        processed[idempotency_key] = fingerprint
        device.last_heartbeat = utc_now()
        device.heartbeat_status = request.status
        device.cpu_usage = request.cpu_usage
        device.signal_strength = request.signal_strength
        return device

    def stop_device(self, device_id: str) -> None:
        if device_id not in self.devices:
            raise KeyError("Device not found")

        # Repeating Stop has the same effect.
        self.simulator_commands[device_id] = "STOPPED"

    def start_device(self, device_id: str) -> None:
        if device_id not in self.devices:
            raise KeyError("Device not found")

        self.simulator_commands[device_id] = "RUNNING"

    def remove_device(self, device_id: str) -> None:
        if device_id not in self.devices:
            # Repeating Remove is idempotent for known tombstones.
            if self.simulator_commands.get(device_id) == "REMOVED":
                return
            raise KeyError("Device not found")

        # Keep a tombstone so the simulator can discover removal.
        self.simulator_commands[device_id] = "REMOVED"
        del self.devices[device_id]
        self.processed_heartbeats.pop(device_id, None)

    def get_simulator_commands(self) -> list[dict[str, str]]:
        return [
            {"device_id": device_id, "command": command}
            for device_id, command in self.simulator_commands.items()
        ]

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
            simulator_state=self.simulator_commands[device.id],
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
