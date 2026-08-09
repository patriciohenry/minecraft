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
        # Un pequeño respiro de seguridad
        await asyncio.sleep(1.0)

        # Enviar comandos de inicialización sin la barra '/'
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

async def process_handshake(path, request_headers):
    """
    Manejador del saludo inicial adaptado para Websockets 12+.
    Acepta cualquier origen y subprotocolo enviado por la tablet sin restricciones de proxy.
    """
    response_headers = []
    
    # Si Minecraft envía la cabecera solicitando subprotocolo, se la aprobamos de vuelta
    if "Sec-WebSocket-Protocol" in request_headers:
        response_headers.append(("Sec-WebSocket-Protocol", request_headers["Sec-WebSocket-Protocol"]))
        
    return None, response_headers

async def main():
    logger.info(f"[*] Iniciando Servidor WebSockets v12+ en Puerto {PORT}...")
    
    # Usamos process_request para un bypass absoluto de seguridad sobre el proxy de Render
    async with websockets.serve(
        process_command_stream, 
        HOST, 
        PORT,
        process_request=process_handshake
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

