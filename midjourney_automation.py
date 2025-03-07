#!/usr/bin/env python3
import asyncio
import random
import configparser
import os
import re
import logging
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import uuid
from datetime import datetime
import websockets

# ------------------------------
# Logging Setup: console, Session.log, and prompt tracking log.
# ------------------------------
logger = logging.getLogger("Minerva")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# Console handler
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

# File handler for session logs
fh = logging.FileHandler("Session.log", encoding="utf-8")
fh.setFormatter(formatter)
logger.addHandler(fh)

def log_prompt(prompt_id, message):
    with open("SentPrompts.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} [Prompt {prompt_id}] {message}\n")

# ------------------------------
# Global Config & Variables
# ------------------------------
config = configparser.ConfigParser()
config.read("config.ini")

# Load prompt templates from Prompts.json if available; otherwise, use config value.
PROMPTS_FILE = "Prompts.json"
if os.path.exists(PROMPTS_FILE):
    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        prompt_templates = json.load(f)
    if not prompt_templates:
        prompt_templates = [config.get("Settings", "PromptTemplate", fallback="a [STYLE] [TYPE] character")]
else:
    prompt_templates = [config.get("Settings", "PromptTemplate", fallback="a [STYLE] [TYPE] character")]

current_template_index = 0
current_message_send_delay = config.getint("Settings", "MessageSendDelay", fallback=5)
current_max_concurrent = config.getint("Settings", "MaxConcurrentPrompts", fallback=3)
stop_after = config.getint("Settings", "StopAfter", fallback=20)
enable_stop_after = config.getboolean("Settings", "EnableStopAfter", fallback=True)
WILDCARD_DIR = config.get("Settings", "WildcardDirectory", fallback="wildcards")

total_prompts_sent = 0
prompt_tracking = {}  # prompt_id -> last logged status

server_thread = None
loop = None
stop_event = None

# ------------------------------
# Save prompt list and settings to file.
# ------------------------------
def save_prompts():
    with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
        json.dump(prompt_templates, f, indent=2)

def save_config():
    if not config.has_section("Settings"):
        config.add_section("Settings")
    config.set("Settings", "PromptTemplate", prompt_templates[0] if prompt_templates else "")
    config.set("Settings", "MessageSendDelay", str(current_message_send_delay))
    config.set("Settings", "MaxConcurrentPrompts", str(current_max_concurrent))
    config.set("Settings", "StopAfter", str(stop_after))
    config.set("Settings", "EnableStopAfter", str(enable_stop_after))
    with open("config.ini", "w") as f:
        config.write(f)

# ------------------------------
# Load Wildcards (normalize keys to uppercase)
# ------------------------------
wildcards = {}
for filename in os.listdir(WILDCARD_DIR):
    if filename.endswith(".txt"):
        key = filename[:-4]
        with open(os.path.join(WILDCARD_DIR, filename), "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            wildcards[key.upper()] = lines

# ------------------------------
# Prompt Expansion Function (case- and symbol-insensitive)
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
# Asynchronous WebSocket Server & Prompt Generator
# ------------------------------
connected_clients = set()

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
                        log_prompt(prompt_id, f"Status updated to: {status}")
                        logger.info(f"Minerva: Updated prompt {prompt_id} status to {status}")
            except Exception as e:
                logger.error("Minerva: Error processing client message: " + str(e))
    except websockets.ConnectionClosed:
        logger.info("Minerva: Client disconnected")
    finally:
        connected_clients.remove(websocket)

async def prompt_generator():
    global current_template_index, total_prompts_sent
    while not stop_event.is_set():
        if enable_stop_after and total_prompts_sent >= stop_after:
            logger.info("Minerva: StopAfter limit reached. Stopping prompt generation.")
            stop_event.set()
            break
        while not connected_clients and not stop_event.is_set():
            await asyncio.sleep(0.5)
        while len([s for s in prompt_tracking.values() if s != "progress_complete"]) >= current_max_concurrent and not stop_event.is_set():
            await asyncio.sleep(0.5)
        template = prompt_templates[current_template_index]
        current_template_index = (current_template_index + 1) % len(prompt_templates)
        prompt_text = expand_prompt(template)
        prompt_id = str(uuid.uuid4())
        data = {"prompt_id": prompt_id, "text": prompt_text}
        json_data = json.dumps(data)
        logger.info(f"Minerva: Generated prompt: {json_data}")
        try:
            await asyncio.gather(*(client.send(json_data) for client in connected_clients))
            logger.info("Minerva: Prompt sent to clients.")
            prompt_tracking[prompt_id] = "sent"
            log_prompt(prompt_id, "Prompt sent to client.")
            total_prompts_sent += 1
            save_config()
            save_prompts()
        except Exception as e:
            logger.error("Minerva: Error sending prompt: " + str(e))
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=current_message_send_delay)
        except asyncio.TimeoutError:
            continue

