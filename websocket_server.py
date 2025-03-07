import asyncio
import json
import uuid
import logging
import threading
import websockets
from prompt_expansion import expand_prompt, load_wildcards
from config_manager import load_config

# Global variables (will be reset on server start)
total_prompts_sent = 0
prompt_tracking = {}  # prompt_id -> last logged status
connected_clients = set()
stop_event = None
server_thread = None  # Exposed for UI use
loop = None

# Load settings and wildcards
settings = load_config()
MESSAGE_SEND_DELAY = settings.get("MessageSendDelay", 5)
MAX_CONCURRENT_PROMPTS = settings.get("MaxConcurrentPrompts", 3)
STOP_AFTER = settings.get("StopAfter", 20)
ENABLE_STOP_AFTER = settings.get("EnableStopAfter", True)
WILDCARD_DIR = settings.get("WildcardDirectory", "wildcards")
wildcards = load_wildcards(WILDCARD_DIR)
RECURSION_DEPTH = 5  # Can be made configurable

logger = logging.getLogger("Minerva")

async def handler(websocket, path=None):
    logger.info(f"Minerva: New client connected: {websocket.remote_address}")
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            logger.info(f"Minerva: Received message from client: {message}")
            try:
                data = json.loads(message)
                prompt_id = data.get("prompt_id")
                status = data.get("status")
                if prompt_id:
                    if prompt_tracking.get(prompt_id) != status:
                        prompt_tracking[prompt_id] = status
                        logger.info(f"Minerva: Updated prompt {prompt_id} status to {status}")
            except Exception as e:
                logger.error("Minerva: Error processing client message: " + str(e))
    except websockets.ConnectionClosed:
        logger.info("Minerva: Client disconnected")
    finally:
        connected_clients.remove(websocket)

async def prompt_generator(prompt_templates):
    global total_prompts_sent, prompt_tracking
    while not stop_event.is_set():
        if ENABLE_STOP_AFTER and total_prompts_sent >= STOP_AFTER:
            logger.info("Minerva: StopAfter limit reached. Stopping prompt generation.")
            stop_event.set()
            break
        while not connected_clients and not stop_event.is_set():
            await asyncio.sleep(0.5)
        while len([s for s in prompt_tracking.values() if s != "progress_complete"]) >= MAX_CONCURRENT_PROMPTS and not stop_event.is_set():
            await asyncio.sleep(0.5)
        template = prompt_templates[0]  # For simplicity, using the first template.
        prompt_text = expand_prompt(template, wildcards, depth=RECURSION_DEPTH)
        prompt_id = str(uuid.uuid4())
        data = {"prompt_id": prompt_id, "text": prompt_text}
        json_data = json.dumps(data)
        logger.info(f"Minerva: Generated prompt: {json_data}")
        try:
            await asyncio.gather(*(client.send(json_data) for client in connected_clients))
            logger.info("Minerva: Prompt sent to clients.")
            prompt_tracking[prompt_id] = "sent"
            total_prompts_sent += 1
        except Exception as e:
            logger.error("Minerva: Error sending prompt: " + str(e))
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=MESSAGE_SEND_DELAY)
        except asyncio.TimeoutError:
            continue

async def run_server(prompt_templates):
    global stop_event
    stop_event = asyncio.Event()
    server = await websockets.serve(handler, "localhost", 8080)
    logger.info("Minerva: WebSocket server started on ws://localhost:8080")
    prompt_task = asyncio.create_task(prompt_generator(prompt_templates))
    await stop_event.wait()
    prompt_task.cancel()
    server.close()
    await server.wait_closed()
    logger.info("Minerva: WebSocket server stopped.")

def start_asyncio_server(prompt_templates):
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_server(prompt_templates))
    except Exception as e:
        logger.error("Minerva: Server error: " + str(e))
    finally:
        loop.close()

def start_websocket_server(prompt_templates):
    global server_thread, total_prompts_sent, prompt_tracking
    total_prompts_sent = 0
    prompt_tracking.clear()
    if server_thread is None or not server_thread.is_alive():
        logger.info("Minerva: Starting server...")
        server_thread = threading.Thread(target=start_asyncio_server, args=(prompt_templates,), daemon=True)
        server_thread.start()

def stop_server():
    global stop_event, loop
    if stop_event and loop:
        try:
            loop.call_soon_threadsafe(stop_event.set)
            logger.info("Minerva: Stop signal sent to server.")
        except Exception as e:
            logger.error("Minerva: Error stopping server: " + str(e))
