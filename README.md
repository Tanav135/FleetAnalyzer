# FleetAnalyzer

FleetAnalyzer is a simple device fleet monitoring system built using Python and FastAPI. It allows users to register devices, receive heartbeats, check device status, and view a summary of the fleet through a web dashboard.

The project also includes a simulator that runs multiple devices and sends heartbeats to the server. This makes it easier to test how the system behaves when devices are running, stopped, or offline.

## 1. Features

- Register devices using a unique device ID and name.
- Receive heartbeat updates from registered devices.
- Automatically mark devices as offline if no heartbeat is received for more than 30 seconds.
- View all registered devices and their current status.
- Check individual device details.
- View a summary of total, online, and offline devices.
- Start and stop individual simulated devices.
- Remove devices from the fleet.
- Test the API using automated tests.
- View device information through a simple web dashboard.
- Run the backend using Docker Compose.

## 2. Technologies Used

- **Python** – Main programming language.
- **FastAPI** – Backend API framework.
- **Uvicorn** – Runs the FastAPI application.
- **Pytest** – Automated testing.
- **Requests** – Sends HTTP requests from the simulator.
- **HTML, CSS and JavaScript** – Dashboard interface.
- **Docker and Docker Compose** – Containerization and application setup.

## 3. Project Structure

```text
FleetAnalyzer/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   └── service.py
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── simulator/
│   ├── __init__.py
│   └── simulator.py
├── tests/
│   ├── __init__.py
│   └── test_devices.py
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── compose.yaml
├── .gitignore
└── README.md
```

## 4. Requirements

Before running the project, make sure you have:

- Python 3.13 or a compatible Python version.
- pip, which is used to install Python packages.
- Git, if you want to clone the repository.
- Docker Desktop, if you want to run the application using Docker.

## 5. Setup and Installation

### Step 1: Clone the repository

```bash
git clone https://github.com/Tanav135/FleetAnalyzer.git
cd FleetAnalyzer
```

If you already have the project on your computer, open a terminal inside the project folder instead.

### Step 2: Create a virtual environment

On Windows:

```bash
python -m venv venv
```

### Step 3: Activate the virtual environment

On Windows Command Prompt:

```bash
venv\Scripts\activate
```

On Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### Step 4: Install dependencies

```bash
python -m pip install -r requirements.txt
```

## 6. Running the Application Locally

Start the backend from the project root directory:

```bash
python -m uvicorn app.main:app --reload
```

Once the server starts, open these URLs in your browser:

- **Dashboard:** http://127.0.0.1:8000/dashboard
- **API documentation:** http://127.0.0.1:8000/docs
- **API root:** http://127.0.0.1:8000/

Keep the terminal running while using the application.

## 7. Running the Device Simulator

The simulator creates five simulated devices and periodically sends heartbeat requests to the backend.

Make sure the backend is running before starting the simulator. Open a second terminal in the project folder and activate the virtual environment.

Run:

```bash
python simulator\simulator.py
```

The simulator registers devices D1 through D5 and begins sending heartbeats.

To stop an individual simulated device, enter its device ID in the simulator terminal. For example:

```text
D3
```

To stop all simulators and exit, enter:

```text
quit
```

Stopping a simulated device does not immediately make it offline. Its status remains online until its last heartbeat becomes older than 30 seconds. After that, it is marked offline.

The simulator runs separately from Docker Compose. If the backend is running in Docker on the same computer, the simulator can still connect through `http://127.0.0.1:8000`.

## 8. Running with Docker

Docker can be used to build and run the backend without manually installing the project dependencies in your local Python environment.

Make sure Docker Desktop is installed and running.

From the project root, run:

```bash
docker compose up --build
```

This builds the Docker image and starts the backend container.

Open the dashboard at:

http://127.0.0.1:8000/dashboard

The API documentation is available at:

http://127.0.0.1:8000/docs

To stop the container, press `Ctrl+C` in the terminal. To stop and remove the Compose containers, run:

```bash
docker compose down
```

To run the simulator with the containerized backend, open another terminal on the host computer and run:

```bash
python simulator\simulator.py
```

The simulator is started manually; it is not automatically launched by Docker Compose.

## 9. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/devices` | Register a device |
| POST | `/devices/{device_id}/heartbeat` | Send a heartbeat |
| GET | `/devices` | List registered devices |
| GET | `/devices/{device_id}` | Get details of one device |
| GET | `/summary` | Get fleet statistics |
| POST | `/devices/{device_id}/stop` | Stop a simulated device |
| POST | `/devices/{device_id}/start` | Resume a simulated device |
| DELETE | `/devices/{device_id}` | Remove a device |
| GET | `/simulator/commands` | View simulator control states |

### Example: Register a device

Send a `POST` request to `/devices` with this JSON body:

```json
{
  "id": "D6",
  "name": "Test Device"
}
```

### Example: Send a heartbeat

Send a `POST` request to `/devices/D6/heartbeat` with this JSON body:

```json
{
  "status": "OK",
  "cpu_usage": 35.5,
  "signal_strength": -60
}
```

The `Idempotency-Key` header is optional. If supplied, it helps prevent the same heartbeat request from being processed more than once when the same key is reused.

For interactive API testing, open `/docs` and try the endpoints directly.

## 10. Running Tests

Run the automated tests from the project root:

```bash
python -m pytest -v
```

The tests cover important device management behaviour, including registration, heartbeat processing, offline status, duplicate requests, and fleet summaries.

Run the tests after making changes to check that existing functionality still works.

## 11. Assumptions and Limitations

- A device is considered online if its most recent heartbeat was received within the last 30 seconds.
- A device without a heartbeat is considered offline.
- Device information is stored in memory, so it is cleared when the backend restarts.
- Device IDs are unique. Registering an existing ID with the same name is treated as an idempotent registration; using the same ID with a different name returns a conflict.
- The simulator is intended for local testing and demonstration.
- The project does not currently implement authentication or role-based access control.
- The current implementation is suitable for a small demonstration fleet, not a production monitoring environment.

## 12. Possible Improvements

Some improvements that could be added in the future include:

- Store device information in a database so it survives server restarts.
- Add authentication and authorization.
- Add charts showing heartbeat history and device status changes.
- Add structured logging and monitoring.
- Add CI checks to run tests automatically when code is pushed.
- Improve simulator management and support a larger number of devices.

## AI Usage

AI tools were used as a development aid during this project for discussing implementation approaches, debugging issues, improving documentation, and reviewing parts of the code.

The generated suggestions were reviewed and adapted during implementation. The project was tested locally to check that the main functionality worked as expected.

AI assistance was used to support development, not as a replacement for understanding or testing the code.

## Approach

I broke the project into three main parts: the FastAPI backend, the device simulator, and the web dashboard. I first implemented device registration and heartbeat handling, then added online/offline status tracking using a 30-second timeout. After that, I added simulator controls, API validation, and automated tests. I kept the implementation simple and modular so each part could be tested independently.

## Development Process

I built the project incrementally, testing each feature before moving to the next. During development, I fixed issues related to duplicate registrations, repeated heartbeat requests, and simulator state management. I also added Docker support to make the backend easier to set up and run consistently. Finally, I connected the dashboard to the API and tested the main workflows locally.

## Making It Production-Ready

For production use, I would replace in-memory storage with a database such as PostgreSQL so device data survives restarts. I would add authentication, role-based access control, stronger input validation, and secure API communication. I would also introduce structured logging, monitoring, metrics, and automated CI/CD pipelines. For larger fleets, I would consider asynchronous processing, a message queue, and deployment with health checks and horizontal scaling.