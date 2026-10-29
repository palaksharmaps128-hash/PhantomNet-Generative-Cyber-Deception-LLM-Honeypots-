import re

SEVERITY = {
    "destructive": "critical",
    "exfiltration": "high",
    "malware_download": "high",
    "persistence": "high",
    "privilege_escalation": "high",
    "credential_access": "medium",
    "recon": "low",
    "other": "info",
}

RULES = [
    ("destructive", [
        r"\brm\s+-[a-z]*[rf]",
        r"\bmkfs",
        r"\bdd\s+if=",
        r"\bshred\b",
        r":\(\)\s*\{",
        r">\s*/dev/sd",
        r"\bdrop\s+(database|table)\b",
        r"\b(shutdown|reboot|halt|poweroff)\b",
        r"\b(killall|pkill)\b",
        r"chmod\s+-R\s+777\s+/",
    ]),
    ("exfiltration", [
        r"\b(scp|rsync|sftp|ftp|nc|ncat|netcat)\b",
        r"\bpg_dump(all)?\b",
        r"curl\b.*(\s-T\b|--upload-file|\s-F\b)",
    ]),
    ("malware_download", [
        r"\b(wget|curl|tftp)\b",
        r"chmod\s+\+x",
        r"\|\s*(ba)?sh\b",
    ]),
    ("persistence", [
        r"\bcrontab\b",
        r"/etc/cron",
        r"authorized_keys",
        r"\.bashrc",
        r"\.profile\b",
        r"rc\.local",
        r"systemctl\s+enable",
        r"\b(useradd|adduser)\b",
        r"/etc/systemd",
        r"\bnohup\b",
    ]),
    ("credential_access", [
        r"/etc/(passwd|shadow)",
        r"\.ssh\b",
        r"id_rsa",
        r"\.pgpass",
        r"pg_hba\.conf",
        r"\.env\b",
        r"\.bash_history",
        r"\bhistory\b",
        r"password",
        r"credential",
        r"\.aws",
        r"secret",
    ]),
    ("privilege_escalation", [
        r"\bsudo\b",
        r"\bsu\b",
        r"\bpasswd\b",
        r"chmod\s+(\+s|u\+s|[2467][0-7]{3})\b",
        r"/etc/sudoers",
        r"\bvisudo\b",
        r"\busermod\b",
        r"\bgetcap\b",
        r"find\s+/.*-perm",
    ]),
]

COMPILED = [
    (category, [re.compile(p, re.IGNORECASE) for p in patterns])
    for category, patterns in RULES
]

RECON_CMDS = {
    "ls", "pwd", "whoami", "id", "uname", "hostname", "ifconfig", "ip",
    "netstat", "ss", "ps", "top", "env", "printenv", "df", "du", "free",
    "uptime", "w", "who", "last", "lsof", "lscpu", "arch", "lsb_release",
    "find", "locate", "which", "whereis", "dpkg", "mount", "nmap", "ping",
    "dig", "nslookup", "arp", "route", "cd", "cat", "head", "tail", "less",
    "more", "grep", "file", "stat", "psql",
}


def classify(cmd):
    cmd = (cmd or "").strip()
    if not cmd:
        return "other"
    for category, patterns in COMPILED:
        if any(p.search(cmd) for p in patterns):
            return category
    if cmd.split()[0] in RECON_CMDS:
        return "recon"
    return "other"