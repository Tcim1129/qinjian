import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('143.198.110.145', username='root', password='7507906119HJL')

stdin, stdout, stderr = ssh.exec_command('docker compose -f /opt/qinjian/docker-compose.yml logs backend --tail=100')
print(stdout.read().decode())
print(stderr.read().decode())

ssh.close()
