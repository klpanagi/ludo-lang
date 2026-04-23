import pytest
import textwrap
import tempfile
import os
from textx import metamodel_from_file, TextXSyntaxError, TextXSemanticError
from conftest import ROOT, GRAMMAR_PATH, EXAMPLES_DIR


@pytest.fixture(scope="module")
def mm():
    return metamodel_from_file(str(GRAMMAR_PATH))


def parse(mm, src):
    with tempfile.NamedTemporaryFile(suffix=".ludo", mode="w", delete=False) as f:
        f.write(textwrap.dedent(src))
        path = f.name
    try:
        return mm.model_from_file(path)
    finally:
        os.unlink(path)


class TestGrammarLoads:
    def test_grammar_file_exists(self):
        assert GRAMMAR_PATH.exists()

    def test_metamodel_loads(self, mm):
        assert mm is not None


class TestAllExamplesParseClean:
    @pytest.mark.parametrize(
        "game_file", sorted(EXAMPLES_DIR.glob("*.ludo")), ids=lambda p: p.stem
    )
    def test_example_parses(self, mm, game_file):
        model = mm.model_from_file(str(game_file))
        assert model is not None
        assert model.name
        assert model.engine is not None
        assert model.engine.engine_type in ("grid", "top_down", "platformer", "physics")


