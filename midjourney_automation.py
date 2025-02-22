#!/usr/bin/env python3
import asyncio
import random
import configparser
import os
import re
import logging
import threading
import tkinter as tk
from tkinter import ttk
import websockets
import json
import uuid

# ------------------------------
# Global Variables & Configuration
# ------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
config = configparser.ConfigParser()
config.read("config.ini")

# Global configuration values (from config.ini)
current_prompt_template = config.get("Settings", "PromptTemplate", fallback="a [STYLE] [TYPE] character")
current_message_send_delay = config.getint("Settings", "MessageSendDelay", fallback=5)
current_max_concurrent = config.getint("Settings", "MaxConcurrentPrompts", fallback=3)
WILDCARD_DIR = config.get("Settings", "WildcardDirectory", fallback="wildcards")

# Global objects for asyncio server control
server_thread = None
loop = None
stop_event = None

# Dictionary to track prompts by id. Values: one of "sent", "input_complete", "progress_complete"
prompt_tracking = {}

# ------------------------------
# Load Wildcards
# ------------------------------
wildcards = {}
for filename in os.listdir(WILDCARD_DIR):
    if filename.endswith(".txt"):
        key = filename[:-4]  # remove .txt extension
        with open(os.path.join(WILDCARD_DIR, filename), "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            wildcards[key.upper()] = lines  # normalize keys to uppercase

# ------------------------------
# Prompt Expansion Function (allow any characters inside [ ... ])
# ------------------------------
RECURSION_DEPTH = config.getint("Settings", "RecursionDepth", fallback=5)
def expand_prompt(template, depth=RECURSION_DEPTH):
    if depth <= 0:
        return template
    pattern = r"\[([^\]]+)\]"
    def replace(match):
        key = match.group(1).upper()
        if key in wildcards:
            replacement = random.choice(wildcards[key])
            return expand_prompt(replacement, depth-1)
        else:
            return match.group(0)
    return re.sub(pattern, replace, template)

# ------------------------------
# WebSocket Server Code (Async)
# ------------------------------
connected_clients = set()

async def handler(websocket, path):
    logging.info(f"Minerva: New client connected: {websocket.remote_address}")
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            logging.info(f"Minerva: Received message from client: {message}")
            try:
                data = json.loads(message)
                prompt_id = data.get("prompt_id")
                status = data.get("status")
                if prompt_id:
                    prompt_tracking[prompt_id] = status
                    logging.info(f"Minerva: Updated prompt {prompt_id} status to {status}")
            except Exception as e:
                logging.error("Minerva: Error processing client message: " + str(e))
    except websockets.ConnectionClosed:
        logging.info("Minerva: Client disconnected")
    finally:
        connected_clients.remove(websocket)

async def prompt_generator():
    global current_prompt_template, current_message_send_delay, current_max_concurrent, prompt_tracking
    while not stop_event.is_set():
        # Wait until at least one client is connected
        while not connected_clients and not stop_event.is_set():
            await asyncio.sleep(0.5)
        # Wait until concurrent prompts is below max limit
        while len([s for s in prompt_tracking.values() if s != "progress_complete"]) >= current_max_concurrent and not stop_event.is_set():
            await asyncio.sleep(0.5)
        # Generate new prompt and assign a unique id
        prompt_text = expand_prompt(current_prompt_template)
        prompt_id = str(uuid.uuid4())
        data = {"prompt_id": prompt_id, "text": prompt_text}
        json_data = json.dumps(data)
        logging.info(f"Minerva: Generated prompt: {json_data}")
        try:
            await asyncio.gather(*(client.send(json_data) for client in connected_clients))
            logging.info("Minerva: Prompt sent to clients.")
            prompt_tracking[prompt_id] = "sent"
        except Exception as e:
            logging.error("Minerva: Error sending prompt: " + str(e))
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=current_message_send_delay)
        except asyncio.TimeoutError:
            continue

