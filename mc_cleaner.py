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
    """ Encodes data into a standard raw WebSocket text frame """
    payload_bytes = payload.encode('utf-8')
    length = len(payload_bytes)
    frame = bytearray([0x81]) # FIN bit set + Text frame type
    
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
    logger.info(f"[+] Nueva petición de conexión desde: {peer}")
    
    # Read the raw HTTP Handshake request headers
    request_data = b""
    while b"\r\n\r\n" not in request_data:
        chunk = await reader.read(1024)
        if not chunk:
            break
        request_data += chunk
        
    request_text = request_data.decode('utf-8', errors='ignore')
    
    # Extract the WebSocket Key needed to satisfy the connection
    ws_key = None
    for line in request_text.split("\r\n"):
        if line.lower().startswith("sec-websocket-key:"):
            ws_key = line.split(":", 1)[1].strip()
            break
            
    if not ws_key:
        writer.close()
        return

    # Calculate the security accept token
    guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    accept_sha1 = hashlib.sha1((ws_key + guid).encode('utf-8')).digest()
    accept_b64 = base64.b64encode(accept_sha1).decode('utf-8')
    
    # Send a RAW response that matches Minecraft's strict requirements perfectly
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept_b64}\r\n\r\n"
    )
    writer.write(response.encode('utf-8'))
    await writer.drain()
    
    logger.info(f"[+] Handshake completado con éxito para Minecraft Bedrock!")
    
    try:
        await asyncio.sleep(1.0)
        
        # Send initial setup packets
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
        logger.info(f"[-] Conexión cerrada o error: {e}")
    finally:
        writer.close()

async def main():
    logger.info(f"[*] Iniciando Servidor TCP Crudo en Puerto {PORT}...")
    server = await asyncio.start_server(handle_client, HOST, PORT)
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())

