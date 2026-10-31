import shutil, os

# 1. Backup maintenance banner
shutil.copyfile('index.html', 'index.html.maintenance.bak')
print('Backed up maintenance banner to index.html.maintenance.bak')

# 2. Copy dist/index.html to root index.html
shutil.copyfile('dist/index.html', 'index.html')
print('Promoted dist/index.html to root index.html')

# 3. Update backend/main.py
with open('backend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if '# ─── Frontend Static Delivery' in line or '# ─── React Frontend Delivery' in line:
        skip = True
    if skip:
        continue
    new_lines.append(line)

replacement = """
# ─── Frontend Delivery (React Production) ───────────────────────────────────
dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dist"))
dist_assets_dir = os.path.join(dist_dir, "assets")
if os.path.exists(dist_assets_dir):
    app.mount("/assets", StaticFiles(directory=dist_assets_dir), name="assets")

@app.get("/", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
@app.get("/app", include_in_schema=False)
async def serve_index():
    react_index = os.path.join(dist_dir, "index.html")
    if os.path.exists(react_index):
        resp = FileResponse(react_index, media_type="text/html")
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    index_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
    if os.path.exists(index_path):
        resp = FileResponse(index_path, media_type="text/html")
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    return {"status": "ok", "message": "FRIDAY AI Engine Operational"}
"""

result = "".join(new_lines) + replacement

with open('backend/main.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(result)

print("Updated backend/main.py successfully.")

