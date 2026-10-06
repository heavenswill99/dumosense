"""Load the one Health Reserve score implementation without Django app name collision."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

source = Path(__file__).resolve().parents[1] / "health_reserve" / "score.py"
spec = spec_from_file_location("dumosense_health_reserve_score", source)
if spec is None or spec.loader is None:
    raise RuntimeError("Health Reserve score implementation unavailable")
module = module_from_spec(spec)
spec.loader.exec_module(module)
score_buffer = module.score_buffer
SCORE_LOWER_BOUNDS = module.SCORE_LOWER_BOUNDS
