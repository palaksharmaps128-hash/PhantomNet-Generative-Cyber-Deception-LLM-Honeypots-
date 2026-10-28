from config import HOSTNAME, START_DIR
from logger import log_event
from llm_engine import ask, clean
from shell import do_cd

cwd = START_DIR
print(f"Ubuntu 22.04.3 LTS {HOSTNAME} tty1\n")

while True:
    try:
        shown = "~" if cwd == "/root" else cwd
        cmd = input(f"root@{HOSTNAME}:{shown}# ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        break
    if cmd in ("exit", "logout"):
        log_event(cwd, cmd, "", "python")
        break
    if not cmd:
        continue
    if cmd.split()[0] == "cd":
        old_cwd = cwd
        cwd, err = do_cd(cmd, cwd)
        if err:
            print(err)
        log_event(old_cwd, cmd, err, "python")
        continue
    if cmd == "pwd":
        print(cwd)
        log_event(cwd, cmd, cwd, "python")
        continue
    raw, ok = ask(cwd, cmd)
    out = clean(raw)
    if out:
        print(out)
    log_event(cwd, cmd, out, "llm" if ok else "llm-error")