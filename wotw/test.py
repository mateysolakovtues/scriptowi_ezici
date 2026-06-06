import math
import arcade
import arcade.gui
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
TILE_SCALE = 3
TILE_SIZE  = 18 * TILE_SCALE   # 54 px

# -- Death threshold -----------------------------------------------------------
DEATH_Y = -50

# -- Asset paths ---------------------------------------------------------------
SAMURAI_PATH = HERE / "assets/image/craftpix-net-123681-free-samurai-pixel-art-sprite-sheets/Samurai"
KENNEY_TILES = HERE / "assets/image/kenney_pixel-platformer-food-expansion/Tiles"
BG_IMAGE     = HERE / "assets/image/pixel-stars-set-night-sky-background_107791-34629.avif"
SLIME_BASE   = HERE / "assets/enemy/craftpix-net-788364-free-slime-mobs-pixel-art-top-down-sprite-pack/PNG"

# -- Slime constants -----------------------------------------------------------
SLIME_FRAME_W       = 64
SLIME_FRAME_H       = 64
SLIME_SCALE         = 3.0
SLIME_PATROL        = TILE_SIZE * 4   # patrol ±4 tiles from spawn
SWORD_REACH_X       = 90              # px in facing direction
SWORD_REACH_Y       = 60              # px vertical tolerance
# Pixel analysis: visible body occupies rows 24-39 in the 64px frame,
# so 24px of transparent space sits below the visible body.
# foot_offset = half_frame - transparent_bottom = 32 - 24 = 8
SLIME_FOOT_OFFSET   = 8

# -- Attack keys ---------------------------------------------------------------
ATTACK_KEYS = {
    arcade.key.Z: 0, arcade.key.J: 0,
    arcade.key.X: 1, arcade.key.K: 1,
    arcade.key.C: 2, arcade.key.L: 2,
}

# -- Level maps ----------------------------------------------------------------
def _make_grid(rows):
    w = max(len(r) for r in rows)
    return [r.ljust(w) for r in rows]

# enemies: list of (col, floor_row, slime_type)
#   col        – tile column
#   floor_row  – row index of the surface the slime stands ON TOP OF
#   slime_type – 1 / 2 / 3
LEVELS = {
    1: {
        "grid": _make_grid([
            "                                                                                ",
            "                                                                                ",
            "                                                 HHHHH                          ",
            "                         FFF                    H     H                         ",
            "                                               H       H                        ",
            "                FFF                           H  S S S  H                       ",
            "                                             HHHHHHHHHHHH                       ",
            "         FFF                                                                    ",
            "                                    FFFFF                                       ",
            "    P                      HHH                                  HHHH            ",
            "   FFF                    H   H                                H    H           ",
            "                         H     H      S   S                   H      H          ",
            "                        H       H   BBBBBBBBB                H        H         ",
            "       S    S          H         H                          H          S   S    ",
            "BBBBBBBBBBBBBBBB   BBBB           BBBBBBBBBBBB   BBBBBBBBBBB            BBBBBBBB",
        ]),
        "enemies": [
            ( 8, 14, 1), (12, 14, 2),   # left solid floor section
            (37, 14, 1), (42, 14, 3),   # middle-right floor section
            (52, 14, 2), (57, 14, 1),   # second right floor section
            (74, 14, 3),                # rightmost floor section
            (10,  7, 2),                # FFF platform  (row 7)
            (38,  8, 1),                # FFFFF platform (row 8)
            (40, 12, 3),                # BBBBBBBBB platform (row 12)
        ],
    },
    2: {
        "grid": _make_grid([
            "                FFFFF                                H      H                   ",
            "                                                    H   S    H                  ",
            "         FFF             FFF                       H   BBBB   H                 ",
            "                                                  H            H                ",
            "    P                                            H              H               ",
            "   BBB    S   S         S    S                  H                H              ",
            "   BBBB  BBBBBBB       BBBBBBBB     FFFFF      H                  H             ",
            "   BBBB  BBBBBBB       BBBBBBBB               H                    H            ",
            "   BBBB  BBBBBBB  SSS  BBBBBBBB  S         S H                      H S    S     ",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB   BBBBBBBBBBBBBBBBBBBB   BBBBBBBBBBBBBBBBBB",
        ]),
        "enemies": [
            (15, 9, 1), (25, 9, 2),    # ground floor section 1
            (45, 9, 3), (50, 9, 1),    # ground floor section 2
            (68, 9, 2), (73, 9, 3),    # ground floor section 3
            ( 5, 6, 1), (12, 6, 2),    # BBBB / BBBBBBB platforms row 6
            (27, 6, 3), (39, 6, 1),    # BBBBBBBB / FFFFF platforms row 6
            (10, 2, 2), (26, 2, 3),    # FFF platforms row 2
        ],
    },
}

