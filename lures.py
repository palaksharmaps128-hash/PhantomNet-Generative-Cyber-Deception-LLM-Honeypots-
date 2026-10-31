import posixpath

# Fake files that act as bait for attackers. Contents are invented.
FAKE_FILES = {
    "/root/.bash_history": (
        "ls -la\n"
        "cd /var/lib/postgresql/14/main\n"
        "psql -U postgres\n"
        "systemctl status postgresql\n"
        "vim /etc/postgresql/14/main/pg_hba.conf\n"
        "./backup.sh\n"
        "cat /root/notes.txt\n"
    ),
    "/root/.pgpass": (
        "localhost:5432:customers:app_admin:Pr0d#Db2024!\n"
        "10.0.2.15:5432:billing:billing_ro:b1ll1ng_r3adonly\n"
    ),
    "/root/backup.sh": (
        "#!/bin/bash\n"
        "# nightly dump of the customers database\n"
        "export PGPASSWORD='Pr0d#Db2024!'\n"
        "pg_dump -U app_admin -h localhost customers > /root/db_backup.sql\n"
        "aws s3 cp /root/db_backup.sql s3://prod-db-backups/nightly/\n"
    ),
    "/root/db_backup.sql": (
        "--\n"
        "-- PostgreSQL database dump\n"
        "--\n\n"
        "-- Dumped from database version 14.9 (Ubuntu 14.9-0ubuntu0.22.04.1)\n"
        "-- Dumped by pg_dump version 14.9 (Ubuntu 14.9-0ubuntu0.22.04.1)\n\n"
        "SET statement_timeout = 0;\n"
        "SET client_encoding = 'UTF8';\n\n"
        "CREATE TABLE public.customers (\n"
        "    id integer NOT NULL,\n"
        "    name text,\n"
        "    email text,\n"
        "    plan text\n"
        ");\n\n"
        "COPY public.customers (id, name, email, plan) FROM stdin;\n"
        "1\tAarav Mehta\taarav.mehta@example.com\tpremium\n"
        "2\tDiya Nair\tdiya.nair@example.com\tbasic\n"
        "3\tKabir Singh\tkabir.singh@example.com\tpremium\n"
        "\\.\n\n"
        "--\n"
        "-- PostgreSQL database dump complete\n"
        "--\n"
    ),
    "/root/notes.txt": (
        "TODO\n"
        "- rotate postgres password after migration\n"
        "- move nightly dump to s3://prod-db-backups (see backup.sh)\n"
        "- ask Rahul to close port 5432 on the public interface\n"
    ),
}

FILE_MODES = {
    "/root/.bash_history": "-rw-------",
    "/root/.pgpass": "-rw-------",
    "/root/backup.sh": "-rwxr-xr-x",
    "/root/db_backup.sql": "-rw-r--r--",
    "/root/notes.txt": "-rw-r--r--",
}

FILE_MTIME = {
    "/root/.bash_history": "Oct 29 18:22",
    "/root/.pgpass": "Sep 14 11:05",
    "/root/backup.sh": "Sep 14 11:09",
    "/root/db_backup.sql": "Oct 30 02:00",
    "/root/notes.txt": "Oct 20 16:41",
}

# Directories whose listing is fully controlled by us.
FAKE_DIRS = {"/root", "/var/lib/postgresql"}
EXTRA_SUBDIRS = {"/var/lib/postgresql": ["14"]}
DIR_OWNER = {"/root": "root", "/var/lib/postgresql": "postgres"}
DIR_MODE = {"/root": "drwx------", "/var/lib/postgresql": "drwxr-xr-x"}
DIR_MTIME = {"/root": "Oct 30 02:00", "/var/lib/postgresql": "Sep  2 08:30"}
PARENT_LINKS = {"/root": 19, "/var/lib/postgresql": 40}


def prompt_section():
    lines = [
        "These files really exist on this server. Use EXACTLY this content and "
        "never invent other files inside these directories:",
        "/root contains: .bash_history .pgpass backup.sh db_backup.sql notes.txt",
        "/var/lib/postgresql contains only the directory: 14",
    ]
    for path, content in FAKE_FILES.items():
        lines.append(f"\nFile {path}:\n{content}")
    return "\n".join(lines)


def resolve(path, cwd):
    if path == "~" or path.startswith("~/"):
        path = "/root" + path[1:]
    if not path.startswith("/"):
        path = posixpath.join(cwd, path)
    return posixpath.normpath(path)