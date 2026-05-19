"""
Repo Assessor — Two-stage directive enrichment

Source pattern: OpenAgent/legacy/assessor.py + writer.py
Extract date: 2026-05-18
Adaptation: Uses llm_client.py instead of raw requests, combined into single module

Contract:
- assess(scan_result, intent) — Stage 1: cheap model structures assessment
- write_directive(assessment, intent) — Stage 2: capable model writes directive
"""

import json
import re
import ast
from typing import Dict, Any
from .model_router import ModelRouter
from .llm_client import OpenRouterLLMAdapter


class RepoAssessor:
    """Two-stage repo assessment and directive generation."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.router = ModelRouter()
        
    def assess(self, scan_result: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """
        Stage 1: Send scan result to cheap model for structured assessment.
        
        Args:
            scan_result: Dict with file_tree, ast_summary, test_list keys
            intent: Architect's intent for this phase
            
        Returns:
            Structured assessment dict with repo analysis
        """
        file_tree = scan_result.get('file_tree', '')
        ast_summary = scan_result.get('ast_summary', '')
        test_list = scan_result.get('test_list', '')
        
        prompt = f"""SYSTEM: You are a senior software architect analyzing a repository.
Extract the primary Goal and Why before listing files or modules.
A correct goal statement is worth more than a complete file list.

CRITICAL OUTPUT RULES — VIOLATIONS WILL CAUSE SYSTEM FAILURE:
- Output ONLY ASCII characters. No Unicode. No Chinese. No Greek. No Cyrillic. No special characters.
- Output ONLY valid JSON. No markdown. No explanation. No code blocks.
- Every string value must use double quotes. No single quotes. No unquoted text.
- files_in_scope must be a JSON array of plain ASCII filename strings only.
- If you cannot produce valid JSON, output: {{"error": "generation_failed"}}

Return ONLY valid JSON with exactly these keys and no others:
{{
  "repo_name": "string",
  "phase_current": "string",
  "what_is_built": "string — 2-3 sentences max",
  "what_is_stubbed": ["list of string"],
  "test_floor": {{
    "passing": 0,
    "failing": 0,
    "skipped": 0,
    "ok": true
  }},
  "open_questions": ["list of string"],
  "recent_decisions": ["list of string"],
  "files_in_scope": ["list of short ASCII filename strings only — no paths, no nested objects"],
  "complexity_flags": ["list of string — empty if none"],
  "doc_gaps": ["list of string — empty if none"]
}}
No other keys. No nesting beyond what is shown above. No preamble. No explanation.

EXAMPLE JSON OUTPUT:
{{
  "repo_name": "ContentEngine",
  "phase_current": "Phase E1",
  "what_is_built": "Repo scanning and directive enrichment",
  "what_is_stubbed": [],
  "test_floor": {{"passing": 111, "failing": 0, "skipped": 0, "ok": true}},
  "open_questions": [],
  "recent_decisions": ["ADR-014: OpenAgent ADK rebuild parked"],
  "files_in_scope": ["scanner.py", "repo_assessor.py"],
  "complexity_flags": [],
  "doc_gaps": []
}}

USER:
ARCHITECT INTENT: {intent}

FILE TREE:
{file_tree}

PYTHON MODULES DETECTED:
{ast_summary}

TEST COLLECTION:
{test_list}

AGENT CONTRACT INVARIANTS:
0 failing, 0 skipped. Scope strictly enforced.

Produce assessment JSON now."""

        # Use llm_client with cheap model
        model = self.router.get_model('inventory')
        llm = OpenRouterLLMAdapter(model=model)
        
        response = llm.generate(
            prompt=prompt,
            temperature=0.0,
            response_format={"type": "json_object"},
            agent_name="repo_assessor"
        )
        
        raw_output = response['text']
        if self.verbose:
            print(f"--- RAW MODEL OUTPUT ---\n{raw_output}\n--- END RAW ---\n")
        
        assessment = self._parse_assessment_response(raw_output)
        return assessment

    def write_directive(self, assessment: Dict[str, Any], intent: str) -> str:
        """
        Stage 2: Send assessment to capable model for directive generation.
        
        Args:
            assessment: Structured assessment dict from assess()
            intent: Architect's intent for this phase
            
        Returns:
            Plain text directive string
        """
        repo_name = assessment.get('repo_name', '')
        phase_current = assessment.get('phase_current', '')
        what_is_built = assessment.get('what_is_built', '')
        what_is_stubbed = assessment.get('what_is_stubbed', [])
        test_floor = assessment.get('test_floor', {})
        open_questions = assessment.get('open_questions', [])
        recent_decisions = assessment.get('recent_decisions', [])
        files_in_scope = assessment.get('files_in_scope', [])
        
        prompt = f"""SYSTEM: You are a senior software architect writing implementation directives
