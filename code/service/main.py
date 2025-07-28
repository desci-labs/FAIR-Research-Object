from fastapi import FastAPI, Request, HTTPException, Depends, Body, UploadFile, File
from pathlib import Path
from datetime import datetime, UTC
import sqlite3
import random
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from config import settings
import paho.mqtt.client as mqtt

# Create logs directory if it doesn't exist
LOG_DIR = "../../logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Define log file path with date suffix
log_file = os.path.join(LOG_DIR, "service.log")

# Set up rotating file handler (daily rotation)
handler = TimedRotatingFileHandler(
    log_file,
    when="midnight",     # Rotate at midnight
    interval=1,
    backupCount=7,       # Keep logs for 7 days
    encoding="utf-8"
)

# Set log format
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)

# Set up the root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)

DB_PATH = "api_control.db"

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to FAIROs, a service to assess Research Objects."}

#@app.get("/tests")
#def get_tests():
def get_db():
    return sqlite3.connect(DB_PATH)

def get_client_ip(request: Request):
    return request.client.host  # You can adjust for proxies if needed

def check_access(request: Request):
    conn = get_db()
    cursor = conn.cursor()
    token = request.headers.get("Authorization")

    # Token-based access (no limit)
    if token:
        cursor.execute("SELECT token FROM tokens WHERE token = ?", (token,))
        if cursor.fetchone():
            conn.close
            return  "private"
        else:
            conn.close()
            raise HTTPException(status_code=403, detail="Invalid token")

    # IP-based access (rate limited)
    ip = get_client_ip(request)
    today = datetime.now().date().isoformat()
    cursor.execute("SELECT count FROM ip_requests WHERE ip = ? AND date = ?", (ip, today))
    row = cursor.fetchone()

    if row:
        if row[0] >= 100:
            raise HTTPException(status_code=429, detail="Daily request limit reached for this IP")
        cursor.execute("UPDATE ip_requests SET count = count + 1 WHERE ip = ? AND date = ?", (ip, today))
    else:
        cursor.execute("INSERT INTO ip_requests (ip, date, count) VALUES (?, ?, ?)", (ip, today, 1))

    conn.commit()
    conn.close()
    return "public"
    

@app.post("/assess/algorithm/{algorithm_id}")
def execute_algorithm(
    algorithm_id: str,
    file: UploadFile = File(...),
    storage_mode: str = Depends(check_access),  # This ensures check_access runs
    request: Request = None,  # Optional, only if you need request inside
):
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    random_suffix = random.randint(1000, 9999)
    ticket_id = f"{timestamp}-{random_suffix}"
    logger.info(f"New request arrived to execute algorithm '{algorithm_id}'. New ticket generated: {ticket_id}")
    
        # Determine directory based on access type
    target_dir = Path(settings.FILE_STORAGE_DIR if storage_mode == "private" else settings.NO_TOKEN_DIRECTORY)
    target_dir.mkdir(parents=True, exist_ok=True)  # Ensure it exists

    # Save the uploaded file to the FILE_STORAGE_DIR
    filename = f"{ticket_id}_{file.filename}"
    save_path = target_dir / filename

    with open(save_path, "wb") as f:
        f.write(file.file.read())

    logger.info(
        f"File '{file.filename}' uploaded from IP {request.client.host} → ticket {ticket_id}"
    )
    return {
        "ticket_id": ticket_id
    }

#@app.get("/assessment/{assessment_id}")
#def get_assessment(assessment_id: str):