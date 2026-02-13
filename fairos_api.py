#!/usr/bin/env python3
"""
FAIROs API Server
=================

A FastAPI server that provides FAIR assessment as a REST API.
This allows web applications like dpid.org to request FAIR scores for Research Objects.

Usage:
    # Start the server
    cd /path/to/FAIR-Research-Object
    source venv/bin/activate
    uvicorn fairos_api:app --host 0.0.0.0 --port 8000 --reload

Endpoints:
    GET  /                      - Health check
    GET  /health                - Detailed health status
    POST /assess                - Assess FAIR score from URL or RO-Crate data
    POST /assess/url            - Assess FAIR score from a URL (F-UJI)
    POST /assess/rocrate        - Assess FAIR score from RO-Crate JSON-LD

Requirements:
    pip install fastapi uvicorn
"""

import os
import sys
import json
import tempfile
import shutil
from typing import Optional, Dict, Any, List
from datetime import datetime

# Add the code path for FAIROs imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "code/fair_assessment"))

# ============================================================================
# Configuration (overridable via environment variables)
# ============================================================================

FUJI_SERVER_URL = os.environ.get("FUJI_SERVER_URL", "http://localhost:1071")
DPID_API_URL = os.environ.get("DPID_API_URL", "http://localhost:5461")

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests

# Import FAIROs components
try:
    from rocrate_fairness.ro_fairness import ROCrateFAIRnessCalculator
    ROCRATE_AVAILABLE = True
except ImportError:
    ROCRATE_AVAILABLE = False
    print("⚠️  ROCrateFAIRnessCalculator not available")

try:
    from fuji_wrapper.fujiwrapper import FujiWrapper
    FUJI_AVAILABLE = True
except ImportError:
    FUJI_AVAILABLE = False
    print("⚠️  FujiWrapper not available")


# ============================================================================
# API Models
# ============================================================================

class AssessURLRequest(BaseModel):
    """Request to assess a URL using F-UJI"""
    url: str = Field(..., description="URL to assess (DOI, IPFS URL, or other resolvable URL)")
    use_fuji: bool = Field(True, description="Use F-UJI for assessment")
    
class AssessROCrateRequest(BaseModel):
    """Request to assess an RO-Crate from JSON-LD data"""
    jsonld: Dict[str, Any] = Field(..., description="RO-Crate JSON-LD data")
    identifier: Optional[str] = Field(None, description="Optional identifier for the RO")

class AssessRequest(BaseModel):
    """Generic assess request - can be URL or inline data"""
    url: Optional[str] = Field(None, description="URL to assess")
    jsonld: Optional[Dict[str, Any]] = Field(None, description="RO-Crate JSON-LD data")
    dpid: Optional[int] = Field(None, description="dPID number to assess")
    dpid_api_url: Optional[str] = Field(default=None, description="dPID API base URL (defaults to DPID_API_URL env var)")

class FAIRScore(BaseModel):
    """FAIR assessment score result"""
    overall_score: float = Field(..., description="Overall FAIR score (0-100)")
    findable: Optional[float] = Field(None, description="Findable score")
    accessible: Optional[float] = Field(None, description="Accessible score")
    interoperable: Optional[float] = Field(None, description="Interoperable score")
    reusable: Optional[float] = Field(None, description="Reusable score")
    checks_passed: int = Field(0, description="Number of checks passed")
    checks_total: int = Field(0, description="Total number of checks")
    tool_used: str = Field(..., description="Assessment tool used")
    timestamp: str = Field(..., description="Assessment timestamp")
    details: Optional[List[Dict[str, Any]]] = Field(None, description="Detailed check results")

class AssessResponse(BaseModel):
    """Assessment response"""
    success: bool
    score: Optional[FAIRScore] = None
    error: Optional[str] = None
    identifier: Optional[str] = None

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    services: Dict[str, bool]
    timestamp: str


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="FAIROs API",
    description="FAIR Assessment API for Research Objects",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for web app integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Helper Functions
# ============================================================================

