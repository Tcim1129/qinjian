import paramiko
import time
import sys


def deploy():
    # 服务器信息
    host = "143.198.110.145"
    username = "root"
    password = "7507906119HJL"

    print("🚀 开始部署亲健项目到服务器...")
    print(f"📍 服务器: {host}")
    print()

    # 创建SSH客户端
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # 连接服务器
        print("[1/6] 连接服务器...")
        client.connect(host, username=username, password=password, timeout=30)
        print("✅ 连接成功")
        print()

        # 执行部署命令
        commands = [
            ("[2/6] 进入项目目录", "cd /opt/qinjian && pwd"),
            ("[3/6] 拉取最新代码", "cd /opt/qinjian && git pull origin main"),
            ("[4/6] 停止现有服务", "cd /opt/qinjian && docker-compose down"),
            ("[5/6] 构建并启动服务", "cd /opt/qinjian && docker-compose up -d --build"),
            ("[6/6] 等待服务启动", "sleep 10"),
        ]

        for desc, cmd in commands:
            print(desc)
            print(f"执行: {cmd}")

            stdin, stdout, stderr = client.exec_command(cmd, timeout=300)
            exit_status = stdout.channel.recv_exit_status()

            output = stdout.read().decode("utf-8", errors="ignore")
            error = stderr.read().decode("utf-8", errors="ignore")

            if output:
                print(f"输出:\n{output}")
            if error and exit_status != 0:
                print(f"错误:\n{error}")
                if exit_status != 0:
                    print(f"❌ 命令失败，退出码: {exit_status}")
                    return False

            print("✅ 完成")
            print()

        # 检查服务状态
        print("🔍 检查服务状态...")
        stdin, stdout, stderr = client.exec_command(
            "cd /opt/qinjian && docker-compose ps"
        )
        print(stdout.read().decode("utf-8", errors="ignore"))

        # 检查后端日志
        print("📋 后端服务日志 (最近20行):")
        stdin, stdout, stderr = client.exec_command(
            "cd /opt/qinjian && docker-compose logs --tail=20 backend"
        )
        logs = stdout.read().decode("utf-8", errors="ignore")
        print(logs)

        print()
        print("=" * 50)
        print("🎉 部署完成！")
        print("=" * 50)
        print()
        print("访问地址:")
        print(f"  Web前端: http://{host}:8080")
        print(f"  API接口: http://{host}:8080/api/health")
        print()
        print("常用命令:")
        print(f"  ssh root@{host}")
        print("  cd /opt/qinjian && docker-compose logs -f")

        return True

    except Exception as e:
        print(f"❌ 部署失败: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        client.close()


if __name__ == "__main__":
    success = deploy()
    sys.exit(0 if success else 1)
