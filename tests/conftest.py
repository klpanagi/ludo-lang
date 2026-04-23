import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "generator"))

GRAMMAR_PATH = ROOT / "grammar" / "game.tx"
EXAMPLES_DIR = ROOT / "examples"
TEMPLATES_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "output"
