"""
Tests for core/model_router.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.model_router import ModelRouter


class TestModelRouter:
    def test_router_inventory_task(self):
        """inventory task returns deepseek model string."""
        router = ModelRouter()
        model = router.get_model('inventory')
        
        assert model == 'deepseek/deepseek-chat-v3-0324'
    
    def test_router_directive_task(self):
        """directive task returns haiku model string."""
        router = ModelRouter()
        model = router.get_model('directive')
        
        assert model == 'anthropic/claude-haiku-4-5'
    
    def test_router_assembly_task(self):
        """assembly task returns sonnet model string."""
        router = ModelRouter()
        model = router.get_model('assembly')
        
        assert model == 'anthropic/claude-sonnet-4-6'
    
    def test_router_fallback_task(self):
        """unknown task returns free fallback model."""
        router = ModelRouter()
        model = router.get_model('unknown_task')
        
        assert model == 'meta-llama/llama-3.3-70b-instruct:free'
    
    def test_router_explicit_fallback(self):
        """explicit fallback task returns free model."""
        router = ModelRouter()
        model = router.get_model('fallback')
        
        assert model == 'meta-llama/llama-3.3-70b-instruct:free'