class TestEngineBlock:
    def test_grid_engine_parses(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  cell_size: 20  movement: continuous  grow_on_eat: true }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 3 }
        """)
        assert m.engine.engine_type == "grid"
        assert m.engine.cell_size == 20
        assert m.engine.movement == "continuous"
        assert m.engine.grow_on_eat is True

    def test_top_down_engine_parses(self, mm):
        m = parse(mm, """
            game "G" { canvas: 600x600 fps: 60 background: "#000" }
            engine { type: top_down  shooting: true  ai_enemies: true  wave_system: true  wave_count: 5 }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 6  lives: 3 }
        """)
        assert m.engine.engine_type == "top_down"
        assert m.engine.shooting is True
        assert m.engine.wave_count == 5

    def test_platformer_engine_parses(self, mm):
        m = parse(mm, """
            game "G" { canvas: 800x500 fps: 60 background: "#000" }
            engine { type: platformer  gravity: 900.0  jump_force: 420.0  scroll_speed: 0.0 }
            entities { entity ground { type: solid  symbol: "#"  color: "#555" } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 5  lives: 3 }
        """)
        assert m.engine.engine_type == "platformer"
        assert m.engine.gravity == pytest.approx(900.0)
        assert m.engine.jump_force == pytest.approx(420.0)

    def test_physics_engine_parses(self, mm):
        m = parse(mm, """
            game "G" { canvas: 600x700 fps: 60 background: "#000" }
            engine { type: physics  ball_speed: 8.0  paddle_speed: 9.0  ball_size: 10 }
            entities { entity brick { type: obstacle  symbol: "B"  color: "#f00"  score: 10 } }
            player { name: "P"  start: (300, 650)  color: "#fff"  speed: 9  lives: 3 }
        """)
        assert m.engine.engine_type == "physics"
        assert m.engine.ball_speed == pytest.approx(8.0)
        assert m.engine.ball_size == 10

    def test_all_grid_movements(self, mm):
        for movement in ("continuous", "step", "formation", "falling"):
            m = parse(mm, f"""
                game "G" {{ canvas: 400x400 fps: 60 background: "#000" }}
                engine {{ type: grid  movement: {movement} }}
                entities {{ entity wall {{ type: solid  symbol: "#"  color: "#333" }} }}
                player {{ name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }}
            """)
            assert m.engine.movement == movement

    def test_invalid_engine_type_rejected(self, mm):
        with pytest.raises((TextXSyntaxError, TextXSemanticError, Exception)):
            parse(mm, """
                game "G" { canvas: 400x400 fps: 60 background: "#000" }
                engine { type: pong }
                player { name: "P"  start: (1, 1)  color: "#fff"  speed: 3  lives: 1 }
            """)


class TestEntitiesBlock:
    def test_solid_entity_parses(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#334455" } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }
        """)
        assert len(m.entities.entities) == 1
        e = m.entities.entities[0]
        assert e.name == "wall"
        assert e.entity_type == "solid"
        assert e.symbol == "#"
        assert e.color == "#334455"

    def test_enemy_entity_with_spawn_and_ai(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity ghost { type: enemy  spawn: "G"  color: "#ff0000"  speed: 3.0  ai: pathfinding  points: 200 } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 3 }
        """)
        e = m.entities.entities[0]
        assert e.entity_type == "enemy"
        assert e.spawn_symbol == "G"
        assert e.ai == "pathfinding"
        assert e.speed == pytest.approx(3.0)
        assert e.points == 200

    def test_collectible_entity_with_respawn(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity food { type: collectible  symbol: "F"  color: "#f00"  score: 10  respawn: true } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }
        """)
        e = m.entities.entities[0]
        assert e.entity_type == "collectible"
        assert e.score == 10
        assert e.respawn is True

    def test_projectile_entity_with_direction_and_hit_actions(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: top_down  shooting: true }
            entities {
                entity wall { type: solid  symbol: "#"  color: "#333" }
                entity bullet { type: projectile  color: "#fbbf24"  speed: 18  direction: from_player  on_hit_wall: destroy  on_hit_entity: destroy }
            }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 6  lives: 3 }
        """)
        assert len(m.entities.entities) == 2
        bullet = next(e for e in m.entities.entities if e.name == "bullet")
        assert bullet.entity_type == "projectile"
        assert bullet.direction == "from_player"
        assert bullet.on_hit_wall == "destroy"
        assert bullet.on_hit_entity == "destroy"

    def test_pickup_entity_with_effect(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity pellet { type: pickup  symbol: "o"  color: "#fff"  score: 50  effect: invincible  duration: 8.0 } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 3 }
        """)
        e = m.entities.entities[0]
        assert e.entity_type == "pickup"
        assert e.effect == "invincible"
        assert e.duration == pytest.approx(8.0)

    def test_multiple_entities(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities {
                entity wall  { type: solid       symbol: "#"  color: "#333" }
                entity food  { type: collectible  symbol: "F"  color: "#f00"  score: 10 }
                entity ghost { type: enemy        spawn: "G"   color: "#f0f"  speed: 2.0  ai: chase  points: 100 }
            }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 3 }
        """)
        assert len(m.entities.entities) == 3
        names = [e.name for e in m.entities.entities]
        assert "wall" in names
        assert "food" in names
        assert "ghost" in names

    def test_all_entity_types_valid(self, mm):
        for et in ("solid", "open", "collectible", "enemy", "projectile", "pickup", "obstacle", "target", "explosive"):
            m = parse(mm, f"""
                game "G" {{ canvas: 400x400 fps: 60 background: "#000" }}
                engine {{ type: grid  movement: continuous }}
                entities {{ entity e {{ type: {et}  symbol: "X"  color: "#333" }} }}
                player {{ name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }}
            """)
            assert m.entities.entities[0].entity_type == et

    def test_all_ai_types_valid(self, mm):
        for ai in ("chase", "formation", "random", "patrol", "pathfinding", "ambush", "none"):
            m = parse(mm, f"""
                game "G" {{ canvas: 400x400 fps: 60 background: "#000" }}
                engine {{ type: grid  movement: continuous }}
                entities {{ entity e {{ type: enemy  spawn: "E"  color: "#f00"  speed: 2.0  ai: {ai} }} }}
                player {{ name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }}
            """)
            assert m.entities.entities[0].ai == ai


class TestRulesBlock:
    def test_win_lose_conditions(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 3 }
            rules {
                win: all_dots_collected
                lose: lives_depleted
            }
        """)
        assert m.rules.win == "all_dots_collected"
        assert m.rules.lose == "lives_depleted"

    def test_collision_rule_parses(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities {
                entity food  { type: collectible  symbol: "F"  color: "#f00"  score: 10 }
                entity ghost { type: enemy  spawn: "G"  color: "#f0f"  speed: 2.0  ai: chase }
            }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 3 }
            rules {
                lose: lives_depleted
                on_collision player food: collect, add_points, grow
                on_collision player ghost: lose_life
            }
        """)
        assert len(m.rules.collision_rules) == 2
        r0 = m.rules.collision_rules[0]
        assert r0.subject == "player"
        assert r0.object == "food"
        assert len(r0.actions) == 3

    def test_conditional_collision_rule(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity ghost { type: enemy  spawn: "G"  color: "#f0f"  speed: 2.0  ai: chase } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 3 }
            rules {
                lose: lives_depleted
                on_collision player ghost when $powered == true: destroy, add_points
                on_collision player ghost when $powered == false: lose_life
            }
            variables {
                bool powered = false
            }
        """)
        cond_rules = [r for r in m.rules.collision_rules if r.condition is not None]
        assert len(cond_rules) == 2
        r = cond_rules[0]
        assert r.condition.op == "=="
        assert r.condition.left.name == "powered"

    def test_timer_rule_parses(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity ghost { type: enemy  spawn: "G"  color: "#f0f"  speed: 2.0  ai: chase } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 3 }
            rules {
                lose: lives_depleted
                on_timer 8.0: set $powered = false
            }
            variables { bool powered = true }
        """)
        assert len(m.rules.timer_rules) == 1
        tr = m.rules.timer_rules[0]
        assert tr.interval == pytest.approx(8.0)
        assert len(tr.actions) == 1
        assert tr.actions[0].__class__.__name__ == "SetVarAction"

    def test_set_var_action(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity pellet { type: pickup  symbol: "o"  color: "#fff"  score: 50 } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 3 }
            rules {
                lose: lives_depleted
                on_collision player pellet: collect, add_points, set $powered = true
            }
            variables { bool powered = false }
        """)
        rule = m.rules.collision_rules[0]
        set_actions = [a for a in rule.actions if a.__class__.__name__ == "SetVarAction"]
        assert len(set_actions) == 1
        assert set_actions[0].var_name == "powered"

    def test_spawn_action_at_random(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity ghost { type: enemy  spawn: "G"  color: "#f0f"  speed: 2.0  ai: chase } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 3 }
            rules {
                lose: lives_depleted
                on_timer 5.0: spawn ghost at random
            }
        """)
        tr = m.rules.timer_rules[0]
        spawn = tr.actions[0]
        assert spawn.__class__.__name__ == "SpawnAction"
        assert spawn.entity == "ghost"
        assert spawn.loc_type == "random"

    def test_all_win_conditions_valid(self, mm):
        for win in ("all_dots_collected", "all_enemies_defeated", "all_targets_filled", "survival", "reached_exit"):
            m = parse(mm, f"""
                game "G" {{ canvas: 400x400 fps: 60 background: "#000" }}
                engine {{ type: grid  movement: continuous }}
                entities {{ entity wall {{ type: solid  symbol: "#"  color: "#333" }} }}
                player {{ name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }}
                rules {{ win: {win}  lose: lives_depleted }}
            """)
            assert m.rules.win == win


class TestVariablesBlock:
    def test_variables_parse(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }
            variables {
                bool powered = false
                int  score   = 0
                float timer  = 0.0
            }
        """)
        assert m.variables is not None
        assert len(m.variables.vars) == 3
        vmap = {v.name: v for v in m.variables.vars}
        assert vmap["powered"].type == "bool"
        assert vmap["score"].type == "int"
        assert vmap["timer"].type == "float"

    def test_variable_default_bool(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }
            variables { bool powered = false }
        """)
        v = m.variables.vars[0]
        assert v.default_val.val == "false"

    def test_variable_default_int(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }
            variables { int score = 42 }
        """)
        v = m.variables.vars[0]
        assert v.default_val.val == 42


