import math
import arcade
import arcade.gui

from constants import (
    SCREEN_TITLE, CHARACTER_SCALING, PLAYER_SPEED, GRAVITY, JUMP_SPEED,
    UPDATES_PER_FRAME, PHYS_W, PHYS_H, TILE_SCALE, TILE_SIZE, DEATH_Y,
    SAMURAI_PATH, KENNEY_TILES, BG_IMAGE, SLIME_BASE, HERE, BOSS_PATH, BOSS_MUSIC,
    ATTACK_KEYS, TILE_CHARS, WALL_TILES, PLATFORM_TILES, DECOR_TILES,
    TERRAIN_SURFACE, TERRAIN_FILL, PLATFORM_F_TILES, PLATFORM_H_TILES,
    SLIME_FRAME_W, SLIME_FRAME_H, SLIME_SCALE, SLIME_FOOT_OFFSET,
    SWORD_REACH_X, SWORD_REACH_Y, ANIM_X_OFFSETS,
)
from levels import LEVELS
from enemy import SlimeEnemy, BossNinja
import save_client

# Autosave the player's position this often (seconds) while playing.
AUTOSAVE_INTERVAL = 3.0


class MyGame(arcade.Window):

    def __init__(self):
        super().__init__(title=SCREEN_TITLE, fullscreen=True)

        self.current_level = 1
        self.bg_texture    = None
        self.bg_sprites    = None
        self._menu_bg_list = None
        self.player_list   = None
        self.wall_list     = None
        self.platform_list = None
        self.decor_list    = None
        self.enemy_list    = None
        self.slime_textures   = {}
        self._ground_tile_set: set = set()

        self.physics_sprite = None
        self.player_sprite  = None
        self.physics_engine = None
        self.camera         = None
        self.hud_camera     = None
        self.level_width    = 0
        self.time_remaining = 60.0
        self.spawn_x = 0
        self.spawn_y = 0

        self.game_state = "playing"
        self._cam_cx = 0.0
        self._cam_cy = 0.0
        self._save_timer = 0.0
        self._defeated = set()   # ids of enemies killed this save ("level:index")

        self.ui_manager            = arcade.gui.UIManager()
        self._death_panel          = None
        self._level_complete_panel = None
        self._game_won_panel       = None
        self._timer_text           = None

        self.cur_texture   = 0
        self.frame_counter = 0
        self.facing_right  = True
        self.attacking     = None
        self.current_anim  = None

        self.slash_draw = None
        self.bg_music_sound   = None
        self.boss_music_sound = None
        self.music_player      = None    # background-theme playback handle
        self.boss_music_player = None    # boss-theme playback handle
        self._boss_music_on    = False

        self.idle_textures_right   = []
        self.idle_textures_left    = []
        self.walk_textures_right   = []
        self.walk_textures_left    = []
        self.attack_textures_right = [[], [], []]
        self.attack_textures_left  = [[], [], []]
        self.dead_textures_right   = []
        self.dead_textures_left    = []

        self.boss          = None
        self.boss_list     = None
        self.boss_anims    = {}
        self._attack_hit_boss = False   # one boss hit per sword swing

        self.invincible    = False      # secret burger power-up
        self.powerup       = None
        self.powerup_list  = None

    # ------------------------------------------------------------------ utils

    def _try_load_sound(self, path):
        try:
            return arcade.load_sound(path)
        except Exception:
            return None

    def _play_attack_sound(self):
        if self.slash_draw:
            arcade.play_sound(self.slash_draw, volume=15.0)

    def _stop_sound(self, player):
        try:
            arcade.stop_sound(player)
        except Exception:
            pass

    def _start_bg_music(self):
        """Play the normal theme; stop the boss theme if it was running."""
        if self.boss_music_player is not None:
            self._stop_sound(self.boss_music_player)
            self.boss_music_player = None
        self._boss_music_on = False
        if self.bg_music_sound is not None and self.music_player is None:
            self.music_player = arcade.play_sound(self.bg_music_sound, volume=7.0, loop=True)

    def _start_boss_music(self):
        """Switch from the normal theme to the boss battle theme."""
        if self._boss_music_on:
            return
        if self.music_player is not None:
            self._stop_sound(self.music_player)
            self.music_player = None
        if self.boss_music_sound is not None:
            self.boss_music_player = arcade.play_sound(self.boss_music_sound, volume=8.0, loop=True)
        self._boss_music_on = True

    def _load_sheet(self, filename, count, base=SAMURAI_PATH):
        try:
            sheet  = arcade.load_spritesheet(f"{base}/{filename}")
            frames = sheet.get_texture_grid(size=(128, 128), columns=count, count=count)
            return frames, [t.flip_left_right() for t in frames]
        except Exception:
            fallback = arcade.make_soft_circle_texture(64, arcade.color.RED)
            return [fallback] * count, [fallback] * count

    def _load_slime_textures(self):
        for i in (1, 2, 3):
            try:
                base  = SLIME_BASE / f"Slime{i}/Without_shadow"
                walk  = arcade.load_spritesheet(base / f"Slime{i}_Walk_without_shadow.png")
                walk_right = walk.get_texture_grid(
                    size=(SLIME_FRAME_W, SLIME_FRAME_H), columns=8, count=32
                )[:8]
                walk_left  = [t.flip_left_right() for t in walk_right]

                death = arcade.load_spritesheet(base / f"Slime{i}_Death_without_shadow.png")
                death_right = death.get_texture_grid(
                    size=(SLIME_FRAME_W, SLIME_FRAME_H), columns=10, count=40
                )[:10]
                death_left  = [t.flip_left_right() for t in death_right]

                self.slime_textures[i] = (walk_right, walk_left, death_right, death_left)
            except Exception:
                fallback = arcade.make_soft_circle_texture(16, arcade.color.BLUE)
                self.slime_textures[i] = ([fallback], [fallback], [fallback], [fallback])

    def _sync_player_sprite(self):
        x_off = ANIM_X_OFFSETS.get(self.current_anim, 0.0)
        y_off = (128 * CHARACTER_SCALING / 2) - (self.physics_sprite.height / 2)
        self.player_sprite.center_x = self.physics_sprite.center_x + x_off
        self.player_sprite.center_y = self.physics_sprite.center_y + y_off

    # ------------------------------------------------------------------ level

    def _tile_for(self, char, row_idx, col_idx, map_grid):
        """Pick the right tile so terrain connects: surface on top, fill below."""
        if char in ("B", "X"):                 # X = passable fake wall, drawn as terrain
            above = map_grid[row_idx - 1][col_idx] if row_idx > 0 else " "
            pool = TERRAIN_SURFACE if above not in ("B", "X") else TERRAIN_FILL
        elif char == "F":
            pool = PLATFORM_F_TILES
        elif char == "H":
            pool = PLATFORM_H_TILES
        else:
            return TILE_CHARS.get(char)
        return pool[col_idx % len(pool)]

    def _build_level(self, map_grid):
        total_rows = len(map_grid)
        spawn = None
        for row_idx, row in enumerate(map_grid):
            for col_idx, char in enumerate(row):
                if char == " ":
                    continue
                x = col_idx * TILE_SIZE + TILE_SIZE // 2
                y = (total_rows - 1 - row_idx) * TILE_SIZE + TILE_SIZE // 2
                if char == "P":
                    spawn = (x, y + TILE_SIZE)
                    continue
                filename = self._tile_for(char, row_idx, col_idx, map_grid)
                if not filename:
                    continue
                try:
                    sprite = arcade.Sprite(f"{KENNEY_TILES}/{filename}", TILE_SCALE)
                except Exception:
                    if char == "B":
                        color = (139, 69, 19)
                    elif char == "F":
                        color = (255, 105, 180)
                    else:
                        color = (210, 105, 30)
                    sprite = arcade.SpriteSolidColor(int(TILE_SIZE), int(TILE_SIZE), color)
                    sprite.color = color
                sprite.center_x = x
                sprite.center_y = y
                if char in WALL_TILES:
                    self.wall_list.append(sprite)
                    self._ground_tile_set.add((x, y))
                elif char in PLATFORM_TILES:
                    self.platform_list.append(sprite)
                    self._ground_tile_set.add((x, y))
                elif char in DECOR_TILES:
                    self.decor_list.append(sprite)
        return spawn

    def _build_death_panel(self):
        v_box = arcade.gui.UIBoxLayout(vertical=True, space_between=18)
        v_box.add(arcade.gui.UILabel(text="YOU DIED", font_size=72, text_color=(220, 30, 30, 255)))
        r = arcade.gui.UIFlatButton(text="RESTART", width=260, height=58)
        r.event("on_click")(lambda e: self._restart())
        v_box.add(r)
        m = arcade.gui.UIFlatButton(text="MAIN MENU", width=260, height=58)
        m.event("on_click")(lambda e: self._show_main_menu())
        v_box.add(m)
        v_box.add(arcade.gui.UILabel(text="R / ENTER = restart     M = menu", font_size=16, text_color=(200, 200, 200, 255)))
        panel = arcade.gui.UIAnchorLayout()
        panel.add(child=v_box, anchor_x="center_x", anchor_y="center_y")
        return panel

    def _build_level_complete_panel(self):
        v_box = arcade.gui.UIBoxLayout(vertical=True, space_between=20)
        v_box.add(arcade.gui.UILabel(text=f"LEVEL {self.current_level} COMPLETE!", font_size=60, text_color=(255, 215, 0, 255)))
        n = arcade.gui.UIFlatButton(text="NEXT LEVEL", width=280, height=60)
        @n.event("on_click")
        def _(_): self._advance_level()
        v_box.add(n)
        v_box.add(arcade.gui.UILabel(text="or press  N / ENTER", font_size=14, text_color=(200, 200, 200, 255)))
        panel = arcade.gui.UIAnchorLayout()
        panel.add(child=v_box, anchor_x="center_x", anchor_y="center_y")
        return panel

    def _build_game_won_panel(self):
        v_box = arcade.gui.UIBoxLayout(vertical=True, space_between=20)
        v_box.add(arcade.gui.UILabel(text="CONGRATULATIONS!", font_size=64, text_color=(255, 215, 0, 255)))
        v_box.add(arcade.gui.UILabel(text="You beat the game!", font_size=32, text_color=(255, 255, 255, 255)))
        p = arcade.gui.UIFlatButton(text="MAIN MENU", width=280, height=60)
        @p.event("on_click")
        def _(_): self._show_main_menu()
        v_box.add(p)
        v_box.add(arcade.gui.UILabel(text="or press  ENTER", font_size=14, text_color=(200, 200, 200, 255)))
        panel = arcade.gui.UIAnchorLayout()
        panel.add(child=v_box, anchor_x="center_x", anchor_y="center_y")
        return panel

    def _build_main_menu_panel(self):
        v_box = arcade.gui.UIBoxLayout(vertical=True, space_between=18)
        v_box.add(arcade.gui.UILabel(text="WOK OF THE WARRIOR", font_size=56, text_color=(255, 215, 0, 255)))
        for text, action in [
            ("NEW GAME",      self._new_game),
            ("CONTINUE GAME", self._continue_game),
            ("CHOOSE LEVEL",  self._show_level_select),
        ]:
            btn = arcade.gui.UIFlatButton(text=text, width=320, height=58)
            btn.event("on_click")(lambda e, a=action: a())
            v_box.add(btn)
        panel = arcade.gui.UIAnchorLayout()
        panel.add(child=v_box, anchor_x="center_x", anchor_y="center_y")
        return panel

    def _build_level_select_panel(self):
        v_box = arcade.gui.UIBoxLayout(vertical=True, space_between=14)
        v_box.add(arcade.gui.UILabel(text="CHOOSE LEVEL", font_size=46, text_color=(255, 215, 0, 255)))
        levels = sorted(LEVELS)
        for start in range(0, len(levels), 5):           # rows of 5 buttons
            row = arcade.gui.UIBoxLayout(vertical=False, space_between=10)
            for n in levels[start:start + 5]:
                b = arcade.gui.UIFlatButton(text=str(n), width=80, height=58)
                b.event("on_click")(lambda e, nn=n: self._choose_level(nn))
                row.add(b)
            v_box.add(row)
        back = arcade.gui.UIFlatButton(text="BACK", width=200, height=46)
        back.event("on_click")(lambda e: self._show_main_menu())
        v_box.add(back)
        panel = arcade.gui.UIAnchorLayout()
        panel.add(child=v_box, anchor_x="center_x", anchor_y="center_y")
        return panel

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

        self.bg_sprites       = arcade.SpriteList()
        self._ground_tile_set = set()
        self.wall_list        = arcade.SpriteList(use_spatial_hash=True)
        self.platform_list    = arcade.SpriteList(use_spatial_hash=True)
        self.decor_list       = arcade.SpriteList()
        self.enemy_list       = arcade.SpriteList()
        self.boss_list        = arcade.SpriteList()
        self.boss             = None
        self.powerup_list     = arcade.SpriteList()
        self.powerup          = None
        self.invincible       = False

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
            (-10, level_height, 20, level_height * 4),
            (self.level_width + 10, level_height, 20, level_height * 4),
        ]:
            b = arcade.SpriteSolidColor(ww, hh, arcade.color.WHITE)
            b.alpha = 0; b.center_x = cx; b.center_y = cy
            self.wall_list.append(b)

        for idx, (col, floor_row, stype) in enumerate(level_data["enemies"]):
            eid = f"{self.current_level}:{idx}"
            if eid in self._defeated:
                continue   # already killed in a previous session — stay dead
            ex = col * TILE_SIZE + TILE_SIZE // 2
            floor_top = (total_rows - 1 - floor_row) * TILE_SIZE + TILE_SIZE
            ey = floor_top + int(SLIME_SCALE * SLIME_FOOT_OFFSET)
            if stype in self.slime_textures:
                wr, wl, dr, dl = self.slime_textures[stype]
                self.enemy_list.append(SlimeEnemy(ex, ey, wr, wl, dr, dl, eid))

        boss_col = level_data.get("boss_col")
        if boss_col is not None and self.boss_anims:
            bx = boss_col * TILE_SIZE + TILE_SIZE // 2
            floor_top = (total_rows - 1 - 13) * TILE_SIZE + TILE_SIZE
            by = floor_top + (128 * BossNinja.SCALE) / 2   # feet sit on the ground
            self.boss = BossNinja(bx, by, self.boss_anims)
            self.boss_list.append(self.boss)

        # Secret invincibility burger.
        burger_col = level_data.get("burger_col")
        if burger_col is not None:
            floor_top = (total_rows - 1 - 13) * TILE_SIZE + TILE_SIZE
            try:
                burger = arcade.Sprite(f"{KENNEY_TILES}/tile_0092.png", 3.5)
            except Exception:
                burger = arcade.SpriteSolidColor(48, 40, (235, 170, 90))
            burger.center_x = burger_col * TILE_SIZE + TILE_SIZE // 2
            burger.center_y = floor_top + burger.height / 2
            self.powerup = burger
            self.powerup_list.append(burger)

        self.physics_sprite.center_x = self.spawn_x
        self.physics_sprite.center_y = self.spawn_y
        self.physics_sprite.change_x = 0
        self.physics_sprite.change_y = 0

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.physics_sprite, gravity_constant=GRAVITY,
            walls=self.wall_list, platforms=self.platform_list,
        )

        self._cam_cx = W / 2
        self._cam_cy = H / 2
        self.camera.position = (round(self._cam_cx), round(self._cam_cy))

        self.cur_texture   = 0
        self.frame_counter = 0
        self.facing_right  = True
        self.attacking     = None
        self.current_anim  = "idle_right"
        self.player_sprite.texture = self.idle_textures_right[0]
        self.player_sprite.color   = (255, 255, 255)   # clear any invincible tint
        self._sync_player_sprite()

        self._death_panel          = self._build_death_panel()
        self._level_complete_panel = self._build_level_complete_panel()
        self._game_won_panel       = self._build_game_won_panel()
        self.time_remaining = 60.0
        self.game_state = "playing"
        self._start_bg_music()      # normal theme (resets boss theme on restart)

    # ------------------------------------------------------------------ setup

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
        self.dead_textures_right, self.dead_textures_left = self._load_sheet("Dead.png", 6)
        for i, n in enumerate([4, 5, 4]):
            self.attack_textures_right[i], self.attack_textures_left[i] = \
                self._load_sheet(f"Attack_{i+1}.png", n)

        # Boss uses the Samurai Commander character sheets.
        self.boss_anims = {
            "idle":   self._load_sheet("Idle.png", 5, BOSS_PATH),
            "run":    self._load_sheet("Run.png", 8, BOSS_PATH),
            "attack": self._load_sheet("Attack_2.png", 5, BOSS_PATH),
            "hurt":   self._load_sheet("Hurt.png", 2, BOSS_PATH),
            "dead":   self._load_sheet("Dead.png", 6, BOSS_PATH),
        }

        self._load_slime_textures()

        self.physics_sprite = arcade.SpriteSolidColor(PHYS_W, PHYS_H, arcade.color.WHITE)
        self.physics_sprite.alpha = 0

        self.player_list   = arcade.SpriteList()
        self.player_sprite = arcade.Sprite()
        self.player_sprite.texture = self.idle_textures_right[0]
        self.player_sprite.scale   = CHARACTER_SCALING
        self.player_list.append(self.player_sprite)

        self.camera     = arcade.Camera2D()
        self.hud_camera = arcade.Camera2D()

        # Persistent Text object for the HUD timer (far cheaper than draw_text).
        self._timer_text = arcade.Text(
            "0:00", self.width - 20, self.height - 20,
            arcade.color.WHITE, 36, anchor_x="right", anchor_y="top", bold=True,
        )

        self.bg_music_sound   = self._try_load_sound(HERE / "assets/music/balloons-forever.ogg")
        self.boss_music_sound = self._try_load_sound(BOSS_MUSIC)

        # Full-screen menu backdrop.
        self._menu_bg_list = arcade.SpriteList()
        if self.bg_texture is not None:
            s = arcade.Sprite()
            s.texture  = self.bg_texture
            s.center_x = self.width / 2
            s.center_y = self.height / 2
            s.width    = self.width
            s.height   = self.height
            self._menu_bg_list.append(s)

        # Open on the main menu instead of jumping straight into the game.
        self._show_main_menu()

    def _restore_position(self, saved):
        """Place the player where they last were, clamped to safe bounds."""
        x = float(saved.get("position_x", self.spawn_x))
        y = float(saved.get("position_y", self.spawn_y))
        x = max(PHYS_W / 2, min(self.level_width - PHYS_W / 2, x))
        if y < 0:                      # below the death plane -> use spawn
            y = self.spawn_y
        self.physics_sprite.center_x = x
        self.physics_sprite.center_y = y
        self.physics_sprite.change_x = 0
        self.physics_sprite.change_y = 0
        self._sync_player_sprite()

        # Resume the countdown where it left off (fall back to a full timer).
        saved_time = float(saved.get("time_remaining", self.time_remaining))
        self.time_remaining = saved_time if saved_time > 0 else 60.0

        cam_left = max(0.0, min(x - self.width // 3, self.level_width - self.width))
        self._cam_cx = cam_left + self.width / 2
        self.camera.position = (round(self._cam_cx), round(self._cam_cy))

    def _persist_progress(self, sync=False):
        """Save level, position and defeated enemies through the API."""
        if self.physics_sprite is None:
            return
        save = save_client.save_progress if sync else save_client.save_progress_async
        save(
            self.current_level,
            self.physics_sprite.center_x,
            self.physics_sprite.center_y,
            defeated_enemies=list(self._defeated),
            time_remaining=self.time_remaining,
        )

    def on_close(self):
        self._persist_progress(sync=True)
        super().on_close()

    # ------------------------------------------------------------------ state

    def _trigger_death(self):
        if self.game_state != "playing" or self.invincible:
            return
        # Play the player's death animation first; the panel shows when it ends.
        self.game_state = "player_dying"
        self.physics_sprite.change_x = 0
        self.physics_sprite.change_y = 0
        self.attacking     = None
        self.cur_texture   = 0
        self.frame_counter = 0
        frames = self.dead_textures_right if self.facing_right else self.dead_textures_left
        self.player_sprite.texture = frames[0]

    def _update_player_death(self):
        """Advance the player's death animation, then show the death panel."""
        self.frame_counter += 1
        if self.frame_counter < UPDATES_PER_FRAME:
            return
        self.frame_counter = 0
        frames = self.dead_textures_right if self.facing_right else self.dead_textures_left
        self.cur_texture += 1
        if self.cur_texture >= len(frames):
            self.player_sprite.texture = frames[-1]
            self.game_state = "dead"
            self.ui_manager.add(self._death_panel)
        else:
            self.player_sprite.texture = frames[self.cur_texture]

    def _trigger_level_complete(self):
        self.physics_sprite.change_x = 0
        self.physics_sprite.change_y = 0
        if self.current_level >= len(LEVELS):
            # Beating the final level wins the game.
            self.game_state = "game_won"
            self.ui_manager.add(self._game_won_panel)
        else:
            self.game_state = "level_complete"
            self.ui_manager.add(self._level_complete_panel)

    def _respawn_enemies(self, level):
        """Forget this level's kills so its enemies spawn fresh again."""
        prefix = f"{level}:"
        self._defeated = {e for e in self._defeated if not e.startswith(prefix)}

    def _restart(self):
        # Respawn this level's enemies whenever the *player* respawns. Kills
        # still survive a full game stop because we only clear them on a restart
        # or level entry, not on load — so quitting mid-level keeps them dead.
        self._respawn_enemies(self.current_level)
        self._load_level(self.current_level)

    def _advance_level(self):
        next_num = (self.current_level % len(LEVELS)) + 1
        # Entering a new level repopulates it with enemies.
        self._respawn_enemies(next_num)
        self._load_level(next_num)
        self._persist_progress()

    # ------------------------------------------------------------------ menu

    def _reset_ui(self):
        self.ui_manager.disable()
        self.ui_manager = arcade.gui.UIManager()
        self.ui_manager.enable()

    def _show_main_menu(self):
        self.game_state = "menu"
        self.boss = None
        self._start_bg_music()
        self._reset_ui()
        self.ui_manager.add(self._build_main_menu_panel())

    def _show_level_select(self):
        self.game_state = "level_select"
        self._reset_ui()
        self.ui_manager.add(self._build_level_select_panel())

    def _new_game(self):
        """Fresh run from level 1."""
        self._defeated = set()
        self._load_level(1)
        self._persist_progress()

    def _continue_game(self):
        """Resume from the saved progress (or start fresh if there is none)."""
        saved = save_client.load_progress()
        if saved and saved.get("current_level") in LEVELS:
            self._defeated = set(saved.get("defeated_enemies", []))
            self._load_level(int(saved["current_level"]))
            self._restore_position(saved)
        else:
            self._new_game()

    def _choose_level(self, level_num):
        """Start fresh from a chosen level."""
        self._respawn_enemies(level_num)
        self._load_level(level_num)
        self._persist_progress()

    # ------------------------------------------------------------------ combat

    def _defeat(self, enemy):
        """Mark an enemy as killed and play its death animation before removal."""
        if enemy.eid is not None:
            self._defeated.add(enemy.eid)
        enemy.start_death()        # removed once the animation finishes
        self._persist_progress()   # record the kill in the background

    def _check_enemy_collisions(self):
        player_bottom = self.physics_sprite.center_y - PHYS_H / 2
        for enemy in list(self.enemy_list):
            if enemy.dying:
                continue           # already defeated, just animating
            if not arcade.check_for_collision(self.physics_sprite, enemy):
                continue
            if self.physics_sprite.change_y <= 0 and player_bottom >= enemy.center_y:
                self._defeat(enemy)
                self.physics_sprite.change_y = JUMP_SPEED * 0.7
            elif self.invincible:
                self._defeat(enemy)          # plow straight through while invincible
            else:
                self._trigger_death()
                return
        if self.attacking is not None:
            px, py = self.physics_sprite.center_x, self.physics_sprite.center_y
            y_tol  = SWORD_REACH_Y + PHYS_H / 2 + SLIME_SCALE * SLIME_FRAME_H / 2
            for enemy in list(self.enemy_list):
                if enemy.dying:
                    continue
                dx = enemy.center_x - px
                if abs(enemy.center_y - py) < y_tol:
                    if self.facing_right and 0 < dx < SWORD_REACH_X:
                        self._defeat(enemy)
                    elif not self.facing_right and -SWORD_REACH_X < dx < 0:
                        self._defeat(enemy)

    def _update_boss(self, dt):
        boss = self.boss
        px, py = self.physics_sprite.center_x, self.physics_sprite.center_y
        boss.update_boss(px, py, dt)

        # Kick off the boss battle theme once the player gets near.
        if not self._boss_music_on and abs(boss.center_x - px) <= boss.ACTIVATE_DIST:
            self._start_boss_music()

        if boss.state == "dead":
            # Death animation finished — boss vanquished, the game is won.
            boss.remove_from_sprite_lists()
            self.boss = None
            self._start_bg_music()      # back to the normal theme
            self._trigger_level_complete()
            return
        if boss.state == "dying":
            return

        # Sword strike: reach the boss without having to touch it. One per swing.
        if self.attacking is not None and not self._attack_hit_boss:
            dx = boss.center_x - px
            reach = SWORD_REACH_X + 70
            in_x = (self.facing_right and 0 < dx < reach) or \
                   (not self.facing_right and -reach < dx < 0)
            if in_x and boss.bottom - 20 <= py <= boss.top:
                boss.hit()
                self._attack_hit_boss = True
                return

        # Stomp from above always damages the boss.
        if arcade.check_for_collision(self.physics_sprite, boss):
            if self.physics_sprite.change_y < 0 and (py - PHYS_H / 2) > boss.center_y:
                boss.hit()
                self.physics_sprite.change_y = JUMP_SPEED * 0.7
                return

        # The boss's swing is lethal only within reach, only while it actually
        # swings, and only if you aren't swinging back — so you can dodge it by
        # stepping out of range during the telegraph. (No effect if invincible.)
        if boss.attacking and self.attacking is None and not self.invincible:
            if abs(boss.center_x - px) <= boss.ATTACK_HIT_RANGE and boss.bottom - 30 <= py <= boss.top:
                self._trigger_death()

    # ------------------------------------------------------------------ draw

    def on_draw(self):
        self.clear()

        # Menu screens: no level is loaded, so just draw the backdrop + UI.
        if self.game_state in ("menu", "level_select"):
            self.hud_camera.use()
            if self._menu_bg_list is not None:
                self._menu_bg_list.draw(pixelated=True)
            self.ui_manager.draw()
            return

        self.camera.use()
        # pixelated=True -> nearest-neighbour sampling: crisp pixels and no
        # seams bleeding between adjacent terrain tiles.
        self.bg_sprites.draw(pixelated=True)
        self.enemy_list.draw(pixelated=True)
        if self.boss_list is not None:
            self.boss_list.draw(pixelated=True)
        if self.powerup_list is not None:
            self.powerup_list.draw(pixelated=True)
        self.wall_list.draw(pixelated=True)
        self.platform_list.draw(pixelated=True)
        self.decor_list.draw(pixelated=True)
        self.player_list.draw(pixelated=True)

        self.hud_camera.use()
        secs = int(self.time_remaining)
        self._timer_text.text = f"{secs // 60}:{secs % 60:02d}"
        if self.time_remaining <= 10:
            self._timer_text.color = arcade.color.RED
        elif self.time_remaining <= 20:
            self._timer_text.color = arcade.color.ORANGE
        else:
            self._timer_text.color = arcade.color.WHITE
        self._timer_text.draw()

        if self.game_state in ("dead", "level_complete", "game_won"):
            self.ui_manager.draw()

    # ------------------------------------------------------------------ input

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            if self.game_state not in ("menu", "level_select"):
                self._persist_progress(sync=True)
            arcade.close_window()
            return
        if self.game_state in ("menu", "level_select"):
            return                                    # menus are mouse-driven
        if self.game_state == "dead":
            if key in (arcade.key.R, arcade.key.ENTER, arcade.key.RETURN):
                self._restart()
            elif key == arcade.key.M:
                self._show_main_menu()
            return
        if self.game_state == "level_complete":
            if key in (arcade.key.N, arcade.key.ENTER, arcade.key.RETURN):
                self._advance_level()
            return
        if self.game_state == "game_won":
            if key in (arcade.key.ENTER, arcade.key.RETURN):
                self._show_main_menu()
            return
        if key in ATTACK_KEYS:
            if self.attacking is None:
                self.attacking = ATTACK_KEYS[key]
                self.cur_texture = self.frame_counter = 0
                self._attack_hit_boss = False
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

    # ------------------------------------------------------------------ update

    def on_update(self, delta_time):
        if self.game_state == "player_dying":
            self._update_player_death()
            return
        if self.game_state != "playing":
            return

        self.physics_engine.update()

        self.physics_sprite.center_x = max(
            PHYS_W / 2,
            min(self.level_width - PHYS_W / 2, self.physics_sprite.center_x),
        )

        self._update_animation()
        self._sync_player_sprite()

        # Secret burger: grab it to become invincible for the rest of the run.
        if self.powerup is not None and arcade.check_for_collision(self.physics_sprite, self.powerup):
            self.powerup.remove_from_sprite_lists()
            self.powerup = None
            self.invincible = True
            self.player_sprite.color = (255, 215, 0)   # golden glow

        if self.physics_sprite.center_y < DEATH_Y and not self.invincible:
            self._trigger_death()
            return
        # On a boss level the exit is the boss, not the right edge.
        if self.boss is None and self.physics_sprite.center_x >= self.level_width - TILE_SIZE * 2:
            self._trigger_level_complete()
            return

        self.time_remaining -= delta_time
        if self.time_remaining <= 0.0:
            self.time_remaining = 0.0
            if not self.invincible:
                self._trigger_death()
                return

        screen_left  = self._cam_cx - self.width  / 2 - TILE_SIZE * 4
        screen_right = self._cam_cx + self.width  / 2 + TILE_SIZE * 4
        for enemy in list(self.enemy_list):
            if enemy.dying:
                if enemy.update_death():
                    enemy.remove_from_sprite_lists()
            elif screen_left <= enemy.center_x <= screen_right:
                enemy.update_patrol(self._ground_tile_set)

        self._check_enemy_collisions()
        if self.game_state != "playing":
            return

        if self.boss is not None:
            self._update_boss(delta_time)
            if self.game_state != "playing":
                return

        cam_left     = self.physics_sprite.center_x - self.width // 3
        cam_left     = max(0.0, min(cam_left, self.level_width - self.width))
        self._cam_cx = cam_left + self.width  / 2
        self._cam_cy =            self.height / 2
        # Snap to whole pixels so tiles never render with sub-pixel seams.
        self.camera.position = (round(self._cam_cx), round(self._cam_cy))

        # Periodically persist progress in the background.
        self._save_timer += delta_time
        if self._save_timer >= AUTOSAVE_INTERVAL:
            self._save_timer = 0.0
            self._persist_progress()

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
                self.attacking   = None
                self.cur_texture = 0
                is_walking = self.physics_sprite.change_x != 0
                if self.facing_right:
                    self.current_anim = "walk_right" if is_walking else "idle_right"
                else:
                    self.current_anim = "walk_left" if is_walking else "idle_left"
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