async def run_server():
    global stop_event
    stop_event = asyncio.Event()
    server = await websockets.serve(handler, "localhost", 8080)
    logging.info("Minerva: WebSocket server started on ws://localhost:8080")
    prompt_task = asyncio.create_task(prompt_generator())
    await stop_event.wait()
    prompt_task.cancel()
    server.close()
    await server.wait_closed()
    logging.info("Minerva: WebSocket server stopped.")

def start_asyncio_server():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_server())
    except Exception as e:
        logging.error("Minerva: Server error: " + str(e))
    finally:
        loop.close()

def start_server():
    global server_thread
    if server_thread is None or not server_thread.is_alive():
        logging.info("Minerva: Starting server...")
        server_thread = threading.Thread(target=start_asyncio_server, daemon=True)
        server_thread.start()

def stop_server():
    global stop_event, loop
    if stop_event and loop:
        loop.call_soon_threadsafe(stop_event.set)
        logging.info("Minerva: Stop signal sent to server.")

# ------------------------------
# Tkinter UI Code
# ------------------------------
def update_config():
    global current_prompt_template, current_message_send_delay, current_max_concurrent
    new_template = prompt_template_var.get()
    try:
        new_delay = int(message_delay_var.get())
    except ValueError:
        status_label.config(text="MessageSendDelay must be an integer!", foreground="red")
        return
    try:
        new_max_concurrent = int(max_concurrent_var.get())
    except ValueError:
        status_label.config(text="MaxConcurrentPrompts must be an integer!", foreground="red")
        return
    current_prompt_template = new_template
    current_message_send_delay = new_delay
    current_max_concurrent = new_max_concurrent
    if not config.has_section("Settings"):
        config.add_section("Settings")
    config.set("Settings", "PromptTemplate", new_template)
    config.set("Settings", "MessageSendDelay", str(new_delay))
    config.set("Settings", "MaxConcurrentPrompts", str(new_max_concurrent))
    with open("config.ini", "w") as configfile:
        config.write(configfile)
    status_label.config(text="Config updated!", foreground="green")
    logging.info("Minerva: Config updated via UI.")

root = tk.Tk()
root.title("MidJourney Automation UI")
root.geometry("400x300")

status_frame = ttk.Frame(root)
status_frame.pack(pady=10)
status_label = ttk.Label(status_frame, text="Server OFF", font=("Arial", 12))
status_label.pack()

control_frame = ttk.Frame(root)
control_frame.pack(pady=10)
def on_start():
    start_server()
    status_label.config(text="Server ON", foreground="green")
def on_stop():
    stop_server()
    status_label.config(text="Server OFF", foreground="red")
start_button = ttk.Button(control_frame, text="ON", command=on_start)
start_button.grid(row=0, column=0, padx=5)
stop_button = ttk.Button(control_frame, text="OFF", command=on_stop)
stop_button.grid(row=0, column=1, padx=5)

config_frame = ttk.Frame(root)
config_frame.pack(pady=10, fill="x", padx=10)
ttk.Label(config_frame, text="PromptTemplate:").grid(row=0, column=0, sticky="w")
prompt_template_var = tk.StringVar(value=current_prompt_template)
prompt_template_entry = ttk.Entry(config_frame, textvariable=prompt_template_var, width=40)
prompt_template_entry.grid(row=0, column=1, padx=5, pady=5)
ttk.Label(config_frame, text="MessageSendDelay (sec):").grid(row=1, column=0, sticky="w")
message_delay_var = tk.StringVar(value=str(current_message_send_delay))
message_delay_entry = ttk.Entry(config_frame, textvariable=message_delay_var, width=40)
message_delay_entry.grid(row=1, column=1, padx=5, pady=5)
ttk.Label(config_frame, text="MaxConcurrentPrompts:").grid(row=2, column=0, sticky="w")
max_concurrent_var = tk.StringVar(value=str(current_max_concurrent))
max_concurrent_entry = ttk.Entry(config_frame, textvariable=max_concurrent_var, width=40)
max_concurrent_entry.grid(row=2, column=1, padx=5, pady=5)
save_button = ttk.Button(root, text="Save Config", command=update_config)
save_button.pack(pady=10)
root.mainloop()
