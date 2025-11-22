import os
import threading
import time
import uuid
import logging
from datetime import datetime
import json
import shutil

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file,
    abort,
    redirect,
    url_for,
    after_this_request,
)

import yt_dlp

# ----------------------------------------------
# Grundopsætning
# ----------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "app.log")

# ---------- HISTORY DATABASE ----------
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


# ---------- LOGGING ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Sluk Flask access-log (undgå spam med GET /status...)
werk_log = logging.getLogger("werkzeug")
werk_log.setLevel(logging.ERROR)

# ---------- JOB DATABASE ----------
JOBS_FILE = os.path.join(BASE_DIR, "jobs.json")


def load_jobs():
    if not os.path.exists(JOBS_FILE):
        return {}
    try:
        with open(JOBS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_jobs():
    try:
        with open(JOBS_FILE, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("Kunne ikke gemme jobs: %s", e)


# job_id -> status dict
jobs = load_jobs()

# ---------- AUTO CLEANUP AF /tmp/job_* ----------
CLEANUP_MAX_AGE_SECONDS = 24 * 60 * 60  # 24 timer


def cleanup_old_job_dirs():
    now = time.time()
    tmp_root = "/tmp"
    try:
        for name in os.listdir(tmp_root):
            if not name.startswith("job_"):
                continue
            path = os.path.join(tmp_root, name)
            if not os.path.isdir(path):
                continue

            age = now - os.path.getmtime(path)
            if age > CLEANUP_MAX_AGE_SECONDS:
                try:
                    shutil.rmtree(path)
                    logger.info("Slettede gammel job-mappe: %s", path)
                except Exception as e:
                    logger.error("Kunne ikke slette %s: %s", path, e)
    except Exception as e:
        logger.error("Fejl i cleanup_old_job_dirs: %s", e)


# ----------------------------------------------
# Hjælpefunktion: opret job
# ----------------------------------------------
def create_job(url: str):
    # Ryd gamle tmp-jobmapper før vi laver et nyt job
    cleanup_old_job_dirs()

    job_id = uuid.uuid4().hex
    tmp_dir = f"/tmp/job_{job_id}"
    os.makedirs(tmp_dir, exist_ok=True)

    jobs[job_id] = {
        "id": job_id,
        "url": url,
        "phase": "queued",
        "progress": 0.0,
        "error": None,
        "tmp_dir": tmp_dir,
        "result_path": None,
        "title": None,
        "last_update": time.time(),
    }

    logger.info("Oprettet job %s for URL %s", job_id, url)
    save_jobs()
    return job_id


# ----------------------------------------------
# Progress-hook bundet til job_id
# ----------------------------------------------
def make_progress_hook(job_id: str):
    def hook(d):
        job = jobs.get(job_id)
        if not job:
            return

        status = d.get("status", "")
        filename = d.get("filename", "") or ""
        info = d.get("info_dict") or {}

        # Sæt titel første gang vi ser den
        if not job.get("title"):
            title = info.get("title")
            if title:
                job["title"] = title

        # VIDEO DOWNLOAD
        if status == "downloading" and "audio" not in filename.lower():
            job["phase"] = "downloading_video"
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            downloaded = d.get("downloaded_bytes", 0)
            job["progress"] = downloaded / total

        # AUDIO DOWNLOAD
        if status == "downloading" and "audio" in filename.lower():
            job["phase"] = "downloading_audio"
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            downloaded = d.get("downloaded_bytes", 0)
            job["progress"] = downloaded / total

        # Efter fragments men før endelig .mp4
        if status == "finished" and ".mp4" not in filename.lower():
            job["phase"] = "processing"
            job["progress"] = max(job["progress"], 0.97)

        job["last_update"] = time.time()

    return hook


# ----------------------------------------------
# Download-arbejder i baggrundstråd
# ----------------------------------------------
def download_worker(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return

    url = job["url"]
    tmp_dir = job["tmp_dir"]

    logger.info("Starter download job_id=%s, url=%s", job_id, url)

    ydl_opts = {
        "outtmpl": os.path.join(tmp_dir, "%(title)s.%(ext)s"),
        "format": "bv*+ba/b",
        "noplaylist": True,
        "progress_hooks": [make_progress_hook(job_id)],
        "merge_output_format": "mp4",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Find endelig MP4 (helst den merged uden 'audio'/'fvideo' i navnet)
        final_mp4 = None
        for f in os.listdir(tmp_dir):
            lower = f.lower()
            if lower.endswith(".mp4") and "audio" not in lower and "fvideo" not in lower:
                final_mp4 = os.path.join(tmp_dir, f)
                break

        if not final_mp4:
            for f in os.listdir(tmp_dir):
                if f.lower().endswith(".mp4"):
                    final_mp4 = os.path.join(tmp_dir, f)
                    break

        if not final_mp4:
            raise Exception("Ingen .mp4 fundet efter merging!")

        job["result_path"] = final_mp4
        job["phase"] = "finished"
        job["progress"] = 1.0
        save_jobs()

        # Gem historik
        history = load_history()
        history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": job.get("title"),
            "url": url,
        })
        save_history(history)

        logger.info(
            "Job %s færdigt: %s (%s)",
            job_id,
            final_mp4,
            job.get("title") or ""
        )

    except Exception as e:
        logger.exception("Fejl i job %s: %s", job_id, e)
        job["phase"] = "error"
        job["error"] = str(e)
        job["progress"] = 0.0
        save_jobs()


# ----------------------------------------------
# Flask routes
# ----------------------------------------------
@app.route("/jobs")
def jobs_page():
    # Sorter jobs efter seneste aktivitet (nyeste foerst)
    job_list = sorted(
        jobs.values(),
        key=lambda j: j.get("last_update", 0),
        reverse=True,
    )
    return render_template("jobs.html", jobs=job_list)

@app.route("/jobs-json")
def jobs_json():
    job_list = sorted(
        jobs.values(),
        key=lambda j: j.get("last_update", 0),
        reverse=True,
    )
    return jsonify([
        {
            "id": j["id"],
            "title": j.get("title") or j.get("url"),
            "phase": j.get("phase"),
            "progress": int((j.get("progress") or 0) * 100),
        }
        for j in job_list
    ])


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/start", methods=["POST"])
def start_download():
    url = request.form.get("url", "").strip()
    if not url:
        return jsonify({"error": "Ingen URL angivet"}), 400

    job_id = create_job(url)

    threading.Thread(
        target=download_worker,
        args=(job_id,),
        daemon=True
    ).start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>", methods=["GET"])
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Ukendt job"}), 404

    return jsonify({
        "job_id": job_id,
        "phase": job["phase"],
        "progress": int(job["progress"] * 100),
        "error": job["error"],
        "title": job["title"],
    })


@app.route("/download/<job_id>", methods=["GET"])
def download_file(job_id):
    job = jobs.get(job_id)
    if not job:
        abort(404)

    result = job.get("result_path")
    tmp_dir = job.get("tmp_dir")

    if not result or not os.path.exists(result):
        abort(404)

    logger.info("Sender fil til download for job %s", job_id)

    @after_this_request
    def cleanup(response):
        try:
            # Slet selve videofilen
            if result and os.path.exists(result):
                os.remove(result)

            # Slet hele temp-mappen for jobbet
            if tmp_dir and os.path.isdir(tmp_dir):
                shutil.rmtree(tmp_dir)

            # Opdater job-status
            job["phase"] = "downloaded"
            job["result_path"] = None
            save_jobs()

            logger.info("Ryddede op efter job %s", job_id)
        except Exception as e:
            logger.error("Fejl ved oprydning efter download job %s: %s", job_id, e)

        return response

    return send_file(
        result,
        as_attachment=True,
        download_name=os.path.basename(result),
    )


@app.route("/fetch/<job_id>", methods=["GET"])
def fetch(job_id):
    return download_file(job_id)


@app.route("/log")
def log_page():
    # Vis de sidste 200 linjer af logfilen
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()[-200:]
    except Exception as e:
        lines = [f"Kunne ikke læse logfilen: {e}"]

    return render_template("log.html", log_lines=lines)


@app.route("/commands")
def commands_page():
    return render_template("commands.html")


@app.route("/history")
def history_page():
    history = load_history()
    return render_template("history.html", history=history)


if __name__ == "__main__":
    logger.info("Starter DR Downloader server...")
    app.run(host="0.0.0.0", port=5000)
