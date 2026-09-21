from __future__ import annotations

import argparse
import fnmatch
import os
import posixpath
import secrets
import shlex
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

import paramiko


HOST = os.getenv("QJ_REMOTE_HOST", "")
USERNAME = os.getenv("QJ_REMOTE_USER", "root")
PASSWORD = os.getenv("QJ_REMOTE_PASSWORD", "")
KEY_FILE = os.getenv("QJ_REMOTE_KEY_FILE", "")
FRONTEND_ORIGIN = os.getenv("QJ_FRONTEND_ORIGIN", os.getenv("FRONTEND_ORIGIN", "")).rstrip("/")
RELAXED_TEST_ACCOUNT_EMAILS = os.getenv(
    "QJ_RELAXED_TEST_ACCOUNT_EMAILS",
    os.getenv("RELAXED_TEST_ACCOUNT_EMAILS", ""),
).strip()
REMOTE_ROOT = "/root/qinjian"
LOCAL_ROOT = Path(__file__).resolve().parent

INCLUDE_PATHS = [
    "backend",
    "web-vue3",
    "docker-compose.yml",
    "nginx.conf",
]

IGNORE_PATTERNS = [
    "__pycache__",
    ".pytest_cache",
    "*.pyc",
    "*.pyo",
    "*.db",
    "*.db.*",
    "*.sqlite",
    "*.sqlite3",
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
    "dist",
    "site-packages",
    "uploads",
    "screenshots",
    "backend.log",
    "qinjian.db*",
    "nul",
]

KEEP_REMOTE_PATHS = {
    ".env",
    "backend",
    "web-vue3",
    "docker-compose.yml",
    "nginx.conf",
}


def should_ignore(path: Path) -> bool:
    try:
        relative = path.relative_to(LOCAL_ROOT).as_posix()
    except ValueError:
        relative = path.as_posix()
    if relative == "web-vue3/dist" or relative.startswith("web-vue3/dist/"):
        return False
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


def connect_client(
    host: str, username: str, password: str, key_file: str = ""
) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs = {
        "username": username,
        "timeout": 30,
        "banner_timeout": 120,
        "auth_timeout": 60,
    }
    if password:
        connect_kwargs.update(
            {
                "password": password,
                "look_for_keys": False,
                "allow_agent": False,
            }
        )
    elif key_file:
        connect_kwargs.update(
            {
                "key_filename": key_file,
                "look_for_keys": False,
                "allow_agent": False,
            }
        )
    else:
        connect_kwargs.update({"look_for_keys": True, "allow_agent": True})

    last_exc = None
    for attempt in range(1, 4):
        try:
            client.connect(host, **connect_kwargs)
            return client
        except (paramiko.SSHException, OSError) as exc:
            last_exc = exc
            if attempt < 3:
                time.sleep(2)
    if last_exc:
        raise last_exc
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
    qwen_asr_api_key = os.getenv("QWEN_ASR_API_KEY", "")
    ai_base_url = os.getenv("AI_BASE_URL", "https://api.siliconflow.cn/v1")
    default_asr_provider = "qwen3" if qwen_asr_api_key else "openai-compatible"
    default_realtime_asr_provider = "qwen3" if qwen_asr_api_key else "batch"
    asr_provider = os.getenv("ASR_PROVIDER", default_asr_provider)
    realtime_asr_provider = os.getenv(
        "REALTIME_ASR_PROVIDER", default_realtime_asr_provider
    )
    openai_compatible_asr_model = os.getenv(
        "OPENAI_COMPATIBLE_ASR_MODEL",
        "FunAudioLLM/SenseVoiceSmall" if ai_api_key else "whisper-1",
    )
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
                "AI_MULTIMODAL_MODEL=qwen3.8-flash",
                "AI_TEXT_MODEL=deepseek-v4.1-flash",
                f"ASR_PROVIDER={asr_provider}",
                f"OPENAI_COMPATIBLE_ASR_MODEL={openai_compatible_asr_model}",
                f"REALTIME_ASR_PROVIDER={realtime_asr_provider}",
                "REALTIME_ASR_TICKET_EXPIRE_SECONDS=120",
                "REALTIME_ASR_MAX_SESSION_SECONDS=60",
                "REALTIME_ASR_STOP_TIMEOUT_SECONDS=12",
                f"QWEN_ASR_API_KEY={qwen_asr_api_key}",
                "QWEN_ASR_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1",
                "QWEN_ASR_FILE_MODEL=qwen3-asr-flash",
                "QWEN_ASR_REALTIME_MODEL=qwen3-asr-flash-realtime",
                f"FRONTEND_ORIGIN={frontend_origin}",
                "PHONE_CODE_DEBUG_RETURN=false",
            ]
        )
        + "\n"
    )

    with sftp.open(env_path, "w") as remote_file:
        remote_file.write(env_content)

    return True


