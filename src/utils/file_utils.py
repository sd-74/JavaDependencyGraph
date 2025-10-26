from pathlib import Path

def find_files(root: str | Path, exts=(".java",)) -> list[Path]:
    root = Path(root)
    return [p for p in root.rglob("*") if p.suffix in exts]
