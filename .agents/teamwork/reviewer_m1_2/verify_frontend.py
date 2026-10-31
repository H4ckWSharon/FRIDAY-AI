import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

phrases = [
    'jr hacker',
    'the jr',
    'the advanced',
    'advanced pentester',
    'junior pentester',
    'dolphin',
    'baronllm',
    'eric hartford',
    'cognitive computations',
    'huihui',
    'ravichandranj',
    'ollama',
    'friday v1',
    'orcasaq',
]

for fn in ['index.html', 'admin.html']:
    with open(fn, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    print(f"=== Scanning {fn} ({len(lines)} lines) ===")
    matches = []
    for line_idx, line in enumerate(lines, 1):
        line_lower = line.lower()
        for phrase in phrases:
            if phrase in line_lower:
                matches.append((line_idx, phrase, line.strip()))
    print(f"Total matching lines in {fn}: {len(matches)}")
    for line_idx, phrase, content in matches:
        print(f"  Line {line_idx} [{phrase}]: {content[:100]}")
print("Scan completed successfully.")
