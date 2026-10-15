
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "siteguard.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id TEXT NOT NULL,
                location TEXT NOT NULL,
                incident TEXT NOT NULL,
                priority TEXT DEFAULT 'HIGH',
                status TEXT DEFAULT 'OPEN',
                photo TEXT,
                created_at TEXT NOT NULL
            )
        """)


@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:filename>")
def frontend_files(filename):
    if filename in {
        "index.html", "style.css", "script.js",
        "manifest.json", "sw.js"
    }:
        return send_from_directory(BASE_DIR, filename)
    return jsonify({"error": "File not found"}), 404


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "online",
        "app": "SiteGuard AI",
        "message": "Backend connected successfully"
    })


@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    with get_db() as db:
        total = db.execute(
            "SELECT COUNT(*) FROM incidents WHERE status='OPEN'"
        ).fetchone()[0]

        incidents = db.execute(
            "SELECT * FROM incidents ORDER BY id DESC LIMIT 10"
        ).fetchall()

    return jsonify({
        "workers": 48,
        "open_incidents": total,
        "risk_score": min(100, total * 12),
        "incidents": [dict(row) for row in incidents]
    })


@app.route("/api/incidents", methods=["GET", "POST"])
def incidents_api():
    if request.method == "GET":
        with get_db() as db:
            rows = db.execute(
                "SELECT * FROM incidents ORDER BY id DESC"
            ).fetchall()
        return jsonify([dict(row) for row in rows])

    data = request.get_json(silent=True) or {}

    worker_id = str(data.get("worker_id", "")).strip()
    location = str(data.get("location", "")).strip()
    incident = str(data.get("incident", "")).strip()

    if not worker_id or not location or not incident:
        return jsonify({
            "error": "Worker ID, location and incident are required"
        }), 400

    with get_db() as db:
        cursor = db.execute("""
            INSERT INTO incidents
            (worker_id, location, incident, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            worker_id, location, incident,
            datetime.now().isoformat(timespec="seconds")
        ))
        incident_id = cursor.lastrowid

    return jsonify({
        "success": True,
        "message": "Safety incident recorded",
        "incident_id": incident_id
    }), 201


@app.route("/api/incidents/<int:incident_id>/resolve",
           methods=["PATCH"])
def resolve_incident(incident_id):
    with get_db() as db:
        cursor = db.execute("""
            UPDATE incidents
            SET status='RESOLVED'
            WHERE id=?
        """, (incident_id,))

    if cursor.rowcount == 0:
        return jsonify({"error": "Incident not found"}), 404

    return jsonify({
        "success": True,
        "message": "Incident resolved"
    })


@app.route("/api/emergency", methods=["POST"])
def emergency():
    worker_id = request.form.get("worker_id", "").strip()
    location = request.form.get("location", "").strip()
    incident = request.form.get("incident", "").strip()

    if not worker_id or not location or not incident:
        return jsonify({
            "error": "Worker ID, location and incident are required"
        }), 400

    photo_name = None
    photo = request.files.get("photo")

    if photo and photo.filename:
        filename = secure_filename(photo.filename)
        extension = filename.rsplit(".", 1)[-1].lower() \
            if "." in filename else ""

        if extension not in ALLOWED_EXTENSIONS:
            return jsonify({
                "error": "Use JPG, JPEG, PNG or WEBP images only"
            }), 400

        photo_name = (
            datetime.now().strftime("%Y%m%d%H%M%S%f")
            + "_" + filename
        )
        photo.save(os.path.join(UPLOAD_FOLDER, photo_name))

    with get_db() as db:
        cursor = db.execute("""
            INSERT INTO incidents
            (worker_id, location, incident, priority,
             status, photo, created_at)
            VALUES (?, ?, ?, 'HIGH', 'OPEN', ?, ?)
        """, (
            worker_id,
            location,
            incident,
            photo_name,
            datetime.now().isoformat(timespec="seconds")
        ))
        incident_id = cursor.lastrowid

    return jsonify({
        "success": True,
        "message": "Emergency report saved",
        "incident_id": incident_id,
        "priority": "HIGH",
        "photo": photo_name,
        "ambulance_notified": False
    }), 201


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "error": "Photo size must be 5 MB or less"
    }), 413


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
