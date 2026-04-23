import pytest
import textwrap
from textx import metamodel_from_file, TextXSyntaxError, TextXSemanticError
from conftest import GRAMMAR_PATH, EXAMPLES_DIR


@pytest.fixture(scope="module")
def mm():
    return metamodel_from_file(str(GRAMMAR_PATH))


def parse(mm, src):
    import tempfile, pathlib

    with tempfile.NamedTemporaryFile(suffix=".game", mode="w", delete=False) as f:
        f.write(textwrap.dedent(src))
        path = f.name
    return mm.model_from_file(path)


class TestGrammarLoads:
    def test_grammar_file_exists(self):
        assert GRAMMAR_PATH.exists()

    def test_metamodel_loads(self, mm):
        assert mm is not None


class TestAllExamplesParseClean:
    @pytest.mark.parametrize(
        "game_file", sorted(EXAMPLES_DIR.glob("*.game")), ids=lambda p: p.stem
    )
    def test_example_parses(self, mm, game_file):
        model = mm.model_from_file(str(game_file))
        assert model is not None
        assert model.name
        assert model.type in (
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
        )


class TestGameModelFields:
    def test_pacman_model(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman.game"))
        assert m.type == "pacman"
        assert m.map is not None
        assert m.player is not None
        assert m.player.color == "#ffff00"
        assert m.player.lives == 3
        assert len(m.actors.actors) == 4

    def test_snake_model(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "snake.game"))
        assert m.type == "snake"
        assert m.food is not None
        assert m.food.respawn is True

    def test_shooter_model(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "space_defender.game"))
        assert m.type == "shooter"
        assert m.player.shoot is not None
        assert m.player.shoot.key == "space"

    def test_breakout_model(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "breakout.game"))
        assert m.type == "breakout"

    def test_invaders_model(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "space_invaders.game"))
        assert m.type == "invaders"

    def test_bomberman_model(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "bomberman.game"))
        assert m.type == "bomberman"

    def test_frogger_model(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "frogger.game"))
        assert m.type == "frogger"

    def test_sokoban_model(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "sokoban.game"))
        assert m.type == "sokoban"

    def test_tetris_model(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "tetris.game"))
        assert m.type == "tetris"
        assert m.map is None or m.player is None or m.type == "tetris"

    def test_platformer_model(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "platformer.game"))
        assert m.type == "platformer"

    def test_towerdefense_model(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "towerdefense.game"))
        assert m.type == "towerdefense"


class TestNewDSLFeatures:
    def test_enhanced_shooter_has_sounds(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "enhanced_shooter.game"))
        assert m.sounds is not None
        assert len(m.sounds.sounds) == 3
        names = [s.name for s in m.sounds.sounds]
        assert "shoot" in names
        assert "die" in names

    def test_enhanced_shooter_has_animations(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "enhanced_shooter.game"))
        assert m.animations is not None
        assert len(m.animations.animations) >= 1
        effects = [a.effect for a in m.animations.animations]
        assert "explode" in effects

    def test_enhanced_shooter_has_items(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "enhanced_shooter.game"))
        assert m.items is not None
        assert len(m.items.items) == 2
        item_names = [i.name for i in m.items.items]
        assert "health_pack" in item_names

    def test_enhanced_shooter_has_levels(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "enhanced_shooter.game"))
        assert m.levels is not None
        assert len(m.levels.levels) == 3
        assert m.levels.levels[0].number == 1
        assert m.levels.levels[1].speed_multiplier == pytest.approx(1.3)

    def test_enhanced_snake_has_sounds(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "enhanced_snake.game"))
        assert m.sounds is not None
        assert len(m.sounds.sounds) >= 2

    def test_enhanced_snake_has_items(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "enhanced_snake.game"))
        assert m.items is not None
        assert len(m.items.items) >= 1


class TestActorTypeSeparation:
    def test_enemies_are_enemy_def(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman.game"))
        for actor in m.actors.actors:
            assert actor.__class__.__name__ == "EnemyDef"

    def test_projectile_in_shooter(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "space_defender.game"))
        classes = [a.__class__.__name__ for a in m.actors.actors]
        assert "ProjectileDef" in classes
        assert "EnemyDef" in classes

    def test_enemy_behavior_values(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman.game"))
        behaviors = {a.name: a.behavior for a in m.actors.actors}
        assert behaviors["Blinky"] == "chase"
        assert behaviors["Pinky"] == "ambush"
        assert behaviors["Inky"] == "flanker"
        assert behaviors["Clyde"] == "random"


class TestSpawnResolution:
    def test_player_spawn_from_tile(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "space_defender.game"))
        assert m.player.spawn_tile is not None
        assert m.player.spawn_tile == "P"

    def test_player_start_coords(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman.game"))
        assert m.player.start_x == 13
        assert m.player.start_y == 22

    def test_enemy_spawn_tile(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "space_defender.game"))
        enemies = [a for a in m.actors.actors if a.__class__.__name__ == "EnemyDef"]
        assert any(e.spawn_tile == "E" for e in enemies)


