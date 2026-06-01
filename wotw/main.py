import arcade
from pathlib import Path

HERE = Path(__file__).parent

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Wok of the Warrior"
CHARACTER_SCALING = 2.0
PLAYER_MOVEMENT_SPEED = 5
GRAVITY = 1
PLAYER_JUMP_SPEED = 20
UPDATES_PER_FRAME = 6
KENNEY_TILE_SCALING = 4

SAMURAI_PATH = HERE / "assets/image/craftpix-net-123681-free-samurai-pixel-art-sprite-sheets/Samurai"
KENNEY_TILES = HERE / "assets/image/kenney_pixel-platformer-food-expansion/Tiles"

ATTACK_KEYS = {
    arcade.key.Z: 0, arcade.key.J: 0,
    arcade.key.X: 1, arcade.key.K: 1,
    arcade.key.C: 2, arcade.key.L: 2,
}

PLAYER_MIN_X = 35       # keeps visible character at left screen edge
PLAYER_MAX_X = SCREEN_WIDTH - 35  # keeps visible character at right screen edge


class MyGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        self.player_list = None
        self.wall_list = None
        self.player_sprite = None
        self.physics_engine = None
        self.cur_texture = 0
        self.frame_counter = 0
        self.facing_right = True
        self.attacking = None
        self.slash_draw = None
        self.idle_textures_right = []
        self.idle_textures_left = []
        self.walk_textures_right = []
        self.walk_textures_left = []
        self.attack_textures_right = [[], [], []]
        self.attack_textures_left = [[], [], []]

    def _try_load_sound(self, path):
        try:
            return arcade.load_sound(path)
        except Exception:
            return None

    def _play_attack_sound(self):
        if self.slash_draw:
            arcade.play_sound(self.slash_draw, volume=7.0)

    def _load_sheet(self, filename, count):
        sheet = arcade.load_spritesheet(f"{SAMURAI_PATH}/{filename}")
        frames = sheet.get_texture_grid(size=(128, 128), columns=count, count=count)
        return frames, [t.flip_left_right() for t in frames]

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.wall_list = arcade.SpriteList()

        self.slash_draw = self._try_load_sound(
            HERE / "assets/sounds/484298__giddster__drawing-sword-from-scabbard.wav"
        )

        self.idle_textures_right, self.idle_textures_left = self._load_sheet("Idle.png", 6)
        self.walk_textures_right, self.walk_textures_left = self._load_sheet("Walk.png", 9)
        for i, n in enumerate([4, 5, 4]):
            self.attack_textures_right[i], self.attack_textures_left[i] = self._load_sheet(f"Attack_{i+1}.png", n)

        self.player_sprite = arcade.Sprite()
        self.player_sprite.texture = self.idle_textures_right[0]
        self.player_sprite.scale = CHARACTER_SCALING
        self.player_sprite.center_x = SCREEN_WIDTH // 2
        self.player_sprite.center_y = 300
        self.player_list.append(self.player_sprite)

        tile_size = 18 * KENNEY_TILE_SCALING
        for x in range(int(tile_size // 2), 1300, int(tile_size)):
            w = arcade.Sprite(f"{KENNEY_TILES}/tile_0011.png", KENNEY_TILE_SCALING)
            w.center_x = x
            w.center_y = tile_size // 2
            self.wall_list.append(w)

        for cx, cy, ww, hh in [
            (-200, SCREEN_HEIGHT // 2, 20, SCREEN_HEIGHT * 2),
            (SCREEN_WIDTH + 200, SCREEN_HEIGHT // 2, 20, SCREEN_HEIGHT * 2),
            (SCREEN_WIDTH // 2, SCREEN_HEIGHT + 10, SCREEN_WIDTH * 2, 20),
        ]:
            b = arcade.SpriteSolidColor(ww, hh, arcade.color.WHITE)
            b.center_x, b.center_y, b.alpha = cx, cy, 0
            self.wall_list.append(b)

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player_sprite, gravity_constant=GRAVITY, walls=self.wall_list
        )

    def on_draw(self):
        self.clear()
        self.wall_list.draw()
        self.player_list.draw()

    def on_key_press(self, key, modifiers):
        if key in ATTACK_KEYS:
            if self.attacking is None:
                self.attacking = ATTACK_KEYS[key]
                self.cur_texture = self.frame_counter = 0
                self._play_attack_sound()
            return
        if key in (arcade.key.UP, arcade.key.SPACE, arcade.key.W):
            if self.physics_engine.can_jump():
                self.player_sprite.change_y = PLAYER_JUMP_SPEED
        elif key in (arcade.key.LEFT, arcade.key.A):
            self.player_sprite.change_x, self.facing_right = -PLAYER_MOVEMENT_SPEED, False
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.player_sprite.change_x, self.facing_right = PLAYER_MOVEMENT_SPEED, True

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.LEFT, arcade.key.A, arcade.key.RIGHT, arcade.key.D):
            self.player_sprite.change_x = 0

    def on_update(self, delta_time):
        self.physics_engine.update()
        self.player_sprite.center_x = max(PLAYER_MIN_X, min(PLAYER_MAX_X, self.player_sprite.center_x))
        self._update_animation()

    def _update_animation(self):
        self.frame_counter += 1
        if self.frame_counter < UPDATES_PER_FRAME:
            return
        self.frame_counter = 0
        self.cur_texture += 1

        if self.attacking is not None:
            frames = (self.attack_textures_right if self.facing_right else self.attack_textures_left)[self.attacking]
            if self.cur_texture >= len(frames):
                self.attacking, self.cur_texture = None, 0
            else:
                self.player_sprite.texture = frames[self.cur_texture]
            return

        frames = (self.walk_textures_right if self.player_sprite.change_x != 0 else self.idle_textures_right) \
                 if self.facing_right else \
                 (self.walk_textures_left if self.player_sprite.change_x != 0 else self.idle_textures_left)
        self.cur_texture %= len(frames)
        self.player_sprite.texture = frames[self.cur_texture]


if __name__ == "__main__":
    window = MyGame()
    window.setup()
    arcade.run()
