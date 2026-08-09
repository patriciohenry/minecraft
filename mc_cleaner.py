import asyncio
import json
import uuid
import sys
import logging
import websockets

# Clean logging setup
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
        # Crucial pause to let Bedrock finalize its internal connection state
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

# CRITICAL BEDROCK HANDSHAKE FIX FOR WEBSOCKETS 12.0+
def select_minecraft_protocol(connection, requested_protocols):
    """
    Forces the server to accept Minecraft Bedrock's handshake signature.
    If Minecraft asks for a specific protocol or leaves it blank, 
    we approve it directly to prevent 'conexion terminada'.
    """
    if requested_protocols:
        return requested_protocols[0]
    return None

async def main():
    logger.info(f"[*] Iniciando Servidor WebSockets en Puerto {PORT}...")
    
    # We bypass cross-origin checks via origins=[None] for the Render proxy
    # and use select_subprotocol to intercept and solve the protocol selection natively
    async with websockets.serve(
        process_command_stream, 
        HOST, 
        PORT,
        origins=[None],
        select_subprotocol=select_minecraft_protocol
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

