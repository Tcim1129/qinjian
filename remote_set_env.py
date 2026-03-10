from __future__ import annotations

import argparse
import sys

import paramiko


def update_remote_env(host: str, username: str, password: str, remote_root: str, key: str, restart_service: str | None) -> int:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=username, password=password, timeout=30)

    try:
        commands = [
            f"python3 -c \"from pathlib import Path; path=Path('{remote_root}/.env'); text=path.read_text(encoding='utf-8') if path.exists() else ''; lines=[line for line in text.splitlines() if not line.startswith('SILICONFLOW_API_KEY=')]; lines.append('SILICONFLOW_API_KEY={key}'); path.write_text('\\n'.join(lines)+'\\n', encoding='utf-8')\""
        ]
        if restart_service:
            commands.append(
                f"cd {remote_root} && docker compose up -d {restart_service}"
            )

        command = " ; ".join(commands)
        stdin, stdout, stderr = client.exec_command(command, timeout=600)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="ignore")
        error = stderr.read().decode("utf-8", errors="ignore")
        if output.strip():
            print(output.strip())
        if error.strip():
            print(error.strip(), file=sys.stderr)
        return exit_code
    finally:
        client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="更新远端 .env 中的 SiliconFlow API Key")
    parser.add_argument("--host", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--remote-root", default="/opt/qinjian")
    parser.add_argument("--key", required=True)
    parser.add_argument("--restart-service", default="backend")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(
        update_remote_env(
            host=args.host,
            username=args.username,
            password=args.password,
            remote_root=args.remote_root,
            key=args.key,
            restart_service=args.restart_service,
        )
    )