from __future__ import annotations

import argparse
import os
import sys

import paramiko


def run_remote(host: str, username: str, password: str, command: str, timeout: int) -> int:
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
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="ignore")
        error_text = stderr.read().decode("utf-8", errors="ignore")
        if output:
            print(output, end="")
        if error_text:
            print(error_text, end="", file=sys.stderr)
        return exit_code
    finally:
        client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="执行远端 SSH 命令")
    parser.add_argument("--host", default=os.getenv("QJ_REMOTE_HOST"), required=not os.getenv("QJ_REMOTE_HOST"))
    parser.add_argument("--username", default=os.getenv("QJ_REMOTE_USER"), required=not os.getenv("QJ_REMOTE_USER"))
    parser.add_argument("--password", default=os.getenv("QJ_REMOTE_PASSWORD"), required=not os.getenv("QJ_REMOTE_PASSWORD"))
    parser.add_argument("--command", required=True)
    parser.add_argument("--timeout", type=int, default=600)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(run_remote(args.host, args.username, args.password, args.command, args.timeout))
