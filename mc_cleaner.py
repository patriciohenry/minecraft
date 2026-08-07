import asyncio
import json
import uuid
import sys
import logging
import websockets

# Configuración de logs limpia
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

async def process_command_stream(websocket):
    """Bucle asíncrono principal que inyecta comandos al juego de forma fluida."""
    peer_address = websocket.remote_address
    logging.info(f"[+] Minecraft Conectado Exitosamente: {peer_address}")
    
    try:
        # Enviar reglas automáticas al iniciar por si acaso
        await websocket.send(json.dumps(generate_command_packet("/gamerule commandBlockOutput false")))
        await websocket.send(json.dumps(generate_command_packet("/gamerule sendCommandFeedback false")))
        await websocket.send(json.dumps(generate_command_packet("/say [Nube] Servicio de Proteccion Activo.")))

        while True:
            for mob in ALL_MOBS:
                cmd = f"/kill @e[type={mob}]"
                await websocket.send(json.dumps(generate_command_packet(cmd)))
            await asyncio.sleep(2.0)
            
    except websockets.exceptions.ConnectionClosed:
        logging.info(f"[-] Minecraft desconectado: {peer_address}")

async def health_check_filter(connection, HTTP_path):
    """
    Filtro de Arquitectura: Intercepta las solicitudes HTTP antes del handshake.
    Si la petición es del bot de Render (HTTP plano), responde 200 OK de forma
    silenciosa y evita que inunde el log con errores '400 Bad Request'.
    """
    # Si no es una solicitud de actualización a WebSocket (es un ping de Render)
    if "Upgrade" not in connection.headers:
        # Devolvemos un estado HTTP 200 válido silencioso para el balanceador
        return (
            websockets.http.HTTPStatus.OK,
            [("Content-Type", "text/plain")],
            b"Healthy"
        )
    return None

async def main():
    logging.info(f"[*] Iniciando Servidor WebSockets Híbrido en Puerto {PORT}...")
    
    # Inyectamos el filtro de salud 'process_request' en el constructor del servidor
    async with websockets.serve(
        process_command_stream, 
        HOST, 
        PORT,
        process_request=health_check_filter
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

