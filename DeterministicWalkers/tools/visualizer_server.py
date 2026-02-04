import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import List, Dict

app = FastAPI(title="Dataset Visualizer API")

# Project Root (parent of tools/)
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
DATA_DIR = PROJECT_ROOT / "data"

# Ensure data directory exists
if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def get_visualizer():
    """Serves the main visualizer HTML file."""
    visualizer_path = PROJECT_ROOT / "visualizer.html"
    if not visualizer_path.exists():
        raise HTTPException(status_code=404, detail="visualizer.html not found")
    return visualizer_path.read_text(encoding="utf-8")

@app.get("/api/datasets")
async def list_datasets() -> List[Dict]:
    """Recursively list all .jsonl files in the data directory."""
    datasets = []
    
    # Files to look for in priority order
    priority_paths = [
        "hydrated-dataset/dialogue_dataset.jsonl",
        "clean_predataset/dialogue_dataset.jsonl",
        "predataset/dialogue_dataset.jsonl"
    ]
    
    # Check priority files first
    for p in priority_paths:
        full_path = DATA_DIR / p
        if full_path.exists():
            datasets.append({
                "name": p,
                "path": str(p).replace("\\", "/"),
                "size": full_path.stat().st_size,
                "priority": True
            })
    
    # Then find all other .jsonl files
    for root, dirs, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith(".jsonl") or file.endswith(".json"):
                rel_path = os.path.relpath(os.path.join(root, file), DATA_DIR).replace("\\", "/")
                # Skip if already in priority
                if any(d["path"] == rel_path for d in datasets):
                    continue
                datasets.append({
                    "name": rel_path,
                    "path": rel_path,
                    "size": Path(os.path.join(root, file)).stat().st_size,
                    "priority": False
                })
                
    return datasets

@app.get("/api/data/{file_path:path}")
async def get_dataset_content(file_path: str):
    """Returns the content of a specific dataset file."""
    # Security check: prevent directory traversal
    safe_path = (DATA_DIR / file_path).resolve()
    if not str(safe_path).startswith(str(DATA_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
        
    if not safe_path.exists() or not safe_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    # Return as FileResponse to support large files and correct caching
    return FileResponse(
        safe_path, 
        media_type="application/x-jsonlines" if file_path.endswith(".jsonl") else "application/json",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
