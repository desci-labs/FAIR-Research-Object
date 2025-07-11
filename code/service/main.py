from fastapi import FastAPI, Request, HTTPException, Depends, Body
from datetime import datetime, UTC
import sqlite3
import random

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
            return  # Authorized, no rate limit
        else:
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
    

@app.post("/algorithms")
def execute_algorithm(
    identifier: str = Body(..., embed=True),
    _: None = Depends(check_access),  # This ensures check_access runs
    request: Request = None,  # Optional, only if you need request inside
):
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    random_suffix = random.randint(1000, 9999)
    ticket_id = f"{timestamp}-{random_suffix}"
    return {
        "ticket_id": ticket_id
    }

#@app.get("/assessment/{assessment_id}")
#def get_assessment(assessment_id: str):