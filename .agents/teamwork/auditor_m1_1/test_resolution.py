import sys
sys.path.insert(0, 'backend')
from schemas import ChatRequest, ChatMessage
from routes.chat import _prepare_messages
from fastapi import HTTPException

def test_model_resolution():
    # 1. Default (None)
    req = ChatRequest(messages=[ChatMessage(role="user", content="hello")], model=None)
    msgs, model = _prepare_messages(req)
    assert model == "orcasaq-cyber-27b:latest", f"Expected default model, got {model}"

    # 2. Legacy Dolphin
    req = ChatRequest(messages=[ChatMessage(role="user", content="hello")], model="hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0")
    msgs, model = _prepare_messages(req)
    assert model == "orcasaq-cyber-27b:latest", f"Expected remapped model, got {model}"

    # 3. Legacy BaronLLM
    req = ChatRequest(messages=[ChatMessage(role="user", content="hello")], model="huihui_ai/baronllm-abliterated:latest")
    msgs, model = _prepare_messages(req)
    assert model == "orcasaq-cyber-27b:latest", f"Expected remapped model, got {model}"

    # 4. Valid explicit model
    req = ChatRequest(messages=[ChatMessage(role="user", content="hello")], model="orcasaq-cyber-27b:latest")
    msgs, model = _prepare_messages(req)
    assert model == "orcasaq-cyber-27b:latest", f"Expected explicit model, got {model}"

    # 5. Invalid model
    req = ChatRequest(messages=[ChatMessage(role="user", content="hello")], model="unapproved-model")
    try:
        _prepare_messages(req)
        assert False, "Should have raised HTTPException 400"
    except HTTPException as e:
        assert e.status_code == 400
        print("Invalid model rejected with 400:", e.detail)

    print("All model resolution tests PASSED!")

if __name__ == "__main__":
    test_model_resolution()
