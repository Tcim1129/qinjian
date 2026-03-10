import paramiko

def check_server():
    host = "143.198.110.145"
    username = "root"
    password = "7507906119HJL"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print("🔍 正在连接服务器检查状态...")
        client.connect(host, username=username, password=password, timeout=30)
        
        commands = [
            "echo '--- 检查 docker 进程 ---'",
            "cd /root/qinjian && docker compose ps",
            "echo '--- 检查 Nginx 日志 (最后20行) ---'",
            "cd /root/qinjian && docker compose logs --tail=20 web",
            "echo '--- 检查后端日志 (最后20行) ---'",
            "cd /root/qinjian && docker compose logs --tail=20 backend",
            "echo '--- 检查文件目录是否存在 ---'",
            "ls -la /root/qinjian/web"
        ]
        
        for cmd in commands:
            stdin, stdout, stderr = client.exec_command(cmd)
            out = stdout.read().decode("utf-8", errors="ignore")
            err = stderr.read().decode("utf-8", errors="ignore")
            if out: print(out)
            if err: print(f"错误: {err}")
            
    except Exception as e:
        print(f"执行诊断脚本时出错: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    check_server()