TILE_CHARS = {
    "B": "tile_0011.png",
    "F": "tile_0055.png",
    "H": "tile_0033.png",
    "S": "tile_0099.png",
}
WALL_TILES     = {"B"}
PLATFORM_TILES = {"F", "H"}
DECOR_TILES    = {"S"}


# -- Slime enemy sprite --------------------------------------------------------
class SlimeEnemy(arcade.Sprite):

    ANIM_RATE = 7  # ticks between texture changes

    def __init__(self, x, y, walk_right, walk_left):
        super().__init__()
        self._walk_right = walk_right
        self._walk_left  = walk_left
        self.texture     = walk_right[0]
        self.scale       = SLIME_SCALE
        self.center_x    = x
        self.center_y    = y
        self._spawn_x    = x
        self.change_x    = 0.9
        self._frame      = 0
        self._tick       = 0

    def update_patrol(self, wall_list, platform_list):
        # Probe just below the leading edge; reverse if no tile is there.
        lead    = 1 if self.change_x >= 0 else -1
        probe_x = self.center_x + lead * SLIME_SCALE * 20
        probe_y = self.center_y - int(SLIME_SCALE * SLIME_FOOT_OFFSET) - 4
        has_ground = (
            arcade.get_sprites_at_point((probe_x, probe_y), wall_list) or
            arcade.get_sprites_at_point((probe_x, probe_y), platform_list)
        )
        if not has_ground:
            self.change_x *= -1

        self.center_x += self.change_x
        if abs(self.center_x - self._spawn_x) >= SLIME_PATROL:
            self.change_x *= -1
        self._tick += 1
        if self._tick >= self.ANIM_RATE:
            self._tick  = 0
            self._frame = (self._frame + 1) % len(self._walk_right)
            frames      = self._walk_right if self.change_x >= 0 else self._walk_left
            self.texture = frames[self._frame]


