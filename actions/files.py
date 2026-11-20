"""Read-only file search, limited to a few user folders."""
import os
from pathlib import Path

SEARCH_ROOTS = [Path.home() / d for d in ("Documents", "Downloads", "Desktop")]
MAX_RESULTS, MAX_DEPTH, MAX_ENTRIES = 10, 4, 20000


def search_files(query: str, roots: list[Path] | None = None) -> str:
    query = query.strip().lower()
    if len(query) < 2:
        raise ValueError("Search text is too short.")
    found, seen = [], 0
    for root in roots if roots is not None else SEARCH_ROOTS:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            depth = len(Path(dirpath).relative_to(root).parts)
            dirnames[:] = [d for d in dirnames if not d.startswith(".")] if depth < MAX_DEPTH else []
            for name in filenames:
                seen += 1
                if seen > MAX_ENTRIES:
                    break
                if query in name.lower() and not name.startswith("."):
                    found.append(str(Path(dirpath) / name))
                    if len(found) >= MAX_RESULTS:
                        return "Found:\n" + "\n".join(found)
    return "Found:\n" + "\n".join(found) if found else f"No files matching {query!r} in Documents, Downloads or Desktop."
