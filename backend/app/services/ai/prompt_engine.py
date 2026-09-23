import json
from pathlib import Path
from typing import Dict, Any, Tuple
from app.core.config import settings

PROMPTS_FILE = settings.BASE_DIR / "prompts" / "prompts.json"

class PromptEngine:
    def __init__(self):
        self._prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, Any]:
        try:
            with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def get_prompt(self, task_type: str, version: str, context: Dict[str, Any]) -> Tuple[str, str]:
        """
        task_type: 'idea_generation', 'content_draft', 'performance_summary'
        version: 'v1', 'v2', 'v3'
        context: biến thay thế
        """
        task_prompts = self._prompts.get(task_type, {})
        selected_version = task_prompts.get(version.lower(), task_prompts.get("v3", {}))
        
        system_tmpl = selected_version.get("system", "Bạn là trợ lý AI.")
        user_tmpl = selected_version.get("user", "")

        # Render variables
        system_prompt = system_tmpl
        user_prompt = user_tmpl
        for key, val in context.items():
            placeholder = "{{" + str(key) + "}}"
            val_str = str(val) if val is not None else ""
            system_prompt = system_prompt.replace(placeholder, val_str)
            user_prompt = user_prompt.replace(placeholder, val_str)

        return system_prompt, user_prompt

prompt_engine = PromptEngine()
