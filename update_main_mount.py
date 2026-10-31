import os

with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add StaticFiles import
if 'from fastapi.staticfiles import StaticFiles' not in content:
    content = content.replace(
        'from fastapi.responses import FileResponse',
        'from fastapi.responses import FileResponse\nfrom fastapi.staticfiles import StaticFiles'
    )

addition = """
# ─── React Frontend Delivery ────────────────────────────────────────────────
dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dist"))
dist_assets_dir = os.path.join(dist_dir, "assets")
if os.path.exists(dist_assets_dir):
    app.mount("/assets", StaticFiles(directory=dist_assets_dir), name="assets")

@app.get("/app", include_in_schema=False)
async def serve_react_app():
    react_index = os.path.join(dist_dir, "index.html")
    if os.path.exists(react_index):
        resp = FileResponse(react_index, media_type="text/html")
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp
    return {"status": "error", "message": "React build not found"}
"""

if 'serve_react_app' not in content:
    content += addition

with open('backend/main.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("Updated backend/main.py successfully.")

