from __future__ import annotations

import argparse
import fnmatch
import os
import posixpath
import secrets
import sys
import time
from pathlib import Path

import paramiko


HOST = "143.198.110.145"
USERNAME = "root"
PASSWORD = "7507906119HJL"
REMOTE_ROOT = "/opt/qinjian"
LOCAL_ROOT = Path(__file__).resolve().parent

INCLUDE_PATHS = [
    "backend",
    "web",
    "docker-compose.yml",
    "nginx.conf",
]

IGNORE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
]


def should_ignore(path: Path) -> bool:
    name = path.name
    return any(fnmatch.fnmatch(name, pattern) for pattern in IGNORE_PATTERNS)


def iter_upload_items() -> list[tuple[Path, str]]:
    items: list[tuple[Path, str]] = []
    for relative in INCLUDE_PATHS:
        local_path = LOCAL_ROOT / relative
        if not local_path.exists():
            raise FileNotFoundError(f"缺少部署文件: {local_path}")

        if local_path.is_file():
            items.append((local_path, relative.replace("\\", "/")))
            continue

        for child in sorted(local_path.rglob("*")):
            if child.is_dir() or should_ignore(child):
                continue
            remote_relative = child.relative_to(LOCAL_ROOT).as_posix()
            items.append((child, remote_relative))

    return items


def connect_client(host: str, username: str, password: str) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=username, password=password, timeout=30)
    return client


def run_remote(client: paramiko.SSHClient, command: str, timeout: int = 600) -> tuple[int, str, str]:
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode("utf-8", errors="ignore")
    error = stderr.read().decode("utf-8", errors="ignore")
    return exit_code, output, error


def ensure_remote_dirs(sftp: paramiko.SFTPClient, remote_path: str) -> None:
    current = "/"
    for part in [segment for segment in remote_path.split("/") if segment]:
        current = posixpath.join(current, part)
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


def remote_exists(sftp: paramiko.SFTPClient, remote_path: str) -> bool:
    try:
        sftp.stat(remote_path)
        return True
    except FileNotFoundError:
        return False


def create_remote_env_if_missing(sftp: paramiko.SFTPClient, remote_root: str) -> bool:
    env_path = posixpath.join(remote_root, ".env")
    if remote_exists(sftp, env_path):
        return False

    secret_key = secrets.token_hex(32)
    db_password = secrets.token_hex(16)
    siliconflow_api_key = os.getenv("SILICONFLOW_API_KEY", "")
    env_content = "\n".join(
        [
            f"SECRET_KEY={secret_key}",
            f"DB_PASSWORD={db_password}",
            f"SILICONFLOW_API_KEY={siliconflow_api_key}",
            "SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1",
            "AI_MULTIMODAL_MODEL=moonshot/kimi-k2.5",
            "AI_TEXT_MODEL=deepseek-ai/DeepSeek-V3",
            "PHONE_CODE_DEBUG_RETURN=false",
        ]
    ) + "\n"

    with sftp.open(env_path, "w") as remote_file:
        remote_file.write(env_content)

    return True


def upload_files(sftp: paramiko.SFTPClient, items: list[tuple[Path, str]], remote_root: str) -> None:
    total = len(items)
    for index, (local_path, remote_relative) in enumerate(items, start=1):
        remote_path = posixpath.join(remote_root, remote_relative)
        ensure_remote_dirs(sftp, posixpath.dirname(remote_path))
        sftp.put(str(local_path), remote_path)
        print(f"[{index}/{total}] 已上传 {remote_relative}")


def wait_for_http(host: str, path: str, timeout_seconds: int = 120) -> tuple[bool, str]:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout_seconds
    last_error = ""
    url = f"http://{host}:8080{path}"

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                body = response.read().decode("utf-8", errors="ignore")
                return True, body
        except urllib.error.URLError as exc:
            last_error = str(exc)
            time.sleep(3)

    return False, last_error


