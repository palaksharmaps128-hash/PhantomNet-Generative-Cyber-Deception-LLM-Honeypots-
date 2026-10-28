import posixpath

VALID_DIRS = {
    "/", "/root", "/home", "/etc", "/var", "/var/lib", "/var/log", "/var/tmp",
    "/var/lib/postgresql", "/var/lib/postgresql/14", "/var/lib/postgresql/14/main",
    "/var/log/postgresql", "/etc/postgresql", "/etc/postgresql/14",
    "/etc/postgresql/14/main", "/tmp", "/usr", "/usr/bin", "/usr/local",
    "/usr/share", "/opt", "/bin", "/sbin", "/boot", "/dev", "/proc", "/sys",
    "/run", "/srv", "/mnt", "/media", "/lib",
}


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