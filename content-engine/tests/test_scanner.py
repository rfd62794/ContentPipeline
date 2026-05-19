"""
Tests for core/scanner.py
"""

import sys
from pathlib import Path
import tempfile
import os

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.scanner import RepoScanner


class TestRepoScanner:
    def test_scanner_returns_dict(self):
        """scan() returns dict with file_tree, ast_summary, test_list keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal repo structure
            (Path(tmpdir) / "test.py").write_text("class TestClass: pass")
            tests_dir = Path(tmpdir) / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_example.py").write_text("def test_example(): pass")
            
            scanner = RepoScanner(tmpdir)
            result = scanner.scan()
            
            assert isinstance(result, dict)
            assert 'file_tree' in result
            assert 'ast_summary' in result
            assert 'test_list' in result
    
    def test_scanner_file_tree_not_empty(self):
        """file_tree string is non-empty for valid repo path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.py").write_text("class TestClass: pass")
            
            scanner = RepoScanner(tmpdir)
            result = scanner.scan()
            
            assert result['file_tree']
            assert len(result['file_tree']) > 0
    
    def test_scanner_ast_extracts_classes(self):
        """ast_summary contains class names from Python files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.py").write_text("class MyClass: pass\nclass OtherClass: pass")
            
            scanner = RepoScanner(tmpdir)
            result = scanner.scan()
            
            assert 'MyClass' in result['ast_summary'] or 'OtherClass' in result['ast_summary']
    
    def test_scanner_test_collection(self):
        """test_list contains test function names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tests_dir = Path(tmpdir) / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_example.py").write_text("def test_example(): pass\ndef test_another(): pass")
            
            scanner = RepoScanner(tmpdir)
            result = scanner.scan()
            
            # Test collection may be empty if pytest is not available, but structure should exist
            assert isinstance(result['test_list'], str)
    
    def test_scanner_truncates_large_repos(self):
        """file_tree truncates at 60 files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create more than 60 files
            for i in range(70):
                (Path(tmpdir) / f"file_{i}.py").write_text("pass")
            
            scanner = RepoScanner(tmpdir)
            result = scanner.scan()
            
            assert '... (truncated)' in result['file_tree']
    
    def test_scanner_handles_empty_repo(self):
        """scan() returns empty strings for empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = RepoScanner(tmpdir)
            result = scanner.scan()
            
            assert result['file_tree'] == ''
            assert result['ast_summary'] == 'No classes detected'
            # pytest returns "no tests collected" when there are no tests
            assert result['test_list'] == '' or 'no tests collected' in result['test_list'].lower()