# -- Main game window ----------------------------------------------------------
class MyGame(arcade.Window):

    def __init__(self):
        super().__init__(title=SCREEN_TITLE, fullscreen=True)

        self.current_level = 1

        self.bg_texture    = None
        self.bg_sprites    = None
        self.player_list   = None
        self.wall_list     = None
        self.platform_list = None
        self.decor_list    = None
        self.enemy_list    = None

        self.slime_textures = {}   # {1: (walk_right, walk_left), ...}

        self.physics_sprite = None
        self.player_sprite  = None
        self.physics_engine = None
        self.camera         = None
        self.level_width    = 0

        self.spawn_x = 0
        self.spawn_y = 0

        # "playing" | "dead" | "level_complete"
        self.game_state = "playing"

        self._cam_cx = 0.0
        self._cam_cy = 0.0

        self.ui_manager            = arcade.gui.UIManager()
        self._death_panel          = None
        self._level_complete_panel = None

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

    # -- Helpers ---------------------------------------------------------------
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

    def _load_slime_textures(self):
        for i in (1, 2, 3):
            path  = SLIME_BASE / f"Slime{i}/Without_shadow/Slime{i}_Walk_without_shadow.png"
            sheet = arcade.load_spritesheet(path)
            # Sheet is 512x256: 8 cols × 4 rows of 64x64 frames.
            # Row 0 (first 8 frames) is the front-facing walk cycle.
            all_frames = sheet.get_texture_grid(
                size=(SLIME_FRAME_W, SLIME_FRAME_H), columns=8, count=32
            )
            walk_right = all_frames[:8]
            walk_left  = [t.flip_left_right() for t in walk_right]
            self.slime_textures[i] = (walk_right, walk_left)

    # -- Level builder ---------------------------------------------------------
    def _build_level(self, map_grid):
        total_rows = len(map_grid)
        spawn      = None

        for row_idx, row in enumerate(map_grid):
            for col_idx, char in enumerate(row):
                if char == " ":
                    continue
                x = col_idx * TILE_SIZE + TILE_SIZE // 2
                y = (total_rows - 1 - row_idx) * TILE_SIZE + TILE_SIZE // 2
                if char == "P":
                    spawn = (x, y + TILE_SIZE)
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

    # -- UI panels -------------------------------------------------------------
    def _build_death_panel(self):
        v_box = arcade.gui.UIBoxLayout(vertical=True, space_between=20)
        v_box.add(arcade.gui.UILabel(
            text="YOU DIED",
            font_size=72,
            text_color=(220, 30, 30, 255),
        ))
        restart_btn = arcade.gui.UIFlatButton(text="RESTART", width=240, height=60)
        @restart_btn.event("on_click")
        def _on_click(event):
            self._restart()
        v_box.add(restart_btn)
        v_box.add(arcade.gui.UILabel(
            text="or press  R / ENTER",
            font_size=16,
            text_color=(200, 200, 200, 255),
        ))
        panel = arcade.gui.UIAnchorLayout()
        panel.add(child=v_box, anchor_x="center_x", anchor_y="center_y")
        return panel

    def _build_level_complete_panel(self):
        v_box = arcade.gui.UIBoxLayout(vertical=True, space_between=20)
        v_box.add(arcade.gui.UILabel(
            text=f"LEVEL {self.current_level} COMPLETE!",
            font_size=60,
            text_color=(255, 215, 0, 255),
        ))
        restart_btn = arcade.gui.UIFlatButton(text="RESTART LEVEL", width=280, height=60)
        @restart_btn.event("on_click")
        def _on_restart(event):
            self._restart()
        v_box.add(restart_btn)
        next_btn = arcade.gui.UIFlatButton(text="NEXT LEVEL", width=280, height=60)
        @next_btn.event("on_click")
        def _on_next(event):
            self._advance_level()
        v_box.add(next_btn)
        v_box.add(arcade.gui.UILabel(
            text="or  R = restart   N / ENTER = next level",
            font_size=14,
            text_color=(200, 200, 200, 255),
        ))
        panel = arcade.gui.UIAnchorLayout()
        panel.add(child=v_box, anchor_x="center_x", anchor_y="center_y")
        return panel

    # -- Per-level load --------------------------------------------------------
    def _load_level(self, level_num):
        W, H = self.width, self.height

        self.current_level = level_num
        level_data         = LEVELS[self.current_level]
        map_grid           = level_data["grid"]
        self.level_width   = len(map_grid[0]) * TILE_SIZE
        level_height       = len(map_grid) * TILE_SIZE
        total_rows         = len(map_grid)

        self.ui_manager.disable()
        self.ui_manager = arcade.gui.UIManager()
        self.ui_manager.enable()

        self.bg_sprites    = arcade.SpriteList()
        self.wall_list     = arcade.SpriteList()
        self.platform_list = arcade.SpriteList()
        self.decor_list    = arcade.SpriteList()
        self.enemy_list    = arcade.SpriteList()

        if self.bg_texture is not None:
            bw, bh = self.bg_texture.width, self.bg_texture.height
            for row in range(math.ceil(H / bh) + 1):
                for col in range(math.ceil(self.level_width / bw) + 1):
                    s = arcade.Sprite()
                    s.texture  = self.bg_texture
                    s.center_x = col * bw + bw / 2
                    s.center_y = row * bh + bh / 2
                    self.bg_sprites.append(s)

        spawn = self._build_level(map_grid)
        self.spawn_x = spawn[0] if spawn else TILE_SIZE * 2
        self.spawn_y = spawn[1] if spawn else level_height // 2

        for cx, cy, ww, hh in [
            (-10,                   level_height, 20, level_height * 4),
            (self.level_width + 10, level_height, 20, level_height * 4),
        ]:
            b = arcade.SpriteSolidColor(ww, hh, arcade.color.WHITE)
            b.alpha    = 0
            b.center_x = cx
            b.center_y = cy
            self.wall_list.append(b)

        # Spawn enemies so their visible body sits on the tile surface.
        # ey = floor_top + SLIME_SCALE * SLIME_FOOT_OFFSET aligns the visual
        # bottom of the sprite (not the transparent frame edge) with the tile top.
        for col, floor_row, stype in level_data["enemies"]:
            ex = col * TILE_SIZE + TILE_SIZE // 2
            floor_top = (total_rows - 1 - floor_row) * TILE_SIZE + TILE_SIZE
            ey = floor_top + int(SLIME_SCALE * SLIME_FOOT_OFFSET)
            wr, wl = self.slime_textures[stype]
            self.enemy_list.append(SlimeEnemy(ex, ey, wr, wl))

        self.physics_sprite.center_x = self.spawn_x
        self.physics_sprite.center_y = self.spawn_y
        self.physics_sprite.change_x = 0
        self.physics_sprite.change_y = 0

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.physics_sprite,
            gravity_constant=GRAVITY,
            walls=self.wall_list,
            platforms=self.platform_list,
        )

        self.camera.position = (W / 2, H / 2)
        self._cam_cx = W / 2
        self._cam_cy = H / 2

        self.cur_texture   = 0
        self.frame_counter = 0
        self.facing_right  = True
        self.attacking     = None
        self.current_anim  = None
        self.player_sprite.texture = self.idle_textures_right[0]

        self._death_panel          = self._build_death_panel()
        self._level_complete_panel = self._build_level_complete_panel()
        self.game_state = "playing"

    # -- Setup (one-time) ------------------------------------------------------
    def setup(self):
        try:
            self.bg_texture = arcade.load_texture(BG_IMAGE)
        except Exception:
            self.bg_texture = None

        self.slash_draw = self._try_load_sound(
            HERE / "assets/sounds/484298__giddster__drawing-sword-from-scabbard.wav"
        )

        self.idle_textures_right, self.idle_textures_left = self._load_sheet("Idle.png", 6)
        self.walk_textures_right, self.walk_textures_left = self._load_sheet("Walk.png", 9)
        for i, n in enumerate([4, 5, 4]):
            self.attack_textures_right[i], self.attack_textures_left[i] = \
                self._load_sheet(f"Attack_{i+1}.png", n)

        self._load_slime_textures()

        self.physics_sprite = arcade.SpriteSolidColor(PHYS_W, PHYS_H, arcade.color.WHITE)
        self.physics_sprite.alpha = 0

        self.player_list   = arcade.SpriteList()
        self.player_sprite = arcade.Sprite()
        self.player_sprite.texture = self.idle_textures_right[0]
        self.player_sprite.scale   = CHARACTER_SCALING
        self.player_list.append(self.player_sprite)

        self.camera = arcade.Camera2D()

        music = self._try_load_sound(HERE / "assets/music/balloons-forever.ogg")
        if music:
            self.music = arcade.play_sound(music, volume=9.0, loop=True)

        self._load_level(1)

    # -- State transitions -----------------------------------------------------
    def _trigger_death(self):
        self.game_state = "dead"
        self.physics_sprite.change_x = 0
        self.physics_sprite.change_y = 0
        self.ui_manager.add(self._death_panel)

    def _trigger_level_complete(self):
        self.game_state = "level_complete"
        self.physics_sprite.change_x = 0
        self.physics_sprite.change_y = 0
        self.ui_manager.add(self._level_complete_panel)

    def _restart(self):
        self._load_level(self.current_level)

    def _advance_level(self):
        next_num = (self.current_level % len(LEVELS)) + 1
        self._load_level(next_num)

    # -- Enemy collision -------------------------------------------------------
    def _check_enemy_collisions(self):
        player_bottom = self.physics_sprite.center_y - PHYS_H / 2

        for enemy in list(self.enemy_list):
            if not arcade.check_for_collision(self.physics_sprite, enemy):
                continue
            # Stomp: player falling with feet above enemy centre
            if self.physics_sprite.change_y <= 0 and player_bottom >= enemy.center_y:
                enemy.remove_from_sprite_lists()
                self.physics_sprite.change_y = JUMP_SPEED * 0.7
            else:
                self._trigger_death()
                return

        # Sword: any enemy in the attack arc while the player is mid-swing
        if self.attacking is not None:
            px, py = self.physics_sprite.center_x, self.physics_sprite.center_y
            y_tol  = SWORD_REACH_Y + PHYS_H / 2 + SLIME_SCALE * SLIME_FRAME_H / 2
            for enemy in list(self.enemy_list):
                dx = enemy.center_x - px
                if abs(enemy.center_y - py) < y_tol:
                    if self.facing_right and 0 < dx < SWORD_REACH_X:
                        enemy.remove_from_sprite_lists()
                    elif not self.facing_right and -SWORD_REACH_X < dx < 0:
                        enemy.remove_from_sprite_lists()

    # -- Drawing ---------------------------------------------------------------
    def on_draw(self):
        self.clear()

        self.camera.use()
        self.bg_sprites.draw()
        self.enemy_list.draw()       # enemies behind tiles so tile surfaces cover transparent frame edges
        self.wall_list.draw()
        self.platform_list.draw()
        self.decor_list.draw()
        self.player_list.draw()

        if self.game_state in ("dead", "level_complete"):
            self.ui_manager.draw()

    # -- Input -----------------------------------------------------------------
    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            arcade.close_window()
            return

        if self.game_state == "dead":
            if key in (arcade.key.R, arcade.key.ENTER, arcade.key.RETURN):
                self._restart()
            return

        if self.game_state == "level_complete":
            if key in (arcade.key.N, arcade.key.ENTER, arcade.key.RETURN):
                self._advance_level()
            elif key == arcade.key.R:
                self._restart()
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

    # -- Game logic ------------------------------------------------------------
    def on_update(self, delta_time):
        if self.game_state != "playing":
            return

        self.physics_engine.update()

        self.physics_sprite.center_x = max(
            PHYS_W / 2,
            min(self.level_width - PHYS_W / 2, self.physics_sprite.center_x),
        )

        if self.physics_sprite.center_y < DEATH_Y:
            self._trigger_death()
            return

        if self.physics_sprite.center_x >= self.level_width - TILE_SIZE * 2:
            self._trigger_level_complete()
            return

        for enemy in self.enemy_list:
            enemy.update_patrol(self.wall_list, self.platform_list)

        self._check_enemy_collisions()
        if self.game_state != "playing":
            return

        y_offset = (128 * CHARACTER_SCALING / 2) - (PHYS_H / 2)
        self.player_sprite.center_x = self.physics_sprite.center_x
        self.player_sprite.center_y = self.physics_sprite.center_y + y_offset

        cam_left     = self.physics_sprite.center_x - self.width // 3
        cam_left     = max(0.0, min(cam_left, self.level_width - self.width))
        self._cam_cx = cam_left + self.width  / 2
        self._cam_cy =            self.height / 2
        self.camera.position = (self._cam_cx, self._cam_cy)

        self._update_animation()

    # -- Animation -------------------------------------------------------------
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


# -- Entry point ---------------------------------------------------------------
if __name__ == "__main__":
    window = MyGame()
    window.setup()
    arcade.run()
    print("Goodbye!")
    print("Thanks for playing Wok of the Warrior!")
