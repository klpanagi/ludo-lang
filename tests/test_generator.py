import pathlib
import subprocess
import sys
import tempfile
import pytest
from conftest import ROOT, EXAMPLES_DIR, OUTPUT_DIR, GRAMMAR_PATH, TEMPLATES_DIR

GENERATOR = ROOT / "generator" / "generate.py"
PYTHON = sys.executable

ALL_EXAMPLES = sorted(EXAMPLES_DIR.glob("*.game"))
ALL_TEMPLATES = sorted(TEMPLATES_DIR.glob("*.html.j2"))


def run_generator(game_file):
    result = subprocess.run(
        [PYTHON, str(GENERATOR), str(game_file)],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(ROOT),
    )
    return result


class TestAllExamplesGenerate:
    @pytest.mark.parametrize("game_file", ALL_EXAMPLES, ids=lambda p: p.stem)
    def test_generates_successfully(self, game_file):
        result = run_generator(game_file)
        assert result.returncode == 0, (
            f"Generator failed for {game_file.name}:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

    @pytest.mark.parametrize("game_file", ALL_EXAMPLES, ids=lambda p: p.stem)
    def test_output_file_exists(self, game_file):
        result = run_generator(game_file)
        assert result.returncode == 0
        assert "Generated:" in result.stdout
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        out_path = pathlib.Path(out_path_str)
        assert out_path.exists(), f"Output file not found: {out_path}"

    @pytest.mark.parametrize("game_file", ALL_EXAMPLES, ids=lambda p: p.stem)
    def test_output_is_valid_html(self, game_file):
        result = run_generator(game_file)
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()
        assert "<canvas" in html
        assert "<script" in html
        assert "</html>" in html

    @pytest.mark.parametrize("game_file", ALL_EXAMPLES, ids=lambda p: p.stem)
    def test_output_is_self_contained(self, game_file):
        result = run_generator(game_file)
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert "cdn." not in html, "Output should not reference external CDN"
        assert 'src="http' not in html, "Output should not load external scripts"
        assert "import " not in html or "import " in html and "from_player" in html


class TestOutputContent:
    def test_pacman_output_contains_game_name(self):
        result = run_generator(EXAMPLES_DIR / "pacman.game")
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert "Pacman" in html or "pacman" in html.lower()

    def test_snake_output_has_canvas(self):
        result = run_generator(EXAMPLES_DIR / "snake.game")
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert "<canvas" in html
        assert "requestAnimationFrame" in html

    def test_shooter_output_has_player_color(self):
        result = run_generator(EXAMPLES_DIR / "space_defender.game")
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert "#60a5fa" in html

    def test_enhanced_shooter_has_sound_functions(self):
        result = run_generator(EXAMPLES_DIR / "enhanced_shooter.game")
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert (
            "AudioContext" in html
            or "audioContext" in html.lower()
            or "playSound" in html
        )

    def test_tetris_output_no_map_error(self):
        result = run_generator(EXAMPLES_DIR / "tetris.game")
        assert result.returncode == 0
        assert "Error" not in result.stderr
        assert "Traceback" not in result.stderr

    def test_output_size_reasonable(self):
        for game_file in ALL_EXAMPLES:
            result = run_generator(game_file)
            if result.returncode == 0:
                out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
                size = pathlib.Path(out_path_str).stat().st_size
                assert size > 5_000, f"{game_file.stem} output too small ({size} bytes)"
                assert size < 500_000, (
                    f"{game_file.stem} output suspiciously large ({size} bytes)"
                )


class TestTemplateFiles:
    def test_all_game_types_have_templates(self):
        game_types = [
            "pacman",
            "snake",
            "shooter",
            "breakout",
            "invaders",
            "bomberman",
            "frogger",
            "sokoban",
            "tetris",
            "platformer",
            "towerdefense",
        ]
        for gt in game_types:
            tmpl = TEMPLATES_DIR / f"{gt}.html.j2"
            assert tmpl.exists(), f"Missing template: {gt}.html.j2"

    def test_templates_are_non_empty(self):
        for tmpl in ALL_TEMPLATES:
            assert tmpl.stat().st_size > 1000, f"Template too small: {tmpl.name}"

    def test_templates_have_jinja_vars(self):
        for tmpl in ALL_TEMPLATES:
            content = tmpl.read_text()
            assert "{{" in content and "}}" in content, f"No Jinja vars in {tmpl.name}"

    def test_templates_have_canvas(self):
        for tmpl in ALL_TEMPLATES:
            content = tmpl.read_text()
            assert "<canvas" in content, f"No canvas in {tmpl.name}"


class TestGeneratorErrorHandling:
    def test_missing_file_exits_nonzero(self):
        result = subprocess.run(
            [PYTHON, str(GENERATOR), "nonexistent_totally_fake.game"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(ROOT),
        )
        assert result.returncode != 0

    def test_no_args_exits_nonzero(self):
        result = subprocess.run(
            [PYTHON, str(GENERATOR)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(ROOT),
        )
        assert result.returncode != 0

    def test_invalid_game_source_exits_nonzero(self):
        with tempfile.NamedTemporaryFile(
            suffix=".game", mode="w", delete=False, dir=str(EXAMPLES_DIR)
        ) as f:
            f.write("this is not valid game DSL syntax @@@@")
            tmp_path = f.name
        try:
            result = subprocess.run(
                [PYTHON, str(GENERATOR), tmp_path],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(ROOT),
            )
            assert result.returncode != 0
        finally:
            pathlib.Path(tmp_path).unlink(missing_ok=True)


class TestPhase1BehaviorDSLGenerator:
    def test_pacman_behavior_generates(self):
        result = run_generator(EXAMPLES_DIR / "pacman_behavior.game")
        assert result.returncode == 0, (
            f"Generator failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert "GAME_VARS" in html
        assert "COLLISION_RULES" in html
        assert "TIMER_RULES" in html
        assert "evalRuleCond" in html
        assert "fireCollisionRule" in html

    def test_shooter_waves_generates(self):
        result = run_generator(EXAMPLES_DIR / "shooter_waves.game")
        assert result.returncode == 0, (
            f"Generator failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )


class TestSpawnResolutionInGenerator:
    def test_player_spawn_resolved_correctly(self):
        result = run_generator(EXAMPLES_DIR / "space_defender.game")
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert (
            "playerX" in html
            or "PLAYER_X" in html
            or "player_x" in html.lower()
            or "spawn" in html.lower()
        )

    def test_all_examples_output_names_are_unique(self):
        output_names = set()
        for game_file in ALL_EXAMPLES:
            result = run_generator(game_file)
            if result.returncode == 0:
                out_name = (
                    result.stdout.strip().split("Generated:")[-1].strip().split("/")[-1]
                )
                output_names.add(out_name)
        assert len(output_names) == len(ALL_EXAMPLES), (
            "Some games produced the same output filename"
        )
