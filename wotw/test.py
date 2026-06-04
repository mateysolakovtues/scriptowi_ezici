import arcade
from pathlib import Path

# -- Path helper ---------------------------------------------------------------
HERE = Path(__file__).parent

# -- Window --------------------------------------------------------------------
SCREEN_TITLE = "Wok of the Warrior"

# -- Player movement -----------------------------------------------------------
CHARACTER_SCALING  = 2.0
PLAYER_SPEED       = 5
GRAVITY            = 1
JUMP_SPEED         = 25
UPDATES_PER_FRAME  = 6

# -- Physics body size (pixels) ------------------------------------------------
PHYS_W = 40
PHYS_H = 90

# -- Tile settings -------------------------------------------------------------
TILE_SCALE = 4

# -- Asset paths ---------------------------------------------------------------
SAMURAI_PATH = HERE / "assets/image/craftpix-net-123681-free-samurai-pixel-art-sprite-sheets/Samurai"
KENNEY_TILES = HERE / "assets/image/kenney_pixel-platformer-food-expansion/Tiles"

# -- Attack key mapping --------------------------------------------------------
ATTACK_KEYS = {
    arcade.key.Z: 0, arcade.key.J: 0,
    arcade.key.X: 1, arcade.key.K: 1,
    arcade.key.C: 2, arcade.key.L: 2,
}

# -- Level map -----------------------------------------------------------------
MAP_GRID = [
    "                                        ",  # row 0
    "         FFF                            ",  # row 1
    "                                 HHHH   ",  # row 2
    "    P              S     S              ",  # row 3
    "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",  # row 4  (floor)
]

TILE_CHARS = {
    "B": "tile_0011.png",
    "F": "tile_0055.png",
    "H": "tile_0033.png",
    "S": "tile_0099.png",
}

WALL_TILES     = {"B"}
PLATFORM_TILES = {"F", "H"}
DECOR_TILES    = {"S"}


