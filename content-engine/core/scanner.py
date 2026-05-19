"""
Repo Scanner — Extracted from OpenAgent legacy

Source: OpenAgent/legacy/scanner.py (71 lines)
Extract date: 2026-05-18
Adaptation: Stdlib only, returns dict format for repo_assessor.py

Contract:
- scan(repo_path) returns dict with keys: file_tree (str), ast_summary (str), test_list (str)
- Pure stdlib (os, ast, subprocess, sys) — no external dependencies
"""

import os
import ast
import subprocess
import sys
from typing import Dict, Any


class RepoScanner:
    """Scan repository structure and extract code context."""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def scan(self) -> Dict[str, str]:
        """
        Scan repository and return structured context.
        
        Returns:
            Dict with keys: file_tree (str), ast_summary (str), test_list (str)
        """
        file_tree = self._get_file_tree()
        ast_summary = self._extract_ast_summary(file_tree)
        test_list = self._collect_tests()
        
        return {
            "file_tree": "\n".join(file_tree),
            "ast_summary": ast_summary,
            "test_list": "\n".join(test_list)
        }

    def _get_file_tree(self) -> list[str]:
        """Get file tree with smart truncation (60 file limit)."""
        tree = []
        for root, dirs, files in os.walk(self.repo_path):
            if '.git' in dirs:
                dirs.remove('.git')
            if '.venv' in dirs:
                dirs.remove('.venv')
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')
            for file in files:
                tree.append(os.path.relpath(os.path.join(root, file), self.repo_path).replace("\\", "/"))

        test_files = [f for f in tree if f.startswith('tests/') and f.endswith('.py')]
        py_files = [f for f in tree if f.endswith('.py') and f not in test_files]
        config_files = [f for f in tree if f in ["pyproject.toml", ".env.example", "Cargo.toml"]]
        doc_files = [f for f in tree if f in ["README.md", "AGENT_CONTRACT.md", "docs/state/current.md", "current.md"]]
        
        handled = set(test_files + py_files + config_files + doc_files)
        other_files = [f for f in tree if f not in handled]
        
        limit = 60
        budget_for_others = max(0, limit - len(test_files))
        
        part_py = py_files[:budget_for_others]
        budget_for_others -= len(part_py)
        
        part_config = config_files[:budget_for_others]
        budget_for_others -= len(part_config)
        
        part_doc = doc_files[:budget_for_others]
        budget_for_others -= len(part_doc)
        
        part_other = other_files[:budget_for_others]
        
        final_tree = part_py + test_files + part_config + part_doc + part_other
        if len(tree) > limit:
            final_tree.append('... (truncated)')
            
        return final_tree

    def _extract_ast_summary(self, file_tree: list[str]) -> str:
        """Extract AST summary from Python files."""
        all_classes = []
        py_files = [f for f in file_tree if f.endswith('.py') and not f.startswith('tests/')]
        
        for file_path in py_files[:20]:  # Limit to 20 files for summary
            try:
                full_path = os.path.join(self.repo_path, file_path)
                with open(full_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=full_path)
                classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
                if classes:
                    all_classes.append(f"{file_path}: {', '.join(classes)}")
            except Exception:
                pass  # Skip files that can't be parsed
        
        if not all_classes:
            return "No classes detected"
        
        summary = "\n".join(all_classes)
        if len(summary) > 3000:
            summary = summary[:3000] + f"\n... (truncated, {len(all_classes)} classes total)"
        
        return summary

    def _collect_tests(self) -> list[str]:
        """Collect test names via pytest."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", "-q"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            return lines
        except Exception:
            return []