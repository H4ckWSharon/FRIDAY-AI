import sys
sys.path.insert(0, 'backend')
from routes.chat import _sanitize_response

LOOKAHEAD_WINDOW = 64

def run_split_simulation(chunks):
    stream_buffer = ""
    emitted = []
    for chunk in chunks:
        stream_buffer += chunk
        stream_buffer = _sanitize_response(stream_buffer)
        if len(stream_buffer) > LOOKAHEAD_WINDOW:
            emit_limit = len(stream_buffer) - LOOKAHEAD_WINDOW
            last_break = -1
            for d in " \n\t.,;:!?)]}\"'":
                pos = stream_buffer.rfind(d, 0, emit_limit)
                if pos > last_break:
                    last_break = pos
            emit_len = (last_break + 1) if last_break != -1 else emit_limit
            safe_to_emit = stream_buffer[:emit_len]
            stream_buffer = stream_buffer[emit_len:]
            if safe_to_emit:
                emitted.append(safe_to_emit)
    if stream_buffer:
        final_chunk = _sanitize_response(stream_buffer)
        if final_chunk:
            emitted.append(final_chunk)
    return "".join(emitted)

# Worst-case split where 'Cognitive Computations' is right at the 64-char boundary
prefix = "A" * 40 + " "  # 41 chars
chunk1 = prefix + "Cognitive " # 51 chars
chunk2 = "Computations is our team."
full = run_split_simulation([chunk1, chunk2])
print("Result 1:", full)
assert "Cognitive Computations" not in full
assert "FRIDAY AI" in full

# Another worst case: orcasaq-cyber-27b split into 3 chunks
chunk_a = "B" * 60 + " orca"
chunk_b = "saq-cyber-"
chunk_c = "27b:latest verified."
full2 = run_split_simulation([chunk_a, chunk_b, chunk_c])
print("Result 2:", full2)
assert "orcasaq" not in full2.lower()
assert "friday Cyber Pro" in full2

print("Stress test PASSED!")
