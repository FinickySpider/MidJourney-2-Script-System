import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from config_manager import load_config, save_config, load_prompts, save_prompts
from logging_setup import setup_logger
import threading
import websocket_server  # our websocket server module

# Load settings and prompt templates
settings = load_config()
prompt_templates = load_prompts()

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
        self.current_label = ttk.Label(self, text=f"Next Template: {prompt_templates[0]}", width=40, anchor="w")
        self.current_label.grid(row=2, column=0, columnspan=2, pady=2)
        ttk.Button(self, text="Add", command=self.add_template).grid(row=3, column=0, padx=5, pady=2)
        ttk.Button(self, text="Remove", command=self.remove_template).grid(row=3, column=1, padx=5, pady=2)
        ttk.Button(self, text="Modify", command=self.modify_template).grid(row=4, column=0, padx=5, pady=2)
        ttk.Button(self, text="Cycle Current", command=self.cycle_current).grid(row=4, column=1, padx=5, pady=2)
        ttk.Label(self, text="MessageSendDelay (sec):").grid(row=5, column=0, sticky="w", padx=5)
        self.delay_var = tk.StringVar(value=str(settings.get("MessageSendDelay", 5)))
        ttk.Entry(self, textvariable=self.delay_var).grid(row=5, column=1, sticky="ew", padx=5)
        ttk.Label(self, text="MaxConcurrentPrompts:").grid(row=6, column=0, sticky="w", padx=5)
        self.max_var = tk.StringVar(value=str(settings.get("MaxConcurrentPrompts", 3)))
        ttk.Entry(self, textvariable=self.max_var).grid(row=6, column=1, sticky="ew", padx=5)
        ttk.Label(self, text="StopAfter (total prompts):").grid(row=7, column=0, sticky="w", padx=5)
        self.stop_after_var = tk.StringVar(value=str(settings.get("StopAfter", 20)))
        ttk.Entry(self, textvariable=self.stop_after_var).grid(row=7, column=1, sticky="ew", padx=5)
        self.enable_stop_var = tk.BooleanVar(value=settings.get("EnableStopAfter", True))
        ttk.Checkbutton(self, text="Enable StopAfter", variable=self.enable_stop_var).grid(row=8, column=0, columnspan=2, pady=2)
        ttk.Button(self, text="Save Settings", command=self.save_settings).grid(row=9, column=0, columnspan=2, pady=5)
        ttk.Button(self, text="Generate Example Prompts", command=self.generate_examples).grid(row=10, column=0, columnspan=2, pady=5)
    
    def refresh_listbox(self):
        self.template_list.delete(0, "end")
        for tmpl in prompt_templates:
            self.template_list.insert("end", tmpl)
    
    def add_template(self):
        from tkinter.simpledialog import askstring
        new_tmpl = askstring("Input", "Enter new prompt template:")
        if new_tmpl:
            prompt_templates.append(new_tmpl)
            self.refresh_listbox()
            save_prompts(prompt_templates)
    
    def remove_template(self):
        selection = self.template_list.curselection()
        if selection:
            index = selection[0]
            del prompt_templates[index]
            self.refresh_listbox()
            save_prompts(prompt_templates)
    
    def modify_template(self):
        from tkinter.simpledialog import askstring
        selection = self.template_list.curselection()
        if selection:
            index = selection[0]
            current = prompt_templates[index]
            new_val = askstring("Input", "Modify prompt template:", initialvalue=current)
            if new_val:
                prompt_templates[index] = new_val
                self.refresh_listbox()
                save_prompts(prompt_templates)
    
    def cycle_current(self):
        global prompt_templates
        current_index = self.template_list.curselection()
        if current_index:
            idx = current_index[0]
        else:
            idx = 0
        idx = (idx + 1) % len(prompt_templates)
        self.template_list.select_clear(0, "end")
        self.template_list.select_set(idx)
        self.current_label.config(text=f"Next Template: {prompt_templates[idx]}")
    
    def save_settings(self):
        global settings
        try:
            settings["MessageSendDelay"] = int(self.delay_var.get())
            settings["MaxConcurrentPrompts"] = int(self.max_var.get())
            settings["StopAfter"] = int(self.stop_after_var.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid integers for settings.")
            return
        settings["EnableStopAfter"] = self.enable_stop_var.get()
        save_config(settings)
        # Instead of using 'app', we use self.master.master to access MainApp's log_viewer.
        self.master.master.log_viewer.add_log("Settings updated.", "info")
    
    def generate_examples(self):
        from prompt_expansion import expand_prompt, load_wildcards
        wildcards = load_wildcards(settings.get("WildcardDirectory", "wildcards"))
        examples = []
        for i in range(5):
            examples.append(expand_prompt(prompt_templates[0], wildcards, depth=5))
        example_text = "\n".join(examples)
        messagebox.showinfo("Example Prompts", example_text)

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MJ-Control")
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
        self.prompt_counter_label = ttk.Label(status_frame, text="Prompts: 0", width=15, anchor="w")
        self.prompt_counter_label.pack(side="left", padx=5)
        self.concurrent_label = ttk.Label(status_frame, text="Concurrent: 0/{}".format(settings.get("MaxConcurrentPrompts", 3)), width=15, anchor="w")
        self.concurrent_label.pack(side="left", padx=5)
        control_frame = ttk.Frame(status_frame)
        control_frame.pack(side="right")
        ttk.Button(control_frame, text="ON", command=self.start_server).pack(side="left", padx=5)
        ttk.Button(control_frame, text="OFF", command=self.stop_server).pack(side="left", padx=5)
        setup_logger(self.log_viewer)
        self.after(500, self.periodic_update)
    
    def start_server(self):
        threading.Thread(target=lambda: websocket_server.start_websocket_server(prompt_templates),
                         daemon=True).start()
        self.status_label.config(text="Server ON", foreground="green")
        self.log_viewer.add_log("Server started.", "info")
    
    def stop_server(self):
        websocket_server.stop_server()
        self.status_label.config(text="Server OFF", foreground="red")
        self.log_viewer.add_log("Server stopped.", "info")
    
    def periodic_update(self):
        self.prompt_counter_label.config(text="Prompts: {}".format(websocket_server.total_prompts_sent))
        concurrent = len([s for s in websocket_server.prompt_tracking.values() if s != "progress_complete"])
        self.concurrent_label.config(text="Concurrent: {}/{}".format(concurrent, settings.get("MaxConcurrentPrompts", 3)))
        if websocket_server.server_thread is None or not websocket_server.server_thread.is_alive():
            self.status_label.config(text="Server OFF", foreground="red")
        self.after(500, self.periodic_update)
