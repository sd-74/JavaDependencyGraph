from pathlib import Path
from utils.file_utils import find_files
from dependency_graph.java_parser import parse_file
import json

def index_repo(repo_path: str | Path) -> list[dict]:
    paths = find_files(repo_path, (".java",))
    files = []
    for p in paths:
        files.append(parse_file(p))
    return files

def write_jsonl(path: str | Path, items: list[dict]):
    with open(path, "w") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
