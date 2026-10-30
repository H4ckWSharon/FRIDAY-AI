import paramiko, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('213.133.97.141', username='root', password='AfjbCUvqgdpST8', timeout=15, disabled_algorithms={'kex': ['kex-strict-s-v00@openssh.com']})

def run_cmd(cmd):
    print(f">>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out:
        print(out)
    if err:
        print("[STDERR]", err)

if len(sys.argv) > 1:
    cmd = " ".join(sys.argv[1:])
    run_cmd(cmd)
else:
    run_cmd("ps aux | grep -E 'python|ollama' | grep -v grep")

ssh.close()