def deploy(host: str, username: str, password: str, remote_root: str) -> int:
    print(f"连接服务器 {host} ...")
    client = connect_client(host, username, password)
    sftp = client.open_sftp()

    try:
        print("检查服务器部署目录和环境文件...")
        ensure_remote_dirs(sftp, remote_root)
        env_created = create_remote_env_if_missing(sftp, remote_root)
        if env_created:
            print("服务器缺少 .env，已自动生成基础生产配置。")
            print("当前未检测到本机 SILICONFLOW_API_KEY，AI 功能可能暂不可用。")

        print("停止现有服务...")
        down_command = (
            f'cd {remote_root} && '
            'if docker compose version >/dev/null 2>&1; then docker compose down; '
            'elif command -v docker-compose >/dev/null 2>&1; then docker-compose down; '
            'else echo "Docker Compose 不存在" >&2; exit 1; fi'
        )
        exit_code, output, error = run_remote(client, down_command, timeout=1200)
        if output.strip():
            print(output.strip())
        if exit_code != 0 and "no configuration file provided" not in error.lower():
            print(error.strip() or "停止服务失败")
            return 3

        print("清理远端旧代码目录...")
        cleanup_command = (
            f"rm -rf {remote_root}/backend {remote_root}/web "
            f"{remote_root}/docker-compose.yml {remote_root}/nginx.conf"
        )
        exit_code, output, error = run_remote(client, cleanup_command)
        if exit_code != 0:
            print(error.strip() or "清理远端目录失败")
            return 4

        print("准备上传当前工作区运行文件...")
        items = iter_upload_items()
        upload_files(sftp, items, remote_root)

        print("启动最新容器...")
        up_command = (
            f'cd {remote_root} && '
            'if docker compose version >/dev/null 2>&1; then docker compose up -d --build; '
            'else docker-compose up -d --build; fi'
        )
        exit_code, output, error = run_remote(client, up_command, timeout=1800)
        if output.strip():
            print(output.strip())
        if exit_code != 0:
            print(error.strip() or "启动容器失败")
            return 5

        print("检查容器状态...")
        ps_command = (
            f'cd {remote_root} && '
            'if docker compose version >/dev/null 2>&1; then docker compose ps; '
            'else docker-compose ps; fi'
        )
        _, ps_output, ps_error = run_remote(client, ps_command)
        print(ps_output.strip() or ps_error.strip())

        print("读取后端最近日志...")
        logs_command = (
            f'cd {remote_root} && '
            'if docker compose version >/dev/null 2>&1; then docker compose logs --tail=80 backend; '
            'else docker-compose logs --tail=80 backend; fi'
        )
        _, logs_output, logs_error = run_remote(client, logs_command)
        print(logs_output.strip() or logs_error.strip())

        if env_created and "InvalidPasswordError" in logs_output:
            print("检测到旧 PostgreSQL 卷密码不匹配，正在重建数据库卷...")
            reset_command = (
                f'cd {remote_root} && '
                'if docker compose version >/dev/null 2>&1; then '
                'docker compose down -v && docker compose up -d --build; '
                'else docker-compose down -v && docker-compose up -d --build; fi'
            )
            exit_code, output, error = run_remote(client, reset_command, timeout=1800)
            if output.strip():
                print(output.strip())
            if exit_code != 0:
                print(error.strip() or "重建数据库卷失败")
                return 6

            print("重新读取后端日志...")
            _, logs_output, logs_error = run_remote(client, logs_command)
            print(logs_output.strip() or logs_error.strip())

        print("等待线上健康检查...")
        ok, result = wait_for_http(host, "/api/health")
        if not ok:
            print("健康检查失败:")
            print(result)
            return 7

        print("健康检查成功:")
        print(result)
        print(f"Web: http://{host}:8080")
        print(f"API: http://{host}:8080/api/health")
        return 0
    finally:
        sftp.close()
        client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="直传当前工作区到远端并重启 Docker Compose")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--username", default=USERNAME)
    parser.add_argument("--password", default=PASSWORD)
    parser.add_argument("--remote-root", default=REMOTE_ROOT)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    sys.exit(deploy(arguments.host, arguments.username, arguments.password, arguments.remote_root))