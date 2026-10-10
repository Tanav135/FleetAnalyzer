
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DeviceRegistration(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)


class HeartbeatRequest(BaseModel):
    timestamp: datetime | None = None
    status: Literal["OK", "WARNING", "ERROR"] = "OK"
    cpu_usage: float | None = Field(default=None, ge=0, le=100)
    signal_strength: int | None = None


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: Literal["ONLINE", "OFFLINE"]
    last_heartbeat: datetime | None
    registered_at: datetime


class FleetSummary(BaseModel):
    total: int
    online: int
    offline: int
