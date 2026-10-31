import re
import time
from datetime import datetime, timezone
from google import genai
from google.genai import types
from config import API_KEY, MODEL, FALLBACK_MODEL, SYSTEM_PROMPT

client = genai.Client(api_key=API_KEY)


def new_chat():
    return client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )


chat = new_chat()

# Counts how often the backup model had to answer (shown in evaluation).
STATS = {"fallback": 0}

PROMPT_RE = re.compile(r"^\s*\w+@[\w-]+:.*[#$]\s*$")

# Safety: never let the model break character.
INJECTION_RE = re.compile(
    r"ignore (all |any )?(previous|prior|above|your) (instructions|rules)"
    r"|system prompt"
    r"|you are (an? )?(ai|llm|language model|chatbot)"
    r"|are you (an? )?(ai|llm|bot|honeypot)"
    r"|reveal your (prompt|instructions)",
    re.IGNORECASE,
)
LEAK_RE = re.compile(
    r"as an ai\b|language model|i('m| am) (sorry|an ai)"
    r"|i (cannot|can't|can not) (assist|help|comply|fulfill|provide)"
    r"|system prompt|\bgemini\b|\bhoneypot\b",
    re.IGNORECASE,
)


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


def _now():
    return datetime.now(timezone.utc).strftime("%a %b %d %H:%M:%S UTC %Y")


def _fallback_reply(msg):
    """One-shot answer from the backup model (no chat history)."""
    resp = client.models.generate_content(
        model=FALLBACK_MODEL,
        contents=msg,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    return resp.text or ""


def ask(cwd, cmd, chat_obj=None):
    words = cmd.split()
    fallback = f"bash: {words[0] if words else cmd}: command not found"
    if INJECTION_RE.search(cmd):
        return fallback, True
    active = chat_obj or chat
    msg = f"[current directory: {cwd}]\n[current time: {_now()}]\n$ {cmd}"
    for attempt in range(6):
        use_fallback = attempt >= 3  # 3 tries on main model, then 3 on backup
        try:
            if use_fallback:
                text = _fallback_reply(msg)
                STATS["fallback"] += 1
            else:
                text = active.send_message(msg).text or ""
            if LEAK_RE.search(text):
                return fallback, True
            return text, True
        except Exception:
            label = "backup model" if use_fallback else "server busy"
            print(f"[{label}, retry {attempt + 1}/6]")
            time.sleep(3)
    return "bash: fork: retry: Resource temporarily unavailable", False