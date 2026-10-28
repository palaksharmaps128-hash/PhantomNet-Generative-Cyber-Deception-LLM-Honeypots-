import re
import time
from google import genai
from google.genai import types
from config import API_KEY, MODEL, SYSTEM_PROMPT

client = genai.Client(api_key=API_KEY)
chat = client.chats.create(
    model=MODEL,
    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
)

PROMPT_RE = re.compile(r"^\s*\w+@[\w-]+:.*[#$]\s*$")


def clean(text):
    lines = []
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("```"):
            continue
        if PROMPT_RE.match(line):
            continue
        if s.startswith("$ "):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def ask(cwd, cmd):
    msg = f"[current directory: {cwd}]\n$ {cmd}"
    for attempt in range(6):
        try:
            return (chat.send_message(msg).text or ""), True
        except Exception:
            print(f"[server busy, retry {attempt + 1}/6]")
            time.sleep(4)
    return "bash: fork: retry: Resource temporarily unavailable", False