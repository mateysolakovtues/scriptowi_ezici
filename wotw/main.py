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

# -- Death threshold -----------------------------------------------------------
DEATH_Y = -50

# -- Asset paths ---------------------------------------------------------------
SAMURAI_PATH = HERE / "assets/image/craftpix-net-123681-free-samurai-pixel-art-sprite-sheets/Samurai"
KENNEY_TILES = HERE / "assets/image/kenney_pixel-platformer-food-expansion/Tiles"
BG_IMAGE    = HERE / "assets/image/pixel-stars-set-night-sky-background_107791-34629.avif"

# -- Attack keys ---------------------------------------------------------------
ATTACK_KEYS = {
    arcade.key.Z: 0, arcade.key.J: 0,
    arcade.key.X: 1, arcade.key.K: 1,
    arcade.key.C: 2, arcade.key.L: 2,
}

# -- Level map -----------------------------------------------------------------
_LEVEL = [
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
]
_W       = max(len(r) for r in _LEVEL)
MAP_GRID = [r.ljust(_W) for r in _LEVEL]

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

        self.bg_sprites    = None
        self.player_list   = None
        self.wall_list     = None
        self.platform_list = None
        self.decor_list    = None

        self.physics_sprite = None
        self.player_sprite  = None
        self.physics_engine = None
        self.camera         = None
        self.level_width    = 0

        self.spawn_x = 0
        self.spawn_y = 0

        # "playing" | "dead"
        self.game_state = "playing"

        # Camera centre in world coords – used to draw the dark overlay
        # at the correct world position when the player dies.
        self._cam_cx = 0.0
        self._cam_cy = 0.0

        # arcade.gui – handles its OWN projection, no camera conflicts
        self.ui_manager   = arcade.gui.UIManager()
        self._death_panel = None   # built in setup()

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

    # -- Level builder ---------------------------------------------------------
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

    # -- Death UI (arcade.gui) -------------------------------------------------
    def _build_death_panel(self):
        """
        Build the YOU DIED overlay using arcade.gui.
        UIManager draws in screen-space with its own internal camera, so it
        is completely independent of Camera2D and will never conflict with it.
        """
        v_box = arcade.gui.UIBoxLayout(vertical=True, space_between=20)

        v_box.add(arcade.gui.UILabel(
            text="YOU DIED",
            font_size=72,
            text_color=(220, 30, 30, 255),
        ))

        restart_btn = arcade.gui.UIFlatButton(text="RESTART", width=240, height=60)

        # Connect the button click to _restart
        @restart_btn.event("on_click")
        def _on_click(event):
            self._restart()

        v_box.add(restart_btn)

        v_box.add(arcade.gui.UILabel(
            text="or press  R / ENTER",
            font_size=16,
            text_color=(200, 200, 200, 255),
        ))

        # UIAnchorLayout centres the box on the screen automatically
        panel = arcade.gui.UIAnchorLayout()
        panel.add(child=v_box, anchor_x="center_x", anchor_y="center_y")
        return panel

    # -- Setup -----------------------------------------------------------------
    def setup(self):
        W, H = self.width, self.height

        tile_size         = 18 * TILE_SCALE
        self.level_width  = len(MAP_GRID[0]) * tile_size
        level_height      = len(MAP_GRID) * tile_size

        self.bg_sprites    = arcade.SpriteList()
        self.player_list   = arcade.SpriteList()
        self.wall_list     = arcade.SpriteList()
        self.platform_list = arcade.SpriteList()
        self.decor_list    = arcade.SpriteList()

        try:
            bg_tex = arcade.load_texture(BG_IMAGE)
            cols = math.ceil(self.level_width / bg_tex.width)  + 1
            rows = math.ceil(H              / bg_tex.height) + 1
            for row in range(rows):
                for col in range(cols):
                    s = arcade.Sprite()
                    s.texture   = bg_tex
                    s.center_x  = col * bg_tex.width  + bg_tex.width  / 2
                    s.center_y  = row * bg_tex.height + bg_tex.height / 2
                    self.bg_sprites.append(s)
        except Exception:
            pass

        self.slash_draw = self._try_load_sound(
            HERE / "assets/sounds/484298__giddster__drawing-sword-from-scabbard.wav"
        )

        self.idle_textures_right, self.idle_textures_left = self._load_sheet("Idle.png", 6)
        self.walk_textures_right, self.walk_textures_left = self._load_sheet("Walk.png", 9)
        for i, n in enumerate([4, 5, 4]):
            self.attack_textures_right[i], self.attack_textures_left[i] = \
                self._load_sheet(f"Attack_{i+1}.png", n)

        spawn        = self._build_level()
        self.spawn_x = spawn[0] if spawn else tile_size * 2
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

        self.physics_sprite = arcade.SpriteSolidColor(PHYS_W, PHYS_H, arcade.color.WHITE)
        self.physics_sprite.alpha    = 0
        self.physics_sprite.center_x = self.spawn_x
        self.physics_sprite.center_y = self.spawn_y

        self.player_sprite = arcade.Sprite()
        self.player_sprite.texture  = self.idle_textures_right[0]
        self.player_sprite.scale    = CHARACTER_SCALING
        self.player_sprite.center_x = self.spawn_x
        self.player_sprite.center_y = self.spawn_y
        self.player_list.append(self.player_sprite)

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.physics_sprite,
            gravity_constant=GRAVITY,
            walls=self.wall_list,
            platforms=self.platform_list,
        )

        self.camera = arcade.Camera2D()
        self._cam_cx = W / 2
        self._cam_cy = H / 2

        # Build the death panel and enable the UI manager
        self.ui_manager.enable()
        self._death_panel = self._build_death_panel()

        music = self._try_load_sound(HERE / "assets/music/balloons-forever.ogg")
        if music:
            self.music = arcade.play_sound(music, volume=9.0, loop=True)

        self.game_state = "playing"

    # -- Death & restart -------------------------------------------------------
    def _trigger_death(self):
        self.game_state = "dead"
        self.physics_sprite.change_x = 0
        self.physics_sprite.change_y = 0
        # Show the GUI death panel
        self.ui_manager.add(self._death_panel)

    def _restart(self):
        self.physics_sprite.center_x = self.spawn_x
        self.physics_sprite.center_y = self.spawn_y
        self.physics_sprite.change_x = 0
        self.physics_sprite.change_y = 0

        self.cur_texture   = 0
        self.frame_counter = 0
        self.facing_right  = True
        self.attacking     = None
        self.current_anim  = None
        self.player_sprite.texture = self.idle_textures_right[0]

        self.camera.position = (self.width / 2, self.height / 2)
        self._cam_cx = self.width  / 2
        self._cam_cy = self.height / 2

        # Remove the GUI panel and rebuild it for the next death
        try:
            self._death_panel.parent = None   # detach from UIManager
        except Exception:
            pass
        self._death_panel = self._build_death_panel()

        self.game_state = "playing"

    # -- Drawing ---------------------------------------------------------------
    def on_draw(self):
        self.clear()

        # ── World (scrolling camera) ──────────────────────────────────────────
        self.camera.use()
        self.bg_sprites.draw()
        self.wall_list.draw()
        self.platform_list.draw()
        self.decor_list.draw()
        self.player_list.draw()

        # ── Death screen ──────────────────────────────────────────────────────
        if self.game_state == "dead":
            # UIManager uses its own screen-space projection – no camera conflicts.
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
        if self.game_state == "dead":
            return

        self.physics_engine.update()

        self.physics_sprite.center_x = max(
            PHYS_W / 2,
            min(self.level_width - PHYS_W / 2, self.physics_sprite.center_x),
        )

        if self.physics_sprite.center_y < DEATH_Y:
            self._trigger_death()
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
    print ("Goodbye!")
    print ("Thanks for playing Wok of the Warrior!")