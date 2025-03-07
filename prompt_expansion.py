import os
import re
import random

def load_wildcards(wildcard_dir):
    wildcards = {}
    for filename in os.listdir(wildcard_dir):
        if filename.endswith(".txt"):
            key = filename[:-4]
            with open(os.path.join(wildcard_dir, filename), "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                wildcards[key.upper()] = lines
    return wildcards

def expand_prompt(template, wildcards, depth=5):
    if depth <= 0:
        return template
    pattern = r"\[([^\]]+)\]"
    def replace(match):
        key = match.group(1).upper()
        if key in wildcards:
            replacement = random.choice(wildcards[key])
            return expand_prompt(replacement, wildcards, depth-1)
        else:
            return match.group(0)
    return re.sub(pattern, replace, template)
