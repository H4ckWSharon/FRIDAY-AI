import paramiko, time, sys, json, os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VPS_HOST = "213.133.97.141"
VPS_USER = "root"
VPS_PASS = "AfjbCUvqgdpST8"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=20)

print("[*] Waiting for benchmark completion...")
while True:
    stdin, stdout, stderr = ssh.exec_command("pgrep -fa benchmark_suite; tail -n 5 /tmp/benchmark_live.log 2>/dev/null")
    out = stdout.read().decode('utf-8', errors='replace')
    print(out.strip())
    if "BENCHMARK COMPLETED SUCCESSFULLY" in out or "benchmark_suite" not in out:
        print("[*] Benchmark complete!")
        break
    time.sleep(15)

# Download results JSON
sftp = ssh.open_sftp()
local_path = r"C:\Users\sharo\.gemini\antigravity\brain\1ebb91ec-c9a7-41f9-925d-55b9cad706ed\scratch\benchmark_results.json"
os.makedirs(os.path.dirname(local_path), exist_ok=True)
sftp.get("/tmp/benchmark_results.json", local_path)
sftp.close()
ssh.close()
print(f"[OK] Downloaded results to {local_path}")

