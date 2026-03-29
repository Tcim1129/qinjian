from __future__ import annotations

import argparse
import fnmatch
import os
import posixpath
import secrets
import shlex
import sys
import tarfile
import tempfile
import time
from pathlib import Path

import paramiko


HOST = os.getenv("QJ_REMOTE_HOST", "")
USERNAME = os.getenv("QJ_REMOTE_USER", "root")
PASSWORD = os.getenv("QJ_REMOTE_PASSWORD", "")
FRONTEND_ORIGIN = os.getenv("QJ_FRONTEND_ORIGIN", os.getenv("FRONTEND_ORIGIN", "")).rstrip("/")
REMOTE_ROOT = "/root/qinjian"
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
    "*.db",
    "*.log",
    "*.bak",
    "*.orig",
    "*.tmp",
    ".DS_Store",
    ".env.local",
    ".env",
    "venv",
    ".venv",
    "node_modules",
    "site-packages",
    "uploads",
    "backend.log",
    "nul",
]

KEEP_REMOTE_PATHS = {
    ".env",
    "backend",
    "web",
    "docker-compose.yml",
    "nginx.conf",
}


def should_ignore(path: Path) -> bool:
    parts = path.parts
    for part in parts:
        if any(fnmatch.fnmatch(part, pattern) for pattern in IGNORE_PATTERNS):
            return True
    return any(fnmatch.fnmatch(path.name, pattern) for pattern in IGNORE_PATTERNS)


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
    return client


def resolve_frontend_origin(host: str) -> str:
    origin = FRONTEND_ORIGIN or f"http://{host}"
    return origin.rstrip("/")


def run_remote(
    client: paramiko.SSHClient, command: str, timeout: int = 600
) -> tuple[int, str, str]:
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode("utf-8", errors="ignore")
    error = stderr.read().decode("utf-8", errors="ignore")
    return exit_code, output, error


def set_remote_env_value(
    client: paramiko.SSHClient, remote_root: str, key: str, value: str
) -> tuple[int, str, str]:
    safe_value = value.replace("'", "'\"'\"'")
    command = (
        'python3 -c "from pathlib import Path; '
        f"path=Path('{remote_root}/.env'); "
        "text=path.read_text(encoding='utf-8') if path.exists() else ''; "
        f"lines=[line for line in text.splitlines() if not line.startswith('{key}=')]; "
        f"lines.append('{key}={safe_value}'); "
        "path.write_text('\\n'.join(lines)+'\\n', encoding='utf-8')\""
    )
    return run_remote(client, command, timeout=120)


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
    ai_api_key = os.getenv("AI_API_KEY", os.getenv("SILICONFLOW_API_KEY", ""))
    ai_base_url = os.getenv("AI_BASE_URL", "https://api.siliconflow.cn/v1")
    frontend_origin = resolve_frontend_origin("localhost")
    env_content = (
        "\n".join(
            [
                f"SECRET_KEY={secret_key}",
                f"DB_PASSWORD={db_password}",
                f"AI_API_KEY={ai_api_key}",
                f"AI_BASE_URL={ai_base_url}",
                "SILICONFLOW_API_KEY=",
                "SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1",
                "AI_MULTIMODAL_MODEL=moonshot/kimi-k2.5",
                "AI_TEXT_MODEL=deepseek-ai/DeepSeek-V3",
                f"FRONTEND_ORIGIN={frontend_origin}",
                "PHONE_CODE_DEBUG_RETURN=false",
            ]
        )
        + "\n"
    )

    with sftp.open(env_path, "w") as remote_file:
        remote_file.write(env_content)

    return True


def prune_remote_root(client: paramiko.SSHClient, remote_root: str) -> tuple[int, str, str]:
    command = f"""python3 - <<'PY'
from pathlib import Path
import shutil

root = Path({remote_root!r})
keep = {sorted(KEEP_REMOTE_PATHS)!r}
removed = []

for child in list(root.iterdir()):
    if child.name in keep:
        continue
    removed.append(child.name)
    if child.is_dir() and not child.is_symlink():
        shutil.rmtree(child)
    else:
        child.unlink()

print('removed=' + ','.join(sorted(removed)) if removed else 'removed=')
PY"""
    return run_remote(client, command, timeout=300)


def prune_remote_artifacts(client: paramiko.SSHClient, remote_root: str) -> tuple[int, str, str]:
    command = f"""python3 - <<'PY'
from pathlib import Path
import shutil

root = Path({remote_root!r})
removed = []

for pattern in ('*.bak', '*.orig', '*.tmp', '*.pyc'):
    for child in root.rglob(pattern):
        if child.is_file() or child.is_symlink():
            removed.append(str(child.relative_to(root)))
            child.unlink()

for child in root.rglob('__pycache__'):
    if child.is_dir():
        removed.append(str(child.relative_to(root)))
        shutil.rmtree(child)

print('removed=' + ','.join(sorted(set(removed))) if removed else 'removed=')
PY"""
    return run_remote(client, command, timeout=300)


