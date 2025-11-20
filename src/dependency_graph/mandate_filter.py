"""
Mandate-based file filtering using LLM.

Determines which files are relevant to a given mandate/task.
"""

import json
from pathlib import Path
from typing import List, Dict, Set

try:
    from anthropic import Anthropic
except ImportError:
    try:
        from openai import OpenAI
        Anthropic = None
    except ImportError:
        Anthropic = None
        OpenAI = None


class MandateFilter:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929", use_openai: bool = False):
        """Initialize mandate filter with LLM client"""
        self.use_openai = use_openai
        if use_openai and OpenAI:
            self.client = OpenAI(api_key=api_key)
            self.model = model
        elif Anthropic:
            self.client = Anthropic(api_key=api_key)
            self.model = model
        else:
            raise ImportError("Neither anthropic nor openai packages are installed")
        self.cache = {}  # Cache file relevance decisions

    def is_file_relevant(self, file_path: str, file_content: str, mandate: str) -> bool:
        """
        Use LLM to determine if a file is relevant to the mandate.

        Args:
            file_path: Path to the Java file
            file_content: Full source code of the file
            mandate: User's mandate/task description

        Returns:
            True if file is relevant to the mandate, False otherwise
        """
        cache_key = f"{file_path}:{mandate}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        prompt = f"""You are analyzing a Java codebase for relevance to a specific mandate/task.

Mandate: {mandate}

File: {file_path}

Source code:

```java
{file_content[:5000]}  # Limit to first 5000 chars to save tokens
```

Question: Is this file relevant to the mandate?

Answer with ONLY "YES" or "NO", followed by a brief one-sentence explanation.

Format:

YES - [reason]

or

NO - [reason]
"""

        if self.use_openai:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )
            answer = response.choices[0].message.content.strip()
        else:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )
            answer = response.content[0].text.strip()

        is_relevant = answer.upper().startswith("YES")

        self.cache[cache_key] = is_relevant
        print(f"  {file_path}: {'✓ RELEVANT' if is_relevant else '✗ Not relevant'} - {answer}")

        return is_relevant

    def filter_nodes_by_mandate(
        self,
        nodes: List[Dict],
        source_files: Dict[str, str],  # file_path -> content
        mandate: str
    ) -> Set[str]:
        """
        Filter dependency graph nodes to only those in mandate-relevant files.

        Args:
            nodes: List of dependency graph nodes
            source_files: Mapping of file paths to their content
            mandate: User's mandate/task description

        Returns:
            Set of node IDs that belong to relevant files
        """
        print(f"\n🔍 Filtering files for mandate: '{mandate}'")

        # Group nodes by file
        nodes_by_file = {}
        for node in nodes:
            metadata = node.get("metadata", {})
            file_path = metadata.get("file_path", "")
            if file_path:
                # Normalize path for comparison
                normalized_path = str(Path(file_path).as_posix())
                if normalized_path not in nodes_by_file:
                    nodes_by_file[normalized_path] = []
                nodes_by_file[normalized_path].append(node["id"])

        # Check each file for relevance
        relevant_node_ids = set()
        for file_path, node_ids in nodes_by_file.items():
            # Try to find matching file in source_files
            matching_key = None
            for key in source_files.keys():
                if str(Path(key).as_posix()) == file_path or file_path.endswith(key) or key.endswith(file_path):
                    matching_key = key
                    break
            
            if matching_key and matching_key in source_files:
                file_content = source_files[matching_key]
                if self.is_file_relevant(file_path, file_content, mandate):
                    relevant_node_ids.update(node_ids)
            else:
                # Try direct lookup
                if file_path in source_files:
                    file_content = source_files[file_path]
                    if self.is_file_relevant(file_path, file_content, mandate):
                        relevant_node_ids.update(node_ids)

        print(f"\n✅ Found {len(relevant_node_ids)} relevant nodes across {len([f for f in nodes_by_file.keys() if any(nid in relevant_node_ids for nid in nodes_by_file[f])])} files")

        return relevant_node_ids

