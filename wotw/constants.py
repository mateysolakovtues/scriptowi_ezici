# ===========================================================================
# constants.py
# ---------------------------------------------------------------------------
# All the "knobs" and fixed values for the game live here in one place, so the
# rest of the code can `from constants import ...` instead of hard-coding
# numbers. It also figures out WHERE the asset/save files live (which differs
# between running from source and running the packaged .exe).
# ===========================================================================
import sys
import arcade
from pathlib import Path

# --- Where are the files? ---------------------------------------------------
# When packaged with PyInstaller the bundled assets live under sys._MEIPASS;
# during development they sit next to this file.
# `sys.frozen` is True only inside the built .exe.
if getattr(sys, "frozen", False):
    HERE = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    # Saves must go somewhere writable, not the read-only bundle.
    SAVE_DIR = Path.home() / ".wok_of_the_warrior"
else:
    HERE = Path(__file__).parent
    SAVE_DIR = HERE

# Make sure the save folder exists, then point at the single save file.
SAVE_DIR.mkdir(parents=True, exist_ok=True)
SAVE_FILE = SAVE_DIR / "saves.json"

SCREEN_TITLE = "Wok of the Warrior"   # window title

# --- Player physics / movement tuning --------------------------------------
CHARACTER_SCALING  = 2.0   # how much bigger than its raw art the player is drawn
PLAYER_SPEED       = 5     # horizontal move speed, pixels per frame
GRAVITY            = 1     # downward pull the physics engine applies each frame
JUMP_SPEED         = 25    # upward velocity when you jump
UPDATES_PER_FRAME  = 6     # game frames to wait before showing the next anim frame
                           # (higher = slower animation)

# The player's *collision* box (invisible). It's smaller than the drawn sprite
# so movement feels right; the visible samurai is positioned on top of it.
PHYS_W = 40                # collision box width
PHYS_H = 90                # collision box height

# --- Tile sizing ------------------------------------------------------------
TILE_SCALE = 3             # the food tiles are 18px art, scaled up 3x
TILE_SIZE  = 18 * TILE_SCALE   # 54 px — one grid cell in the level maps

DEATH_Y = -50              # if the player falls below this Y, they die (pit)

# --- Asset folders (built from HERE so they work in dev and in the .exe) ----
SAMURAI_PATH = HERE / "assets/image/craftpix-net-123681-free-samurai-pixel-art-sprite-sheets/Samurai"
KENNEY_TILES = HERE / "assets/image/kenney_pixel-platformer-food-expansion/Tiles"
BG_IMAGE     = HERE / "assets/image/360_F_1504035261_KQEBa5gLMegqUHn6ndz1YC5m4NRYetTl.jpg"
SLIME_BASE   = HERE / "assets/enemy/craftpix-net-788364-free-slime-mobs-pixel-art-top-down-sprite-pack/PNG"

# Boss: the Samurai Commander character + its battle theme.
BOSS_PATH  = HERE / "assets/boss/Samurai_Commander"
BOSS_MUSIC = HERE / "assets/boss/Godfrey, First Elden Lord - Tai Tomisawa - Topic (128k).mp3"

# Fast "monster" enemies (levels 4-10). 32x32 frames, faster than slimes, and
# they have an attack animation. Mapped to enemy-type codes 4/5/6 (slimes are
# 1/2/3). Each value is (folder, file prefix).
NEW_ENEMY_PATH = HERE / "assets/new_enemy/craftpix-net-622999-free-pixel-art-tiny-hero-sprites"
MONSTERS = {
    4: ("1 Pink_Monster",  "Pink_Monster"),
    5: ("2 Owlet_Monster", "Owlet_Monster"),
    6: ("3 Dude_Monster",  "Dude_Monster"),
}
MONSTER_FRAME = 32

# --- Controls ---------------------------------------------------------------
# Which keyboard keys trigger which of the player's 3 attack animations.
# Value 0/1/2 = which attack combo (Attack_1 / Attack_2 / Attack_3).
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

# Fallback tile for each map character (the real per-tile choice is made in
# game._tile_for, but these are used as a default).
TILE_CHARS = {
    "B": "tile_0050.png",   # terrain (surface/fill chosen per-tile at build time)
    "F": "tile_0006.png",   # pink frosting platform
    "H": "tile_0002.png",   # brown cake platform
}
# How each map character behaves physically:
WALL_TILES     = {"B", "H"}   # solid — you stand on them and can't pass through
PLATFORM_TILES = {"F"}        # one-way platform — land on top, jump up through
DECOR_TILES    = {"X"}        # looks like terrain but the player passes through it
                              # (used for the secret fake wall on level 10)

# --- Slime enemy tuning -----------------------------------------------------
SLIME_FRAME_W     = 64        # one slime animation frame is 64x64 px in its sheet
SLIME_FRAME_H     = 64
SLIME_SCALE       = 3.0       # drawn 3x bigger
SLIME_PATROL      = TILE_SIZE * 4   # how far a slime wanders from its spawn
SWORD_REACH_X     = 90        # how far in front your sword hits (pixels)
SWORD_REACH_Y     = 60        # vertical leeway for a sword hit
SLIME_FOOT_OFFSET = 8         # nudges a slime up so its feet sit on the ground

# The samurai art isn't centred in its 128px frame, so when the animation
# switches (idle vs walk, left vs right) the visible sprite must shift a little
# to keep the character lined up over its collision box. These are those nudges.
ANIM_X_OFFSETS = {
    "walk_right":  (64 - 58.2) * CHARACTER_SCALING,
    "walk_left":  -(64 - 58.2) * CHARACTER_SCALING,
    "idle_right":  (64 - 31.7) * CHARACTER_SCALING,
    "idle_left":  -(64 - 31.7) * CHARACTER_SCALING,
    "jump_right":  (64 - 62.2) * CHARACTER_SCALING,   # jump art is near-centred
    "jump_left":  -(64 - 62.2) * CHARACTER_SCALING,
}
