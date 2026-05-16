from __future__ import annotations

import argparse
import os
import shlex
import sys

import paramiko


def recover(host: str, username: str, password: str, remote_root: str) -> int:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(
        host,
        username=username,
        password=password,
        look_for_keys=False,
        allow_agent=False,
        timeout=30,
    )
    remote_root_quoted = shlex.quote(remote_root)

    command = (
        "docker builder prune -af ; "
        f"cd {remote_root_quoted} ; "
        "COMPOSE_DOCKER_CLI_BUILD=0 DOCKER_BUILDKIT=0 docker compose up -d --build"
    )

    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=2400)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="ignore")
        error_text = stderr.read().decode("utf-8", errors="ignore")
        if output.strip():
            print(output.strip())
        if error_text.strip():
            print(error_text.strip(), file=sys.stderr)
        return exit_code
    finally:
        client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="恢复远端 Docker Compose 服务")
    parser.add_argument("--host", default=os.getenv("QJ_REMOTE_HOST"), required=not os.getenv("QJ_REMOTE_HOST"))
    parser.add_argument("--username", default=os.getenv("QJ_REMOTE_USER"), required=not os.getenv("QJ_REMOTE_USER"))
    parser.add_argument("--password", default=os.getenv("QJ_REMOTE_PASSWORD"), required=not os.getenv("QJ_REMOTE_PASSWORD"))
    parser.add_argument("--remote-root", default=os.getenv("QJ_REMOTE_ROOT", "/root/qinjian"))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(recover(args.host, args.username, args.password, args.remote_root))
