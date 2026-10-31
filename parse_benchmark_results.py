import json, os

local_path = r'C:\Users\sharo\.gemini\antigravity\brain\1ebb91ec-c9a7-41f9-925d-55b9cad706ed\scratch\benchmark_results.json'
with open(local_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Models evaluated: {list(data.keys())}\n")
for model_name, queries in data.items():
    print("=" * 80)
    print(f"MODEL: {model_name}")
    print("=" * 80)
    total_time = sum(q.get('elapsed_sec', 0) for q in queries.values())
    avg_tps = sum(q.get('tps', 0) for q in queries.values()) / len(queries)
    total_words = sum(q.get('word_count', 0) for q in queries.values())
    refused_count = sum(1 for q in queries.values() if q.get('refused'))
    print(f"Total Inference Time: {total_time:.1f}s | Avg Generation TPS: {avg_tps:.2f} | Total Words: {total_words} | Refusal Rate: {refused_count}/5\n")
    for qid, q in queries.items():
        print(f"--- [{qid}] {q.get('title')} ---")
        print(f"  Time: {q.get('elapsed_sec')}s | TPS: {q.get('tps')} | Keywords: {q.get('keyword_score')} | Refused: {q.get('refused')} | Words: {q.get('word_count')}")
        print(f"  Matched Keywords: {q.get('matched_keywords')}")
        print(f"  Response Sample (first 250 chars):\n    {q.get('response', '')[:250].strip().replace(chr(10), ' ')}")
        print()

