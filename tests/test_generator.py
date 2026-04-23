import pathlib
import subprocess
import sys
import tempfile
import pytest
from conftest import ROOT, EXAMPLES_DIR, OUTPUT_DIR, GRAMMAR_PATH, TEMPLATES_DIR

GENERATOR = ROOT / "generator" / "generate.py"
PYTHON = sys.executable

ALL_EXAMPLES = sorted(EXAMPLES_DIR.glob("*.game"))
NEW_TEMPLATES = ["grid", "top_down", "platformer", "physics"]


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
        assert "cdn." not in html, "Output must not reference external CDN"
        assert 'src="http' not in html, "Output must not load external scripts"


class TestOutputContent:
    def test_snake_output_has_game_name(self):
        result = run_generator(EXAMPLES_DIR / "snake.game")
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert "Snake" in html or "snake" in html.lower()

    def test_snake_output_has_canvas_and_raf(self):
        result = run_generator(EXAMPLES_DIR / "snake.game")
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert "<canvas" in html
        assert "requestAnimationFrame" in html

    def test_space_defender_has_player_color(self):
        result = run_generator(EXAMPLES_DIR / "space_defender.game")
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert "#60a5fa" in html

    def test_pacman_has_player_color(self):
        result = run_generator(EXAMPLES_DIR / "pacman.game")
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert "#ffff00" in html

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

    def test_output_names_are_unique(self):
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


class TestEntityContextInOutput:
    def test_entity_colors_appear_in_output(self):
        result = run_generator(EXAMPLES_DIR / "snake.game")
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert "ENTITY_DEFS" in html or "entity" in html.lower()

    def test_symbol_map_in_grid_output(self):
        result = run_generator(EXAMPLES_DIR / "snake.game")
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert "SYMBOL_MAP" in html

    def test_engine_flags_appear_in_output(self):
        result = run_generator(EXAMPLES_DIR / "snake.game")
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert "GROW_ON_EAT" in html or "grow_on_eat" in html.lower()

    def test_behavior_dsl_runtime_included(self):
        for game_file in ALL_EXAMPLES:
            result = run_generator(game_file)
            if result.returncode == 0:
                out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
                html = pathlib.Path(out_path_str).read_text()
                assert "GAME_VARS" in html, f"GAME_VARS missing in {game_file.stem}"
                assert "COLLISION_RULES" in html, f"COLLISION_RULES missing in {game_file.stem}"
                assert "drawOverlay" in html, f"drawOverlay missing in {game_file.stem}"


class TestTemplateFiles:
    def test_all_engine_types_have_templates(self):
        for engine_type in NEW_TEMPLATES:
            tmpl = TEMPLATES_DIR / f"{engine_type}.html.j2"
            assert tmpl.exists(), f"Missing template: {engine_type}.html.j2"

    def test_templates_are_non_empty(self):
        for engine_type in NEW_TEMPLATES:
            tmpl = TEMPLATES_DIR / f"{engine_type}.html.j2"
            if tmpl.exists():
                assert tmpl.stat().st_size > 5000, f"Template too small: {engine_type}.html.j2"

    def test_templates_have_jinja_vars(self):
        for engine_type in NEW_TEMPLATES:
            tmpl = TEMPLATES_DIR / f"{engine_type}.html.j2"
            if tmpl.exists():
                content = tmpl.read_text()
                assert "{{" in content and "}}" in content, (
                    f"No Jinja vars in {engine_type}.html.j2"
                )

    def test_templates_have_canvas(self):
        for engine_type in NEW_TEMPLATES:
            tmpl = TEMPLATES_DIR / f"{engine_type}.html.j2"
            if tmpl.exists():
                content = tmpl.read_text()
                assert "<canvas" in content, f"No <canvas> in {engine_type}.html.j2"

    def test_templates_include_behavior_dsl(self):
        for engine_type in NEW_TEMPLATES:
            tmpl = TEMPLATES_DIR / f"{engine_type}.html.j2"
            if tmpl.exists():
                content = tmpl.read_text()
                assert "_behavior_dsl.j2" in content, (
                    f"Missing _behavior_dsl.j2 include in {engine_type}.html.j2"
                )

    def test_templates_include_runtime(self):
        for engine_type in NEW_TEMPLATES:
            tmpl = TEMPLATES_DIR / f"{engine_type}.html.j2"
            if tmpl.exists():
                content = tmpl.read_text()
                assert "_runtime.j2" in content, (
                    f"Missing _runtime.j2 include in {engine_type}.html.j2"
                )


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


class TestRulesInOutput:
    def test_pacman_has_conditional_rules(self):
        result = run_generator(EXAMPLES_DIR / "pacman.game")
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert "COLLISION_RULES" in html
        assert "evalRuleCond" in html
        assert "fireCollisionRule" in html

    def test_pacman_has_timer_rules(self):
        result = run_generator(EXAMPLES_DIR / "pacman.game")
        assert result.returncode == 0
        out_path_str = result.stdout.strip().split("Generated:")[-1].strip()
        html = pathlib.Path(out_path_str).read_text()
        assert "TIMER_RULES" in html
        assert "updateRuleTimers" in html