def sync_remote_model_env(sftp: paramiko.SFTPClient, remote_root: str) -> None:
    env_path = posixpath.join(remote_root, ".env")
    if not remote_exists(sftp, env_path):
        return
    with sftp.open(env_path, "r") as f:
        content = f.read().decode("utf-8")

    desired = {
        "AI_TEXT_MODEL": os.getenv("AI_TEXT_MODEL", "deepseek-v4.1-flash"),
        "AI_TEXT_FALLBACK_MODEL": os.getenv(
            "AI_TEXT_FALLBACK_MODEL", "deepseek-v4.1-flash"
        ),
    }
    # 仅在本机显式提供时才覆盖网关地址与密钥，避免把远端已有配置清空
    explicit_base_url = os.getenv("AI_BASE_URL", "").strip()
    if explicit_base_url:
        desired["AI_BASE_URL"] = explicit_base_url
    explicit_api_key = (
        os.getenv("AI_API_KEY", "").strip() or os.getenv("SILICONFLOW_API_KEY", "").strip()
    )
    if explicit_api_key:
        desired["AI_API_KEY"] = explicit_api_key
    else:
        print(
            "提示：本机未设置 AI_API_KEY / SILICONFLOW_API_KEY，"
            "将保留远端 .env 中已有的 AI_API_KEY 不变。"
        )
    lines = content.splitlines()
    new_lines = []
    found_keys = set()
    for line in lines:
        matched = False
        for k, v in desired.items():
            if line.startswith(f"{k}="):
                new_lines.append(f"{k}={v}")
                found_keys.add(k)
                matched = True
                break
        if not matched:
            new_lines.append(line)
    for k, v in desired.items():
        if k not in found_keys:
            new_lines.append(f"{k}={v}")

    new_content = "\n".join(new_lines) + "\n"
    if new_content != content:
        with sftp.open(env_path, "w") as f:
            f.write(new_content)
        print("已更新远端 .env 中的文本模型配置。")


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
        f"{shlex.quote(posixpath.join(remote_root, 'web-vue3'))} && "
        f"rm -f {shlex.quote(posixpath.join(remote_root, 'docker-compose.yml'))} "
        f"{shlex.quote(posixpath.join(remote_root, 'nginx.conf'))} && "
        f"cp -a {shlex.quote(posixpath.join(remote_temp, 'backend'))} "
        f"{shlex.quote(posixpath.join(remote_root, 'backend'))} && "
        f"cp -a {shlex.quote(posixpath.join(remote_temp, 'web-vue3'))} "
        f"{shlex.quote(posixpath.join(remote_root, 'web-vue3'))} && "
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
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 qinjian-deploy-health-check",
                    "Accept": "application/json,text/plain,*/*",
                },
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                body = response.read().decode("utf-8", errors="ignore")
                return True, body
        except urllib.error.URLError as exc:
            last_error = str(exc)
            time.sleep(3)

    return False, last_error


