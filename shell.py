import ipaddress
import posixpath
import re
import shlex
from datetime import datetime, timezone
from urllib.parse import urlparse
from static_responses import static_reply, base_users
from lures import (
    FAKE_FILES, FILE_MODES, FILE_MTIME, FAKE_DIRS, EXTRA_SUBDIRS,
    DIR_OWNER, DIR_MODE, DIR_MTIME, PARENT_LINKS, resolve,
)

VALID_DIRS = {
    "/", "/root", "/home", "/etc", "/var", "/var/lib", "/var/log", "/var/tmp",
    "/var/lib/postgresql", "/var/lib/postgresql/14", "/var/lib/postgresql/14/main",
    "/var/log/postgresql", "/etc/postgresql", "/etc/postgresql/14",
    "/etc/postgresql/14/main", "/tmp", "/usr", "/usr/bin", "/usr/local",
    "/usr/share", "/opt", "/bin", "/sbin", "/boot", "/dev", "/proc", "/sys",
    "/run", "/srv", "/mnt", "/media", "/lib",
}

SHELL_META = set("|><;&$`*?(){}")


def do_cd(cmd, cwd):
    parts = cmd.split(maxsplit=1)
    raw = parts[1].strip() if len(parts) > 1 else "~"
    target = raw
    if target == "-":
        return cwd, ""
    if target == "~" or target.startswith("~/"):
        target = "/root" + target[1:]
    if not target.startswith("/"):
        target = posixpath.join(cwd, target)
    target = posixpath.normpath(target)
    if target in VALID_DIRS:
        return target, ""
    return cwd, f"bash: cd: {raw}: No such file or directory"


def _sort_key(name):
    return "".join(c for c in name.lower() if c.isalnum())


def _size_str(size, human):
    if human and size >= 1024:
        return f"{size / 1024:.1f}K"
    return str(size)


def _entries(directory):
    """Rows: (name, is_dir, size, mode, links, owner, mtime)."""
    owner = DIR_OWNER.get(directory, "root")
    rows = []
    for path, content in FAKE_FILES.items():
        if posixpath.dirname(path) == directory:
            rows.append((
                posixpath.basename(path), False, len(content.encode()),
                FILE_MODES[path], 1, "root", FILE_MTIME[path],
            ))
    for sub in EXTRA_SUBDIRS.get(directory, []):
        rows.append((sub, True, 4096, "drwx------", 3, owner, "Sep  2 08:30"))
    return rows