async def run_server():
    global stop_event
    stop_event = asyncio.Event()
    server = await websockets.serve(handler, "localhost", 8080)
    logger.info("Minerva: WebSocket server started on ws://localhost:8080")
    prompt_task = asyncio.create_task(prompt_generator())
    await stop_event.wait()
    prompt_task.cancel()
    server.close()
    await server.wait_closed()
    logger.info("Minerva: WebSocket server stopped.")

def start_asyncio_server():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_server())
    except Exception as e:
        logger.error("Minerva: Server error: " + str(e))
    finally:
        loop.close()

def start_server():
    global server_thread, total_prompts_sent, prompt_tracking
    total_prompts_sent = 0
    prompt_tracking.clear()
    save_config()
    save_prompts()
    if server_thread is None or not server_thread.is_alive():
        logger.info("Minerva: Starting server...")
        server_thread = threading.Thread(target=start_asyncio_server, daemon=True)
        server_thread.start()

def stop_server():
    global stop_event, loop
    if stop_event and loop:
        try:
            loop.call_soon_threadsafe(stop_event.set)
            logger.info("Minerva: Stop signal sent to server.")
        except Exception as e:
            logger.error("Minerva: Error stopping server: " + str(e))

# ------------------------------
# Modular Tkinter UI (Tabbed Notebook)
# ------------------------------
class LogViewer(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.text = scrolledtext.ScrolledText(self, state="disabled", height=15)
        self.text.pack(fill="both", expand=True)
        clear_btn = ttk.Button(self, text="Clear Log", command=self.clear_log)
        clear_btn.pack(side="bottom", pady=5)
    
    def add_log(self, message, tag="info"):
        self.text.config(state="normal")
        colors = {"error": "red", "warning": "darkorange", "info": "blue", "neutral": "gray"}
        color = colors.get(tag, "gray")
        parts = message.split("[Prompt")
        if len(parts) > 1:
            self.text.insert("end", parts[0], tag)
            self.text.insert("end", "[Prompt", "prompt_id")
            self.text.insert("end", parts[1], tag)
        else:
            self.text.insert("end", message + "\n", tag)
        self.text.tag_config(tag, foreground=color)
        self.text.tag_config("prompt_id", foreground="orange")
        self.text.config(state="disabled")
        self.text.yview("end")
    
    def clear_log(self):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.config(state="disabled")

class PromptSettings(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        ttk.Label(self, text="Prompt Templates:").grid(row=0, column=0, sticky="w")
        self.template_list = tk.Listbox(self, height=5)
        self.template_list.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.refresh_listbox()
        self.current_label = ttk.Label(self, text=f"Next Template: {prompt_templates[current_template_index]}", width=40, anchor="w")
        self.current_label.grid(row=2, column=0, columnspan=2, pady=2)
        ttk.Button(self, text="Add", command=self.add_template).grid(row=3, column=0, padx=5, pady=2)
        ttk.Button(self, text="Remove", command=self.remove_template).grid(row=3, column=1, padx=5, pady=2)
        ttk.Button(self, text="Modify", command=self.modify_template).grid(row=4, column=0, padx=5, pady=2)
        ttk.Button(self, text="Cycle Current", command=self.cycle_current).grid(row=4, column=1, padx=5, pady=2)
        ttk.Label(self, text="MessageSendDelay (sec):").grid(row=5, column=0, sticky="w", padx=5)
        self.delay_var = tk.StringVar(value=str(current_message_send_delay))
        ttk.Entry(self, textvariable=self.delay_var).grid(row=5, column=1, sticky="ew", padx=5)
        ttk.Label(self, text="MaxConcurrentPrompts:").grid(row=6, column=0, sticky="w", padx=5)
        self.max_var = tk.StringVar(value=str(current_max_concurrent))
        ttk.Entry(self, textvariable=self.max_var).grid(row=6, column=1, sticky="ew", padx=5)
        ttk.Label(self, text="StopAfter (total prompts):").grid(row=7, column=0, sticky="w", padx=5)
        self.stop_after_var = tk.StringVar(value=str(stop_after))
        ttk.Entry(self, textvariable=self.stop_after_var).grid(row=7, column=1, sticky="ew", padx=5)
        self.enable_stop_var = tk.BooleanVar(value=enable_stop_after)
        ttk.Checkbutton(self, text="Enable StopAfter", variable=self.enable_stop_var).grid(row=8, column=0, columnspan=2, pady=2)
        ttk.Button(self, text="Save Settings", command=self.save_settings).grid(row=9, column=0, columnspan=2, pady=5)
        ttk.Button(self, text="Generate Example Prompts", command=self.generate_examples).grid(row=10, column=0, columnspan=2, pady=5)
    
    def refresh_listbox(self):
        self.template_list.delete(0, "end")
        for tmpl in prompt_templates:
            self.template_list.insert("end", tmpl)
    
    def add_template(self):
        new_tmpl = self.simple_prompt("Enter new prompt template:")
        if new_tmpl:
            prompt_templates.append(new_tmpl)
            self.refresh_listbox()
            save_prompts()
    
    def remove_template(self):
        selection = self.template_list.curselection()
        if selection:
            index = selection[0]
            del prompt_templates[index]
            self.refresh_listbox()
            save_prompts()
    
    def modify_template(self):
        selection = self.template_list.curselection()
        if selection:
            index = selection[0]
            current = prompt_templates[index]
            new_val = self.simple_prompt("Modify prompt template:", initial=current)
            if new_val:
                prompt_templates[index] = new_val
                self.refresh_listbox()
                save_prompts()
    
    def cycle_current(self):
        global current_template_index
        current_template_index = (current_template_index + 1) % len(prompt_templates)
        self.current_label.config(text=f"Next Template: {prompt_templates[current_template_index]}")
    
    def save_settings(self):
        global current_message_send_delay, current_max_concurrent, stop_after, enable_stop_after
        try:
            current_message_send_delay = int(self.delay_var.get())
            current_max_concurrent = int(self.max_var.get())
            stop_after_new = int(self.stop_after_var.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid integers for settings.")
            return
        enable_stop_after = self.enable_stop_var.get()
        stop_after = stop_after_new
        if not config.has_section("Settings"):
            config.add_section("Settings")
        config.set("Settings", "PromptTemplate", prompt_templates[0] if prompt_templates else "")
        config.set("Settings", "MessageSendDelay", str(current_message_send_delay))
        config.set("Settings", "MaxConcurrentPrompts", str(current_max_concurrent))
        config.set("Settings", "StopAfter", str(stop_after))
        config.set("Settings", "EnableStopAfter", str(enable_stop_after))
        with open("config.ini", "w") as f:
            config.write(f)
        app.log_viewer.add_log("Settings updated.", "info")
    
    def generate_examples(self):
        examples = []
        for i in range(5):
            examples.append(expand_prompt(prompt_templates[current_template_index]))
        example_text = "\n".join(examples)
        messagebox.showinfo("Example Prompts", example_text)
    
    def simple_prompt(self, prompt, initial=""):
        from tkinter.simpledialog import askstring
        return askstring("Input", prompt, initialvalue=initial)

class LogHandler(logging.Handler):
    def __init__(self, log_viewer):
        super().__init__()
        self.log_viewer = log_viewer
    
    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelno
            if level >= logging.ERROR:
                tag = "error"
            elif level >= logging.WARNING:
                tag = "warning"
            elif level >= logging.INFO:
                tag = "info"
            else:
                tag = "neutral"
            self.log_viewer.add_log(msg, tag)
        except Exception:
            self.handleError(record)

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MidJourney Automation UI")
        self.geometry("600x500")
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self.prompt_settings = PromptSettings(self.notebook)
        self.notebook.add(self.prompt_settings, text="Prompt Settings")
        self.log_viewer = LogViewer(self.notebook)
        self.notebook.add(self.log_viewer, text="Logs & Debugging")
        # Status Panel with counters
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", padx=10, pady=5)
        self.status_label = ttk.Label(status_frame, text="Server OFF", font=("Arial", 12), width=20, anchor="w")
        self.status_label.pack(side="left")
        # New prompt counters:
        self.prompt_counter_label = ttk.Label(status_frame, text="Prompts: 0", width=15, anchor="w")
        self.prompt_counter_label.pack(side="left", padx=5)
        self.concurrent_label = ttk.Label(status_frame, text="Concurrent: 0/{}".format(current_max_concurrent), width=15, anchor="w")
        self.concurrent_label.pack(side="left", padx=5)
        control_frame = ttk.Frame(status_frame)
        control_frame.pack(side="right")
        ttk.Button(control_frame, text="ON", command=self.start_server).pack(side="left", padx=5)
        ttk.Button(control_frame, text="OFF", command=self.stop_server).pack(side="left", padx=5)
        lh = LogHandler(self.log_viewer)
        lh.setFormatter(formatter)
        logger.addHandler(lh)
        self.after(500, self.periodic_update)
    
    def start_server(self):
        start_server()
        self.status_label.config(text="Server ON", foreground="green")
        self.log_viewer.add_log("Server started.", "info")
    
    def stop_server(self):
        stop_server()
        self.status_label.config(text="Server OFF", foreground="red")
        self.log_viewer.add_log("Server stopped.", "info")
    
    def periodic_update(self):
        # Update prompt counter and concurrent counter.
        self.prompt_counter_label.config(text="Prompts: {}".format(total_prompts_sent))
        concurrent = len([s for s in prompt_tracking.values() if s != "progress_complete"])
        self.concurrent_label.config(text="Concurrent: {}/{}".format(concurrent, current_max_concurrent))
        # Also, if server thread is not alive, update status.
        if server_thread is None or not server_thread.is_alive():
            self.status_label.config(text="Server OFF", foreground="red")
        self.after(500, self.periodic_update)

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
