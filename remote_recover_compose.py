from __future__ import annotations

import argparse
import sys

import paramiko


def recover(host: str, username: str, password: str, remote_root: str) -> int:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=username, password=password, timeout=30)

    command = (
        "docker builder prune -af ; "
        f"cd {remote_root} ; "
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
    parser.add_argument("--host", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--remote-root", default="/opt/qinjian")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(recover(args.host, args.username, args.password, args.remote_root))