import os

# 1. Update backend/config.py
with open('backend/config.py', 'r', encoding='utf-8') as f:
    cfg = f.read()

if 'maintenance_mode: bool' not in cfg:
    cfg = cfg.replace(
        'backend_port: int = 8000',
        'backend_port: int = 8000\n    maintenance_mode: bool = True'
    )
    with open('backend/config.py', 'w', encoding='utf-8', newline='\n') as f:
        f.write(cfg)
    print('Added maintenance_mode: bool = True to backend/config.py')

# 2. Update backend/main.py
with open('backend/main.py', 'r', encoding='utf-8') as f:
    main_code = f.read()

target = 'req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"\n    request.state.request_id = req_id'
replacement = '''req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
    request.state.request_id = req_id

    # 0. Global Maintenance Lockdown Gate
    if getattr(settings, "maintenance_mode", True):
        p = request.url.path
        if p.startswith("/api/chat") or p.startswith("/api/conversations") or p.startswith("/api/subscription"):
            return JSONResponse(
                status_code=503,
                content={
                    "status": "maintenance",
                    "error": "maintenance_mode_active",
                    "detail": "Website Temporarily Locked. Scheduled maintenance active across all nodes. Chat sessions and operator consoles are locked. Resuming tomorrow.",
                    "message": "Website Temporarily Locked. Scheduled maintenance active across all nodes. Chat sessions and operator consoles are locked. Resuming tomorrow.",
                    "resuming": "tomorrow",
                },
                headers={"X-Request-ID": req_id, "Retry-After": "86400"},
            )'''

if 'Global Maintenance Lockdown Gate' not in main_code:
    main_code = main_code.replace(target, replacement, 1)
    with open('backend/main.py', 'w', encoding='utf-8', newline='\n') as f:
        f.write(main_code)
    print('Added Global Maintenance Lockdown Gate to backend/main.py')
else:
    print('Maintenance Gate already present')
