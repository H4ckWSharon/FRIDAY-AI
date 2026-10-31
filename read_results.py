import paramiko, sys, json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('213.133.97.141', username='root', password='AfjbCUvqgdpST8', timeout=15)

stdin, stdout, stderr = ssh.exec_command("cat /tmp/benchmark_results.json", timeout=15)
data = json.loads(stdout.read().decode('utf-8', errors='replace'))

for model, queries in data.items():
    print(f"==================================================")
    print(f"MODEL: {model}")
    print(f"==================================================")
    for qid, qdata in queries.items():
        print(f"--- QUERY: {qdata.get('title')} ---")
        print(f"Success: {qdata.get('success')}, Time: {qdata.get('elapsed_sec')}s, TPS: {qdata.get('tps')}, Refused: {qdata.get('refused')}")
        print(f"Keyword score: {qdata.get('keyword_score')}, Matched: {qdata.get('matched_keywords')}")
        print("\n--- EXACT RESPONSE ---")
        print(qdata.get('response'))
        print("\n")

ssh.close()

