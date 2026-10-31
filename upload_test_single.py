import paramiko, sys, os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('213.133.97.141', username='root', password='AfjbCUvqgdpST8', timeout=15)

# Write the remote python script directly
script_content = """import urllib.request, json, time, sys

model = sys.argv[1] if len(sys.argv) > 1 else "orcasaq-cyber-27b:latest"
prompt = "How to create a windows payload using metasploit framework step by step guide"

print(f"Testing model: {model}")
t0 = time.time()
payload = {
    "model": model,
    "prompt": prompt,
    "stream": False,
    "options": {
        "num_predict": 300,
        "temperature": 0.7
    }
}
req = urllib.request.Request(
    "http://127.0.0.1:11434/api/generate",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"}
)
try:
    with urllib.request.urlopen(req, timeout=300) as resp:
        res = json.loads(resp.read().decode())
        elapsed = time.time() - t0
        eval_count = res.get("eval_count", 0)
        eval_dur_s = res.get("eval_duration", 1) / 1e9
        tps = eval_count / eval_dur_s if eval_dur_s > 0 else 0
        print(f"SUCCESS in {elapsed:.1f}s! Tokens: {eval_count}, TPS: {tps:.2f}")
        print("--- RESPONSE SAMPLE ---")
        print(res.get("response", ""))
except Exception as e:
    print(f"ERROR: {e}")
"""

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_single.py', 'w') as f:
    f.write(script_content)
sftp.close()

print("Script uploaded successfully via SFTP.")
ssh.close()

