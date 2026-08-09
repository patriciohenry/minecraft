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
    """Bucle directo de inyección de comandos."""
    peer_address = websocket.remote_address
    logger.info(f"[+] Minecraft Conectado Exitosamente: {peer_address}")
    
    try:
        # Esperamos 2 segundos completos a que la tablet configure el canal antes de hablarle
        await asyncio.sleep(2.0)

        # Enviamos UN SOLO comando inicial para verificar que el puente funciona
        await websocket.send(json.dumps(generate_command_packet("say [Nube] ¡Conectado con éxito!")))
        await asyncio.sleep(1.0)

        # Si el comando anterior funciona, iniciamos el bucle de limpieza
        while True:
            for mob in ALL_MOBS:
                cmd = f"kill @e[type={mob}]"
                await websocket.send(json.dumps(generate_command_packet(cmd)))
            await asyncio.sleep(2.0)
            
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"[-] Minecraft desconectado: {peer_address}")


# CORRECCIÓN PARA WEBSOCKETS 12.0+: Interceptamos de forma segura las cabeceras del objeto Request
async def process_handshake(websocket, request):
    # En websockets 12+, las cabeceras se extraen usando request.headers
    if "Sec-WebSocket-Protocol" in request.headers:
        # Le devolvemos a Minecraft exactamente el protocolo que nos está pidiendo para validar el handshake
        websocket.subprotocol = request.headers["Sec-WebSocket-Protocol"]
    return None

async def main():
    logger.info(f"[*] Iniciando Servidor WebSockets en Puerto {PORT}...")
    
    # Abrimos el servidor ignorando restricciones de origen externas (origins=[None])
    async with websockets.serve(
        process_command_stream, 
        HOST, 
        PORT,
        process_request=process_handshake,
        origins=[None]
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

