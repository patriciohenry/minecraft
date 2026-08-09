import asyncio
import json
import uuid
import sys
import logging
import websockets

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("mc_cleaner")
logger.setLevel(logging.INFO)

HOST = "0.0.0.0"
PORT = 3000

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

async def process_command_stream(websocket):
    """Direct command injection loop."""
    peer_address = websocket.remote_address
    logger.info(f"[+] Minecraft Conectado Exitosamente: {peer_address}")
    
    try:
        await asyncio.sleep(1.0)

        await websocket.send(json.dumps(generate_command_packet("gamerule commandblockoutput false")))
        await websocket.send(json.dumps(generate_command_packet("gamerule sendcommandfeedback false")))
        await websocket.send(json.dumps(generate_command_packet("say [Nube] Anti-Mob protection active.")))

        while True:
            for mob in ALL_MOBS:
                cmd = f"kill @e[type={mob}]"
                await websocket.send(json.dumps(generate_command_packet(cmd)))
            await asyncio.sleep(2.0)
            
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"[-] Minecraft desconectado: {peer_address}")

# FIXED HANDSHAKE LOGIC FOR WEBSOCKETS 12.0+
def select_minecraft_subprotocol(connection, subprotocols):
    """
    Forces the modern library to allow empty subprotocol handshakes.
    This prevents Minecraft Bedrock from triggering a 'conexión terminada' error.
    """
    return ""

async def main():
    logger.info(f"[*] Iniciando Servidor WebSockets en Puerto {PORT}...")
    
    # We pass empty string initialization override directly into the server instance
    async with websockets.serve(
        process_command_stream, 
        HOST, 
        PORT,
        origins=[None],
        select_subprotocol=select_minecraft_subprotocol
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

