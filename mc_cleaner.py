import asyncio
import json
import uuid
import sys
import logging
import hashlib
import base64

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

def encode_websocket_frame(payload):
    payload_bytes = payload.encode('utf-8')
    length = len(payload_bytes)
    frame = bytearray([0x81])
    
    if length <= 125:
        frame.append(length)
    elif length <= 65535:
        frame.append(126)
        frame.extend(length.to_bytes(2, byteorder='big'))
    else:
        frame.append(127)
        frame.extend(length.to_bytes(8, byteorder='big'))
        
    frame.extend(payload_bytes)
    return frame

async def handle_client(reader, writer):
    peer = writer.get_extra_info('peername')
    
    request_data = b""
    try:
        # Esperamos a leer la cabecera HTTP completa
        while b"\r\n\r\n" not in request_data:
            chunk = await asyncio.wait_for(reader.read(1024), timeout=2.0)
            if not chunk:
                break
            request_data += chunk
    except asyncio.TimeoutError:
        writer.close()
        return
        
    request_text = request_data.decode('utf-8', errors='ignore')
    
    # BUSQUEDA INTELIGENTE DE LA LLAVE WEBSOCKET
    ws_key = None
    for line in request_text.split("\r\n"):
        if line.lower().startswith("sec-websocket-key:"):
            ws_key = line.split(":", 1)[1].strip()
            break
            
    # SI ES UN PING DE RENDER (HTTP Normal, sin llave WS)
    if not ws_key:
        # Respondemos con éxito HTTP 200 para mantener el servicio activo en Render
        response = "HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"
        writer.write(response.encode('utf-8'))
        await writer.drain()
        writer.close()
        return

    # SI ES MINECRAFT TABLET REAL (Contiene la llave WS)
    logger.info(f"[+] ¡Minecraft Tablet detectado desde {peer}! Procesando Handshake...")
    
    guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    accept_sha1 = hashlib.sha1((ws_key + guid).encode('utf-8')).digest()
    accept_b64 = base64.b64encode(accept_sha1).decode('utf-8')
    
    # Respondemos con el cambio de protocolo exacto
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept_b64}\r\n\r\n"
    )
    writer.write(response.encode('utf-8'))
    await writer.drain()
    
    logger.info(f"[+] ¡Conexión Establecida y Cifrada con la Tablet!")
    
    try:
        await asyncio.sleep(1.0)
        
        # Inyectamos comandos iniciales
        writer.write(encode_websocket_frame(json.dumps(generate_command_packet("gamerule commandblockoutput false"))))
        writer.write(encode_websocket_frame(json.dumps(generate_command_packet("gamerule sendcommandfeedback false"))))
        writer.write(encode_websocket_frame(json.dumps(generate_command_packet("say [Nube] Anti-Mob protection active."))))
        await writer.drain()

        while True:
            for mob in ALL_MOBS:
                cmd = f"kill @e[type={mob}]"
                writer.write(encode_websocket_frame(json.dumps(generate_command_packet(cmd))))
            await writer.drain()
            await asyncio.sleep(2.0)
            
    except Exception as e:
        logger.info(f"[-] Conexión finalizada de la tablet: {e}")
    finally:
        writer.close()

async def main():
    logger.info(f"[*] Iniciando Servidor TCP Crudo en Puerto {PORT}...")
    server = await asyncio.start_server(handle_client, HOST, PORT)
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())

