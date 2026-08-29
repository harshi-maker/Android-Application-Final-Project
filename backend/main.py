import math
import time
import io
import sqlite3
import os
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

import numpy as np
from PIL import Image, ImageOps
import cv2
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

# ==========================================
# Central Cloud Database (SQLite Engine)
# ==========================================
DB_FILE = os.path.join(os.path.dirname(__file__), "fish_records.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS catch_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            catch_id TEXT UNIQUE NOT NULL,
            timestamp TEXT NOT NULL,
            gps_location TEXT NOT NULL,
            species_common TEXT NOT NULL,
            species_scientific TEXT NOT NULL,
            confidence REAL NOT NULL,
            health_status TEXT NOT NULL,
            health_index REAL NOT NULL,
            length_cm REAL NOT NULL,
            height_cm REAL NOT NULL,
            width_cm REAL NOT NULL,
            volume_cm3 REAL NOT NULL,
            weight_grams REAL NOT NULL,
            weight_kg REAL NOT NULL,
            fulton_k REAL NOT NULL,
            condition_rating TEXT NOT NULL,
            market_price TEXT,
            stakeholder_role TEXT DEFAULT 'fisherman',
            is_synced INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

init_db()

app = FastAPI(
    title="Fish Catch Analyzer - Central Cloud Database & AI Gateway",
    description="Backend API for Android App Edge Sync, Central Cloud DB, and Stakeholder Portals (Fishermen, Inspectors, Buyers)",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. Schemas & Models
# ==========================================

class CatchRecordCreate(BaseModel):
    catch_id: str
    timestamp: str
    gps_location: str
    species_common: str
    species_scientific: str
    confidence: float
    health_status: str
    health_index: float
    length_cm: float
    height_cm: float
    width_cm: float
    volume_cm3: float
    weight_grams: float
    weight_kg: float
    fulton_k: float
    condition_rating: str
    market_price: Optional[str] = "$0.00"

class CatchRecordResponse(CatchRecordCreate):
    id: int
    is_synced: bool

# ==========================================
# 2. Database Sync & CRUD Endpoints
# ==========================================

@app.post("/sync/upload", response_model=Dict[str, Any])
def sync_offline_records(records: List[CatchRecordCreate]):
    """Syncs batches of offline records captured by Android Room/SQLite to Central Cloud DB"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    synced_count = 0

    for r in records:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO catch_records (
                    catch_id, timestamp, gps_location, species_common, species_scientific,
                    confidence, health_status, health_index, length_cm, height_cm, width_cm,
                    volume_cm3, weight_grams, weight_kg, fulton_k, condition_rating, market_price, is_synced
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                r.catch_id, r.timestamp, r.gps_location, r.species_common, r.species_scientific,
                r.confidence, r.health_status, r.health_index, r.length_cm, r.height_cm, r.width_cm,
                r.volume_cm3, r.weight_grams, r.weight_kg, r.fulton_k, r.condition_rating, r.market_price
            ))
            synced_count += 1
        except Exception:
            continue

    conn.commit()
    conn.close()
    return {"success": True, "synced_records": synced_count, "message": "Records successfully synced to Central Cloud DB."}

@app.get("/records", response_model=List[CatchRecordResponse])
def get_central_records(species: Optional[str] = None):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if species:
        cursor.execute("SELECT * FROM catch_records WHERE species_common LIKE ? ORDER BY id DESC", (f"%{species}%",))
    else:
        cursor.execute("SELECT * FROM catch_records ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    return [
        CatchRecordResponse(
            id=r["id"],
            catch_id=r["catch_id"],
            timestamp=r["timestamp"],
            gps_location=r["gps_location"],
            species_common=r["species_common"],
            species_scientific=r["species_scientific"],
            confidence=r["confidence"],
            health_status=r["health_status"],
            health_index=r["health_index"],
            length_cm=r["length_cm"],
            height_cm=r["height_cm"],
            width_cm=r["width_cm"],
            volume_cm3=r["volume_cm3"],
            weight_grams=r["weight_grams"],
            weight_kg=r["weight_kg"],
            fulton_k=r["fulton_k"],
            condition_rating=r["condition_rating"],
            market_price=r["market_price"],
            is_synced=bool(r["is_synced"])
        )
        for r in rows
    ]

# ==========================================
# 3. Stakeholder Portals API (Fishermen, Inspectors, Buyers)
# ==========================================

@app.get("/portal/{stakeholder}")
def get_stakeholder_portal_data(stakeholder: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM catch_records ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    total_catches = len(rows)
    total_weight = sum(r["weight_kg"] for r in rows) if rows else 0.0

    if stakeholder == "fishermen":
        return {
            "role": "Fishermen Quota & Catch Logs",
            "total_catches": total_catches,
            "accumulated_biomass_kg": round(total_weight, 2),
            "records": [dict(r) for r in rows[:10]]
        }
    elif stakeholder == "inspectors":
        healthy = len([r for r in rows if "Prime" in r["health_status"] or "Good" in r["health_status"]])
        return {
            "role": "Quality & Health Inspection Authority",
            "inspected_batches": total_catches,
            "compliance_pass_rate": f"{round((healthy / total_catches * 100), 1) if total_catches else 100}%",
            "flagged_irregularities": total_catches - healthy
        }
    elif stakeholder == "buyers":
        return {
            "role": "Marketplace & Commercial Buyers",
            "active_lots": total_catches,
            "total_available_biomass_kg": round(total_weight, 2),
            "feed": [dict(r) for r in rows[:10]]
        }
    else:
        raise HTTPException(status_code=400, detail="Unknown stakeholder role. Use: fishermen, inspectors, buyers")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Fish Catch Analyzer Central Cloud Gateway"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
