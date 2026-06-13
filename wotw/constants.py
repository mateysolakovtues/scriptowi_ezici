import arcade
from pathlib import Path

HERE = Path(__file__).parent

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

ATTACK_KEYS = {
    arcade.key.Z: 0, arcade.key.J: 0,
    arcade.key.X: 1, arcade.key.K: 1,
    arcade.key.C: 2, arcade.key.L: 2,
}

TILE_CHARS = {
    # terrain
    "B": "tile_0000.png",   # brown cookie/brownie block
    "F": "tile_0040.png",   # pink cupcake platform
    "H": "tile_0007.png",   # pink frosting solid block
    # food decorations (no collision)
    "b": "tile_0092.png",   # burger
    "d": "tile_0013.png",   # donut
    "s": "tile_0045.png",   # sausage link
    "l": "tile_0080.png",   # lollipop
    "c": "tile_0082.png",   # mug / cup
    "n": "tile_0105.png",   # nacho chip
    "j": "tile_0095.png",   # hot dog
    "k": "tile_0093.png",   # cake slice
}
WALL_TILES     = {"B", "H"}
PLATFORM_TILES = {"F"}
DECOR_TILES    = {"b", "d", "s", "l", "c", "n", "j", "k"}

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