def check_fuji_server() -> bool:
    """Check if F-UJI server is running"""
    try:
        resp = requests.get(f"{FUJI_SERVER_URL}/fuji/api/v1/", timeout=2)
        return resp.status_code in [200, 404]  # 404 is OK, means server is running
    except:
        return False

def assess_with_fuji(url: str) -> FAIRScore:
    """Assess a URL using F-UJI"""
    if not check_fuji_server():
        raise HTTPException(status_code=503, detail="F-UJI server not available")
    
    try:
        fuji = FujiWrapper(url)
        checks = fuji.get_checks()
        
        # Calculate scores
        passed = sum(1 for c in checks if c.get("status") == "pass")
        total = len(checks)
        
        # Calculate category scores
        categories = {"Findable": [], "Accessible": [], "Interoperable": [], "Reusable": []}
        for check in checks:
            cat = check.get("category_id", "")
            if cat in categories:
                score = 1 if check.get("status") == "pass" else 0
                categories[cat].append(score)
        
        def avg_score(scores):
            return (sum(scores) / len(scores) * 100) if scores else None
        
        return FAIRScore(
            overall_score=round((passed / total * 100) if total > 0 else 0, 1),
            findable=avg_score(categories["Findable"]),
            accessible=avg_score(categories["Accessible"]),
            interoperable=avg_score(categories["Interoperable"]),
            reusable=avg_score(categories["Reusable"]),
            checks_passed=passed,
            checks_total=total,
            tool_used="F-UJI",
            timestamp=datetime.utcnow().isoformat(),
            details=checks
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"F-UJI assessment failed: {str(e)}")

