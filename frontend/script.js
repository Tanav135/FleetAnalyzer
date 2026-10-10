
const API_BASE = window.location.origin;
const REFRESH_INTERVAL = 3000;

const tableBody = document.getElementById("device-table-body");
const notice = document.getElementById("notice");
const noticeTitle = document.getElementById("notice-title");
const noticeMessage = document.getElementById("notice-message");

let refreshInProgress = false;
let noticeTimer = null;

function showNotice(type, title, message) {
    clearTimeout(noticeTimer);

    notice.className = `notice notice-${type}`;
    noticeTitle.textContent = title;
    noticeMessage.textContent = message;

    noticeTimer = setTimeout(() => {
        notice.classList.add("hidden");
    }, type === "error" ? 10000 : 5000);
}

document.getElementById("dismiss-notice").addEventListener("click", () => {
    notice.classList.add("hidden");
    clearTimeout(noticeTimer);
});

function friendlyError(status, detail, action = "complete this request") {
    const text = typeof detail === "string"
        ? detail
        : JSON.stringify(detail ?? "");

    const normalized = text.toLowerCase();

    if (status === 0) {
        return "The dashboard could not reach the API. Check that the FastAPI server is running and try again.";
    }

    if (status === 404) {
        return "This device was not found. It may have been removed already. Refresh the device list to see the latest fleet state.";
    }

    if (status === 409) {
        if (normalized.includes("not running") ||
            normalized.includes("stopped")) {
            return "This device's simulator is stopped, so it cannot send a heartbeat. Use Start to resume the simulator, then try again.";
        }

        if (normalized.includes("idempotency")) {
            return "This heartbeat request conflicts with an earlier request. Retry using a new request key.";
        }

        return text || "The request conflicts with the device's current state. Refresh the dashboard and try again.";
    }

    if (status === 422) {
        return "Some of the submitted information is invalid or missing. Check the fields and try again.";
    }

    if (status >= 500) {
        return "The server encountered an unexpected problem. Please try again. If the issue continues, check the backend terminal for details.";
    }

    return text || `Unable to ${action}. Please try again.`;
}

async function apiRequest(path, options = {}, action = "complete this request") {
    let response;

    try {
        response = await fetch(`${API_BASE}${path}`, {
            ...options,
            headers: {
                ...(options.body ? { "Content-Type": "application/json" } : {}),
                ...(options.headers || {}),
            },
        });
    } catch {
        throw new Error(friendlyError(0, ""));
    }

    let body = null;

    if (response.status !== 204) {
        const contentType = response.headers.get("content-type") || "";

        if (contentType.includes("application/json")) {
            try {
                body = await response.json();
            } catch {
                body = null;
            }
        } else {
            try {
                body = await response.text();
            } catch {
                body = null;
            }
        }
    }

    if (!response.ok) {
        const detail = body && typeof body === "object"
            ? body.detail
            : body;

        throw new Error(
            friendlyError(response.status, detail, action)
        );
    }

    return body;
}

function formatTimestamp(timestamp) {
    if (!timestamp) {
        return "No heartbeat received";
    }

    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
        return "Timestamp unavailable";
    }

    return date.toLocaleString();
}

function badge(label, className) {
    return `<span class="state-badge ${className}">${label}</span>`;
}

function renderDevice(device) {
    const connectivity = device.status === "ONLINE"
        ? badge("Online", "state-online")
        : badge("Offline", "state-offline");

    const simulatorState = device.simulator_state || "UNKNOWN";

    let simulatorBadge;

    if (simulatorState === "RUNNING") {
        simulatorBadge = badge("Running", "state-running");
    } else if (simulatorState === "STOPPED") {
        simulatorBadge = badge("Stopped", "state-stopped");
    } else {
        simulatorBadge = badge(simulatorState, "state-stopped");
    }

    const isStopped = simulatorState === "STOPPED";
    const isRemoved = simulatorState === "REMOVED";

    const startStopButton = isStopped
        ? `<button class="button button-start" data-action="start"
                   data-id="${escapeHTML(device.id)}">Start</button>`
        : `<button class="button button-stop" data-action="stop"
                   data-id="${escapeHTML(device.id)}"
                   ${isRemoved ? "disabled" : ""}>Stop</button>`;

    const heartbeatButton = `
        <button class="button button-heartbeat"
                data-action="heartbeat"
                data-id="${escapeHTML(device.id)}"
                title="${isStopped
                    ? "The backend will reject heartbeats while the simulator is stopped."
                    : "Send a heartbeat through the API."}">
            Send heartbeat
        </button>`;

    return `
        <tr>
            <td>
                <span class="device-name">${escapeHTML(device.name)}</span>
                <span class="device-id">${escapeHTML(device.id)}</span>
            </td>
            <td>${connectivity}</td>
            <td>${simulatorBadge}</td>
            <td>${escapeHTML(formatTimestamp(device.last_heartbeat))}</td>
            <td>
                <div class="action-group">
                    ${startStopButton}
                    ${heartbeatButton}
                    <button class="button button-remove"
                            data-action="remove"
                            data-id="${escapeHTML(device.id)}">
                        Remove
                    </button>
                </div>
            </td>
        </tr>
    `;
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    })[character]);
}