class TestPlayerBlock:
    def test_player_with_spawn_symbol(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            map { cell_size: 20  layout: ["####", "#P #", "####"] }
            player { name: "Hero"  spawn: "P"  color: "#0f0"  speed: 4  lives: 3 }
        """)
        assert m.player.spawn_symbol == "P"
        assert m.player.name == "Hero"
        assert m.player.color == "#0f0"

    def test_player_with_start_coords(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            player { name: "Hero"  start: (13, 22)  color: "#ff0"  speed: 4  lives: 3 }
        """)
        assert m.player.start_x == 13
        assert m.player.start_y == 22

    def test_player_with_shoot_block(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: top_down  shooting: true }
            entities {
                entity bullet { type: projectile  color: "#fbbf24"  speed: 18  direction: from_player  on_hit_wall: destroy  on_hit_entity: destroy }
            }
            player {
                name: "Commander"
                start: (5, 5)
                color: "#60a5fa"
                speed: 6
                lives: 3
                shoot {
                    projectile: bullet
                    cooldown: 0.2
                    key: space
                }
            }
        """)
        assert m.player.shoot is not None
        assert m.player.shoot.projectile_name == "bullet"
        assert m.player.shoot.cooldown == pytest.approx(0.2)
        assert m.player.shoot.key == "space"

    def test_player_snake_extras(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous  grow_on_eat: true }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            player {
                name: "Serpent"
                start: (10, 10)
                color: "#0a0"
                speed: 8
                lives: 1
                controls: arrows | wasd
                start_length: 3
                start_direction: right
                head_color: "#0f0"
            }
        """)
        assert m.player.head_color == "#0f0"
        assert m.player.start_length == 3
        assert m.player.start_direction == "right"
        schemes = [s for s in m.player.controls.schemes]
        assert "arrows" in schemes
        assert "wasd" in schemes


