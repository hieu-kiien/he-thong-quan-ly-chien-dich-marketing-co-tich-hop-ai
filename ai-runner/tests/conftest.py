import sys
from pathlib import Path

# Add ai-runner root to sys.path so `app.*` imports work seamlessly
ai_runner_root = Path(__file__).parent.parent
if str(ai_runner_root) not in sys.path:
    sys.path.insert(0, str(ai_runner_root))
