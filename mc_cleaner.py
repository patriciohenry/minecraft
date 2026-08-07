import asyncio
import json
import uuid
import sys
import logging
import websockets

# Configure logging for Render console visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

HOST = "0.0.0.0"
PORT = 3000

# Base target list for silent disposal
SILENT_MOBS = ["zombie", "husk", "drowned", "zombie_villager"]
tracked_requests = {}

def generate_command_packet(cmd_string):
    """Encapsulates raw commands into Bedrock structural JSON protocol packets."""
    req_id = str(uuid.uuid4())
    return req_id, {
        "header": {
            "version": 1,
            "requestId": req_id,
            "messageType": "commandRequest",
            "purpose": "commandRequest"
        },
        "body": {
            "version": 1,
            "commandLine": cmd_string,
            "origin": {"type": "player"}
        }
    }

async def response_listener(websocket):
    """Listens to execution receipts from the game client."""
    try:
        async for message in websocket:
            packet = json.loads(message)
            header = packet.get("header", {})
            req_id = header.get("requestId")
            
            if req_id in tracked_requests:
                mob_type = tracked_requests.pop(req_id)
                body = packet.get("body", {})
                status_msg = body.get("statusMessage", "")
                
                if "Killed" in status_msg or "Murió" in status_msg or body.get("statusCode") == 0:
                    await handle_special_kill(websocket, mob_type)
                    
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        logging.error(f"Error in response listener thread: {e}")

async def handle_special_kill(websocket, mob_type):
    """Dispatches targeted sound packets and chat announcements globally."""
    if mob_type == "creeper":
        chat_cmd = "/say [Daemon] ALERT: A hidden Creeper was vaporized nearby!"
        sound_cmd = "/playsound minecraft:block.anvil.land ambient @a ~ ~ ~ 1.0 1.5"
    elif mob_type == "enderman":
        chat_cmd = "/say [Daemon] ALERT: An Enderman tried to stalk you, but was deleted!"
        sound_cmd = "/playsound minecraft:entity.enderman.teleport ambient @a ~ ~ ~ 1.0 1.0"
    else:
        return

    logging.info(f"Special entity triggered: {mob_type}.")
    _, chat_packet = generate_command_packet(chat_cmd)
    _, sound_packet = generate_command_packet(sound_cmd)
    
    await websocket.send(json.dumps(chat_packet))
    await websocket.send(json.dumps(sound_packet))

async def sweep_loop(websocket):
    """Continuously runs global sweeps across the active chunks."""
    try:
        while True:
            # 1. Sweep standard silent hostile targets
            for mob in SILENT_MOBS:
                _, packet = generate_command_packet(f"/kill @e[type={mob}]")
                await websocket.send(json.dumps(packet))
            
            # 2. Sweep special target tracking requests (Creeper)
            req_id_c, packet_c = generate_command_packet("/kill @e[type=creeper]")
            tracked_requests[req_id_c] = "creeper"
            await websocket.send(json.dumps(packet_c))
            
            # 3. Sweep special target tracking requests (Enderman)
            req_id_e, packet_e = generate_command_packet("/kill @e[type=enderman]")
            tracked_requests[req_id_e] = "enderman"
            await websocket.send(json.dumps(packet_e))
            
            await asyncio.sleep(2.0)
            
    except websockets.exceptions.ConnectionClosed:
        pass

async def minecraft_handler(websocket, path=None):
    peer_address = websocket.remote_address
    logging.info(f"Handshake initiated with client: {peer_address}")
    
    try:
        _, rule1 = generate_command_packet("/gamerule commandBlockOutput false")
        _, rule2 = generate_command_packet("/gamerule sendCommandFeedback false")
        await websocket.send(json.dumps(rule1))
        await websocket.send(json.dumps(rule2))
        
        _, welcome = generate_command_packet("/say [Python Daemon]: Operational. Sound alerts active.")
        await websocket.send(json.dumps(welcome))

        await asyncio.gather(
            sweep_loop(websocket),
            response_listener(websocket)
        )
            
    except Exception as e:
        logging.error(f"Execution error on socket {peer_address}: {e}", exc_info=True)
    finally:
        logging.info(f"Socket session terminated for client {peer_address}")

async def main():
    logging.info(f"Booting Production Bedrock Websocket Daemon on ws://{HOST}:{PORT}")
    async with websockets.serve(minecraft_handler, HOST, PORT):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("SIGINT signal intercepted. Graceful termination complete.")
        sys.exit(0)

