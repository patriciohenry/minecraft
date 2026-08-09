import asyncio
import json
import uuid
import sys
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# Set up clean production system logs
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mc_cleaner")
logger.setLevel(logging.INFO)

app = FastAPI()

ALL_MOBS = ["zombie", "enderman", "husk", "drowned", "zombie_villager", "creeper"]

def generate_command_packet(cmd_string):
    return {
        "header": {
            "version": 1,
            "requestId": str(uuid.uuid4()),
            "messageType": "commandRequest",
            "messagePurpose": "commandRequest" 
        },
        "body": {
            "version": 1,
            "commandLine": cmd_string,
            "origin": {"type": "player"}
        }
    }

# Standard HTTP Endpoint for Render's dynamic auto-ping Health Checks
@app.get("/")
async def health_check():
    return {"status": "online", "service": "minecraft_cleaner"}

# Route 1: Catches wss://://onrender.com
@app.websocket("/")
async def websocket_root_endpoint(websocket: WebSocket):
    await handle_minecraft_session(websocket)

# Route 2: Catches wss://://onrender.com/ws
@app.websocket("/ws")
async def websocket_ws_endpoint(websocket: WebSocket):
    await handle_minecraft_session(websocket)

# Reusable core session logic function
async def handle_minecraft_session(websocket: WebSocket):
    # Accept the handshake dynamically, honoring Minecraft's protocol demands
    requested_protocol = websocket.headers.get("sec-websocket-protocol")
    await websocket.accept(subprotocol=requested_protocol)
    
    peer_ip = websocket.client.host if websocket.client else "Unknown"
    logger.info(f"[+] ¡Minecraft Tablet Conectado Exitosamente desde Proxy/IP: {peer_ip}!")
    
    try:
        # Crucial delay to let Bedrock process secure handshake frames
        await asyncio.sleep(1.0)
        
        # Inject standard operational rules into the game environment
        await websocket.send_json(generate_command_packet("gamerule commandblockoutput false"))
        await websocket.send_json(generate_command_packet("gamerule sendcommandfeedback false"))
        await websocket.send_json(generate_command_packet("say [Nube] Anti-Mob protection active."))
        
        while True:
            for mob in ALL_MOBS:
                cmd = f"kill @e[type={mob}]"
                await websocket.send_json(generate_command_packet(cmd))
            await asyncio.sleep(2.0)
            
    except WebSocketDisconnect:
        logger.info(f"[-] Minecraft Tablet desconectado de la sesión de forma limpia.")
    except Exception as e:
        logger.info(f"[-] Conexión interrumpida debido a: {e}")

if __name__ == "__main__":
    import uvicorn
    # Bind directly to Render's exposed environment parameters on port 3000
    uvicorn.run(app, host="0.0.0.0", port=3000)

