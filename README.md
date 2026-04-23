# Ludo — 2D Game Generation DSL

Ludo is a domain-specific language for declaratively defining 2D browser games. Write a `.game` model file describing your game's engine, entities, map, player, rules, and UI — Ludo generates a self-contained, playable HTML file with no build step and no external dependencies.

```
game "Space Defender" {
    canvas: 672x544
    fps: 60
    background: "#05050a"
}

engine {
    type: top_down
    shooting: true
    ai_enemies: true
}

entities {
    entity enemy  { type: enemy       spawn: "E"  color: "#ef4444"  speed: 2.5  ai: chase  points: 100 }
    entity bullet { type: projectile  color: "#fbbf24"  speed: 18  direction: from_player  on_hit_wall: destroy  on_hit_entity: destroy }
}

player { name: "Commander"  spawn: "P"  color: "#60a5fa"  speed: 6  lives: 3 }
rules  { win: all_enemies_defeated  lose: lives_depleted }
ui     { score: top_right  lives: top_left }
```

```bash
python generator/generate.py examples/space_defender.game
# → output/space_defender.html  (open in any browser, no server needed)
```

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Docker](#docker)
3. [Web UI](#web-ui)
4. [Engine Types](#engine-types)
5. [DSL Reference](#dsl-reference)
   - [Game Header](#game-header)
   - [Engine Block](#engine-block)
   - [Entities](#entities)
   - [Map](#map)
   - [Player](#player)
   - [Rules](#rules)
   - [Levels](#levels)
   - [Sounds](#sounds)
   - [Animations](#animations)
   - [Items](#items)
   - [UI](#ui)
   - [Variables](#variables)
   - [Timer Rules](#timer-rules)
   - [Conditional Collision Rules](#conditional-collision-rules)
6. [Behavior Reuse](#behavior-reuse)
7. [Examples](#examples)
8. [Project Structure](#project-structure)
9. [Running Tests](#running-tests)

---

## Quick Start

**Requirements**: Python 3.11+, textX 4.3.0, Jinja2 3.1.6

```bash
pip install textX==4.3.0 Jinja2==3.1.6

# Generate a single game
python generator/generate.py examples/snake.game
# Open output/snake.html in your browser

# Generate all examples at once
for f in examples/*.game; do python generator/generate.py "$f"; done
```

---

## Docker

```bash
docker compose up -d
# Web UI available at http://localhost:8765
```

---

## Web UI

A minimal local web UI lets you edit `.game` files and preview the generated output in real time.

```bash
python ui/server.py
# → http://localhost:8765
```

The UI shows a list of available game models on the left, a DSL editor in the center, and a live iframe preview on the right.

---

## Engine Types

Ludo uses four generic engine types. All game behaviors — movement, AI, win/lose conditions, collision effects — are expressed through entity definitions, engine flags, and rule declarations.

| `type` | Description | Example games |
|--------|-------------|---------------|
| `grid` | Tile-based movement; cells are discrete steps | Snake, Pac-Man, Bomberman, Sokoban, Frogger, Space Invaders, Tetris |
| `top_down` | Free pixel-space movement from a bird's-eye view | Space Defender, Tower Defense |
| `platformer` | Side-scrolling with gravity, jump physics, and platforms | Platformer |
| `physics` | Ball/paddle physics with bounce mechanics | Breakout |

---

## DSL Reference

### Game Header

Every `.game` file starts with a `game` block.

```
game "My Game" {
    canvas: 600x600    # Width x Height in pixels
    fps: 60            # Target frame rate
    background: "#0d1117"
}
```

---

### Engine Block

The `engine` block selects the runtime engine and configures its behavior.

```
engine {
    type: grid         # grid | top_down | platformer | physics
    cell_size: 20      # Pixels per grid cell (grid engine)
    movement: continuous   # continuous | step | formation | falling (grid engine)
    wrap_edges: false  # Whether the player wraps around edges (grid engine)
    grow_on_eat: true  # Grow on collectible pickup (grid engine, snake-style)
}
```

#### `grid` engine flags

| Flag | Type | Description |
|------|------|-------------|
| `cell_size` | int | Pixels per grid cell |
| `movement` | enum | `continuous` (free direction), `step` (sokoban-style push), `formation` (invaders), `falling` (tetris) |
| `wrap_edges` | bool | Player teleports past map edges |
| `grow_on_eat` | bool | Player body grows when a collectible is consumed |
| `bomb_system` | bool | Enable bomb placement and blast mechanics |
| `dot_collect` | bool | Enable dot collection (Pac-Man style) |

#### `top_down` engine flags

| Flag | Type | Description |
|------|------|-------------|
| `shooting` | bool | Enable player shooting with a projectile entity |
| `ai_enemies` | bool | Activate AI behaviour on enemy entities |
| `wave_system` | bool | Spawn enemies in progressive waves |

#### `platformer` engine flags

| Flag | Type | Description |
|------|------|-------------|
| `gravity` | float | Downward acceleration in px/s² (default 900) |
| `jump_force` | float | Initial upward velocity on jump in px/s (default 420) |
| `scroll_speed` | float | Auto-scroll speed; 0 for camera-follow mode |
| `double_jump` | bool | Allow a second jump in mid-air |

#### `physics` engine flags

| Flag | Type | Description |
|------|------|-------------|
| `ball_speed` | float | Initial ball speed |
| `paddle_speed` | float | Paddle movement speed |
| `ball_size` | int | Ball radius in pixels |

---

### Entities

The `entities` block defines every interactive object in the game. There are no separate `tiles`, `actors`, or `food` blocks — all game objects are expressed here.

```
entities {
    entity wall {
        type: solid
        symbol: "#"
        color: "#334455"
    }
    entity food {
        type: collectible
        symbol: "F"
        color: "#ff4444"
        count: 1
        score: 10
        respawn: true
    }
    entity ghost {
        type: enemy
        spawn: "G"
        color: "#ff00ff"
        speed: 3.0
        ai: pathfinding
        points: 200
    }
    entity bullet {
        type: projectile
        color: "#fbbf24"
        speed: 18
        direction: from_player
        on_hit_wall: destroy
        on_hit_entity: destroy
    }
}
```

#### Entity types

| `type` | Role |
|--------|------|
| `solid` | Blocks movement; wall/ground tiles |
| `open` | Passable background tile |
| `collectible` | Collected by the player on contact |
| `enemy` | Adversarial — uses AI movement |
| `projectile` | Fired object; follows `direction` |
| `pickup` | One-time power-up item |
| `obstacle` | Collidable non-enemy object |
| `target` | Win condition marker (e.g. exit door) |
| `explosive` | Triggers area blast on detonation |

#### Entity attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `type` | EntityType | Required. One of the types above. |
| `symbol` | string (1 char) | Map layout character for this entity |
| `spawn` | string (1 char) | Character that marks spawn positions in the map |
| `color` | hex string | Render color |
| `solid` | bool | Override: whether this entity blocks movement |
| `speed` | float | Movement speed |
| `ai` | AIType | AI mode: `chase`, `formation`, `random`, `patrol`, `pathfinding`, `ambush`, `none` |
| `count` | int | Number to keep active simultaneously |
| `score` | int | Points awarded when collected |
| `points` | int | Points awarded when destroyed |
| `respawn` | bool | Re-appear after being collected/destroyed |
| `tag` | identifier | Semantic label for rule matching |
| `effect` | identifier | Power-up effect: `speed_up`, `score_multiply`, `extra_life`, `shield` |
| `duration` | float | Seconds the `effect` lasts |
| `direction` | identifier | Projectile direction: `from_player`, `down`, `up`, `left`, `right` |
| `on_hit_wall` | identifier | Projectile wall response: `destroy`, `bounce` |
| `on_hit_entity` | identifier | Projectile entity response: `destroy`, `bounce`, `pass_through` |
| `blast_radius` | int | Explosive blast radius in cells |
| `fuse_time` | float | Seconds before explosion |
| `release_delay` | float | Seconds between consecutive releases |
| `drop_chance` | float | 0.0–1.0 probability of spawning as a pickup |

---

### Map

Defines the level grid. Each string row maps characters to entity `symbol` values.

```
map {
    cell_size: 20
    layout: [
        "####################",
        "#                  #",
        "#        P         #",
        "#                  #",
        "####################"
    ]
}
```

Player spawn is marked with `"P"` in the layout, matched by `spawn: "P"` in the `player` block.

---

### Player

```
player {
    name: "Serpent"
    spawn: "P"            # Spawn at the cell with this map symbol
    start: (15, 15)       # Alternative: explicit grid position (col, row)
    shape: square         # Visual shape: square | circle
    color: "#00aa44"
    head_color: "#00ff66" # Distinct head color (grid engine, snake-style)
    speed: 8
    lives: 3
    controls: arrows      # Key bindings: arrows | wasd
    start_length: 3       # Initial tail length (grid/grow_on_eat)
    start_direction: right # Initial direction: up | down | left | right

    shoot {               # Enable player shooting
        projectile: bullet    # Name of a projectile entity
        cooldown: 0.2         # Seconds between shots
        key: space
    }
}
```

---

### Rules

Define win/lose conditions and collision-triggered effects.

```
rules {
    win: all_dots_collected
    lose: lives_depleted
    on_collision player food: collect, add_points, grow
    on_collision player ghost when $powered == true: destroy, add_points
    on_collision player ghost when $powered == false: lose_life
    on_collision bullet enemy: destroy, add_points
    on_timer 8.0: set $powered = false
}
```

#### Win conditions

| Condition | Triggers when |
|-----------|---------------|
| `all_dots_collected` | All collectible entities consumed |
| `all_enemies_defeated` | All enemy entities destroyed |
| `reached_exit` | Player contacts a `target` entity |
| `survival` | Player survives until time runs out |

#### Lose conditions

| Condition | Triggers when |
|-----------|---------------|
| `lives_depleted` | Player lives reach zero |
| `collision_detected` | Any harmful collision occurs |
| `time_expired` | Timer reaches zero |

#### Collision actions

| Action | Effect |
|--------|--------|
| `lose_life` | Decrement player lives |
| `add_points` | Award entity's `score` or `points` value |
| `destroy` | Remove the target entity |
| `collect` | Remove collectible and apply its `score` |
| `grow` | Extend player body (grid engine) |
| `next_level` | Advance to next level |
| `spawn <entity> at <loc>` | Spawn a new entity instance |

---

### Levels

Define progressive difficulty with per-level overrides.

```
levels {
    level 1 {
        speed_multiplier: 1.0
        enemy_count: 6
        background: "#05050a"
    }
    level 2 {
        speed_multiplier: 1.3
        enemy_count: 9
        background: "#050510"
    }
}
```

---

### Sounds

Procedural audio via the Web Audio API — no audio files needed.

```
sounds {
    sound eat {
        type: beep            # beep | explosion | sweep_up | sweep_down | noise
        frequency: 660        # Hz (for beep/sweep types)
        duration: 0.08        # Seconds
        volume: 0.3           # 0.0–1.0
    }
    sound die {
        type: explosion
        duration: 0.35
        volume: 0.5
    }
}
```

---

### Animations

Visual particle effects for game events.

```
animations {
    animation enemy_death {
        effect: explode       # explode | flash | slide
        duration: 0.5
        color: "#ff6600"
        particle_count: 12
    }
    animation player_hit {
        effect: flash
        duration: 0.3
        color: "#ff0000"
        particle_count: 6
    }
}
```

---

### Items

Collectible power-ups that appear during gameplay.

```
items {
    item speed_boost {
        symbol: "⚡"
        color: "#facc15"
        score: 20
        effect: speed_up      # speed_up | score_multiply | extra_life | shield
        duration: 3.0         # Seconds the effect lasts
        drop_chance: 0.20     # 0.0–1.0 probability of spawning
    }
}
```

---

### UI

Position HUD elements on screen.

```
ui {
    score: top_left      # top_left | top_right | top_center | bottom_left | bottom_right
    lives: top_right
    level: top_center
}
```

---

### Variables

Named typed state variables referenced in rules with the `$` sigil.

```
variables {
    int   kill_count = 0
    float power_timer = 0.0
    bool  powered = false
}
```

| Type | Values |
|------|--------|
| `int` | Integer with optional default |
| `float` | Float with optional default |
| `bool` | `true` or `false` |

---

### Timer Rules

Trigger rule actions on a fixed time interval with an optional condition.

```
rules {
    on_timer 5.0: spawn enemy at random
    on_timer 10.0 when $kill_count >= 5: spawn flanker at random
    on_timer 8.0: set $powered = false
}
```

---

### Conditional Collision Rules

Collision rules can be guarded by a variable condition.

```
rules {
    on_collision player ghost when $powered == true: destroy, add_points
    on_collision player ghost when $powered == false: lose_life
}
```

Supported condition operators: `==`, `!=`, `<`, `>`, `<=`, `>=`

---

## Behavior Reuse

Behaviors are reusable DSL fragments shared across multiple game models. They are defined in `.behavior` files and imported into `.game` files.

### Defining a behavior file

```
# behaviors/shooter_base.behavior

ruleset ShooterBase {
    entities {
        entity wall   { type: solid       symbol: "#"  color: "#1e293b" }
        entity open   { type: open        symbol: "."  color: "#05050a" }
        entity enemy  { type: enemy       spawn: "E"   color: "#ef4444"  speed: 2.5  ai: chase  points: 100 }
        entity bullet { type: projectile  color: "#fbbf24"  speed: 18  direction: from_player  on_hit_wall: destroy  on_hit_entity: destroy }
    }
    rules {
        win: all_enemies_defeated
        lose: lives_depleted
        on_collision player enemy: lose_life
        on_collision bullet enemy: destroy, add_points
    }
    ui {
        score: top_right
        lives: top_left
    }
}
```

### Using a behavior in a game file

```
import "../behaviors/shooter_base.behavior"

game "My Shooter" {
    canvas: 672x544
    fps: 60
    background: "#05050a"
}

use ruleset ShooterBase

engine { type: top_down  shooting: true  ai_enemies: true }
map { ... }
player { name: "Hero"  spawn: "P"  color: "#60a5fa"  speed: 6  lives: 3 }
```

### Merge semantics

When `use ruleset X` is applied:

| Section | Merge behavior |
|---------|----------------|
| `entities`, `sounds`, `animations`, `items` | Ruleset entries **prepended**; game-specific entries win on conflict |
| `engine`, `map`, `player`, `ui` | Game model wins (single-value sections) |
| `rules.collision_rules`, `rules.timer_rules` | **Union** — all rules from both sources are active |
| `variables` | Combined; game model wins on name conflict |

### Available behavior files

| File | Ruleset | Provides |
|------|---------|----------|
| `behaviors/shooter_base.behavior` | `ShooterBase` | Wall/open entities, enemy with chase AI, bullet projectile, win/lose rules |
| `behaviors/pacman_base.behavior` | `PacManBase` | Wall/dot/pellet/ghost entities, Pac-Man collision rules, UI layout |
| `behaviors/snake_base.behavior` | `SnakeBase` | Wall/food entities, grow-on-eat rules |
| `behaviors/bomberman_base.behavior` | `BombermanBase` | Wall/bomb/powerup entities, bomb system rules |
| `behaviors/invaders_base.behavior` | `InvadersBase` | Wall/invader/bullet entities, formation movement, wave rules |

---

## Examples

| File | Engine | Description |
|------|--------|-------------|
| `examples/snake.game` | `grid` | Classic snake — grow by eating food, avoid walls and yourself |
| `examples/pacman.game` | `grid` | Maze dot-collector with BFS ghost AI and power pellets |
| `examples/bomberman.game` | `grid` | Grid-based bomb placement with blast radius and chain explosions |
| `examples/sokoban.game` | `grid` | Push-the-box puzzle with step movement |
| `examples/frogger.game` | `grid` | Lane-crossing with moving obstacles |
| `examples/space_invaders.game` | `grid` | Fixed-formation space invaders with formation movement |
| `examples/tetris.game` | `grid` | Falling-tetromino stacker |
| `examples/space_defender.game` | `top_down` | Top-down arena shooter with multiple enemy AI types |
| `examples/towerdefense.game` | `top_down` | Path-based tower defense with wave spawning |
| `examples/platformer.game` | `platformer` | Side-scrolling platformer with gravity, jump, and patrol AI |
| `examples/breakout.game` | `physics` | Paddle-and-ball brick breaker with bounce physics |

Generate all examples:

```bash
for f in examples/*.game; do python generator/generate.py "$f"; done
ls output/
```

---

## Project Structure

```
├── grammar/
│   ├── game.tx            # textX grammar — GameModel (engine, entities, player, rules, ...)
│   └── behavior.tx        # textX grammar — BehaviorModel (ruleset definitions)
├── generator/
│   └── generate.py        # CLI: python generator/generate.py <model.game>
├── templates/
│   ├── _behavior_dsl.j2   # Shared: GAME_VARS, COLLISION_RULES, TIMER_RULES interpreter
│   ├── _runtime.j2        # Shared: drawOverlay, ctx.roundRect polyfill, key input
│   ├── grid.html.j2       # Engine: grid (snake, pacman, bomberman, sokoban, frogger, invaders, tetris)
│   ├── top_down.html.j2   # Engine: top_down (shooter, tower defense)
│   ├── platformer.html.j2 # Engine: platformer
│   └── physics.html.j2    # Engine: physics (breakout)
├── behaviors/
│   ├── shooter_base.behavior
│   ├── pacman_base.behavior
│   ├── snake_base.behavior
│   ├── bomberman_base.behavior
│   └── invaders_base.behavior
├── examples/              # 11 example .game models
├── output/                # Generated HTML files (git-ignored)
├── tests/
│   ├── conftest.py
│   ├── test_grammar.py
│   └── test_generator.py
├── ui/
│   ├── server.py          # stdlib HTTP server (port 8765)
│   └── index.html         # SPA: game list | DSL editor | iframe preview
├── Dockerfile
└── docker-compose.yml
```

---

## Running Tests

```bash
python -m pytest tests/ -q
# 123 passed
```
