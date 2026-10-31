import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

extra_terms = [
    'qwen',
    'abliterated',
    'mradermacher',
    'llama',
    'cyber-8b',
    'cyber-27b',
    '27b',
    '8b',
    'dolphin3',
]

for fn in ['index.html', 'admin.html']:
    with open(fn, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    print(f"=== Scanning extra terms in {fn} ===")
    matches = []
    for line_idx, line in enumerate(lines, 1):
        line_lower = line.lower()
        for term in extra_terms:
            if term in line_lower:
                matches.append((line_idx, term, line.strip()))
    print(f"Matches count in {fn}: {len(matches)}")
    for line_idx, term, content in matches:
        print(f"  Line {line_idx} [{term}]: {content[:100]}")