class TestMapBlock:
    def test_map_with_layout(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            map {
                cell_size: 20
                layout: ["####", "#  #", "# P#", "####"]
            }
            player { name: "P"  spawn: "P"  color: "#fff"  speed: 4  lives: 1 }
        """)
        assert m.map is not None
        assert m.map.cell_size == 20
        assert len(m.map.layout) == 4

    def test_map_with_border(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            map { cell_size: 20  border: wall }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }
        """)
        assert m.map.border == "wall"


class TestOptionalSections:
    def test_sounds_parse(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }
            sounds {
                sound eat { type: beep  frequency: 660  duration: 0.08  volume: 0.3 }
                sound die { type: explosion  duration: 0.35  volume: 0.5 }
            }
        """)
        assert m.sounds is not None
        assert len(m.sounds.sounds) == 2
        names = [s.name for s in m.sounds.sounds]
        assert "eat" in names
        assert "die" in names

    def test_levels_parse(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }
            levels {
                level 1 { speed_multiplier: 1.0  enemy_count: 6 }
                level 2 { speed_multiplier: 1.3  enemy_count: 9 }
            }
        """)
        assert m.levels is not None
        assert len(m.levels.levels) == 2
        assert m.levels.levels[1].speed_multiplier == pytest.approx(1.3)

    def test_animations_parse(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }
            animations {
                animation enemy_death { effect: explode  duration: 0.5  color: "#ff6600"  particle_count: 12 }
            }
        """)
        assert m.animations is not None
        assert m.animations.animations[0].effect == "explode"
        assert m.animations.animations[0].particle_count == 12

    def test_items_parse(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }
            items {
                item boost { symbol: "*"  color: "#facc15"  score: 20  effect: speed_up  duration: 3.0  drop_chance: 0.2 }
            }
        """)
        assert m.items is not None
        item = m.items.items[0]
        assert item.name == "boost"
        assert item.effect == "speed_up"
        assert item.drop_chance == pytest.approx(0.2)

    def test_ui_block_parses(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }
            ui { score: top_left  lives: top_right  level: top_center }
        """)
        assert m.ui.score_pos == "top_left"
        assert m.ui.lives_pos == "top_right"
        assert m.ui.level_pos == "top_center"


class TestInvalidModels:
    def test_invalid_engine_type_rejected(self, mm):
        with pytest.raises((TextXSyntaxError, TextXSemanticError, Exception)):
            parse(mm, """
                game "Bad" { canvas: 400x400 fps: 60 background: "#000" }
                engine { type: pong }
                player { name: "P"  start: (1, 1)  color: "#fff"  speed: 3  lives: 1 }
            """)

    def test_invalid_entity_type_rejected(self, mm):
        with pytest.raises((TextXSyntaxError, TextXSemanticError, Exception)):
            parse(mm, """
                game "Bad" { canvas: 400x400 fps: 60 background: "#000" }
                engine { type: grid  movement: continuous }
                entities { entity x { type: flying  symbol: "X"  color: "#fff" } }
                player { name: "P"  start: (1, 1)  color: "#fff"  speed: 3  lives: 1 }
            """)

    def test_invalid_sound_type_rejected(self, mm):
        with pytest.raises((TextXSyntaxError, TextXSemanticError, Exception)):
            parse(mm, """
                game "Bad" { canvas: 400x400 fps: 60 background: "#000" }
                engine { type: grid  movement: continuous }
                entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
                player { name: "P"  start: (1, 1)  color: "#fff"  speed: 3  lives: 1 }
                sounds { sound sfx { type: laser } }
            """)

    def test_invalid_item_effect_rejected(self, mm):
        with pytest.raises((TextXSyntaxError, TextXSemanticError, Exception)):
            parse(mm, """
                game "Bad" { canvas: 400x400 fps: 60 background: "#000" }
                engine { type: grid  movement: continuous }
                entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
                player { name: "P"  start: (1, 1)  color: "#fff"  speed: 3  lives: 1 }
                items { item gem { symbol: "*"  color: "#fff"  effect: fly } }
            """)

    def test_invalid_ai_type_rejected(self, mm):
        with pytest.raises((TextXSyntaxError, TextXSemanticError, Exception)):
            parse(mm, """
                game "Bad" { canvas: 400x400 fps: 60 background: "#000" }
                engine { type: grid  movement: continuous }
                entities { entity enemy { type: enemy  spawn: "E"  color: "#f00"  ai: smarty } }
                player { name: "P"  start: (1, 1)  color: "#fff"  speed: 3  lives: 1 }
            """)


class TestBehaviorGrammar:
    @pytest.fixture(scope="class")
    def behavior_mm(self):
        return metamodel_from_file(str(ROOT / "grammar" / "behavior.tx"))

    def test_behavior_grammar_loads(self, behavior_mm):
        assert behavior_mm is not None

    def test_empty_ruleset_parses(self, behavior_mm):
        with tempfile.NamedTemporaryFile(suffix=".behavior", mode="w", delete=False) as f:
            f.write("ruleset Empty {}")
            path = f.name
        try:
            model = behavior_mm.model_from_file(path)
            assert len(model.rulesets) == 1
            assert model.rulesets[0].name == "Empty"
        finally:
            os.unlink(path)

    def test_ruleset_with_entities_and_rules(self, behavior_mm):
        with tempfile.NamedTemporaryFile(suffix=".behavior", mode="w", delete=False) as f:
            f.write(textwrap.dedent("""
                ruleset BaseShooter {
                    entities {
                        entity wall   { type: solid  symbol: "#"  color: "#1e293b" }
                        entity enemy  { type: enemy  spawn: "E"  color: "#ef4444"  speed: 2.5  ai: chase  points: 100 }
                        entity bullet { type: projectile  color: "#fbbf24"  speed: 18  direction: from_player  on_hit_wall: destroy  on_hit_entity: destroy }
                    }
                    rules {
                        win: all_enemies_defeated
                        lose: lives_depleted
                        on_collision player enemy: lose_life
                        on_collision bullet enemy: destroy, add_points
                    }
                }
            """))
            path = f.name
        try:
            model = behavior_mm.model_from_file(path)
            rs = model.rulesets[0]
            assert rs.name == "BaseShooter"
            assert rs.entities is not None
            assert len(rs.entities.entities) == 3
            assert rs.rules.win == "all_enemies_defeated"
        finally:
            os.unlink(path)


class TestImportDirectives:
    def test_import_directive_parses(self, mm):
        m = parse(mm, """
            import "../behaviors/dummy.behavior"
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }
        """)
        assert len(m.imports) == 1
        assert "dummy.behavior" in m.imports[0].path

    def test_use_directive_parses(self, mm):
        m = parse(mm, """
            game "G" { canvas: 400x400 fps: 60 background: "#000" }
            use ruleset MyBase
            engine { type: grid  movement: continuous }
            entities { entity wall { type: solid  symbol: "#"  color: "#333" } }
            player { name: "P"  start: (5, 5)  color: "#fff"  speed: 4  lives: 1 }
        """)
        assert len(m.uses) == 1
        assert m.uses[0].ruleset_name == "MyBase"
