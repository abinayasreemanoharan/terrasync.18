
const API_URL = "http://127.0.0.1:5000";
const QUEUE = "siteguard-emergency-queue";

const photoInput = document.getElementById("emergencyPhoto");

photoInput?.addEventListener("change", () => {
  const file = photoInput.files[0];
  const preview = document.getElementById("photoPreview");

  if (!file) return;

  if (!file.type.startsWith("image/")) {
    alert("Please select an image.");
    photoInput.value = "";
    return;
  }

  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
});

function readQueue() {
  try {
    return JSON.parse(localStorage.getItem(QUEUE) || "[]");
  } catch {
    return [];
  }
}

function updateNetwork() {
  document.getElementById("networkStatus").textContent =
    navigator.onLine ? "🟢 Online" : "🟠 Offline — reports queued locally";

  document.getElementById("pendingCount").textContent =
    "Pending reports: " + readQueue().length;
}

async function sendEmergency() {
  const status = document.getElementById("emergencyStatus");
  const file = photoInput?.files[0];

  const report = {
    worker_id: document.getElementById("workerId").value || "W-104",
    location: document.getElementById("workerLocation").value || "Unknown",
    created_at: new Date().toISOString()
  };

  try {
    if (!navigator.onLine) {
      throw new Error("Offline");
    }

    const form = new FormData();
    form.append("worker_id", report.worker_id);
    form.append("location", report.location);

    if (file) form.append("photo", file);

    const response = await fetch(API_URL + "/api/emergency", {
      method: "POST",
      body: form
    });

    if (!response.ok) throw new Error("Server unavailable");

    status.textContent =
      "Emergency report saved to backend. Ambulance notification is not confirmed.";
  } catch {
    try {
      // Store text locally; avoid storing large photos in localStorage.
      const queue = readQueue();
      queue.push(report);
      localStorage.setItem(QUEUE, JSON.stringify(queue));

      status.textContent =
        "Offline/server unavailable: report details queued on this device. Photo not queued.";
    } catch {
      status.textContent = "Unable to save report. Call emergency services directly.";
    }
  }

  updateNetwork();
}

function call112() {
  window.location.href = "tel:112";
}

window.addEventListener("online", updateNetwork);
window.addEventListener("offline", updateNetwork);
updateNetwork();

// Device battery information, when browser supports it
async function monitorBattery() {
  const status = document.getElementById("batteryStatus");
  const bar = document.getElementById("batteryLevel");
  const advice = document.getElementById("batteryAdvice");

  if (!navigator.getBattery) {
    status.textContent = "Battery API is not supported by this browser.";
    return;
  }

  try {
    const battery = await navigator.getBattery();

    function refresh() {
      const percent = Math.round(battery.level * 100);

      status.textContent = `${percent}% — ${
        battery.charging ? "Charging" : "Not charging"
      }`;

      bar.style.width = percent + "%";
      bar.style.background = percent <= 20 ? "#ff5c82" : "#43edb0";

      advice.textContent = percent <= 20 && !battery.charging
        ? "Low battery: connect charger or UPS."
        : "Keep the device charged for continuous operation.";
    }

    battery.addEventListener("levelchange", refresh);
    battery.addEventListener("chargingchange", refresh);
    refresh();
  } catch {
    status.textContent = "Battery information unavailable.";
  }
}

monitorBattery();
