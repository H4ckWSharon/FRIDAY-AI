import paramiko, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('213.133.97.141', username='root', password='AfjbCUvqgdpST8', timeout=15)

stdin, stdout, stderr = ssh.exec_command("tail -n 25 /tmp/benchmark_live.log 2>/dev/null; pgrep -fa benchmark_suite", timeout=15)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()

