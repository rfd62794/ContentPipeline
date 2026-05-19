"""
Tests for core/repo_assessor.py
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.repo_assessor import RepoAssessor


class TestRepoAssessor:
    @patch('core.repo_assessor.OpenRouterLLMAdapter')
    def test_assessor_assess_calls_llm(self, mock_llm_class):
        """assess() calls llm_client with cheap model."""
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        mock_llm.generate.return_value = {
            'text': '{"repo_name": "TestRepo", "phase_current": "Phase 1", "what_is_built": "Test", "what_is_stubbed": [], "test_floor": {"passing": 10, "failing": 0, "skipped": 0, "ok": true}, "open_questions": [], "recent_decisions": [], "files_in_scope": [], "complexity_flags": [], "doc_gaps": []}'
        }
        
        assessor = RepoAssessor()
        scan_result = {
            'file_tree': 'test.py',
            'ast_summary': 'class TestClass',
            'test_list': 'test_example'
        }
        
        result = assessor.assess(scan_result, "test intent")
        
        assert mock_llm.generate.called
        # Check that the model used is the inventory model (deepseek)
        call_kwargs = mock_llm.generate.call_args[1]
        assert call_kwargs['temperature'] == 0.0
        assert call_kwargs['response_format'] == {"type": "json_object"}
    
    @patch('core.repo_assessor.OpenRouterLLMAdapter')
    def test_assessor_returns_dict(self, mock_llm_class):
        """assess() returns dict with required keys."""
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        mock_llm.generate.return_value = {
            'text': '{"repo_name": "TestRepo", "phase_current": "Phase 1", "what_is_built": "Test", "what_is_stubbed": [], "test_floor": {"passing": 10, "failing": 0, "skipped": 0, "ok": true}, "open_questions": [], "recent_decisions": [], "files_in_scope": [], "complexity_flags": [], "doc_gaps": []}'
        }
        
        assessor = RepoAssessor()
        scan_result = {
            'file_tree': 'test.py',
            'ast_summary': 'class TestClass',
            'test_list': 'test_example'
        }
        
        result = assessor.assess(scan_result, "test intent")
        
        assert isinstance(result, dict)
        assert 'repo_name' in result
        assert 'phase_current' in result
        assert 'what_is_built' in result
        assert 'files_in_scope' in result
    
    @patch('core.repo_assessor.OpenRouterLLMAdapter')
    def test_assessor_strips_json_fences(self, mock_llm_class):
        """assess() handles ```json wrapped response."""
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        mock_llm.generate.return_value = {
            'text': '```json\n{"repo_name": "TestRepo", "phase_current": "Phase 1", "what_is_built": "Test", "what_is_stubbed": [], "test_floor": {"passing": 10, "failing": 0, "skipped": 0, "ok": true}, "open_questions": [], "recent_decisions": [], "files_in_scope": [], "complexity_flags": [], "doc_gaps": []}\n```'
        }
        
        assessor = RepoAssessor()
        scan_result = {
            'file_tree': 'test.py',
            'ast_summary': 'class TestClass',
            'test_list': 'test_example'
        }
        
        result = assessor.assess(scan_result, "test intent")
        
        assert result['repo_name'] == 'TestRepo'
    
    @patch('core.repo_assessor.OpenRouterLLMAdapter')
    def test_assessor_write_directive_calls_llm(self, mock_llm_class):
        """write_directive() calls llm_client with capable model."""
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        mock_llm.generate.return_value = {
            'text': 'This is a test directive'
        }
        
        assessor = RepoAssessor()
        assessment = {
            'repo_name': 'TestRepo',
            'phase_current': 'Phase 1',
            'what_is_built': 'Test',
            'what_is_stubbed': [],
            'test_floor': {'passing': 10, 'failing': 0, 'skipped': 0, 'ok': True},
            'open_questions': [],
            'recent_decisions': [],
            'files_in_scope': []
        }
        
        result = assessor.write_directive(assessment, "test intent")
        
        assert mock_llm.generate.called
        # Check that response_format is None for plain text directive
        call_kwargs = mock_llm.generate.call_args[1]
        assert call_kwargs['response_format'] is None
    
    @patch('core.repo_assessor.OpenRouterLLMAdapter')
    def test_assessor_write_directive_returns_str(self, mock_llm_class):
        """write_directive() returns plain string."""
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        mock_llm.generate.return_value = {
            'text': 'This is a test directive'
        }
        
        assessor = RepoAssessor()
        assessment = {
            'repo_name': 'TestRepo',
            'phase_current': 'Phase 1',
            'what_is_built': 'Test',
            'what_is_stubbed': [],
            'test_floor': {'passing': 10, 'failing': 0, 'skipped': 0, 'ok': True},
            'open_questions': [],
            'recent_decisions': [],
            'files_in_scope': []
        }
        
        result = assessor.write_directive(assessment, "test intent")
        
        assert isinstance(result, str)
        assert result == 'This is a test directive'
    
    @patch('core.repo_assessor.OpenRouterLLMAdapter')
    def test_assessor_uses_assessment_in_prompt(self, mock_llm_class):
        """write_directive() includes assessment data in prompt."""
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        mock_llm.generate.return_value = {
            'text': 'This is a test directive'
        }
        
        assessor = RepoAssessor()
        assessment = {
            'repo_name': 'TestRepo',
            'phase_current': 'Phase 1',
            'what_is_built': 'Test implementation',
            'what_is_stubbed': [],
            'test_floor': {'passing': 10, 'failing': 0, 'skipped': 0, 'ok': True},
            'open_questions': [],
            'recent_decisions': [],
            'files_in_scope': ['scanner.py']
        }
        
        result = assessor.write_directive(assessment, "add feature")
        
        # Check that the prompt includes assessment data
        call_kwargs = mock_llm.generate.call_args[1]
        prompt = call_kwargs['prompt']
        assert 'TestRepo' in prompt
        assert 'Phase 1' in prompt
        assert 'Test implementation' in prompt
        assert 'scanner.py' in prompt