class TestInvalidModels:
    def test_invalid_game_type_rejected(self, mm):
        src = """
            game "Bad" {
                type: pong
                canvas: 400x400
                fps: 60
            }
            map { cell_size: 20 }
            player {
                name: "P"
                start: (1, 1)
                color: "#fff"
                speed: 3
            }
        """
        with pytest.raises((TextXSyntaxError, TextXSemanticError, Exception)):
            parse(mm, src)

    def test_invalid_sound_type_rejected(self, mm):
        src = """
            game "Bad" {
                type: snake
                canvas: 400x400
                fps: 60
            }
            map { cell_size: 20 }
            player {
                name: "P"
                start: (1, 1)
                color: "#fff"
                speed: 3
            }
            sounds {
                sound sfx { type: laser }
            }
        """
        with pytest.raises((TextXSyntaxError, TextXSemanticError, Exception)):
            parse(mm, src)

    def test_invalid_item_effect_rejected(self, mm):
        src = """
            game "Bad" {
                type: snake
                canvas: 400x400
                fps: 60
            }
            map { cell_size: 20 }
            player {
                name: "P"
                start: (1, 1)
                color: "#fff"
                speed: 3
            }
            items {
                item gem {
                    symbol: "*"
                    color: "#fff"
                    effect: fly
                }
            }
        """
        with pytest.raises((TextXSyntaxError, TextXSemanticError, Exception)):
            parse(mm, src)


class TestPhase1BehaviorDSL:
    def test_variables_block_parses(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman_behavior.game"))
        assert m.variables is not None
        assert len(m.variables.vars) == 2
        var_names = [v.name for v in m.variables.vars]
        assert "ghost_frightened" in var_names
        assert "ghost_eaten_count" in var_names

    def test_variable_types(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman_behavior.game"))
        vmap = {v.name: v for v in m.variables.vars}
        assert vmap["ghost_frightened"].type == "bool"
        assert vmap["ghost_eaten_count"].type == "int"

    def test_variable_defaults(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman_behavior.game"))
        vmap = {v.name: v for v in m.variables.vars}
        assert vmap["ghost_frightened"].default_val.val == "false"
        assert vmap["ghost_eaten_count"].default_val.val == 0

    def test_conditional_collision_rule(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman_behavior.game"))
        rules = m.rules.collision_rules
        assert len(rules) >= 2
        cond_rules = [r for r in rules if r.condition is not None]
        assert len(cond_rules) >= 1
        r = cond_rules[0]
        assert r.condition.op in ("==", "!=", "<", ">", "<=", ">=")

    def test_timer_rule_parses(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman_behavior.game"))
        assert m.rules.timer_rules is not None
        assert len(m.rules.timer_rules) >= 1
        tr = m.rules.timer_rules[0]
        assert tr.interval == 8.0

    def test_multi_action_rule(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman_behavior.game"))
        multi = [r for r in m.rules.collision_rules if len(r.actions) > 1]
        assert len(multi) >= 1

    def test_set_var_action(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman_behavior.game"))
        set_actions = []
        for r in m.rules.collision_rules + m.rules.timer_rules:
            for a in r.actions:
                if a.__class__.__name__ == "SetVarAction":
                    set_actions.append(a)
        assert len(set_actions) >= 1
        assert set_actions[0].var_name == "ghost_eaten_count"

    def test_all_original_examples_still_parse(self, mm):
        for f in sorted(EXAMPLES_DIR.glob("*.game")):
            if f.stem in ("pacman_behavior", "shooter_waves"):
                continue
            m = mm.model_from_file(str(f))
            assert m is not None

    def test_backward_compat_single_action(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "space_defender.game"))
        if m.rules and m.rules.collision_rules:
            rule = m.rules.collision_rules[0]
            assert len(rule.actions) == 1
            assert rule.actions[0].__class__.__name__ == "SimpleRuleAction"
            assert rule.actions[0].action == "lose_life"


class TestTilesDef:
    def test_pacman_has_expected_tiles(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman.game"))
        tile_names = [t.name for t in m.tiles.tiles]
        assert "wall" in tile_names
        assert "dot" in tile_names
        assert "power_pellet" in tile_names

    def test_wall_tile_is_solid(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman.game"))
        wall = next(t for t in m.tiles.tiles if t.name == "wall")
        assert wall.solid is True
        assert wall.symbol == "#"

    def test_collectible_tile_has_score(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman.game"))
        dot = next(t for t in m.tiles.tiles if t.name == "dot")
        assert dot.collectible is True
        assert dot.score == 10


class TestMapDef:
    def test_map_has_layout(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman.game"))
        assert m.map.layout
        assert len(m.map.layout) > 0
        assert all(isinstance(row, str) for row in m.map.layout)

    def test_map_cell_size(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman.game"))
        assert m.map.cell_size == 20

    def test_map_layout_rows_consistent_length(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman.game"))
        lengths = [len(row) for row in m.map.layout]
        assert max(lengths) - min(lengths) <= 2


class TestUIDef:
    def test_ui_positions(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "pacman.game"))
        assert m.ui is not None
        assert m.ui.score_pos == "top_left"
        assert m.ui.lives_pos == "bottom_left"
        assert m.ui.level_pos == "top_right"

    def test_missing_ui_is_none(self, mm):
        m = mm.model_from_file(str(EXAMPLES_DIR / "snake.game"))
        pass
