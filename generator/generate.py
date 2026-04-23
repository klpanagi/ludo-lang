#!/usr/bin/env python3

import sys, os, json
from textx import metamodel_from_file
from jinja2 import Environment, FileSystemLoader


def resolve_spawn_positions(layout, tile_symbol):
    positions = []
    for r, row in enumerate(layout):
        for c, ch in enumerate(row):
            if ch == tile_symbol:
                positions.append({"col": c, "row": r})
    return positions


def _bool_val_to_js(val):
    if isinstance(val, str):
        return "true" if val == "true" else "false"
    return "true" if val else "false"


def rule_condition_to_js(cond):
    def operand_to_js(op):
        cls = op.__class__.__name__
        if cls == "VarRef":
            return '{"var": ' + json.dumps(op.name) + "}"
        elif cls == "BoolLit":
            return '{"val": ' + _bool_val_to_js(op.val) + "}"
        else:  # NumLit
            return '{"val": ' + str(op.val) + "}"

    return (
        "{left: "
        + operand_to_js(cond.left)
        + ", op: "
        + json.dumps(cond.op)
        + ", right: "
        + operand_to_js(cond.right)
        + "}"
    )


def ext_action_to_js(action):
    cls = action.__class__.__name__
    if cls == "SimpleRuleAction":
        return '{"type": ' + json.dumps(action.action) + "}"
    elif cls == "SetVarAction":
        val_cls = action.value.__class__.__name__
        if val_cls == "BoolLit":
            val = _bool_val_to_js(action.value.val)
        else:
            val = str(action.value.val)
        return (
            '{"type": "set", "var": '
            + json.dumps(action.var_name)
            + ', "val": '
            + val
            + "}"
        )
    elif cls == "SpawnAction":
        return (
            '{"type": "spawn", "entity": '
            + json.dumps(action.entity)
            + ', "location": '
            + json.dumps(action.location)
            + "}"
        )
    return "{}"


