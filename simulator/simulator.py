
import threading
import requests
import uuid

API_BASE = "http://127.0.0.1:8000"
HEARTBEAT_INTERVAL = 5
COMMAND_POLL_INTERVAL = 1
REQUEST_TIMEOUT = 5

devices = [
    {"id": "D1", "name": "Device 1"},
    {"id": "D2", "name": "Device 2"},
    {"id": "D3", "name": "Device 3"},
    {"id": "D4", "name": "Device 4"},
    {"id": "D5", "name": "Device 5"},
]

stop_events = {}
shutdown_event = threading.Event()
state_lock = threading.Lock()

# Local cache only. The backend remains the source of truth.
simulator_states = {}


def register_device(device):
    response = requests.post(
        f"{API_BASE}/devices",
        json=device,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    print(f"{device['id']}: registered successfully.")


def poll_commands():
    """Synchronize local simulator workers with backend commands."""
    while not shutdown_event.is_set():
        try:
            response = requests.get(
                f"{API_BASE}/simulator/commands",
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            commands = response.json()["commands"]

            with state_lock:
                for item in commands:
                    simulator_states[item["device_id"]] = item["command"]

        except requests.RequestException as error:
            print(f"Command polling failed: {error}")

        shutdown_event.wait(COMMAND_POLL_INTERVAL)


def simulate_device(device):
    device_id = device["id"]
    stop_event = stop_events[device_id]

    try:
        register_device(device)
    except requests.RequestException as error:
        print(f"{device_id}: registration failed: {error}")
        return

    while not shutdown_event.is_set() and not stop_event.is_set():
        with state_lock:
            state = simulator_states.get(device_id, "RUNNING")

        if state == "REMOVED":
            print(f"{device_id}: removed; simulator worker exiting.")
            return

        if state == "STOPPED":
            # Keep the worker alive so a later START command can resume it.
            stop_event.wait(COMMAND_POLL_INTERVAL)
            continue

        try:
            response = requests.post(
                f"{API_BASE}/devices/{device_id}/heartbeat",
                json={"status": "OK", "cpu_usage": 25},
                headers={"Idempotency-Key": str(uuid.uuid4())},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            print(f"{device_id}: heartbeat sent")

        except requests.RequestException as error:
            print(f"{device_id}: heartbeat failed: {error}")
            if error.response is not None:
                print(f"API response: {error.response.text}")

        stop_event.wait(HEARTBEAT_INTERVAL)

    print(f"{device_id}: simulator worker stopped.")


def send_stop_command(device_id):
    """Stop a device through the backend API."""
    try:
        response = requests.post(
            f"{API_BASE}/devices/{device_id}/stop",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        with state_lock:
            simulator_states[device_id] = "STOPPED"

        print(f"{device_id}: STOPPED by backend command.")

    except requests.RequestException as error:
        print(f"{device_id}: stop failed: {error}")
        if error.response is not None:
            print(f"API response: {error.response.text}")


def main():
    threads = []

    # Start the command poller first.
    command_thread = threading.Thread(
        target=poll_commands,
        daemon=True,
    )
    command_thread.start()

    for device in devices:
        stop_events[device["id"]] = threading.Event()

        thread = threading.Thread(
            target=simulate_device,
            args=(device,),
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    print("\nAll simulators started.")
    print("Type a device ID (D1-D5) to stop that device.")
    print("Type 'quit' to stop all simulators.\n")

    try:
        while True:
            command = input("Command: ").strip().upper()

            if command in stop_events:
                send_stop_command(command)

            elif command == "QUIT":
                for device_id in stop_events:
                    send_stop_command(device_id)

                shutdown_event.set()
                break

            else:
                print("Unknown command. Enter D1-D5 or quit.")

    except (KeyboardInterrupt, EOFError):
        shutdown_event.set()

    finally:
        shutdown_event.set()

        for event in stop_events.values():
            event.set()

        for thread in threads:
            thread.join(timeout=2)

        command_thread.join(timeout=2)
        print("Simulator controller stopped.")


if __name__ == "__main__":
    main()