def build_web_vue3_dist() -> bool:
    web_vue3_root = LOCAL_ROOT / "web-vue3"
    if not (web_vue3_root / "package.json").exists():
        print("缺少 web-vue3/package.json，无法构建新版前端。")
        return False
    npm_command = "npm.cmd" if os.name == "nt" else "npm"
    print("构建新版 Vue3 前端...")
    result = subprocess.run([npm_command, "run", "build"], cwd=web_vue3_root)
    if result.returncode != 0:
        print("新版 Vue3 前端构建失败。")
        return False
    if not (web_vue3_root / "dist" / "index.html").exists():
        print("新版 Vue3 构建产物缺少 dist/index.html。")
        return False
    return True


def deploy(
    host: str,
    username: str,
    password: str,
    remote_root: str,
    key_file: str = "",
    allow_demo_agent: bool = False,
) -> int:
    if not host or not username:
        print(
            "缺少远端部署信息，请通过 --host/--username 或环境变量 QJ_REMOTE_HOST/QJ_REMOTE_USER 提供。"
        )
        return 2

    frontend_origin = resolve_frontend_origin(host)
    resolved_key_file = ""
    if key_file:
        key_path = Path(key_file).expanduser()
        if not key_path.exists():
            print(f"指定的 SSH 私钥不存在: {key_path}")
            return 2
        resolved_key_file = str(key_path)

    if not build_web_vue3_dist():
        return 11

    if resolved_key_file:
        print(f"使用 SSH 私钥: {resolved_key_file}")
    elif not password:
        print("未提供 SSH 密码，尝试使用本机 SSH key/agent...")
    print(f"连接服务器 {host} ...")
    try:
        client = connect_client(host, username, password, resolved_key_file)
    except paramiko.SSHException as exc:
        print("SSH 认证失败，请提供 QJ_REMOTE_PASSWORD 或配置可用的 SSH key。")
        print(f"原因: {exc}")
        return 10
    except OSError as exc:
        print("SSH 连接失败，请检查服务器地址、端口和网络。")
        print(f"原因: {exc}")
        return 10
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
        if RELAXED_TEST_ACCOUNT_EMAILS:
            env_code, env_output, env_error = set_remote_env_value(
                client,
                remote_root,
                "RELAXED_TEST_ACCOUNT_EMAILS",
                RELAXED_TEST_ACCOUNT_EMAILS,
            )
            if env_output.strip():
                print(env_output.strip())
            if env_code != 0:
                print(env_error.strip() or "更新 RELAXED_TEST_ACCOUNT_EMAILS 失败")
                return 3
        if allow_demo_agent:
            env_code, env_output, env_error = set_remote_env_value(
                client, remote_root, "ALLOW_DEMO_AGENT", "true"
            )
            if env_output.strip():
                print(env_output.strip())
            if env_code != 0:
                print(env_error.strip() or "更新 ALLOW_DEMO_AGENT 失败")
                return 3
            print("已显式开启演示模式: ALLOW_DEMO_AGENT=true（仅用于演示/路演环境）")
        if env_created:
            print("服务器缺少 .env，已自动生成基础生产配置。")
            print("当前未检测到本机 SILICONFLOW_API_KEY，AI 功能可能暂不可用。")
        print(f"已设置前端来源: {frontend_origin}")
        sync_remote_model_env(sftp, remote_root)
        if RELAXED_TEST_ACCOUNT_EMAILS:
            account_count = len(
                [
                    item
                    for item in RELAXED_TEST_ACCOUNT_EMAILS.replace(";", ",").split(",")
                    if item.strip()
                ]
            )
            print(f"已设置放宽权限测试账号数量: {account_count}")

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
    parser.add_argument("--key-file", default=KEY_FILE)
    parser.add_argument("--remote-root", default=REMOTE_ROOT)
    parser.add_argument(
        "--allow-demo-agent",
        action="store_true",
        help="在远端 .env 显式开启 ALLOW_DEMO_AGENT=true（仅演示/路演服务器使用）",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    sys.exit(
        deploy(
            arguments.host,
            arguments.username,
            arguments.password,
            arguments.remote_root,
            arguments.key_file,
            arguments.allow_demo_agent,
        )
    )
