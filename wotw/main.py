import arcade

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Wok of the Warrior"
CHARACTER_SCALING = 2.0
TILE_SCALING = 0.5
PLAYER_MOVEMENT_SPEED = 5
GRAVITY = 1
PLAYER_JUMP_SPEED = 20

SAMURAI_PATH = "craftpix-net-123681-free-samurai-pixel-art-sprite-sheets/Samurai"
KENNEY_TILES = "kenney_pixel-platformer-food-expansion/Tiles"
FRAME_WIDTH = 128
FRAME_HEIGHT = 128
UPDATES_PER_FRAME = 6
KENNEY_TILE_SCALING = 64 / 18  # scale 18px tiles up to ~64px to match floor grid

ATTACK_KEYS = {
    arcade.key.Z: 0,
    arcade.key.X: 1,
    arcade.key.C: 2,
    arcade.key.J: 0,
    arcade.key.K: 1,
    arcade.key.L: 2,
}


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

        self.idle_textures_right = []
        self.idle_textures_left = []
        self.walk_textures_right = []
        self.walk_textures_left = []
        self.attack_textures_right = [[], [], []]
        self.attack_textures_left = [[], [], []]

        # None = not attacking; 0/1/2 = which attack is playing
        self.attacking = None

        self.slash_draw = None

    HEAVY_ATTACK = 1

    def _try_load_sound(self, path):
        try:
            return arcade.load_sound(path)
        except Exception:
            return None

    def _play_attack_sound(self):
        if self.slash_draw:
            arcade.play_sound(self.slash_draw, volume=2.0)

    def _load_sheet(self, filename, count):
        sheet = arcade.load_spritesheet(f"{SAMURAI_PATH}/{filename}")
        frames = sheet.get_texture_grid(
            size=(FRAME_WIDTH, FRAME_HEIGHT),
            columns=count,
            count=count,
        )
        flipped = [t.flip_left_right() for t in frames]
        return frames, flipped

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.wall_list = arcade.SpriteList()

        self.slash_draw = self._try_load_sound("484298__giddster__drawing-sword-from-scabbard.wav")

        self.idle_textures_right, self.idle_textures_left = self._load_sheet("Idle.png", 6)
        self.walk_textures_right, self.walk_textures_left = self._load_sheet("Walk.png", 9)

        attack_frame_counts = [4, 5, 4]
        for i, count in enumerate(attack_frame_counts):
            r, l = self._load_sheet(f"Attack_{i + 1}.png", count)
            self.attack_textures_right[i] = r
            self.attack_textures_left[i] = l

        self.player_sprite = arcade.Sprite()
        self.player_sprite.texture = self.idle_textures_right[0]
        self.player_sprite.scale = CHARACTER_SCALING
        self.player_sprite.center_x = 64
        self.player_sprite.center_y = 128
        self.player_list.append(self.player_sprite)

        for x in range(0, 1250, 64):
            wall = arcade.Sprite(f"{KENNEY_TILES}/tile_0011.png", KENNEY_TILE_SCALING)
            wall.center_x = x
            wall.center_y = 32
            self.wall_list.append(wall)

        self.create_boundary_walls()

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player_sprite, gravity_constant=GRAVITY, walls=self.wall_list
        )

    def create_boundary_walls(self):
        left_wall = arcade.SpriteSolidColor(20, SCREEN_HEIGHT * 2, arcade.color.WHITE)
        left_wall.center_x = -10
        left_wall.center_y = SCREEN_HEIGHT // 2
        left_wall.alpha = 0
        self.wall_list.append(left_wall)

        right_wall = arcade.SpriteSolidColor(20, SCREEN_HEIGHT * 2, arcade.color.WHITE)
        right_wall.center_x = SCREEN_WIDTH + 10
        right_wall.center_y = SCREEN_HEIGHT // 2
        right_wall.alpha = 0
        self.wall_list.append(right_wall)

        ceiling = arcade.SpriteSolidColor(SCREEN_WIDTH * 2, 20, arcade.color.WHITE)
        ceiling.center_x = SCREEN_WIDTH // 2
        ceiling.center_y = SCREEN_HEIGHT + 10
        ceiling.alpha = 0
        self.wall_list.append(ceiling)

    def on_draw(self):
        self.clear()
        self.wall_list.draw()
        self.player_list.draw()

    def on_key_press(self, key, modifiers):
        if key in ATTACK_KEYS:
            if self.attacking is None:
                self.attacking = ATTACK_KEYS[key]
                self.cur_texture = 0
                self.frame_counter = 0
                self._play_attack_sound()
            return

        if key in (arcade.key.UP, arcade.key.SPACE, arcade.key.W):
            if self.physics_engine.can_jump():
                self.player_sprite.change_y = PLAYER_JUMP_SPEED
        elif key in (arcade.key.LEFT, arcade.key.A):
            self.player_sprite.change_x = -PLAYER_MOVEMENT_SPEED
            self.facing_right = False
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.player_sprite.change_x = PLAYER_MOVEMENT_SPEED
            self.facing_right = True

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.LEFT, arcade.key.A):
            self.player_sprite.change_x = 0
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.player_sprite.change_x = 0

    def on_update(self, delta_time):
        self.physics_engine.update()
        self._update_animation()

    def _update_animation(self):
        self.frame_counter += 1
        if self.frame_counter < UPDATES_PER_FRAME:
            return
        self.frame_counter = 0
        self.cur_texture += 1

        if self.attacking is not None:
            frames = (
                self.attack_textures_right[self.attacking]
                if self.facing_right
                else self.attack_textures_left[self.attacking]
            )
            if self.cur_texture >= len(frames):
                # attack finished — return to idle/walk
                self.attacking = None
                self.cur_texture = 0
            else:
                self.player_sprite.texture = frames[self.cur_texture]
            return

        if self.player_sprite.change_x != 0:
            frames = self.walk_textures_right if self.facing_right else self.walk_textures_left
        else:
            frames = self.idle_textures_right if self.facing_right else self.idle_textures_left

        self.cur_texture %= len(frames)
        self.player_sprite.texture = frames[self.cur_texture]


def main():
    window = MyGame()
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()
