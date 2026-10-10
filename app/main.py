from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException, status, Header

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

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(FRONTEND_DIR / "index.html")

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
def heartbeat(
    device_id: str,
    request: HeartbeatRequest,
    idempotency_key: str = Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=200,
    ),
):
    try:
        device = device_service.receive_heartbeat(
            device_id, request, idempotency_key
        )
        return device_service.to_response(device)
    except KeyError as error:
        raise HTTPException(
            status_code=404, detail=str(error).strip("'")
        )
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))

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

@app.post("/devices/{device_id}/stop")
def stop_device(device_id: str):
    try:
        device_service.stop_device(device_id)
        return {"device_id": device_id, "command": "STOPPED"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Device not found")


@app.post("/devices/{device_id}/start")
def start_device(device_id: str):
    try:
        device_service.start_device(device_id)
        return {"device_id": device_id, "command": "RUNNING"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Device not found")


@app.delete("/devices/{device_id}", status_code=204)
def remove_device(device_id: str):
    try:
        device_service.remove_device(device_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Device not found")


@app.get("/simulator/commands")
def simulator_commands():
    return {
        "commands": device_service.get_simulator_commands()
    }
