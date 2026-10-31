import paramiko, sys, json, time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('213.133.97.141', username='root', password='AfjbCUvqgdpST8', timeout=15)

def run_remote(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace')

print("=== CHECK OLLAMA PS ===")
print(run_remote("ollama ps"))

print("\n=== TEST BARONLLM GENERATE (10 tokens) ===")
cmd_test = """python3 -c "
import urllib.request, json, time
t0 = time.time()
try:
    req = urllib.request.Request('http://127.0.0.1:11434/api/generate', data=json.dumps({'model': 'huihui_ai/baronllm-abliterated:latest', 'prompt': 'Hi, who are you? Reply in 1 sentence.', 'stream': False, 'options': {'num_predict': 30}}).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        print('SUCCESS:', json.loads(r.read())['response'])
except Exception as e:
    print('ERROR:', e)
print('ELAPSED:', round(time.time() - t0, 2))
" """
print(run_remote(cmd_test))

print("\n=== TEST ORCASAQ-27B GENERATE (10 tokens) ===")
cmd_orca = """python3 -c "
import urllib.request, json, time
t0 = time.time()
try:
    req = urllib.request.Request('http://127.0.0.1:11434/api/generate', data=json.dumps({'model': 'orcasaq-cyber-27b:latest', 'prompt': 'Hi, who are you? Reply in 1 sentence.', 'stream': False, 'options': {'num_predict': 30}}).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r:
        print('SUCCESS:', json.loads(r.read())['response'])
except Exception as e:
    print('ERROR:', e)
print('ELAPSED:', round(time.time() - t0, 2))
" """
print(run_remote(cmd_orca))

ssh.close()

