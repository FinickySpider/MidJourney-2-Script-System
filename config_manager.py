import configparser
import json
import os

CONFIG_FILE = "config.ini"
PROMPTS_FILE = "Prompts.json"

def load_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    settings = {}
    settings["PromptTemplate"] = config.get("Settings", "PromptTemplate", fallback="a [STYLE] [TYPE] character")
    settings["MessageSendDelay"] = config.getint("Settings", "MessageSendDelay", fallback=5)
    settings["MaxConcurrentPrompts"] = config.getint("Settings", "MaxConcurrentPrompts", fallback=3)
    settings["StopAfter"] = config.getint("Settings", "StopAfter", fallback=20)
    settings["EnableStopAfter"] = config.getboolean("Settings", "EnableStopAfter", fallback=True)
    settings["WildcardDirectory"] = config.get("Settings", "WildcardDirectory", fallback="wildcards")
    return settings

def save_config(settings):
    config = configparser.ConfigParser()
    config["Settings"] = {
        "PromptTemplate": settings.get("PromptTemplate", "a [STYLE] [TYPE] character"),
        "MessageSendDelay": str(settings.get("MessageSendDelay", 5)),
        "MaxConcurrentPrompts": str(settings.get("MaxConcurrentPrompts", 3)),
        "StopAfter": str(settings.get("StopAfter", 20)),
        "EnableStopAfter": str(settings.get("EnableStopAfter", True)),
        "WildcardDirectory": settings.get("WildcardDirectory", "wildcards")
    }
    with open(CONFIG_FILE, "w") as f:
        config.write(f)

def load_prompts():
    if os.path.exists(PROMPTS_FILE):
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            prompts = json.load(f)
        if not prompts:
            default = load_config().get("PromptTemplate", "a [STYLE] [TYPE] character")
            return [default]
        return prompts
    else:
        default = load_config().get("PromptTemplate", "a [STYLE] [TYPE] character")
        return [default]

def save_prompts(prompts):
    with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
        json.dump(prompts, f, indent=2)
