from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import threading
import json
import os
import shutil
import pandas as pd
from typing import List

from agents import AutonomousLeadAgent  # Legacy fallback
from optimized_pipeline import OptimizedResearchAgent  # New optimized pipeline
from report_generator import generate_report
from bulk_reporter import generate_bulk_excel
from data_models import CompanyProfile
import config

# Feature flag from config
USE_OPTIMIZED_PIPELINE = config.USE_OPTIMIZED_PIPELINE

app = FastAPI(title="Atlas API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure folders exist
os.makedirs(config.REPORT_DIR, exist_ok=True)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/reports", StaticFiles(directory=config.REPORT_DIR), name="reports")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_json(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

manager = ConnectionManager()

def run_agent_process(company: str, websocket: WebSocket, loop):
    """
    Runs the agent in a thread and pushes logs to the async loop
    so they can be sent over the websocket.
    Uses OptimizedResearchAgent (new parallel pipeline) or AutonomousLeadAgent (legacy).
    """
    
    def log_bridge(msg):
        # Schedule the coroutine in the main event loop
        asyncio.run_coroutine_threadsafe(
            manager.send_json({"type": "log", "content": msg}, websocket), 
            loop
        )

    try:
        if USE_OPTIMIZED_PIPELINE:
            log_bridge("🚀 Using OPTIMIZED parallel pipeline...")
            agent = OptimizedResearchAgent(company, log_callback=log_bridge)
        else:
            log_bridge("📋 Using legacy sequential pipeline...")
            agent = AutonomousLeadAgent(company, log_callback=log_bridge)
        
        profile = agent.run_pipeline()
        
        # Save Outputs
        json_path = generate_report(profile) # This helper now saves JSON and PDF
        
        # Send Success Signal
        asyncio.run_coroutine_threadsafe(
            manager.send_json({
                "type": "result", 
                "profile": profile.model_dump(mode='json'), # Safe serialization
                "pdf_url": f"http://localhost:8000/reports/{profile.name.replace(' ', '_')}_Dossier.pdf"
            }, websocket),
            loop
        )
        
    except Exception as e:
        asyncio.run_coroutine_threadsafe(
            manager.send_json({"type": "error", "content": str(e)}, websocket),
            loop
        )

def run_bulk_process(file_path: str, websocket: WebSocket, loop):
    """
    Runs bulk processing on a CSV file.
    Uses OptimizedResearchAgent (new parallel pipeline) or AutonomousLeadAgent (legacy).
    """
    def log_bridge(msg):
        asyncio.run_coroutine_threadsafe(
            manager.send_json({"type": "log", "content": msg}, websocket), 
            loop
        )
    
    try:
        log_bridge(f"Reading CSV file: {file_path}")
        df = pd.read_csv(file_path)
        
        if 'domain' not in df.columns:
            raise ValueError("CSV must contain a 'domain' column.")
            
        # Clean domains: Drop NaNs and empties
        df_clean = df.dropna(subset=['domain'])
        df_clean = df_clean[df_clean['domain'].astype(str).str.strip() != ""]
        domains = df_clean['domain'].tolist()
        
        total = len(domains)
        log_bridge(f"Found {total} valid domains to process (filtered blank rows).")
        
        profiles = []
        
        processed_count = 0
        
        pipeline_type = "OPTIMIZED parallel" if USE_OPTIMIZED_PIPELINE else "legacy sequential"
        log_bridge(f"🚀 Starting {pipeline_type} pipeline for {total} records.")

        for i, domain in enumerate(domains):
            log_bridge(f"═══ Processing {i+1}/{total}: {domain} ═══")
            
            try:
                # Use optimized or legacy agent based on feature flag
                if USE_OPTIMIZED_PIPELINE:
                    agent = OptimizedResearchAgent(domain, log_callback=log_bridge)
                else:
                    agent = AutonomousLeadAgent(domain, log_callback=log_bridge)
                
                profile = agent.run_pipeline()
                profiles.append(profile)
                
                # Send intermediate progress
                asyncio.run_coroutine_threadsafe(
                    manager.send_json({
                        "type": "progress", 
                        "current": i+1, 
                        "total": total,
                        "last_profile": profile.model_dump(mode='json')
                    }, websocket), 
                    loop
                )
            except Exception as e:
                log_bridge(f"❌ Error processing {domain}: {str(e)}")
                # Continue to next
            
            processed_count += 1

        # Generate Bulk Excel
        log_bridge("Generating Bulk Excel Report...")
        excel_filename = generate_bulk_excel(profiles)
        
        excel_url = f"http://localhost:8000/reports/{excel_filename}"
        
        asyncio.run_coroutine_threadsafe(
            manager.send_json({
                "type": "bulk_result", 
                "excel_url": excel_url,
                "count": len(profiles)
            }, websocket),
            loop
        )
        
    except Exception as e:
        asyncio.run_coroutine_threadsafe(
            manager.send_json({"type": "error", "content": str(e)}, websocket),
            loop
        )

@app.post("/upload_csv")
async def upload_csv(file: UploadFile = File(...)):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb+") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "location": file_location}

@app.websocket("/ws/research/{company}")
async def websocket_research(websocket: WebSocket, company: str):
    await manager.connect(websocket)
    loop = asyncio.get_event_loop()
    
    try:
        await manager.send_json({"type": "status", "content": f"Connected to Atlas. Target: {company}"}, websocket)
        t = threading.Thread(target=run_agent_process, args=(company, websocket, loop))
        t.start()
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(e)
        manager.disconnect(websocket)

@app.websocket("/ws/bulk")
async def websocket_bulk(websocket: WebSocket):
    await manager.connect(websocket)
    loop = asyncio.get_event_loop()
    
    try:
        while True:
            # Wait for message event loop
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "analyze_file":
                filename = message.get("filename")
                file_path = f"{UPLOAD_DIR}/{filename}"
                
                if not os.path.exists(file_path):
                     await manager.send_json({"type": "error", "content": "File not found"}, websocket)
                     continue

                try:
                    df = pd.read_csv(file_path)
                    if 'domain' in df.columns:
                        # Count valid domains
                        df_clean = df.dropna(subset=['domain'])
                        df_clean = df_clean[df_clean['domain'].astype(str).str.strip() != ""]
                        count = len(df_clean)
                        
                        await manager.send_json({
                            "type": "analysis_result", 
                            "count": count, 
                            "filename": filename
                        }, websocket)
                    else:
                        await manager.send_json({"type": "error", "content": "CSV missing 'domain' column"}, websocket)
                        
                except Exception as e:
                     await manager.send_json({"type": "error", "content": f"Error reading file: {str(e)}"}, websocket)

            elif message.get("type") == "confirm_start":
                filename = message.get("filename")
                file_path = f"{UPLOAD_DIR}/{filename}"
                
                await manager.send_json({"type": "status", "content": f"Starting bulk process for {filename}"}, websocket)
                
                # Start processing thread
                t = threading.Thread(target=run_bulk_process, args=(file_path, websocket, loop))
                t.start()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(e)
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
