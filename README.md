# Ludo — 2D Game Generation DSL

Ludo is a domain-specific language for declaratively defining 2D browser games. Write a `.game` model file describing your game's tiles, map, player, rules, and UI — Ludo generates a self-contained, playable HTML file with no build step and no external dependencies.

```
game "Space Defender" {
  type: shooter
  canvas: 672x544
  fps: 60
  background: "#05050a"
}

player { name: "Commander"  color: "#60a5fa"  speed: 6  lives: 3 }
rules  { win: all_enemies_defeated  lose: lives_depleted }
ui     { score: top_right  lives: top_left }
```

```
python generator/generate.py examples/space_defender.game
# → output/space_defender.html  (open in any browser, no server needed)
```

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Docker](#docker)
3. [Web UI](#web-ui)
4. [Supported Game Types](#supported-game-types)
5. [DSL Reference](#dsl-reference)
   - [Game Header](#game-header)
   - [Tiles](#tiles)
   - [Map](#map)
   - [Player](#player)
   - [Actors](#actors)
   - [Food](#food)
   - [Mechanics](#mechanics)
   - [Rules](#rules)
   - [Levels](#levels)
   - [Sounds](#sounds)
   - [Animations](#animations)
   - [Items](#items)
   - [UI](#ui)
   - [Variables (Behavior DSL)](#variables-behavior-dsl)
   - [Timer Rules](#timer-rules)
   - [Conditional Collision Rules](#conditional-collision-rules)
6. [Behavior Reuse](#behavior-reuse)
7. [Project Structure](#project-structure)
8. [Running Tests](#running-tests)

---

## Quick Start

**Requirements**: Python 3.11+, textX 4.3.0, Jinja2 3.1.6

```bash
pip install textX==4.3.0 Jinja2==3.1.6

# Generate a game
python generator/generate.py examples/enhanced_snake.game
# Open output/enhanced_snake.html in your browser

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

## Supported Game Types

| `type` | Description |
|--------|-------------|
| `snake` | Classic snake — grow by eating food, avoid walls and yourself |
| `pacman` | Maze dot-collector with ghost AI |
| `shooter` | Top-down arena shooter with enemy AI |
| `breakout` | Paddle-and-ball brick breaker |
| `invaders` | Fixed-formation space invaders |
| `bomberman` | Grid-based bomb-placement action |
| `frogger` | Lane-crossing with moving obstacles |
| `sokoban` | Push-the-box puzzle |
| `tetris` | Falling-tetromino stacker |
| `platformer` | Side-scrolling platformer with jump physics |
| `towerdefense` | Path-based tower defense with waves |

---

## DSL Reference

### Game Header

Every `.game` file starts with a `game` block.

```
game "My Game" {
    type: snake          # Required. One of the 11 supported types.
    canvas: 600 x 600   # Width x Height in pixels (spaces around x are optional)
    fps: 60             # Target frame rate
    background: "#0d1117"
}
```

---

### Tiles

Define named tile types used in the map layout. Each character in the map grid corresponds to a tile symbol.

```
tiles {
    tile wall         symbol: "#"  solid: true   color: "#1e293b"
    tile empty        symbol: "."  solid: false  color: "#05050a"
    tile player_spawn symbol: "P"  solid: false  color: "#05050a"  tag: player_spawn
    tile dot          symbol: "."  solid: false  color: "#ffb8ae"  collectible: true  score: 10
    tile power_pellet symbol: "o"  solid: false  color: "#ffffff"  collectible: true  score: 50
}
```

| Attribute | Type | Description |
|-----------|------|-------------|
| `symbol` | string (1 char) | Character used in the map layout |
| `solid` | bool | Whether the tile blocks movement |
| `color` | hex string | Rendered color |
| `collectible` | bool | Whether the player can collect this tile |
| `score` | int | Points awarded on collection |
| `tag` | identifier | Semantic tag (e.g. `player_spawn`, `enemy_spawn`) |

---

### Map

Defines the level grid. Each row is a string; character positions correspond to tile symbols.

```
map {
    cell_size: 20         # Pixels per grid cell
    layout: [
        "##############################",
        "#                            #",
        "#            P               #",
        "#                            #",
        "##############################"
    ]
}
```

---

### Player

```
player {
    name: "Serpent"
    start: (15, 15)           # Grid position (col, row). Or use: spawn: tile "P"
    spawn: tile "P"           # Spawn at the cell tagged with symbol "P"
    shape: square             # Visual shape: square | circle
    color: "#00aa44"
    head_color: "#00ff66"     # Distinct color for the snake head (snake only)
    speed: 8                  # Movement speed (meaning varies by game type)
    lives: 3
    controls: arrows | wasd  # Key bindings
    start_length: 3           # (snake) Initial length
    start_direction: right    # (snake) Initial direction: up | down | left | right
    grow_on_eat: true         # (snake) Whether eating food grows the snake

    shoot {                   # (shooter/invaders) Shooting configuration
        projectile: Bullet    # References an actor defined in actors {}
        cooldown: 0.2         # Seconds between shots
        key: space
    }
}
```

---

### Actors

Define enemies and projectiles.

```
actors {
    enemy "Grunt" {
        spawn: tile "E"       # Spawn at cells with this symbol
        color: "#ef4444"
        speed: 2.5
        points: 100           # Score awarded when destroyed
        behavior: chase       # AI: chase | ambush | patrol | random | sine
    }
    enemy "Flanker" {
        spawn: tile "E"
        color: "#f97316"
        speed: 3.5
        points: 200
        behavior: ambush
    }
    projectile "Bullet" {
        speed: 18
        color: "#fbbf24"
        direction: from_player
        on_hit_wall: destroy
        on_hit_enemy: destroy_all
    }
}
```

---

### Food

Used in snake-type games to define collectible food items.

```
food {
    count: 1          # Number of food items on the board at once
    color: "#ff4444"
    score: 10
    respawn: true     # Whether food reappears after being eaten
}
```

---

### Mechanics

```
mechanics {
    collision: wall | self    # What the player collides with
    lose_condition: collision_detected
    wrap: false               # Whether the player wraps around map edges
}
```

---

### Rules

Define win/lose conditions and collision-triggered effects.

```
rules {
    win: all_enemies_defeated         # or: all_dots_collected | reached_exit | survival
    lose: lives_depleted              # or: collision_detected | time_expired
    on_collision player enemy: lose_life
    on_collision projectile enemy: destroy, add_points
    on_collision player dot: collect, add_points
}
```

**Available actions for `on_collision`**:
`lose_life`, `add_points`, `destroy`, `destroy_all`, `collect`, `next_level`, `spawn <entity>`

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
        drop_chance: 0.20     # 0.0–1.0 probability of spawning after food is eaten
    }
    item star {
        symbol: "★"
        color: "#a855f7"
        score: 50
        effect: score_multiply
        duration: 5.0
        drop_chance: 0.10
    }
}
```

---

### UI

Position score, lives, and level indicators on screen.

```
ui {
    score: top_left      # top_left | top_right | top_center | bottom_left | bottom_right
    lives: top_right
    level: top_center
}
```

---

### Variables (Behavior DSL)

Named typed state variables that can be referenced in rules using the `$` sigil.

```
variables {
    int   kill_count  = 0
    float power_timer = 0.0
    bool  powered_up  = false
}
```

| Type | Values |
|------|--------|
| `int` | Integer with optional default |
| `float` | Float with optional default |
| `bool` | `true` or `false` |

---

### Timer Rules

Trigger actions on a fixed time interval, with an optional condition.

```
rules {
    on_timer 5.0: spawn Grunt at tile "E"
    on_timer 10.0 when $kill_count >= 5: spawn Flanker at tile "E"
}
```

---

### Conditional Collision Rules

Collision rules can be guarded by a variable condition.

```
rules {
    on_collision player enemy when $powered_up == true: destroy_all, add_points
    on_collision player enemy when $powered_up == false: lose_life
}
```

Supported condition operators: `==`, `!=`, `<`, `>`, `<=`, `>=`

---

## Behavior Reuse

Behaviors are reusable DSL fragments that can be shared across multiple game models. They are defined in `.behavior` files and imported into `.game` files.

### Defining a behavior file

```
# behaviors/shooter_base.behavior

ruleset ShooterBase {
  tiles {
    tile wall         symbol: "#"  solid: true   color: "#1e293b"
    tile empty        symbol: "."  solid: false  color: "#05050a"
    tile player_spawn symbol: "P"  solid: false  color: "#05050a"  tag: player_spawn
    tile enemy_spawn  symbol: "E"  solid: false  color: "#05050a"  tag: enemy_spawn
  }
  actors {
    enemy "Grunt" {
      spawn: tile "E"
      color: "#ef4444"
      speed: 2.5
      points: 100
      behavior: chase
    }
    projectile "Bullet" {
      speed: 18
      color: "#fbbf24"
      direction: from_player
      on_hit_wall: destroy
      on_hit_enemy: destroy_all
    }
  }
  rules {
    win: all_enemies_defeated
    lose: lives_depleted
    on_collision player enemy: lose_life
    on_collision projectile enemy: destroy, add_points
  }
}
```

### Using a behavior in a game file

```
import "../behaviors/shooter_base.behavior"

game "Space Defender V2" {
  type: shooter
  canvas: 672x544
  fps: 60
  background: "#05050a"
}

use ruleset ShooterBase    # merge ShooterBase into this model

map { ... }
player { ... }
ui { score: top_right  lives: top_left }
```

### Merge semantics

When `use ruleset X` is applied:

| Section | Merge behavior |
|---------|---------------|
| `tiles`, `actors`, `sounds`, `animations`, `items` | Ruleset entries are **prepended**; game-specific entries win on conflict |
| `map`, `player`, `ui`, `mechanics`, `food` | Game model wins (single-value sections) |
| `rules.collision_rules`, `rules.timer_rules` | **Union** — all rules from both sources are active |
| `variables` | Combined; game model wins on name conflict |

### Available behavior files

| File | Ruleset | Provides |
|------|---------|---------|
| `behaviors/shooter_base.behavior` | `ShooterBase` | Wall/empty/spawn tiles, Grunt enemy, Bullet projectile, win/lose rules |
| `behaviors/pacman_base.behavior` | `PacManBase` | Full pacman tile set, ghost actors, dot/pellet rules, UI layout |

---

## Project Structure

```
├── grammar/
│   ├── game.tx            # textX grammar — GameModel (+ import/use directives)
│   └── behavior.tx        # textX grammar — BehaviorModel (ruleset definitions)
├── generator/
│   └── generate.py        # CLI: python generator/generate.py <model.game>
├── templates/
│   ├── _behavior_dsl.j2   # Shared: GAME_VARS, COLLISION_RULES, TIMER_RULES interpreter
│   ├── _runtime.j2        # Shared: drawOverlay, ctx.roundRect polyfill, keys input
│   ├── snake.html.j2
│   ├── pacman.html.j2
│   ├── shooter.html.j2
│   ├── breakout.html.j2
│   ├── invaders.html.j2
│   ├── bomberman.html.j2
│   ├── frogger.html.j2
│   ├── sokoban.html.j2
│   ├── tetris.html.j2
│   ├── platformer.html.j2
│   └── towerdefense.html.j2
├── behaviors/
│   ├── shooter_base.behavior
│   └── pacman_base.behavior
├── examples/              # 20 example .game models
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
# 175 passed
```
