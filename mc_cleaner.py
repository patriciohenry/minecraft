import asyncio
import json
import uuid
import sys
import logging
import websockets

# Configuración de logs limpia para evitar ruido en producción
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("mc_cleaner")
logger.setLevel(logging.INFO)

# Configuración de red para contenedores Docker en Render
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
    """Bucle directo de inyección de comandos."""
    peer_address = websocket.remote_address
    logger.info(f"[+] Minecraft Conectado Exitosamente desde: {peer_address}")
    
    try:
        await asyncio.sleep(1.0) # Tiempo de espera para que la tablet asimile el canal

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

def select_minecraft_subprotocol(ws, protocols):
    """ Fuerza la aceptación de subprotocolos de Minecraft """
    return None

async def main():
    logger.info(f"[*] Iniciando Servidor WebSockets en Puerto {PORT}...")
    
    # origins=[None] permite saltarse la seguridad de origen que bloquea el proxy de Render
    async with websockets.serve(
        process_command_stream, 
        HOST, 
        PORT,
        select_subprotocol=select_minecraft_subprotocol,
        origins=[None]
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