def _fake_ls(args, cwd):
    flags, paths = set(), []
    for a in args:
        if a.startswith("-") and len(a) > 1:
            flags.update(a[1:])
        else:
            paths.append(a)
    if any(f not in "alhA1" for f in flags) or len(paths) > 1:
        return None
    target = resolve(paths[0], cwd) if paths else cwd
    long_fmt = "l" in flags
    human = "h" in flags
    show_all = "a" in flags
    show_hidden = show_all or "A" in flags

    if target in FAKE_FILES:
        name = paths[0] if paths else target
        if not long_fmt:
            return name
        size = len(FAKE_FILES[target].encode())
        return f"{FILE_MODES[target]} 1 root root {_size_str(size, human)} {FILE_MTIME[target]} {name}"
    if target not in FAKE_DIRS:
        return None

    rows = _entries(target)
    if not show_hidden:
        rows = [r for r in rows if not r[0].startswith(".")]
    rows.sort(key=lambda r: _sort_key(r[0]))
    if show_all:
        owner = DIR_OWNER.get(target, "root")
        subdirs = len(EXTRA_SUBDIRS.get(target, []))
        rows = [
            (".", True, 4096, DIR_MODE[target], 2 + subdirs, owner, DIR_MTIME[target]),
            ("..", True, 4096, "drwxr-xr-x", PARENT_LINKS[target], "root", "Oct 12 09:14"),
        ] + rows

    if not long_fmt:
        names = [r[0] for r in rows]
        return "\n".join(names) if "1" in flags else "  ".join(names)

    total = sum(4 * ((r[2] + 4095) // 4096) for r in rows)
    sizes = [_size_str(r[2], human) for r in rows]
    w_link = max(len(str(r[4])) for r in rows) if rows else 1
    w_own = max(len(r[5]) for r in rows) if rows else 1
    w_size = max(len(s) for s in sizes) if sizes else 1
    lines = [f"total {total}"]
    for r, s in zip(rows, sizes):
        lines.append(
            f"{r[3]} {r[4]:>{w_link}} {r[5]:<{w_own}} {r[5]:<{w_own}} "
            f"{s:>{w_size}} {r[6]} {r[0]}"
        )
    return "\n".join(lines)


def _fake_cat(args, cwd):
    if not args or any(a.startswith("-") for a in args):
        return None
    outs = []
    for a in args:
        p = resolve(a, cwd)
        if p in FAKE_FILES:
            outs.append(FAKE_FILES[p].rstrip("\n"))
        elif p in FAKE_DIRS:
            outs.append(f"cat: {a}: Is a directory")
        else:
            return None
    return "\n".join(outs)


USER_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")


def _fake_useradd(args, state):
    if state is None:
        return None
    flags = [a for a in args if a.startswith("-")]
    names = [a for a in args if not a.startswith("-")]
    if any(f not in ("-m", "-M", "-r") for f in flags) or len(names) != 1:
        return None
    name = names[0]
    if not USER_RE.match(name):
        return f"useradd: invalid user name '{name}'"
    if name in base_users() or name in state["users"]:
        return f"useradd: user '{name}' already exists"
    state["users"].append(name)
    return ""


def _fake_userdel(args, state):
    names = [a for a in args if not a.startswith("-")]
    if state is None or len(names) != 1 or any(a.startswith("-") for a in args):
        return None
    name = names[0]
    if name in state["users"]:
        state["users"].remove(name)
        return ""
    if name in base_users():
        return None
    return f"userdel: user '{name}' does not exist"


def _is_ip(host):
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _url_and_host(args):
    for a in args:
        if "://" in a:
            return a, urlparse(a).hostname
    return None, None


def _fake_wget(args):
    url, host = _url_and_host(args)
    if not host or _is_ip(host):
        return None
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"--{ts}--  {url}\n"
        f"Resolving {host} ({host})... failed: Temporary failure in name resolution.\n"
        f"wget: unable to resolve host address \u2018{host}\u2019"
    )


def _fake_curl(args):
    _, host = _url_and_host(args)
    if not host or _is_ip(host):
        return None
    return f"curl: (6) Could not resolve host: {host}"


def _remote_target(cmd_name, args):
    """Return (host, port) for scp/ssh, or (None, None) if it is a local copy."""
    port_flag = "-P" if cmd_name == "scp" else "-p"
    value_flags = {"-p", "-P", "-i", "-l", "-o", "-F", "-J", "-L", "-R", "-D"}
    port, host, skip = "22", None, False
    for i, a in enumerate(args):
        if skip:
            skip = False
            continue
        if a in value_flags:
            if a == port_flag and i + 1 < len(args):
                port = args[i + 1]
            skip = True
            continue
        if a.startswith("-"):
            continue
        if cmd_name == "scp":
            if ":" in a and not a.startswith(("/", "./", "../")):
                host = a.split(":")[0].split("@")[-1]
                break
        else:
            host = a.split("@")[-1]
            break
    return (host, port) if host else (None, None)


def _fake_remote(cmd_name, args):
    host, port = _remote_target(cmd_name, args)
    if not host:
        return None
    if _is_ip(host):
        msg = f"ssh: connect to host {host} port {port}: Connection timed out"
    else:
        msg = f"ssh: Could not resolve hostname {host}: Temporary failure in name resolution"
    return msg + ("\nlost connection" if cmd_name == "scp" else "")


def try_fake(cmd, cwd, state=None):
    """Return output for static commands, lure files and a few commands that
    must stay consistent, or None so the LLM answers.

    An empty string means "ran silently". state is a per-session dict
    ({"users": [...]}) that remembers users added with useradd.
    """
    users = state["users"] if state else None
    static = static_reply(cmd, users)
    if static is not None:
        return static
    if any(c in SHELL_META for c in cmd):
        return None
    try:
        parts = shlex.split(cmd)
    except ValueError:
        return None
    if not parts:
        return None
    name, args = parts[0], parts[1:]
    if name == "ls":
        return _fake_ls(args, cwd)
    if name == "cat":
        return _fake_cat(args, cwd)
    if name == "useradd":
        return _fake_useradd(args, state)
    if name == "userdel":
        return _fake_userdel(args, state)
    if name == "wget":
        return _fake_wget(args)
    if name == "curl":
        return _fake_curl(args)
    if name in ("scp", "ssh"):
        return _fake_remote(name, args)
    return None