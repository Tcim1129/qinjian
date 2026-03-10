import paramiko
import os
import sys

def deploy():
    host = "143.198.110.145"
    username = "root"
    password = "7507906119HJL"

    files_to_upload = [
        ("web/index.html", "/root/qinjian/web/index.html"),
        ("web/js/app.js", "/root/qinjian/web/js/app.js"),
        ("web/js/api.js", "/root/qinjian/web/js/api.js"),
        ("backend/app/main.py", "/root/qinjian/backend/app/main.py")
    ]

    print("🚀 开始部署更新到服务器...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print("[1/4] 连接服务器...")
        client.connect(host, username=username, password=password, timeout=30)
        print("✅ 连接成功")

        print("[2/4] 上传修改的文件...")
        sftp = client.open_sftp()
        for local_path, remote_path in files_to_upload:
            if os.path.exists(local_path):
                print(f"  -> 上传 {local_path} 到 {remote_path}")
                sftp.put(local_path, remote_path)
            else:
                print(f"  -> 警告: {local_path} 不存在")
        sftp.close()
        print("✅ 文件上传完成")

        print("[3/4] 删除服务器旧路径并重启服务...")
        commands = [
            "rm -rf /opt/qinjian",
            "rm -f /root/qinjian/auto_deploy.py /root/qinjian/check_logs.py",
            "cd /root/qinjian && docker compose down",
            "cd /root/qinjian && docker compose up -d --build",
            "sleep 5"
        ]

        for cmd in commands:
            print(f"执行: {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd, timeout=300)
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode("utf-8", errors="ignore")
            err = stderr.read().decode("utf-8", errors="ignore")
            if out: print(out.strip())
            if err and exit_status != 0: print(f"错误: {err.strip()}")

        print("[4/4] 检查服务状态...")
        stdin, stdout, stderr = client.exec_command("cd /root/qinjian && docker compose ps")
        print(stdout.read().decode("utf-8", errors="ignore"))

        print("🎉 部署完成！访问地址: http://143.198.110.145:8080")
        return True

    except Exception as e:
        print(f"❌ 部署失败: {e}")
        return False
    finally:
        client.close()

if __name__ == "__main__":
    success = deploy()
    sys.exit(0 if success else 1)
