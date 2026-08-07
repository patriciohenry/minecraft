import asyncio
import json
import uuid
import sys
import logging
import websockets
# Importamos la estructura de respuesta nativa de la biblioteca
from websockets.http import Response

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
    """Maneja los comandos de Minecraft de forma continua."""
    peer_address = websocket.remote_address
    logging.info(f"[+] Minecraft Conectado Exitosamente: {peer_address}")
    
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
        logging.info(f"[-] Minecraft desconectado: {peer_address}")

def health_check_filter(path, headers):
    """
    Intercepta las conexiones de Render de forma correcta.
    Usa la clase Response para evitar el error 400 Bad Request.
    """
    if "Upgrade" not in headers:
        logging.info("[Diagnóstico] Respondiendo al ping automático de Render.")
        # Retornamos un objeto Response nativo (Código 200, mensaje, cabeceras, contenido)
        return Response(
            status=200,
            phrase="OK",
            headers=[("Content-Type", "text/plain")],
            body=b"Healthy"
        )
    return None

async def main():
    logging.info(f"[*] Iniciando Servidor WebSockets en Puerto {PORT}...")
    
    async with websockets.serve(
        process_command_stream, 
        HOST, 
        PORT,
        process_request=health_check_filter
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

