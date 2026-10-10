
from fastapi import FastAPI, HTTPException, status

from app.models import (
    DeviceRegistration,
    DeviceResponse,
    FleetSummary,
    HeartbeatRequest,
)
from app.service import DeviceService

app = FastAPI(
    title="FleetAnalyzer",
    description="Monitor device heartbeats and fleet connectivity.",
    version="1.0.0",
)

# In-memory service instance for this application process.
device_service = DeviceService()


@app.get("/")
def root():
    return {
        "application": "FleetAnalyzer",
        "message": "Device Fleet Monitoring API",
        "docs": "/docs",
    }


@app.post(
    "/devices",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_device(request: DeviceRegistration):
    try:
        device = device_service.register_device(request)
        return device_service.to_response(device)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@app.post(
    "/devices/{device_id}/heartbeat",
    response_model=DeviceResponse,
)
def receive_heartbeat(
    device_id: str,
    request: HeartbeatRequest,
):
    try:
        device = device_service.receive_heartbeat(
            device_id, request
        )
        return device_service.to_response(device)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc


@app.get("/devices", response_model=list[DeviceResponse])
def list_devices():
    return device_service.list_devices()


@app.get("/devices/{device_id}", response_model=DeviceResponse)
def get_device(device_id: str):
    try:
        return device_service.get_device(device_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc


@app.get("/summary", response_model=FleetSummary)
def get_summary():
    return device_service.get_summary()
