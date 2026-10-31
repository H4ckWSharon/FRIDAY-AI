import paramiko, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('213.133.97.141', username='root', password='AfjbCUvqgdpST8', timeout=15)

cmd = sys.argv[1] if len(sys.argv) > 1 else "journalctl -u ollama -n 35 --no-pager"
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
