# ===========================================================================
# game.py  —  the heart of the game.
# ---------------------------------------------------------------------------
# Everything lives in one class, MyGame, which extends arcade.Window. Arcade
# calls these "magic" methods for us automatically:
#   setup()              once at the start, to load everything
#   on_update(dt)        ~60 times a second — move things, run game logic
#   on_draw()            ~60 times a second — paint the screen
#   on_key_press/release when a key goes down/up
#
# The game is a STATE MACHINE. `self.game_state` is one of:
#   "menu"          the main menu (New Game / Continue / Choose Level)
#   "level_select"  the level picker
#   "playing"       normal gameplay
#   "player_dying"  death animation is playing
#   "dead"          the "YOU DIED" screen
#   "level_complete" finished a level
#   "game_won"      beat the final level
# Most methods check this state to decide what to do.
# ===========================================================================
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
    NEW_ENEMY_PATH, MONSTERS, MONSTER_FRAME,
)
from levels import LEVELS
from enemy import SlimeEnemy, MonsterEnemy, BossNinja
import save_client

# Autosave the player's position this often (seconds) while playing.
AUTOSAVE_INTERVAL = 3.0


class MyGame(arcade.Window):

    def __init__(self):
        # Create the fullscreen window.
        super().__init__(title=SCREEN_TITLE, fullscreen=True)

        # __init__ just declares every variable (mostly None / empty for now).
        # The real loading happens later in setup(). Grouping them here means
        # you can see the game's entire "memory" in one place.

        # --- the world: tiles, sprites, and the level ----------------------
        self.current_level = 1
        self.bg_texture    = None        # the food background image
        self.bg_sprites    = None        # tiled copies of it across the level
        self._menu_bg_list = None        # background shown on the menu screens
        self.player_list   = None        # the visible samurai sprite
        self.wall_list     = None        # solid tiles (collide)
        self.platform_list = None        # one-way platforms
        self.decor_list    = None        # non-colliding tiles (e.g. fake walls)
        self.enemy_list    = None        # slimes + monsters
        self.slime_textures   = {}       # loaded slime animation frames by type
        self.monster_anims    = {}       # loaded monster animation frames by type
        self._ground_tile_set: set = set()  # (x,y) of solid tiles, for enemy AI

        # --- the player's physics + camera ---------------------------------
        self.physics_sprite = None       # invisible collision box that moves
        self.player_sprite  = None       # the visible samurai drawn over it
        self.physics_engine = None       # arcade's gravity/collision helper
        self.camera         = None       # scrolls to follow the player
        self.hud_camera     = None       # fixed camera for on-screen text/UI
        self.level_width    = 0
        self.time_remaining = 60.0       # countdown timer for the level
        self.spawn_x = 0                 # where the player starts
        self.spawn_y = 0

        # --- game state + camera/save bookkeeping --------------------------
        self.game_state = "playing"      # see the state list at top of file
        self._cam_cx = 0.0               # camera centre we're aiming at
        self._cam_cy = 0.0
        self._save_timer = 0.0           # counts up to AUTOSAVE_INTERVAL
        self._defeated = set()   # ids of enemies killed this save ("level:index")

        # --- on-screen UI (menus, death screen, timer text) ----------------
        self.ui_manager            = arcade.gui.UIManager()  # handles buttons
        self._death_panel          = None
        self._level_complete_panel = None
        self._game_won_panel       = None
        self._timer_text           = None

        # --- player animation state ----------------------------------------
        self.cur_texture   = 0           # current frame index of the animation
        self.frame_counter = 0           # counts up to UPDATES_PER_FRAME
        self.facing_right  = True
        self.attacking     = None        # None, or which attack combo is playing
        self.current_anim  = None        # name of the current animation

        # --- sound + music -------------------------------------------------
        self.slash_draw = None           # sword swing sound
        self.bg_music_sound   = None     # loaded normal theme
        self.boss_music_sound = None     # loaded boss theme
        self.music_player      = None    # background-theme playback handle
        self.boss_music_player = None    # boss-theme playback handle
        self._boss_music_on    = False

        # --- player animation frames (loaded in setup) ---------------------
        # Each is a list of textures; *_right is the original art, *_left is
        # the same frames flipped horizontally.
        self.idle_textures_right   = []
        self.idle_textures_left    = []
        self.walk_textures_right   = []
        self.walk_textures_left    = []
        self.jump_textures_right   = []
        self.jump_textures_left    = []
        self.attack_textures_right = [[], [], []]   # 3 attack combos
        self.attack_textures_left  = [[], [], []]
        self.dead_textures_right   = []
        self.dead_textures_left    = []

        # --- boss (level 10 only) ------------------------------------------
        self.boss          = None        # the BossNinja, or None
        self.boss_list     = None        # sprite list holding it (for drawing)
        self.boss_anims    = {}          # its loaded animation frames
        self._attack_hit_boss = False   # one boss hit per sword swing

        # --- secret invincibility burger -----------------------------------
        self.invincible    = False      # secret burger power-up
        self.powerup       = None        # the burger sprite, or None
        self.powerup_list  = None

    # ------------------------------------------------------------------ utils
    # Small helpers used by the rest of the class. (Methods starting with "_"
    # are "private" by convention — only meant to be called from inside here.)

    def _try_load_sound(self, path):
        """Load a sound file, returning None instead of crashing if it fails."""
        try:
            return arcade.load_sound(path)
        except Exception:
            return None

    def _play_attack_sound(self):
        """Play the sword-swing sound (if it loaded)."""
        if self.slash_draw:
            arcade.play_sound(self.slash_draw, volume=15.0)

    def _stop_sound(self, player):
        """Stop a playing sound, ignoring errors if it already stopped."""
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
        """Load one animation strip (e.g. Walk.png) into a list of frames.

        A "sprite sheet" is one image with all frames in a row. We slice it into
        `count` separate 128x128 textures and also build a mirrored (left-facing)
        copy of each. Returns (right_frames, left_frames). If the file is
        missing it returns red circles so the game still runs.
        """
        try:
            sheet  = arcade.load_spritesheet(f"{base}/{filename}")
            frames = sheet.get_texture_grid(size=(128, 128), columns=count, count=count)
            return frames, [t.flip_left_right() for t in frames]
        except Exception:
            fallback = arcade.make_soft_circle_texture(64, arcade.color.RED)
            return [fallback] * count, [fallback] * count

    def _load_slime_textures(self):
        """Load walk + death frames for all 3 slime types into self.slime_textures."""
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

    def _load_monster_textures(self):
        """Load run/attack/death frames for the 3 monster types (codes 4/5/6)."""
        # (state name, file suffix, frame count) — counts are in the filenames.
        sheets = [("run", "Run_6", 6), ("attack", "Attack1_4", 4), ("death", "Death_8", 8)]
        for code, (folder, prefix) in MONSTERS.items():
            anims = {}
            for state, suffix, n in sheets:
                try:
                    sheet = arcade.load_spritesheet(NEW_ENEMY_PATH / folder / f"{prefix}_{suffix}.png")
                    frames = sheet.get_texture_grid(
                        size=(MONSTER_FRAME, MONSTER_FRAME), columns=n, count=n
                    )
                    anims[state] = (frames, [t.flip_left_right() for t in frames])
                except Exception:
                    fb = arcade.make_soft_circle_texture(24, arcade.color.PURPLE)
                    anims[state] = ([fb], [fb])
            self.monster_anims[code] = anims

    def _sync_player_sprite(self):
        """Line up the visible samurai over the invisible physics box.

        The physics engine moves the small collision box; the big drawn sprite
        just follows it (plus the per-animation nudge so the art stays centred).
        """
        x_off = ANIM_X_OFFSETS.get(self.current_anim, 0.0)
        y_off = (128 * CHARACTER_SCALING / 2) - (self.physics_sprite.height / 2)
        self.player_sprite.center_x = self.physics_sprite.center_x + x_off
        self.player_sprite.center_y = self.physics_sprite.center_y + y_off

    # ------------------------------------------------------------------ level

    def _tile_for(self, char, row_idx, col_idx, map_grid):
        """Pick the right tile image so terrain connects into one smooth mass.

        The block at the TOP of a stack uses a "surface" (frosting) tile; blocks
        below it use a seamless "fill" tile. That's why a pillar looks like a
        capped mound instead of separate boxes.
        """
        if char in ("B", "X"):                 # X = passable fake wall, drawn as terrain
            above = map_grid[row_idx - 1][col_idx] if row_idx > 0 else " "
            # surface if nothing solid sits above this tile, else fill
            pool = TERRAIN_SURFACE if above not in ("B", "X") else TERRAIN_FILL
        elif char == "F":
            pool = PLATFORM_F_TILES
        elif char == "H":
            pool = PLATFORM_H_TILES
        else:
            return TILE_CHARS.get(char)
        return pool[col_idx % len(pool)]

    def _build_level(self, map_grid):
        """Turn a text grid into real tile sprites; return the spawn point.

        Walks every character of the map. Empty spaces are skipped, 'P' records
        where the player starts, and every other letter becomes a tile sprite
        placed in the right sprite list (wall / platform / decor).
        """
        total_rows = len(map_grid)
        spawn = None
        for row_idx, row in enumerate(map_grid):
            for col_idx, char in enumerate(row):
                if char == " ":
                    continue                       # empty sky, nothing to draw
                # Convert grid (col, row) into pixel coordinates. Note the map's
                # top row is the SKY, but pixel Y grows upward, so we flip rows.
                x = col_idx * TILE_SIZE + TILE_SIZE // 2
                y = (total_rows - 1 - row_idx) * TILE_SIZE + TILE_SIZE // 2
                if char == "P":
                    spawn = (x, y + TILE_SIZE)      # start one tile above the mark
                    continue
                filename = self._tile_for(char, row_idx, col_idx, map_grid)
                if not filename:
                    continue
                try:
                    sprite = arcade.Sprite(f"{KENNEY_TILES}/{filename}", TILE_SCALE)
                except Exception:
                    # Art missing? Fall back to a plain coloured square.
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
                # File the tile into the list that matches how it behaves.
                # Solid + platform tiles also go in _ground_tile_set so the
                # slimes can sense the floor without a physics engine.
                if char in WALL_TILES:
                    self.wall_list.append(sprite)
                    self._ground_tile_set.add((x, y))
                elif char in PLATFORM_TILES:
                    self.platform_list.append(sprite)
                    self._ground_tile_set.add((x, y))
                elif char in DECOR_TILES:           # X fake wall: drawn, no collision
                    self.decor_list.append(sprite)
        return spawn

    # --------------------------------------------------------------- UI panels
    # Each of these builds one full-screen overlay out of arcade.gui widgets:
    #   UIBoxLayout    = stack widgets vertically/horizontally
    #   UILabel        = a line of text
    #   UIFlatButton   = a clickable button (.event("on_click") sets what it does)
    #   UIAnchorLayout = centre the whole stack on screen
    # The little `lambda e: ...` is just "when clicked, call this method".

    def _build_death_panel(self):
        """The 'YOU DIED' screen: restart the level or go to the menu."""
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
        """The 'LEVEL X COMPLETE' screen: go to the next level."""
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
        """The 'CONGRATULATIONS' screen shown after beating the final level."""
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
        """The main menu: New Game / Continue / Choose Level."""
        v_box = arcade.gui.UIBoxLayout(vertical=True, space_between=18)
        v_box.add(arcade.gui.UILabel(text="WOK OF THE WARRIOR", font_size=56, text_color=(255, 215, 0, 255)))
        # Build the three buttons from a list so they all look the same.
        for text, action in [
            ("NEW GAME",      self._new_game),
            ("CONTINUE GAME", self._continue_game),
            ("CHOOSE LEVEL",  self._show_level_select),
        ]:
            btn = arcade.gui.UIFlatButton(text=text, width=320, height=58)
            # `a=action` captures THIS loop's action (avoids the classic
            # "all buttons call the last action" closure bug).
            btn.event("on_click")(lambda e, a=action: a())
            v_box.add(btn)
        panel = arcade.gui.UIAnchorLayout()
        panel.add(child=v_box, anchor_x="center_x", anchor_y="center_y")
        return panel

    def _build_level_select_panel(self):
        """A grid of numbered buttons, one per level, plus a Back button."""
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
        """Build a whole level from scratch and start playing it.

        This is the big "reset" — it throws away the old level's sprites and
        creates fresh ones: background, tiles, enemies, boss, the burger, the
        player's position, the physics engine, the UI panels, and the timer.
        Called by New Game, Continue, Choose Level, Next Level and Restart.
        """
        W, H = self.width, self.height          # screen size (shorthand)
        self.current_level = level_num
        level_data         = LEVELS[self.current_level]
        map_grid           = level_data["grid"]
        self.level_width   = len(map_grid[0]) * TILE_SIZE   # total level width in px
        level_height       = len(map_grid) * TILE_SIZE
        total_rows         = len(map_grid)

        # Fresh UI manager so old menu/death buttons don't linger.
        self.ui_manager.disable()
        self.ui_manager = arcade.gui.UIManager()
        self.ui_manager.enable()

        # Empty sprite lists to fill with this level's contents.
        self.bg_sprites       = arcade.SpriteList()
        self._ground_tile_set = set()
        self.wall_list        = arcade.SpriteList(use_spatial_hash=True)  # spatial hash = faster collisions
        self.platform_list    = arcade.SpriteList(use_spatial_hash=True)
        self.decor_list       = arcade.SpriteList()
        self.enemy_list       = arcade.SpriteList()
        self.boss_list        = arcade.SpriteList()
        self.boss             = None
        self.powerup_list     = arcade.SpriteList()
        self.powerup          = None
        self.invincible       = False

        # Tile the background image across the whole (wide) level so it repeats.
        if self.bg_texture is not None:
            bw, bh = self.bg_texture.width, self.bg_texture.height
            for row in range(math.ceil(H / bh) + 1):
                for col in range(math.ceil(self.level_width / bw) + 1):
                    s = arcade.Sprite()
                    s.texture  = self.bg_texture
                    s.center_x = col * bw + bw / 2
                    s.center_y = row * bh + bh / 2
                    self.bg_sprites.append(s)

        # Build the tiles from the text grid; remember the spawn point.
        spawn = self._build_level(map_grid)
        self.spawn_x = spawn[0] if spawn else TILE_SIZE * 2
        self.spawn_y = spawn[1] if spawn else level_height // 2

        # Invisible walls at the far left/right edges so you can't walk off.
        for cx, cy, ww, hh in [
            (-10, level_height, 20, level_height * 4),
            (self.level_width + 10, level_height, 20, level_height * 4),
        ]:
            b = arcade.SpriteSolidColor(ww, hh, arcade.color.WHITE)
            b.alpha = 0; b.center_x = cx; b.center_y = cy   # alpha 0 = invisible
            self.wall_list.append(b)

        # Spawn this level's slimes. Each one has a stable id "level:index";
        # if it's in self._defeated we skip it (it was killed and shouldn't
        # come back when resuming a save).
        for idx, (col, floor_row, stype) in enumerate(level_data["enemies"]):
            eid = f"{self.current_level}:{idx}"
            if eid in self._defeated:
                continue   # already killed in a previous session — stay dead
            ex = col * TILE_SIZE + TILE_SIZE // 2
            floor_top = (total_rows - 1 - floor_row) * TILE_SIZE + TILE_SIZE
            if stype in self.slime_textures:           # codes 1/2/3 = slimes
                ey = floor_top + int(SLIME_SCALE * SLIME_FOOT_OFFSET)   # sit on the floor
                wr, wl, dr, dl = self.slime_textures[stype]
                self.enemy_list.append(SlimeEnemy(ex, ey, wr, wl, dr, dl, eid))
            elif stype in self.monster_anims:          # codes 4/5/6 = monsters
                ey = floor_top + (MONSTER_FRAME * MonsterEnemy.SCALE) / 2 - 3   # feet on floor
                self.enemy_list.append(MonsterEnemy(ex, ey, self.monster_anims[stype], eid))

        # If this level has a boss (only level 10), place it on the ground.
        boss_col = level_data.get("boss_col")
        if boss_col is not None and self.boss_anims:
            bx = boss_col * TILE_SIZE + TILE_SIZE // 2
            floor_top = (total_rows - 1 - 13) * TILE_SIZE + TILE_SIZE
            by = floor_top + (128 * BossNinja.SCALE) / 2   # feet sit on the ground
            self.boss = BossNinja(bx, by, self.boss_anims)
            self.boss_list.append(self.boss)

        # Secret invincibility burger (also level 10), hidden inside a fake wall.
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

        # Drop the player's collision box at the spawn point, standing still.
        self.physics_sprite.center_x = self.spawn_x
        self.physics_sprite.center_y = self.spawn_y
        self.physics_sprite.change_x = 0
        self.physics_sprite.change_y = 0

        # The physics engine applies gravity to the player and stops it from
        # passing through walls; platforms are one-way (land on top only).
        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.physics_sprite, gravity_constant=GRAVITY,
            walls=self.wall_list, platforms=self.platform_list,
        )

        # Centre the camera to start.
        self._cam_cx = W / 2
        self._cam_cy = H / 2
        self.camera.position = (round(self._cam_cx), round(self._cam_cy))

        # Reset the player's animation + appearance.
        self.cur_texture   = 0
        self.frame_counter = 0
        self.facing_right  = True
        self.attacking     = None
        self.current_anim  = "idle_right"
        self.player_sprite.texture = self.idle_textures_right[0]
        self.player_sprite.color   = (255, 255, 255)   # clear any invincible tint
        self._sync_player_sprite()

        # Rebuild the overlay panels (their text depends on the current level).
        self._death_panel          = self._build_death_panel()
        self._level_complete_panel = self._build_level_complete_panel()
        self._game_won_panel       = self._build_game_won_panel()
        self.time_remaining = 60.0
        self.game_state = "playing"
        self._start_bg_music()      # normal theme (resets boss theme on restart)

    # ------------------------------------------------------------------ setup

    def setup(self):
        """Load everything ONCE at startup, then open the main menu.

        main.py calls this right after creating the window. It loads images and
        sounds (slow, so we only do it once), creates the player + cameras, then
        shows the menu instead of jumping straight into a level.
        """
        # Background image (None if it fails to load — the game still runs).
        try:
            self.bg_texture = arcade.load_texture(BG_IMAGE)
        except Exception:
            self.bg_texture = None

        # Sword swing sound.
        self.slash_draw = self._try_load_sound(
            HERE / "assets/sounds/484298__giddster__drawing-sword-from-scabbard.wav"
        )

        # Player animation sheets. The number is how many frames each sheet has.
        self.idle_textures_right, self.idle_textures_left = self._load_sheet("Idle.png", 6)
        self.walk_textures_right, self.walk_textures_left = self._load_sheet("Walk.png", 9)
        self.jump_textures_right, self.jump_textures_left = self._load_sheet("Jump.png", 9)
        self.dead_textures_right, self.dead_textures_left = self._load_sheet("Dead.png", 6)
        for i, n in enumerate([4, 5, 4]):       # the 3 attack combos (4/5/4 frames)
            self.attack_textures_right[i], self.attack_textures_left[i] = \
                self._load_sheet(f"Attack_{i+1}.png", n)

        # Boss uses the Samurai Commander character sheets (different frame counts).
        self.boss_anims = {
            "idle":   self._load_sheet("Idle.png", 5, BOSS_PATH),
            "run":    self._load_sheet("Run.png", 8, BOSS_PATH),
            "attack": self._load_sheet("Attack_2.png", 5, BOSS_PATH),
            "hurt":   self._load_sheet("Hurt.png", 2, BOSS_PATH),
            "dead":   self._load_sheet("Dead.png", 6, BOSS_PATH),
        }

        self._load_slime_textures()
        self._load_monster_textures()

        # The player's collision box: a small, fully transparent rectangle that
        # the physics engine moves around. The visible samurai is drawn on top.
        self.physics_sprite = arcade.SpriteSolidColor(PHYS_W, PHYS_H, arcade.color.WHITE)
        self.physics_sprite.alpha = 0           # invisible

        self.player_list   = arcade.SpriteList()
        self.player_sprite = arcade.Sprite()
        self.player_sprite.texture = self.idle_textures_right[0]
        self.player_sprite.scale   = CHARACTER_SCALING
        self.player_list.append(self.player_sprite)

        self.camera     = arcade.Camera2D()     # scrolls with the player
        self.hud_camera = arcade.Camera2D()     # stays put for on-screen text

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
        """After Continue, drop the player at their saved spot (used by _continue_game)."""
        x = float(saved.get("position_x", self.spawn_x))
        y = float(saved.get("position_y", self.spawn_y))
        # Clamp X inside the level, and ignore a below-the-floor Y.
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

        # Snap the camera onto the restored position.
        cam_left = max(0.0, min(x - self.width // 3, self.level_width - self.width))
        self._cam_cx = cam_left + self.width / 2
        self.camera.position = (round(self._cam_cx), round(self._cam_cy))

    def _persist_progress(self, sync=False):
        """Save the current progress (level, position, kills, timer).

        sync=False -> save on a background thread (used for autosave, no stutter).
        sync=True  -> save right now and wait (used when quitting).
        """
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
        """Arcade calls this when the window closes — save before quitting."""
        self._persist_progress(sync=True)
        super().on_close()

    # ------------------------------------------------------------------ state
    # Methods that change game_state: dying, finishing a level, winning, etc.

    def _trigger_death(self):
        """Kill the player: start the death animation (then the death screen).

        Does nothing if not currently playing, or if the secret burger made the
        player invincible — that's how invincibility blocks all deaths at once.
        """
        if self.game_state != "playing" or self.invincible:
            return
        # Play the player's death animation first; the panel shows when it ends.
        self.game_state = "player_dying"
        self.physics_sprite.change_x = 0       # freeze in place
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
            return                               # not time for the next frame yet
        self.frame_counter = 0
        frames = self.dead_textures_right if self.facing_right else self.dead_textures_left
        self.cur_texture += 1
        if self.cur_texture >= len(frames):      # animation finished
            self.player_sprite.texture = frames[-1]
            self.game_state = "dead"
            self.ui_manager.add(self._death_panel)   # show "YOU DIED"
        else:
            self.player_sprite.texture = frames[self.cur_texture]

    def _trigger_level_complete(self):
        """Reached the end of a level: show 'complete', or 'you won' if it was the last."""
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
        """Forget this level's kills so its enemies spawn fresh again.

        self._defeated holds ids like "3:0". This drops the ones for `level`.
        """
        prefix = f"{level}:"
        self._defeated = {e for e in self._defeated if not e.startswith(prefix)}

    def _restart(self):
        """Replay the current level (used by the death/restart screens)."""
        # Respawn this level's enemies whenever the *player* respawns. Kills
        # still survive a full game stop because we only clear them on a restart
        # or level entry, not on load — so quitting mid-level keeps them dead.
        self._respawn_enemies(self.current_level)
        self._load_level(self.current_level)

    def _advance_level(self):
        """Go to the next level (loops back to 1 after the last)."""
        next_num = (self.current_level % len(LEVELS)) + 1   # 1->2, ..., 10->1
        # Entering a new level repopulates it with enemies.
        self._respawn_enemies(next_num)
        self._load_level(next_num)
        self._persist_progress()

    # ------------------------------------------------------------------ menu
    # The menu/level-select screens and the buttons on them.

    def _reset_ui(self):
        """Swap in a brand-new UI manager (clears whatever panel was showing)."""
        self.ui_manager.disable()
        self.ui_manager = arcade.gui.UIManager()
        self.ui_manager.enable()

    def _show_main_menu(self):
        """Switch to the main menu screen."""
        self.game_state = "menu"
        self.boss = None                # forget any boss from a previous run
        self._start_bg_music()          # normal theme on the menu
        self._reset_ui()
        self.ui_manager.add(self._build_main_menu_panel())

    def _show_level_select(self):
        """Switch to the 'Choose Level' screen."""
        self.game_state = "level_select"
        self._reset_ui()
        self.ui_manager.add(self._build_level_select_panel())

    def _new_game(self):
        """Fresh run from level 1 (clears all defeated-enemy memory)."""
        self._defeated = set()
        self._load_level(1)
        self._persist_progress()

    def _continue_game(self):
        """Resume from the saved progress (or start fresh if there is none)."""
        saved = save_client.load_progress()
        if saved and saved.get("current_level") in LEVELS:
            self._defeated = set(saved.get("defeated_enemies", []))
            self._load_level(int(saved["current_level"]))
            self._restore_position(saved)   # also restore exact spot + timer
        else:
            self._new_game()                # nothing saved -> just start over

    def _choose_level(self, level_num):
        """Start fresh from a chosen level (from the Choose Level screen)."""
        self._respawn_enemies(level_num)
        self._load_level(level_num)
        self._persist_progress()

    # ------------------------------------------------------------------ combat
    # Working out who hits whom each frame: the player vs slimes, and vs the boss.

    def _defeat(self, enemy):
        """Mark a slime as killed and start its death animation."""
        if enemy.eid is not None:
            self._defeated.add(enemy.eid)     # remember it so it stays dead
        enemy.start_death()        # removed once the animation finishes
        self._persist_progress()   # record the kill in the background

    def _check_enemy_collisions(self):
        """Resolve the player touching slimes, and the player's sword hitting them."""
        player_bottom = self.physics_sprite.center_y - PHYS_H / 2
        # 1) Body contact: jumping on top kills the slime; otherwise it kills you.
        for enemy in list(self.enemy_list):
            if enemy.dying:
                continue           # already defeated, just animating
            if not arcade.check_for_collision(self.physics_sprite, enemy):
                continue
            if self.physics_sprite.change_y <= 0 and player_bottom >= enemy.center_y:
                self._defeat(enemy)                      # stomp from above
                self.physics_sprite.change_y = JUMP_SPEED * 0.7   # little bounce
            elif self.invincible:
                self._defeat(enemy)          # plow straight through while invincible
            else:
                self._trigger_death()        # walked into it -> die
                return
        # 2) Sword: if mid-swing, kill any slime within reach in front of you.
        if self.attacking is not None:
            px, py = self.physics_sprite.center_x, self.physics_sprite.center_y
            y_tol  = SWORD_REACH_Y + PHYS_H / 2 + SLIME_SCALE * SLIME_FRAME_H / 2
            for enemy in list(self.enemy_list):
                if enemy.dying:
                    continue
                dx = enemy.center_x - px                 # +ve = to the right
                if abs(enemy.center_y - py) < y_tol:     # roughly same height
                    if self.facing_right and 0 < dx < SWORD_REACH_X:
                        self._defeat(enemy)
                    elif not self.facing_right and -SWORD_REACH_X < dx < 0:
                        self._defeat(enemy)

    def _update_boss(self, dt):
        """Run the boss fight for one frame: move the boss, trade hits."""
        boss = self.boss
        px, py = self.physics_sprite.center_x, self.physics_sprite.center_y
        boss.update_boss(px, py, dt)     # let the boss think/move first

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
            return                       # no trading hits while it dies

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
        """Paint the whole screen. Arcade calls this every frame after on_update.

        Order matters: things drawn later appear ON TOP. The burger is drawn
        before the decor (fake wall) so the wall hides it — that's the secret.
        The player is drawn last so nothing covers it.
        """
        self.clear()                     # wipe last frame

        # Menu screens: no level is loaded, so just draw the backdrop + UI.
        if self.game_state in ("menu", "level_select"):
            self.hud_camera.use()
            if self._menu_bg_list is not None:
                self._menu_bg_list.draw(pixelated=True)
            self.ui_manager.draw()
            return

        # --- the game world (through the scrolling camera) ------------------
        self.camera.use()
        # pixelated=True -> nearest-neighbour sampling: crisp pixels and no
        # seams bleeding between adjacent terrain tiles.
        self.bg_sprites.draw(pixelated=True)
        self.enemy_list.draw(pixelated=True)
        if self.boss_list is not None:
            self.boss_list.draw(pixelated=True)
        if self.powerup_list is not None:
            self.powerup_list.draw(pixelated=True)   # burger (hidden by decor)
        self.wall_list.draw(pixelated=True)
        self.platform_list.draw(pixelated=True)
        self.decor_list.draw(pixelated=True)         # fake wall over the burger
        self.player_list.draw(pixelated=True)

        # --- the HUD timer (fixed camera so it doesn't scroll) --------------
        self.hud_camera.use()
        secs = int(self.time_remaining)
        self._timer_text.text = f"{secs // 60}:{secs % 60:02d}"   # M:SS
        if self.time_remaining <= 10:               # colour-code as it runs out
            self._timer_text.color = arcade.color.RED
        elif self.time_remaining <= 20:
            self._timer_text.color = arcade.color.ORANGE
        else:
            self._timer_text.color = arcade.color.WHITE
        self._timer_text.draw()

        # On the end-of-state screens, draw the overlay panel on top.
        if self.game_state in ("dead", "level_complete", "game_won"):
            self.ui_manager.draw()

    # ------------------------------------------------------------------ input
    # Arcade calls on_key_press when a key goes down, on_key_release when it
    # comes up. We check game_state first so a key does the right thing in each
    # situation (e.g. ENTER = "next level" on the complete screen, nothing in a
    # menu since menus use the mouse).

    def on_key_press(self, key, modifiers):
        # ESC always quits (saving first, unless we're on a menu with no level).
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

        # --- normal gameplay keys ------------------------------------------
        # Attack: start one of the 3 swing animations (if not already swinging).
        if key in ATTACK_KEYS:
            if self.attacking is None:
                self.attacking = ATTACK_KEYS[key]
                self.cur_texture = self.frame_counter = 0
                self._attack_hit_boss = False      # this swing hasn't hit the boss yet
                self._play_attack_sound()
            return
        # Jump (only if standing on something), or move left/right.
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
        # Let go of left/right -> stop moving horizontally.
        if key in (arcade.key.LEFT, arcade.key.A, arcade.key.RIGHT, arcade.key.D):
            self.physics_sprite.change_x = 0

    # ------------------------------------------------------------------ update

    def on_update(self, delta_time):
        """The game's heartbeat — Arcade calls this ~60x/sec. `delta_time` is
        the seconds since the last call. This is where all movement and game
        logic happens (drawing is separate, in on_draw)."""
        # If the player is mid-death-animation, only advance that and stop.
        if self.game_state == "player_dying":
            self._update_player_death()
            return
        # On menus / dead / complete / won screens there's no gameplay to run.
        if self.game_state != "playing":
            return

        # Apply gravity + collisions to the player's box.
        self.physics_engine.update()

        # Keep the player inside the level horizontally.
        self.physics_sprite.center_x = max(
            PHYS_W / 2,
            min(self.level_width - PHYS_W / 2, self.physics_sprite.center_x),
        )

        self._update_animation()         # pick the right player frame
        self._sync_player_sprite()       # move the visible sprite onto the box

        # Secret burger: grab it to become invincible for the rest of the run.
        if self.powerup is not None and arcade.check_for_collision(self.physics_sprite, self.powerup):
            self.powerup.remove_from_sprite_lists()
            self.powerup = None
            self.invincible = True
            self.player_sprite.color = (255, 215, 0)   # golden glow

        # Death by falling into a pit (skipped if invincible).
        if self.physics_sprite.center_y < DEATH_Y and not self.invincible:
            self._trigger_death()
            return
        # Reaching the right edge finishes the level — EXCEPT on the boss level,
        # where you must defeat the boss instead.
        if self.boss is None and self.physics_sprite.center_x >= self.level_width - TILE_SIZE * 2:
            self._trigger_level_complete()
            return

        # Count down the timer; running out kills you (unless invincible).
        self.time_remaining -= delta_time
        if self.time_remaining <= 0.0:
            self.time_remaining = 0.0
            if not self.invincible:
                self._trigger_death()
                return

        # Update enemies. Only the ones near the screen move (saves work); dying
        # ones play their animation and are removed when it finishes. The player
        # position is passed so the monsters can chase/attack (slimes ignore it).
        ppx, ppy = self.physics_sprite.center_x, self.physics_sprite.center_y
        screen_left  = self._cam_cx - self.width  / 2 - TILE_SIZE * 4
        screen_right = self._cam_cx + self.width  / 2 + TILE_SIZE * 4
        for enemy in list(self.enemy_list):
            if enemy.dying:
                if enemy.update_death():
                    enemy.remove_from_sprite_lists()
            elif screen_left <= enemy.center_x <= screen_right:
                enemy.update_patrol(self._ground_tile_set, ppx, ppy)

        # Resolve player <-> slime hits. May trigger death, so re-check state.
        self._check_enemy_collisions()
        if self.game_state != "playing":
            return

        # Run the boss fight if there's a boss. May also trigger death/win.
        if self.boss is not None:
            self._update_boss(delta_time)
            if self.game_state != "playing":
                return

        # Scroll the camera so the player sits about 1/3 from the left edge,
        # clamped so it never shows past the ends of the level.
        cam_left     = self.physics_sprite.center_x - self.width // 3
        cam_left     = max(0.0, min(cam_left, self.level_width - self.width))
        self._cam_cx = cam_left + self.width  / 2
        self._cam_cy =            self.height / 2
        # Snap to whole pixels so tiles never render with sub-pixel seams.
        self.camera.position = (round(self._cam_cx), round(self._cam_cy))

        # Autosave every few seconds (on a background thread, so no stutter).
        self._save_timer += delta_time
        if self._save_timer >= AUTOSAVE_INTERVAL:
            self._save_timer = 0.0
            self._persist_progress()

    def _update_animation(self):
        """Pick the player's current frame: jump, attack, walk, or idle.

        Most animations run slower than the game: we only advance to the next
        frame once every UPDATES_PER_FRAME game ticks (counted by frame_counter).
        Jumping is the exception — its frame is chosen from how fast the player
        is rising/falling, so it's picked every frame for responsiveness.
        """
        # Airborne (and not mid-attack): show a jump pose based on velocity.
        # can_jump() is False when the player isn't standing on anything.
        if (self.attacking is None and self.physics_engine is not None
                and self.jump_textures_right
                and not self.physics_engine.can_jump()):
            frames = self.jump_textures_right if self.facing_right else self.jump_textures_left
            vy = self.physics_sprite.change_y          # + = rising, - = falling
            if   vy >  14: idx = 2     # just launched, rising fast
            elif vy >   5: idx = 3     # rising
            elif vy >  -5: idx = 4     # apex (hanging at the top)
            elif vy > -14: idx = 5     # falling
            else:          idx = 6     # falling fast
            idx = min(idx, len(frames) - 1)            # safety for short sheets
            self.current_anim = "jump_right" if self.facing_right else "jump_left"
            self.player_sprite.texture = frames[idx]
            return

        self.frame_counter += 1
        if self.frame_counter < UPDATES_PER_FRAME:
            return                       # not time for the next frame yet
        self.frame_counter = 0
        self.cur_texture  += 1           # move to the next frame index

        # If an attack is playing, it takes priority over walk/idle.
        if self.attacking is not None:
            frames = (self.attack_textures_right if self.facing_right
                      else self.attack_textures_left)[self.attacking]
            if self.cur_texture >= len(frames):
                # Attack finished -> go back to walking or standing.
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

        # Not attacking: choose walk frames if moving, else idle frames.
        is_walking = self.physics_sprite.change_x != 0
        if self.facing_right:
            frames   = self.walk_textures_right if is_walking else self.idle_textures_right
            anim_key = "walk_right"             if is_walking else "idle_right"
        else:
            frames   = self.walk_textures_left  if is_walking else self.idle_textures_left
            anim_key = "walk_left"              if is_walking else "idle_left"

        # If the animation just changed (e.g. idle->walk), restart at frame 0.
        if anim_key != self.current_anim:
            self.current_anim = anim_key
            self.cur_texture  = 0

        # Loop the frame index around the length of the list, then show it.
        self.cur_texture %= len(frames)
        self.player_sprite.texture = frames[self.cur_texture]
        
        