for AI coding agents. You follow strict spec-driven development principles.

DIRECTIVE FORMAT RULES:
1. First item is always a STOP rule: run pytest, report count, stop if failing.
2. Phase context: what was delivered last phase.
3. Explicit file scope: list files that MAY be modified. All others are read-only.
4. Implementation: step-by-step. No ambiguity. No implicit decisions.
5. Test anchors: minimum 10 named tests. Each maps to one specific behavior.
6. Completion criteria: checklist. All items true = phase complete.
7. Never skip a failing test. Never accept a skipped test as passing.
8. Flag any decision not covered by existing ADRs as an open question.

CRITICAL: Your directive must address ONLY the architect's stated intent.
You define requirements and scope. You do not prescribe implementation.
Prefer the systemic fix over the manual patch.
A directive that solves the wrong problem precisely is a failure.
Do not propose new classes, systems, or abstractions not implied by the intent.
Do not expand scope beyond what is explicitly requested.
If the intent is diagnostic (e.g. "test self-assessment"), the directive
should verify existing behavior — not build new systems.

SCOPE GUARD CONSTRAINTS — YOU MUST OBEY THESE OR FAIL:
1. FORBIDDEN WORDS: Do NOT use the exact word "import", "install", or "refactor". Use "include" or "setup" instead.
2. FORBIDDEN PHRASES: Do NOT use the exact string "phase " (with a space). Use "stage " instead. Our strict regex will fail you if you mention "phase ".
3. Only reference files exactly as they appear in the "Files likely in scope" list. Do not reference __init__.py or any other unlisted files. If you absolutely must create a new file, you MUST write it as [NEW] filename.py.

USER:
Repository: {repo_name}
Current phase: {phase_current}
What is built: {what_is_built}
What is stubbed: {what_is_stubbed}
Test floor: {test_floor}
Open questions: {open_questions}
Recent decisions: {recent_decisions}
Files likely in scope: {files_in_scope}

ARCHITECT INTENT: {intent}

Write the directive now. Plain text only. No JSON. No markdown fences."""

        # Use llm_client with capable model
        model = self.router.get_model('directive')
        llm = OpenRouterLLMAdapter(model=model)
        
        response = llm.generate(
            prompt=prompt,
            temperature=0.7,
            response_format=None,  # Plain text for directive
            agent_name="repo_assessor"
        )
        
        return response['text'].strip()

    def _parse_assessment_response(self, raw: str) -> Dict[str, Any]:
        """Parse JSON response from model with robust error handling."""
        # 1. Try to extract JSON block using regex if markdown formatted
        pattern = re.compile(r'```(?:json)?\s*(.*?)\s*```', re.DOTALL)
        match = pattern.search(raw)
        clean = match.group(1) if match else raw.strip()
        
        # 2. Try standard JSON decode
        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            # 3. Fallback: string might have bad unescaped characters or trailing commas.
            # Try python's literal_eval.
            try:
                # Replace true/false/null with Python equivalents before eval
                py_clean = re.sub(r'\btrue\b', 'True', clean)
                py_clean = re.sub(r'\bfalse\b', 'False', py_clean)
                py_clean = re.sub(r'\bnull\b', 'None', py_clean)
                data = ast.literal_eval(py_clean)
            except Exception as e:
                # If both fail, raise the original json error for transparency
                if self.verbose:
                    print(f"Failed to parse JSON. Raw block was:\n{clean}")
                raise ValueError(f"Could not parse assessment: {e}")

        required = ['repo_name','phase_current','what_is_built','what_is_stubbed',
                    'test_floor','open_questions','recent_decisions',
                    'files_in_scope','complexity_flags','doc_gaps']
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f'Assessment missing keys: {missing}')
            
        tf = data['test_floor']
        tf['ok'] = tf.get('failing', 1) == 0 and tf.get('skipped', 1) == 0
        return data