def assess_with_rocrate(jsonld: Dict[str, Any]) -> FAIRScore:
    """Assess RO-Crate from JSON-LD data"""
    if not ROCRATE_AVAILABLE:
        raise HTTPException(status_code=503, detail="ROCrateFAIRnessCalculator not available")
    
    # Create temporary directory with RO-Crate
    tmp_dir = tempfile.mkdtemp(prefix="fairos_")
    try:
        # Write JSON-LD to file
        metadata_path = os.path.join(tmp_dir, "ro-crate-metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(jsonld, f)
        
        # Run assessment
        calculator = ROCrateFAIRnessCalculator(tmp_dir)
        result = calculator.calculate_fairness()
        
        checks = result.get("checks", [])
        passed = sum(1 for c in checks if c.get("status") == "ok")
        total = len(checks)
        
        # Extract category scores
        score_data = result.get("score", {})
        
        return FAIRScore(
            overall_score=score_data.get("final", 0),
            findable=None,  # ROCrate calculator doesn't break down by category the same way
            accessible=None,
            interoperable=None,
            reusable=None,
            checks_passed=passed,
            checks_total=total,
            tool_used="RO-Crate-FAIR",
            timestamp=datetime.utcnow().isoformat(),
            details=[{
                "principle_id": c.get("principle_id"),
                "title": c.get("title"),
                "status": "pass" if c.get("status") == "ok" else "fail",
                "category_id": c.get("category_id"),
            } for c in checks]
        )
    except ValueError as e:
        # Handle RO-Crate validation errors (e.g., "root entity must have Dataset among its types")
        error_msg = str(e)
        if "Dataset" in error_msg or "root entity" in error_msg.lower():
            raise HTTPException(
                status_code=422, 
                detail=f"Invalid RO-Crate format: {error_msg}. Falling back to F-UJI."
            )
        raise
    finally:
        # Cleanup temp directory
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - health check"""
    return {
        "status": "ok",
        "service": "FAIROs API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Detailed health check including service status"""
    return HealthResponse(
        status="healthy",
        services={
            "fairos_api": True,
            "rocrate_calculator": ROCRATE_AVAILABLE,
            "fuji_wrapper": FUJI_AVAILABLE,
            "fuji_server": check_fuji_server(),
        },
        timestamp=datetime.utcnow().isoformat()
    )

@app.post("/assess", response_model=AssessResponse, tags=["Assessment"])
async def assess(request: AssessRequest):
    """
    Assess FAIR score for a Research Object.
    
    Can accept:
    - `url`: Direct URL to assess with F-UJI
    - `jsonld`: RO-Crate JSON-LD data to assess locally
    - `dpid`: dPID number to fetch and assess
    """
    try:
        identifier = None
        
        # Option 1: Assess by dPID
        if request.dpid is not None:
            # Use provided dpid_api_url or fall back to env-configured default
            dpid_base_url = request.dpid_api_url or DPID_API_URL
            # Fetch JSON-LD from dPID resolver
            jsonld_url = f"{dpid_base_url}/{request.dpid}?format=jsonld"
            identifier = f"dpid://{request.dpid}"
            resolve_url = f"{dpid_base_url}/{request.dpid}"
            
            # Always try F-UJI first for dPIDs (more comprehensive)
            if check_fuji_server():
                try:
                    score = assess_with_fuji(resolve_url)
                except Exception as fuji_error:
                    # If F-UJI fails, try RO-Crate assessment
                    try:
                        resp = requests.get(jsonld_url, timeout=30)
                        resp.raise_for_status()
                        jsonld = resp.json()
                        if ROCRATE_AVAILABLE:
                            score = assess_with_rocrate(jsonld)
                        else:
                            raise HTTPException(status_code=503, detail=f"F-UJI failed and RO-Crate not available: {str(fuji_error)}")
                    except Exception as rocrate_error:
                        raise HTTPException(status_code=502, detail=f"Both F-UJI and RO-Crate assessment failed")
            else:
                # F-UJI not available, try RO-Crate
                try:
                    resp = requests.get(jsonld_url, timeout=30)
                    resp.raise_for_status()
                    jsonld = resp.json()
                    if ROCRATE_AVAILABLE:
                        score = assess_with_rocrate(jsonld)
                    else:
                        raise HTTPException(status_code=503, detail="No assessment services available")
                except requests.RequestException as e:
                    raise HTTPException(status_code=502, detail=f"Failed to fetch dPID JSON-LD: {str(e)}")
        
        # Option 2: Assess by URL
        elif request.url:
            identifier = request.url
            score = assess_with_fuji(request.url)
        
        # Option 3: Assess by JSON-LD
        elif request.jsonld:
            identifier = request.jsonld.get("@id", "inline-rocrate")
            score = assess_with_rocrate(request.jsonld)
        
        else:
            raise HTTPException(status_code=400, detail="Must provide url, jsonld, or dpid")
        
        return AssessResponse(
            success=True,
            score=score,
            identifier=identifier
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return AssessResponse(
            success=False,
            error=str(e)
        )

@app.post("/assess/url", response_model=AssessResponse, tags=["Assessment"])
async def assess_url(request: AssessURLRequest):
    """Assess a URL using F-UJI"""
    try:
        score = assess_with_fuji(request.url)
        return AssessResponse(
            success=True,
            score=score,
            identifier=request.url
        )
    except HTTPException:
        raise
    except Exception as e:
        return AssessResponse(
            success=False,
            error=str(e)
        )

@app.post("/assess/rocrate", response_model=AssessResponse, tags=["Assessment"])
async def assess_rocrate(request: AssessROCrateRequest):
    """Assess RO-Crate from JSON-LD data"""
    try:
        score = assess_with_rocrate(request.jsonld)
        return AssessResponse(
            success=True,
            score=score,
            identifier=request.identifier or "inline-rocrate"
        )
    except HTTPException:
        raise
    except Exception as e:
        return AssessResponse(
            success=False,
            error=str(e)
        )


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("FAIROs API Server")
    print("=" * 60)
    print(f"RO-Crate Calculator: {'✅' if ROCRATE_AVAILABLE else '❌'}")
    print(f"F-UJI Wrapper: {'✅' if FUJI_AVAILABLE else '❌'}")
    print(f"F-UJI Server URL: {FUJI_SERVER_URL}")
    print(f"F-UJI Server: {'✅' if check_fuji_server() else '❌ (start with: python -m fuji_server)'}")
    print(f"dPID API URL: {DPID_API_URL}")
    print("=" * 60)
    print("Starting server on http://localhost:8000")
    print("API docs: http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

