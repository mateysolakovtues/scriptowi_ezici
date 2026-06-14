import sys
import arcade
from pathlib import Path

# When packaged with PyInstaller the bundled assets live under sys._MEIPASS;
# during development they sit next to this file.
if getattr(sys, "frozen", False):
    HERE = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    # Saves must go somewhere writable, not the read-only bundle.
    SAVE_DIR = Path.home() / ".wok_of_the_warrior"
else:
    HERE = Path(__file__).parent
    SAVE_DIR = HERE

SAVE_DIR.mkdir(parents=True, exist_ok=True)
SAVE_FILE = SAVE_DIR / "saves.json"

SCREEN_TITLE = "Wok of the Warrior"

CHARACTER_SCALING  = 2.0
PLAYER_SPEED       = 5
GRAVITY            = 1
JUMP_SPEED         = 25
UPDATES_PER_FRAME  = 6

PHYS_W = 40
PHYS_H = 90

TILE_SCALE = 3
TILE_SIZE  = 18 * TILE_SCALE   # 54 px

DEATH_Y = -50

SAMURAI_PATH = HERE / "assets/image/craftpix-net-123681-free-samurai-pixel-art-sprite-sheets/Samurai"
KENNEY_TILES = HERE / "assets/image/kenney_pixel-platformer-food-expansion/Tiles"
BG_IMAGE     = HERE / "assets/image/360_F_1504035261_KQEBa5gLMegqUHn6ndz1YC5m4NRYetTl.jpg"
SLIME_BASE   = HERE / "assets/enemy/craftpix-net-788364-free-slime-mobs-pixel-art-top-down-sprite-pack/PNG"

# Boss: the Samurai Commander character + its battle theme.
BOSS_PATH  = HERE / "assets/boss/Samurai_Commander"
BOSS_MUSIC = HERE / "assets/boss/Godfrey, First Elden Lord - Tai Tomisawa - Topic (128k).mp3"

ATTACK_KEYS = {
    arcade.key.Z: 0, arcade.key.J: 0,
    arcade.key.X: 1, arcade.key.K: 1,
    arcade.key.C: 2, arcade.key.L: 2,
}

# Connecting terrain tiles. These specific tiles are seamless (no side
# borders), so a run of them reads as one continuous mass: the topmost block
# of a column uses the "surface" tile (frosting top), blocks below use the
# "fill" tile. The bordered variants (0,1,3,16,17,19,...) are caps and would
# break the join, so they are intentionally not used.
TERRAIN_SURFACE = ["tile_0002.png"]   # seamless frosting top
TERRAIN_FILL    = ["tile_0050.png"]   # seamless cake fill (both directions)

# Floating platform tops (one row thick, so always a surface tile).
PLATFORM_F_TILES = ["tile_0006.png"]  # seamless pink frosting
PLATFORM_H_TILES = ["tile_0002.png"]  # seamless brown cake

TILE_CHARS = {
    "B": "tile_0050.png",   # terrain (surface/fill chosen per-tile at build time)
    "F": "tile_0006.png",   # pink frosting platform
    "H": "tile_0002.png",   # brown cake platform
}
WALL_TILES     = {"B", "H"}
PLATFORM_TILES = {"F"}
DECOR_TILES    = {"X"}      # looks like terrain but the player passes through it

SLIME_FRAME_W     = 64
SLIME_FRAME_H     = 64
SLIME_SCALE       = 3.0
SLIME_PATROL      = TILE_SIZE * 4
SWORD_REACH_X     = 90
SWORD_REACH_Y     = 60
SLIME_FOOT_OFFSET = 8

ANIM_X_OFFSETS = {
    "walk_right":  (64 - 58.2) * CHARACTER_SCALING,
    "walk_left":  -(64 - 58.2) * CHARACTER_SCALING,
    "idle_right":  (64 - 31.7) * CHARACTER_SCALING,
    "idle_left":  -(64 - 31.7) * CHARACTER_SCALING,
}