class MyGame(arcade.Window):

    def __init__(self):
        super().__init__(title=SCREEN_TITLE, fullscreen=True)

        self.player_list   = None
        self.wall_list     = None
        self.platform_list = None
        self.decor_list    = None

        self.physics_sprite = None
        self.player_sprite  = None
        self.physics_engine = None

        self.cur_texture   = 0
        self.frame_counter = 0
        self.facing_right  = True
        self.attacking     = None
        self.current_anim  = None

        self.slash_draw = None
        self.music      = None

        self.idle_textures_right   = []
        self.idle_textures_left    = []
        self.walk_textures_right   = []
        self.walk_textures_left    = []
        self.attack_textures_right = [[], [], []]
        self.attack_textures_left  = [[], [], []]

    def _try_load_sound(self, path):
        try:
            return arcade.load_sound(path)
        except Exception:
            return None

    def _play_attack_sound(self):
        if self.slash_draw:
            arcade.play_sound(self.slash_draw, volume=15.0)

    def _load_sheet(self, filename, count):
        sheet  = arcade.load_spritesheet(f"{SAMURAI_PATH}/{filename}")
        frames = sheet.get_texture_grid(size=(128, 128), columns=count, count=count)
        return frames, [t.flip_left_right() for t in frames]

    def _build_level(self):
        tile_size  = 18 * TILE_SCALE
        total_rows = len(MAP_GRID)
        spawn      = None

        for row_idx, row in enumerate(MAP_GRID):
            for col_idx, char in enumerate(row):
                if char == " ":
                    continue

                x = col_idx * tile_size + tile_size // 2
                y = (total_rows - 1 - row_idx) * tile_size + tile_size // 2

                if char == "P":
                    spawn = (x, y + tile_size)
                    continue

                filename = TILE_CHARS.get(char)
                if not filename:
                    continue

                sprite = arcade.Sprite(f"{KENNEY_TILES}/{filename}", TILE_SCALE)
                sprite.center_x = x
                sprite.center_y = y

                if char in WALL_TILES:
                    self.wall_list.append(sprite)
                elif char in PLATFORM_TILES:
                    self.platform_list.append(sprite)
                elif char in DECOR_TILES:
                    self.decor_list.append(sprite)

        return spawn

    def setup(self):
        W, H = self.width, self.height

        self.player_min_x = 35
        self.player_max_x = W - 35

        self.player_list   = arcade.SpriteList()
        self.wall_list     = arcade.SpriteList()
        self.platform_list = arcade.SpriteList()
        self.decor_list    = arcade.SpriteList()

        self.slash_draw = self._try_load_sound(
            HERE / "assets/sounds/484298__giddster__drawing-sword-from-scabbard.wav"
        )

        self.idle_textures_right, self.idle_textures_left = self._load_sheet("Idle.png", 6)
        self.walk_textures_right, self.walk_textures_left = self._load_sheet("Walk.png", 9)
        for i, n in enumerate([4, 5, 4]):
            self.attack_textures_right[i], self.attack_textures_left[i] = \
                self._load_sheet(f"Attack_{i+1}.png", n)

        spawn   = self._build_level()
        spawn_x = spawn[0] if spawn else W // 2
        spawn_y = spawn[1] if spawn else H // 2

        for cx, cy, ww, hh in [
            (-200,    H // 2, 20, H * 2),
            (W + 200, H // 2, 20, H * 2),
            (W // 2,  H + 10, W * 2, 20),
        ]:
            b = arcade.SpriteSolidColor(ww, hh, arcade.color.WHITE)
            b.center_x, b.center_y, b.alpha = cx, cy, 0
            self.wall_list.append(b)

        self.physics_sprite = arcade.SpriteSolidColor(PHYS_W, PHYS_H, arcade.color.WHITE)
        self.physics_sprite.alpha    = 0
        self.physics_sprite.center_x = spawn_x
        self.physics_sprite.center_y = spawn_y

        self.player_sprite = arcade.Sprite()
        self.player_sprite.texture  = self.idle_textures_right[0]
        self.player_sprite.scale    = CHARACTER_SCALING
        self.player_sprite.center_x = spawn_x
        self.player_sprite.center_y = spawn_y
        self.player_list.append(self.player_sprite)

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.physics_sprite,
            gravity_constant=GRAVITY,
            walls=self.wall_list,
            platforms=self.platform_list,
        )

        music = self._try_load_sound(HERE / "assets/music/balloons-forever.ogg")
        if music:
            self.music = arcade.play_sound(music, volume=9.0, loop=True)

    def on_draw(self):
        self.clear()
        self.wall_list.draw()
        self.platform_list.draw()
        self.decor_list.draw()
        self.player_list.draw()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            arcade.close_window()
            return

        if key in ATTACK_KEYS:
            if self.attacking is None:
                self.attacking = ATTACK_KEYS[key]
                self.cur_texture = self.frame_counter = 0
                self._play_attack_sound()
            return

        if key in (arcade.key.UP, arcade.key.SPACE, arcade.key.W):
            if self.physics_engine.can_jump():
                self.physics_sprite.change_y = JUMP_SPEED
        elif key in (arcade.key.LEFT, arcade.key.A):
            self.physics_sprite.change_x = -PLAYER_SPEED
            self.facing_right = False
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.physics_sprite.change_x = PLAYER_SPEED
            self.facing_right = True

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.LEFT, arcade.key.A, arcade.key.RIGHT, arcade.key.D):
            self.physics_sprite.change_x = 0

    def on_update(self, delta_time):
        self.physics_engine.update()

        self.physics_sprite.center_x = max(
            self.player_min_x, min(self.player_max_x, self.physics_sprite.center_x)
        )

        # Sync visual sprite to physics body.
        # The visual sprite is 128 * CHARACTER_SCALING = 256 px tall, but the
        # physics body is only PHYS_H = 90 px tall.  Without an offset their
        # centres align, which means the visual sprite's feet sink 83 px through
        # the floor.  Shifting the visual up by (visual_half - phys_half) aligns
        # their bottoms so the character stands on the floor correctly.
        y_offset = (128 * CHARACTER_SCALING / 2) - (PHYS_H / 2)   # 128 - 45 = 83
        self.player_sprite.center_x = self.physics_sprite.center_x
        self.player_sprite.center_y = self.physics_sprite.center_y + y_offset

        self._update_animation()

    def _update_animation(self):
        self.frame_counter += 1
        if self.frame_counter < UPDATES_PER_FRAME:
            return
        self.frame_counter = 0
        self.cur_texture  += 1

        if self.attacking is not None:
            frames = (self.attack_textures_right if self.facing_right
                      else self.attack_textures_left)[self.attacking]
            if self.cur_texture >= len(frames):
                self.attacking, self.cur_texture = None, 0
            else:
                self.player_sprite.texture = frames[self.cur_texture]
            return

        is_walking = self.physics_sprite.change_x != 0
        if self.facing_right:
            frames   = self.walk_textures_right if is_walking else self.idle_textures_right
            anim_key = "walk_right"             if is_walking else "idle_right"
        else:
            frames   = self.walk_textures_left  if is_walking else self.idle_textures_left
            anim_key = "walk_left"              if is_walking else "idle_left"

        if anim_key != self.current_anim:
            self.current_anim = anim_key
            self.cur_texture  = 0

        self.cur_texture %= len(frames)
        self.player_sprite.texture = frames[self.cur_texture]


if __name__ == "__main__":
    window = MyGame()
    window.setup()
    arcade.run()
    