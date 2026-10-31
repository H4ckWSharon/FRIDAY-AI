import paramiko, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('213.133.97.141', username='root', password='AfjbCUvqgdpST8', timeout=15)

sftp = ssh.open_sftp()
local_file = r'c:\Users\sharo\Desktop\friday\index.html'
remote_file = '/opt/friday/index.html'
print(f"Uploading {local_file} -> {remote_file}...")
sftp.put(local_file, remote_file)
sftp.close()

stdin, stdout, stderr = ssh.exec_command("grep -n 'friday-maintenance-banner' /opt/friday/index.html")
out = stdout.read().decode('utf-8', errors='replace')
print("VPS verification:")
print(out)

ssh.close()

