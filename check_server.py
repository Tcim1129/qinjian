import paramiko
import sys

def check():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('129.212.216.187', username='root', password='7507906119HJL')
    
    stdin, stdout, stderr = client.exec_command('cd /root/qinjian && docker compose ps')
    print("=== docker compose ps ===")
    print(stdout.read().decode())
    
    stdin, stdout, stderr = client.exec_command('cd /root/qinjian && docker compose logs web')
    print("\n=== docker compose logs web ===")
    print(stdout.read().decode())
    
    stdin, stdout, stderr = client.exec_command('cd /root/qinjian && cat nginx.conf')
    print("\n=== nginx.conf ===")
    print(stdout.read().decode())
    
    client.close()

if __name__ == '__main__':
    check()