async function refreshAll() {
    if (refreshInProgress) {
        return;
    }

    refreshInProgress = true;

    try {
        const [summary, devices] = await Promise.all([
            apiRequest("/summary", {}, "load fleet summary"),
            apiRequest("/devices", {}, "load devices"),
        ]);

        document.getElementById("total-count").textContent = summary.total;
        document.getElementById("online-count").textContent = summary.online;
        document.getElementById("offline-count").textContent = summary.offline;

        if (devices.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-state">
                        No devices registered yet. Register a device to get started.
                    </td>
                </tr>`;
        } else {
            tableBody.innerHTML = devices.map(renderDevice).join("");
        }

        document.getElementById("last-updated").textContent =
            `Last refreshed: ${new Date().toLocaleTimeString()}`;

    } catch (error) {
        showNotice(
            "error",
            "Could not refresh the dashboard",
            error.message || "An unexpected error occurred while loading fleet data."
        );
    } finally {
        refreshInProgress = false;
    }
}

async function performDeviceAction(action, deviceId) {
    const encodedId = encodeURIComponent(deviceId);

    try {
        if (action === "stop") {
            await apiRequest(
                `/devices/${encodedId}/stop`,
                { method: "POST" },
                "stop the simulator"
            );

            showNotice(
                "success",
                "Stop command accepted",
                `${deviceId} has been marked STOPPED by the backend. Its connectivity may remain ONLINE until its last heartbeat is more than 30 seconds old.`
            );
        } else if (action === "start") {
            await apiRequest(
                `/devices/${encodedId}/start`,
                { method: "POST" },
                "start the simulator"
            );

            showNotice(
                "success",
                "Start command accepted",
                `${deviceId} has been marked RUNNING. The simulator must be active and polling commands to resume heartbeats.`
            );
        } else if (action === "remove") {
            const confirmed = window.confirm(
                `Remove ${deviceId} from the fleet?\n\nThis deletes the device from the backend. This action cannot be undone from the dashboard.`
            );

            if (!confirmed) {
                return;
            }

            await apiRequest(
                `/devices/${encodedId}`,
                { method: "DELETE" },
                "remove the device"
            );

            showNotice(
                "success",
                "Device removed",
                `${deviceId} has been removed from the fleet.`
            );
        } else if (action === "heartbeat") {
            await apiRequest(
                `/devices/${encodedId}/heartbeat`,
                {
                    method: "POST",
                    headers: {
                        "Idempotency-Key": crypto.randomUUID(),
                    },
                    body: JSON.stringify({
                        status: "OK",
                        cpu_usage: 25,
                    }),
                },
                "send a heartbeat"
            );

            showNotice(
                "success",
                "Heartbeat received",
                `The backend accepted the heartbeat for ${deviceId}.`
            );
        }

        await refreshAll();

    } catch (error) {
        showNotice(
            "error",
            `Could not ${action} ${deviceId}`,
            error.message || "An unexpected error occurred. Please try again."
        );
    }
}

tableBody.addEventListener("click", async event => {
    const button = event.target.closest("button[data-action]");

    if (!button || button.disabled) {
        return;
    }

    const action = button.dataset.action;
    const deviceId = button.dataset.id;

    button.disabled = true;

    try {
        await performDeviceAction(action, deviceId);
    } finally {
        button.disabled = false;
    }
});

document.getElementById("register-form").addEventListener("submit", async event => {
    event.preventDefault();

    const id = document.getElementById("device-id").value.trim();
    const name = document.getElementById("device-name").value.trim();
    const submitButton = event.target.querySelector('button[type="submit"]');

    if (!id || !name) {
        showNotice(
            "error",
            "Missing device details",
            "Enter both a device ID and a device name."
        );
        return;
    }

    submitButton.disabled = true;

    try {
        await apiRequest(
            "/devices",
            {
                method: "POST",
                body: JSON.stringify({ id, name }),
            },
            "register the device"
        );

        event.target.reset();

        showNotice(
            "success",
            "Device registered",
            `${id} is now registered. It will remain OFFLINE until a heartbeat is received.`
        );

        await refreshAll();

    } catch (error) {
        showNotice(
            "error",
            "Registration unsuccessful",
            error.message || "The device could not be registered. Please try again."
        );
    } finally {
        submitButton.disabled = false;
    }
});

document.getElementById("refresh-button").addEventListener("click", refreshAll);

refreshAll();
setInterval(refreshAll, REFRESH_INTERVAL);