def load_rulesets(model_file, imports):
    """Load all .behavior files and return {name: RulesetDef} dict."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    behavior_grammar = os.path.join(script_dir, "..", "grammar", "behavior.tx")
    behavior_mm = metamodel_from_file(behavior_grammar)
    model_dir = os.path.dirname(model_file)
    rulesets = {}
    for imp in imports:
        beh_path = os.path.join(model_dir, imp.path)
        beh_path = os.path.abspath(beh_path)
        beh_model = behavior_mm.model_from_file(beh_path)
        for rs in beh_model.rulesets:
            rulesets[rs.name] = rs
    return rulesets


def merge_ruleset(game, ruleset):
    """
    Merge ruleset sections into game model.
    Merge semantics per section type:
      - List sections (tiles, actors, sounds, animations, items, levels):
          ruleset items prepended to game items (game items take precedence order-wise)
      - Single sections (map, player, food, mechanics, ui):
          game wins — only apply ruleset value if game doesn't have it
      - rules: merge collision_rules and timer_rules lists;
               game's win/lose conditions win over ruleset's
      - variables: combine; on name conflict, game's variable wins
    """
    # --- tiles (list) ---
    if ruleset.tiles and ruleset.tiles.tiles:
        if game.tiles:
            game.tiles.tiles = list(ruleset.tiles.tiles) + list(game.tiles.tiles)
        else:
            game.tiles = ruleset.tiles

    # --- actors (list) ---
    if ruleset.actors and ruleset.actors.actors:
        if game.actors:
            game.actors.actors = list(ruleset.actors.actors) + list(game.actors.actors)
        else:
            game.actors = ruleset.actors

    # --- single-value sections: game wins ---
    for attr in (
        "map",
        "player",
        "food",
        "mechanics",
        "ui",
        "tetris_config",
        "platformer_config",
        "towerdefense_config",
    ):
        rs_val = getattr(ruleset, attr, None)
        g_val = getattr(game, attr, None)
        if rs_val and not g_val:
            setattr(game, attr, rs_val)

    # --- rules: merge ---
    if ruleset.rules:
        if game.rules:
            game.rules.collision_rules = list(ruleset.rules.collision_rules) + list(
                game.rules.collision_rules
            )
            game.rules.timer_rules = list(ruleset.rules.timer_rules) + list(
                game.rules.timer_rules
            )
            if not game.rules.win and ruleset.rules.win:
                game.rules.win = ruleset.rules.win
            if not game.rules.lose and ruleset.rules.lose:
                game.rules.lose = ruleset.rules.lose
        else:
            game.rules = ruleset.rules

    # --- variables: combine, game wins on conflict ---
    if ruleset.variables and ruleset.variables.vars:
        if game.variables:
            existing = {v.name for v in game.variables.vars}
            new_vars = [v for v in ruleset.variables.vars if v.name not in existing]
            game.variables.vars = new_vars + list(game.variables.vars)
        else:
            game.variables = ruleset.variables

    # --- list-extension sections ---
    list_sections = [
        ("sounds", "sounds"),
        ("animations", "animations"),
        ("items", "items"),
        ("levels", "levels"),
    ]
    for section_attr, items_attr in list_sections:
        rs_sec = getattr(ruleset, section_attr, None)
        g_sec = getattr(game, section_attr, None)
        if rs_sec:
            rs_items = getattr(rs_sec, items_attr, [])
            if rs_items:
                if g_sec:
                    g_items = getattr(g_sec, items_attr, [])
                    setattr(g_sec, items_attr, list(rs_items) + list(g_items))
                else:
                    setattr(game, section_attr, rs_sec)


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate.py <model_file.game>")
        sys.exit(1)

    model_file = os.path.abspath(sys.argv[1])
    script_dir = os.path.dirname(os.path.abspath(__file__))
    grammar_path = os.path.join(script_dir, "..", "grammar", "game.tx")
    templates_dir = os.path.join(script_dir, "..", "templates")
    output_dir = os.path.join(script_dir, "..", "output")

    mm = metamodel_from_file(grammar_path)
    model = mm.model_from_file(model_file)

    game = model

    # Load and apply behavior rulesets
    imports = getattr(game, "imports", [])
    uses = getattr(game, "uses", [])
    if imports or uses:
        rulesets = load_rulesets(model_file, imports)
        for use in uses:
            if use.ruleset_name in rulesets:
                merge_ruleset(game, rulesets[use.ruleset_name])
            else:
                print(
                    f"Warning: ruleset '{use.ruleset_name}' not found in imported files",
                    file=sys.stderr,
                )

    if game.map and game.map.layout_file:
        map_path = os.path.join(os.path.dirname(model_file), game.map.layout_file)
        with open(map_path) as f:
            game.map.layout = [line.rstrip("\n") for line in f.readlines()]

    layout = game.map.layout if game.map else []

    enemies = []
    projectiles = []
    if game.actors:
        for actor in game.actors.actors:
            cls = actor.__class__.__name__
            if cls == "EnemyDef":
                if actor.spawn_tile:
                    positions = resolve_spawn_positions(layout, actor.spawn_tile)
                    actor._spawn_positions = positions
                else:
                    actor._spawn_positions = [
                        {"col": actor.start_x, "row": actor.start_y}
                    ]
                enemies.append(actor)
            elif cls == "ProjectileDef":
                projectiles.append(actor)

    player_spawn = None
    if game.player and getattr(game.player, "spawn_tile", None):
        positions = resolve_spawn_positions(layout, game.player.spawn_tile)
        player_spawn = positions[0] if positions else {"col": 0, "row": 0}

    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)
    env.filters["ruleConditionToJS"] = rule_condition_to_js
    env.filters["extActionToJS"] = ext_action_to_js

    game_type = game.type
    template = env.get_template(f"{game_type}.html.j2")

    os.makedirs(output_dir, exist_ok=True)
    game_name = game.name.lower().replace(" ", "_").replace("-", "_")
    output_path = os.path.join(output_dir, f"{game_name}.html")

    html = template.render(
        game=game,
        enemies=enemies,
        projectiles=projectiles,
        player_spawn=player_spawn,
        levels=game.levels.levels if game.levels else [],
        sounds=game.sounds.sounds if game.sounds else [],
        animations=game.animations.animations if game.animations else [],
        items=game.items.items if game.items else [],
        variables=game.variables.vars if game.variables else [],
        game_rules=game.rules if game.rules else None,
    )
    with open(output_path, "w") as f:
        f.write(html)
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