def create_upload_bundle() -> Path:
    bundle_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz")
    bundle_file.close()
    bundle_path = Path(bundle_file.name)

    with tarfile.open(bundle_path, "w:gz") as archive:
        for local_path, remote_relative in iter_upload_items():
            archive.add(local_path, arcname=remote_relative, recursive=False)

    return bundle_path


def upload_bundle(
    sftp: paramiko.SFTPClient, bundle_path: Path, remote_root: str
) -> str:
    ensure_remote_dirs(sftp, remote_root)
    remote_bundle = posixpath.join(remote_root, ".deploy_bundle.tar.gz")
    sftp.put(str(bundle_path), remote_bundle)
    return remote_bundle


def sync_bundle_on_remote(
    client: paramiko.SSHClient, remote_root: str, remote_bundle: str
) -> tuple[int, str, str]:
    remote_root = remote_root.rstrip("/")
    remote_parent = posixpath.dirname(remote_root) or "/"
    remote_name = posixpath.basename(remote_root)
    remote_temp = posixpath.join(remote_parent, f".{remote_name}-deploy")
    command = (
        f"mkdir -p {shlex.quote(remote_root)} && "
        f"rm -rf {shlex.quote(remote_temp)} && "
        f"mkdir -p {shlex.quote(remote_temp)} && "
        f"tar -xzf {shlex.quote(remote_bundle)} -C {shlex.quote(remote_temp)} && "
        f"rm -rf {shlex.quote(posixpath.join(remote_root, 'backend'))} "
        f"{shlex.quote(posixpath.join(remote_root, 'web'))} && "
        f"rm -f {shlex.quote(posixpath.join(remote_root, 'docker-compose.yml'))} "
        f"{shlex.quote(posixpath.join(remote_root, 'nginx.conf'))} && "
        f"cp -a {shlex.quote(posixpath.join(remote_temp, 'backend'))} "
        f"{shlex.quote(posixpath.join(remote_root, 'backend'))} && "
        f"cp -a {shlex.quote(posixpath.join(remote_temp, 'web'))} "
        f"{shlex.quote(posixpath.join(remote_root, 'web'))} && "
        f"cp -a {shlex.quote(posixpath.join(remote_temp, 'docker-compose.yml'))} "
        f"{shlex.quote(posixpath.join(remote_root, 'docker-compose.yml'))} && "
        f"cp -a {shlex.quote(posixpath.join(remote_temp, 'nginx.conf'))} "
        f"{shlex.quote(posixpath.join(remote_root, 'nginx.conf'))} && "
        f"rm -rf {shlex.quote(remote_temp)} {shlex.quote(remote_bundle)}"
    )
    return run_remote(client, command, timeout=1200)


