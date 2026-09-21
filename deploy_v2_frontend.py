from __future__ import annotations

import argparse
import os
import posixpath
import shlex
import tarfile
import tempfile
from pathlib import Path

from deploy_current_workspace import (
    build_qinjian_ui_dist,
    connect_client,
    run_remote,
)


LOCAL_ROOT = Path(__file__).resolve().parent
DEFAULT_REMOTE_ROOT = "/root/qinjian"
LEGACY_SERVICES = ("web", "backend", "db", "redis")


def legacy_snapshot(client, remote_root: str) -> str:
    services = " ".join(shlex.quote(service) for service in LEGACY_SERVICES)
    command = (
        f"cd {shlex.quote(remote_root)} && "
        "if docker compose version >/dev/null 2>&1; then compose='docker compose'; "
        "else compose='docker-compose'; fi; "
        f"for service in {services}; do "
        "cid=$($compose ps -q \"$service\" | head -n 1); "
        "if [ -n \"$cid\" ]; then "
        "docker inspect --format \"$service|{{.Id}}|{{.State.StartedAt}}|{{.RestartCount}}\" \"$cid\"; "
        "else echo \"$service|missing\"; fi; done"
    )
    code, output, error = run_remote(client, command)
    if code != 0:
        raise RuntimeError(error.strip() or "无法读取旧版服务状态")
    return output.strip()


def create_v2_bundle() -> Path:
    bundle_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz")
    bundle_file.close()
    bundle_path = Path(bundle_file.name)
    required = (
        LOCAL_ROOT / "qinjian-ui-preview" / "dist",
        LOCAL_ROOT / "docker-compose.yml",
        LOCAL_ROOT / "nginx-v2.conf",
    )
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"缺少新版部署文件: {path}")
    with tarfile.open(bundle_path, "w:gz") as archive:
        archive.add(required[0], arcname="qinjian-ui-preview/dist")
        archive.add(required[1], arcname="docker-compose.yml")
        archive.add(required[2], arcname="nginx-v2.conf")
    return bundle_path


def deploy_v2(host: str, username: str, password: str, remote_root: str, key_file: str = "") -> int:
    if not build_qinjian_ui_dist():
        return 12
    client = connect_client(host, username, password, key_file)
    before_legacy = legacy_snapshot(client, remote_root)
    sftp = client.open_sftp()
    bundle_path = create_v2_bundle()
    remote_bundle = posixpath.join(remote_root, ".deploy_v2_bundle.tar.gz")
    try:
        try:
            sftp.stat(remote_root)
        except FileNotFoundError:
            sftp.mkdir(remote_root)
        sftp.put(str(bundle_path), remote_bundle)
    finally:
        bundle_path.unlink(missing_ok=True)
        sftp.close()

    temp_root = f"{remote_root}.v2-next"
    command = (
        f"rm -rf {shlex.quote(temp_root)} && "
        f"mkdir -p {shlex.quote(temp_root)} && "
        f"tar -xzf {shlex.quote(remote_bundle)} -C {shlex.quote(temp_root)} && "
        f"mkdir -p {shlex.quote(posixpath.join(remote_root, 'qinjian-ui-preview'))} && "
        f"rm -rf {shlex.quote(posixpath.join(remote_root, 'qinjian-ui-preview', 'dist.previous'))} && "
        f"if [ -d {shlex.quote(posixpath.join(remote_root, 'qinjian-ui-preview', 'dist'))} ]; then "
        f"mv {shlex.quote(posixpath.join(remote_root, 'qinjian-ui-preview', 'dist'))} "
        f"{shlex.quote(posixpath.join(remote_root, 'qinjian-ui-preview', 'dist.previous'))}; fi && "
        f"mv {shlex.quote(posixpath.join(temp_root, 'qinjian-ui-preview', 'dist'))} "
        f"{shlex.quote(posixpath.join(remote_root, 'qinjian-ui-preview', 'dist'))} && "
        f"cp {shlex.quote(posixpath.join(temp_root, 'docker-compose.yml'))} "
        f"{shlex.quote(posixpath.join(remote_root, 'docker-compose.yml'))} && "
        f"cp {shlex.quote(posixpath.join(temp_root, 'nginx-v2.conf'))} "
        f"{shlex.quote(posixpath.join(remote_root, 'nginx-v2.conf'))} && "
        f"rm -rf {shlex.quote(temp_root)} {shlex.quote(remote_bundle)} && "
        f"cd {shlex.quote(remote_root)} && "
        "if docker compose version >/dev/null 2>&1; then "
        "docker compose up -d --no-deps --force-recreate web-v2 && "
        "docker compose exec -T web-v2 test -f /usr/share/nginx/html/index.html; "
        "else docker-compose up -d --no-deps --force-recreate web-v2 && "
        "docker-compose exec -T web-v2 test -f /usr/share/nginx/html/index.html; fi"
    )
    code, output, error = run_remote(client, command, timeout=1200)
    if output.strip():
        print(output.strip())
    if code != 0:
        print(error.strip() or "新版前端容器启动失败")
        client.close()
        return code

    verify_command = (
        f"cd {shlex.quote(remote_root)} && "
        "if docker compose version >/dev/null 2>&1; then docker compose ps web-v2; "
        "else docker-compose ps web-v2; fi && "
        "curl -fsS http://127.0.0.1/ >/dev/null && "
        "curl -fsS http://127.0.0.1/api/health"
    )
    verify_code, output, error = run_remote(client, verify_command)
    if verify_code != 0:
        print(error.strip() or "新版端口或共用后端健康检查失败")
        client.close()
        return verify_code
    print(output.strip())

    after_legacy = legacy_snapshot(client, remote_root)
    if after_legacy != before_legacy:
        print("安全检查失败：新版部署期间旧版或后端容器状态发生变化。")
        print("部署前：")
        print(before_legacy)
        print("部署后：")
        print(after_legacy)
        client.close()
        return 13
    print("旧版 web、backend、db、redis 的容器 ID、启动时间和重启次数均未变化。")
    client.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="只部署亲健新版前端到 80 端口，不重启后端")
    parser.add_argument("--host", default=os.getenv("QJ_REMOTE_HOST", ""))
    parser.add_argument("--username", default=os.getenv("QJ_REMOTE_USER", "root"))
    parser.add_argument("--password", default=os.getenv("QJ_REMOTE_PASSWORD", ""))
    parser.add_argument("--key-file", default=os.getenv("QJ_REMOTE_KEY_FILE", ""))
    parser.add_argument("--remote-root", default=DEFAULT_REMOTE_ROOT)
    args = parser.parse_args()
    if not args.host:
        parser.error("请通过 --host 或 QJ_REMOTE_HOST 提供服务器地址")
    return deploy_v2(args.host, args.username, args.password, args.remote_root, args.key_file)


if __name__ == "__main__":
    raise SystemExit(main())
