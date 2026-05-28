import os
from typing import Any
from assist_runtime.runtime.cache import RuntimeCache

class RepositoryService:
    """Handles low-level file traversal and data gathering for repositories."""

    @staticmethod
    def scan_repository(repo_path: str) -> str:
        """Scans the repository and returns a cache reference ID to the raw data."""
        ignore_dirs = {".git", "__pycache__", "node_modules", "env", "venv"}
        file_list = []
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, repo_path)
                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    size = 0
                file_list.append({
                    "path": rel_path,
                    "absolute_path": full_path,
                    "size": size,
                    "ext": os.path.splitext(f)[1]
                })
                
        # Structure the payload
        payload = {
            "total_files": len(file_list),
            "files": file_list
        }
        
        return RuntimeCache.save_json(payload, prefix="repo_scan")
