"""
Model Router — Extracted from OpenAgent legacy

Source: OpenAgent/legacy/model_router.py (10 lines)
Extract date: 2026-05-18
Adaptation: Extended with task types for ContentEngine integration

Contract:
- get_model(task_type) returns model string for given task type
- No API calls, no business logic — pure routing only
- llm_client.py receives the model string and makes the call
"""


class ModelRouter:
    """Route task types to appropriate models."""
    
    def __init__(self):
        self.base_url = "https://openrouter.ai/api/v1"
        
        # Task type to model mapping
        self.models = {
            'inventory': 'deepseek/deepseek-chat-v3-0324',  # Stage 1: cheap assessment
            'directive': 'anthropic/claude-haiku-4-5',  # Stage 2: capable directive generation
            'assembly': 'anthropic/claude-sonnet-4-6',  # ContentEngine default
            'fallback': 'meta-llama/llama-3.3-70b-instruct:free'  # Free tier fallback
        }

    def get_model(self, task_type: str) -> str:
        """
        Get model string for given task type.
        
        Args:
            task_type: One of 'inventory', 'directive', 'assembly', 'fallback'
            
        Returns:
            Model identifier string for OpenRouter API
        """
        return self.models.get(task_type, self.models['fallback'])