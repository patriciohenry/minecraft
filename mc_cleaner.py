import asyncio
import json
import uuid
import sys
import logging
import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

HOST = "0.0.0.0"
PORT = 3000

ALL_MOBS = ["zombie", "enderman", "husk", "drowned", "zombie_villager", "creeper"]

def generate_command_packet(cmd_string):
    return {
        "header": {
            "version": 1,
            "requestId": str(uuid.uuid4()),
            "messageType": "commandRequest",
            "purpose": "commandRequest"
        },
        "body": {
            "version": 1,
            "commandLine": cmd_string,
            "origin": {"type": "player"}
        }
    }

async def process_command_stream(websocket, path=None):
    """Main communication loop with the Minecraft client."""
    peer_address = websocket.remote_address
    logging.info(f"[+] Minecraft Connected Successfully: {peer_address}")
    
    try:
        await websocket.send(json.dumps(generate_command_packet("/gamerule commandBlockOutput false")))
        await websocket.send(json.dumps(generate_command_packet("/gamerule sendCommandFeedback false")))
        await websocket.send(json.dumps(generate_command_packet("/say [Nube] Anti-Mob protection active.")))

        while True:
            for mob in ALL_MOBS:
                cmd = f"/kill @e[type={mob}]"
                await websocket.send(json.dumps(generate_command_packet(cmd)))
            await asyncio.sleep(2.0)
            
    except websockets.exceptions.ConnectionClosed:
        logging.info(f"[-] Minecraft disconnected: {peer_address}")

def health_check_filter(path, headers):
    """
    Interceptors for non-websocket upgrade strings (Render health bots).
    Bypasses package dependencies by explicitly delivering a fallback integer.
    """
    # Check if the connection request lacks standard WebSocket Upgrade keys
    if "Upgrade" not in headers:
        # 200 represents HTTPStatus.OK across all variations
        return (
            200,
            [("Content-Type", "text/plain")],
            b"Healthy"
        )
    return None

async def main():
    logging.info(f"[*] Starting Production Websocket Daemon on Port {PORT}...")
    
    async with websockets.serve(
        process_command_stream, 
        HOST, 
        PORT,
        process_request=health_check_filter
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