def wait_for_http(base_url: str, path: str, timeout_seconds: int = 120) -> tuple[bool, str]:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout_seconds
    last_error = ""
    url = f"{base_url.rstrip('/')}{path}"

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
    if not host or not username or not password:
        print(
            "缺少远端部署信息，请通过 --host/--username/--password 或环境变量 QJ_REMOTE_HOST/QJ_REMOTE_USER/QJ_REMOTE_PASSWORD 提供。"
        )
        return 2

    frontend_origin = resolve_frontend_origin(host)

    print(f"连接服务器 {host} ...")
    client = connect_client(host, username, password)
    sftp = client.open_sftp()

    try:
        print("检查服务器部署目录和环境文件...")
        ensure_remote_dirs(sftp, remote_root)
        env_created = create_remote_env_if_missing(sftp, remote_root)
        env_code, env_output, env_error = set_remote_env_value(
            client, remote_root, "FRONTEND_ORIGIN", frontend_origin
        )
        if env_output.strip():
            print(env_output.strip())
        if env_code != 0:
            print(env_error.strip() or "更新 FRONTEND_ORIGIN 失败")
            return 3
        if env_created:
            print("服务器缺少 .env，已自动生成基础生产配置。")
            print("当前未检测到本机 SILICONFLOW_API_KEY，AI 功能可能暂不可用。")
        print(f"已设置前端来源: {frontend_origin}")

        print("打包当前工作区并上传...")
        bundle_path = create_upload_bundle()
        try:
            remote_bundle = upload_bundle(sftp, bundle_path, remote_root)
        finally:
            bundle_path.unlink(missing_ok=True)

        print("同步远端代码目录...")
        exit_code, output, error = sync_bundle_on_remote(
            client, remote_root, remote_bundle
        )
        if output.strip():
            print(output.strip())
        if exit_code != 0:
            print(error.strip() or "同步远端目录失败")
            return 4

        print("清理远端旧内容...")
        exit_code, output, error = prune_remote_root(client, remote_root)
        if output.strip():
            print(output.strip())
        if exit_code != 0:
            print(error.strip() or "清理远端旧内容失败")
            return 4

        print("清理远端临时/备份文件...")
        exit_code, output, error = prune_remote_artifacts(client, remote_root)
        if output.strip():
            print(output.strip())
        if exit_code != 0:
            print(error.strip() or "清理远端临时/备份文件失败")
            return 4

        print("启动最新容器...")
        up_command = (
            f"cd {remote_root} && "
            "if docker compose version >/dev/null 2>&1; then docker compose up -d --build; "
            "else docker-compose up -d --build; fi"
        )
        exit_code, output, error = run_remote(client, up_command, timeout=1800)
        if output.strip():
            print(output.strip())
        if exit_code != 0:
            mirror_error = (
                "docker.mirrors.sjtug.sjtu.edu.cn" in output
                or "docker.mirrors.sjtug.sjtu.edu.cn" in error
            )
            if mirror_error:
                print("检测到镜像源异常，写入官方镜像并重试...")
                for key, value in (
                    ("POSTGRES_IMAGE", "postgres:16-alpine"),
                    ("NGINX_IMAGE", "nginx:alpine"),
                ):
                    env_code, env_output, env_error = set_remote_env_value(
                        client, remote_root, key, value
                    )
                    if env_output.strip():
                        print(env_output.strip())
                    if env_code != 0:
                        print(env_error.strip() or f"写入 {key} 失败")
                        return 5
                exit_code, output, error = run_remote(client, up_command, timeout=1800)
                if output.strip():
                    print(output.strip())

        if exit_code != 0:
            print(error.strip() or "启动容器失败")
            return 5

        print("强制刷新 Web 静态容器...")
        web_refresh_command = (
            f"cd {remote_root} && "
            "if docker compose version >/dev/null 2>&1; then docker compose up -d --force-recreate web; "
            "else docker-compose up -d --force-recreate web; fi"
        )
        exit_code, output, error = run_remote(client, web_refresh_command, timeout=1200)
        if output.strip():
            print(output.strip())
        if exit_code != 0:
            print(error.strip() or "重建 Web 容器失败")
            return 8

        print("验证 Web 静态文件...")
        verify_web_command = (
            f"cd {remote_root} && "
            "if docker compose version >/dev/null 2>&1; then docker compose exec -T web test -f /usr/share/nginx/html/index.html; "
            "else docker-compose exec -T web test -f /usr/share/nginx/html/index.html; fi"
        )
        exit_code, _, error = run_remote(client, verify_web_command, timeout=120)
        if exit_code != 0:
            print(error.strip() or "Web 容器内未找到 index.html")
            return 9

        print("检查容器状态...")
        ps_command = (
            f"cd {remote_root} && "
            "if docker compose version >/dev/null 2>&1; then docker compose ps; "
            "else docker-compose ps; fi"
        )
        _, ps_output, ps_error = run_remote(client, ps_command)
        print(ps_output.strip() or ps_error.strip())

        print("读取后端最近日志...")
        logs_command = (
            f"cd {remote_root} && "
            "if docker compose version >/dev/null 2>&1; then docker compose logs --tail=80 backend; "
            "else docker-compose logs --tail=80 backend; fi"
        )
        _, logs_output, logs_error = run_remote(client, logs_command)
        print(logs_output.strip() or logs_error.strip())

        if env_created and "InvalidPasswordError" in logs_output:
            print("检测到旧 PostgreSQL 卷密码不匹配，正在重建数据库卷...")
            reset_command = (
                f"cd {remote_root} && "
                "if docker compose version >/dev/null 2>&1; then "
                "docker compose down -v && docker compose up -d --build; "
                "else docker-compose down -v && docker-compose up -d --build; fi"
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
        ok, result = wait_for_http(frontend_origin, "/api/health")
        if not ok:
            print("健康检查失败:")
            print(result)
            return 7

        print("健康检查成功:")
        print(result)
        print(f"Web: {frontend_origin}")
        print(f"API: {frontend_origin}/api/health")
        return 0
    finally:
        sftp.close()
        client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="直传当前工作区到远端并重启 Docker Compose"
    )
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--username", default=USERNAME)
    parser.add_argument("--password", default=PASSWORD)
    parser.add_argument("--remote-root", default=REMOTE_ROOT)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    sys.exit(
        deploy(
            arguments.host,
            arguments.username,
            arguments.password,
            arguments.remote_root,
        )
    )
