from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import threading
import json
import os
from agents import AutonomousLeadAgent
from report_generator import generate_report
import config

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
    """
    
    def log_bridge(msg):
        # Schedule the coroutine in the main event loop
        asyncio.run_coroutine_threadsafe(
            manager.send_json({"type": "log", "content": msg}, websocket), 
            loop
        )

    try:
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

@app.websocket("/ws/research/{company}")
async def websocket_research(websocket: WebSocket, company: str):
    await manager.connect(websocket)
    loop = asyncio.get_event_loop()
    
    try:
        await manager.send_json({"type": "status", "content": f"Connected to Atlas. Target: {company}"}, websocket)
        
        # Spawn Agent Thread
        # We use a thread because the Agent uses blocking Selenium calls
        t = threading.Thread(target=run_agent_process, args=(company, websocket, loop))
        t.start()
        
        # Keep connection open
        while True:
            await websocket.receive_text() # Just listen for close
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(e)
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
