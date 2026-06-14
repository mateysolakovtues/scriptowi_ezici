import arcade
from constants import SLIME_SCALE, SLIME_PATROL, SLIME_FOOT_OFFSET, TILE_SIZE


class SlimeEnemy(arcade.Sprite):
    ANIM_RATE  = 7
    DEATH_RATE = 4   # ticks per death frame

    def __init__(self, x, y, walk_right, walk_left,
                 death_right=None, death_left=None, eid=None):
        super().__init__()
        self.eid          = eid         # stable "level:index" id for save tracking
        self._walk_right  = walk_right
        self._walk_left   = walk_left
        self._death_right = death_right or walk_right
        self._death_left  = death_left or walk_left
        self.texture      = walk_right[0]
        self.scale        = SLIME_SCALE
        self.center_x     = x
        self.center_y     = y
        self._spawn_x     = x
        self.change_x     = 0.9
        self._frame       = 0
        self._tick        = 0

        self.dying        = False
        self._death_frames = None
        self._dframe      = 0
        self._dtick       = 0

    def start_death(self):
        """Begin the death animation; the slime stops moving and plays it out."""
        self.dying = True
        facing_right = self.change_x >= 0
        self.change_x = 0
        self._death_frames = self._death_right if facing_right else self._death_left
        self._dframe = 0
        self._dtick = 0
        self.texture = self._death_frames[0]

    def update_death(self):
        """Advance the death animation. Returns True once it has finished."""
        self._dtick += 1
        if self._dtick >= self.DEATH_RATE:
            self._dtick = 0
            self._dframe += 1
            if self._dframe >= len(self._death_frames):
                return True
            self.texture = self._death_frames[self._dframe]
        return False

    def update_patrol(self, ground_tile_set):
        lead = 1 if self.change_x >= 0 else -1

        # Cliff check: is there still ground under the step we're about to take?
        cliff_x = self.center_x + lead * SLIME_SCALE * 20
        cliff_y = self.center_y - int(SLIME_SCALE * SLIME_FOOT_OFFSET) - 4
        cliff_tx = int(cliff_x // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
        cliff_ty = int(cliff_y // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
        cliff_ahead = (cliff_tx, cliff_ty) not in ground_tile_set

        # Wall check: is there a solid tile at body height blocking the path?
        wall_x = self.center_x + lead * (TILE_SIZE * 0.8)
        wall_tx = int(wall_x // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
        wall_ty = int(self.center_y // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
        wall_ahead = (wall_tx, wall_ty) in ground_tile_set

        if cliff_ahead or wall_ahead:
            # Blocked: turn around and don't step this frame so we never overlap.
            self.change_x *= -1
        else:
            self.center_x += self.change_x
            if abs(self.center_x - self._spawn_x) >= SLIME_PATROL:
                self.change_x *= -1

        self._tick += 1
        if self._tick >= self.ANIM_RATE:
            self._tick  = 0
            self._frame = (self._frame + 1) % len(self._walk_right)
            frames      = self._walk_right if self.change_x >= 0 else self._walk_left
            self.texture = frames[self._frame]


class BossNinja(arcade.Sprite):
    """End-of-game boss: chases the player, swings its weapon, and takes 5 hits.

    It fights in a readable rhythm — close in, do a single telegraphed swing
    (only the swing is lethal), then recover for a beat (during which it can be
    hit safely) before attacking again.

    `anims` maps a state name to a (right_frames, left_frames) pair:
    'idle', 'run', 'attack', 'hurt', 'dead'.
    """
    MAX_HP         = 5
    SPEED          = 1.8
    ACTIVATE_DIST  = 750    # starts chasing once the player is this close
    ATTACK_RANGE   = 120    # closes to here, then swings
    ATTACK_HIT_RANGE = 135  # the swing is only lethal within this reach
    ATTACK_COOLDOWN = 1.6   # seconds between swings
    RECOVER_TIME    = 0.8   # vulnerable pause after a swing
    ANIM_RATE      = 5
    DEATH_RATE     = 8
    HURT_TIME      = 0.4    # seconds of invulnerability / flinch after a hit
    SCALE          = 2.8

    def __init__(self, x, y, anims):
        super().__init__()
        self._anim = anims
        self.scale = self.SCALE
        self.center_x = x
        self.center_y = y
        self.hp = self.MAX_HP
        self.state = "idle"     # idle | chase | attack | recover | hurt | dying | dead
        self.facing_right = False
        self._tick = 0
        self._frame = 0
        self._invuln = 0.0
        self._attack_cd = self.ATTACK_COOLDOWN   # don't swing the instant you arrive
        self._recover = 0.0
        self.texture = anims["idle"][1][0]

    @property
    def attacking(self):
        # Only the actual swing is dangerous to touch.
        return self.state == "attack"

    def _frames(self, state):
        right, left = self._anim[state]
        return right if self.facing_right else left

    def _advance(self, state, loop, rate):
        """Step the animation for `state`. Returns True when a one-shot ends."""
        frames = self._frames(state)
        self._tick += 1
        if self._tick < rate:
            self.texture = frames[min(self._frame, len(frames) - 1)]
            return False
        self._tick = 0
        self._frame += 1
        if self._frame >= len(frames):
            if loop:
                self._frame = 0
            else:
                self._frame = len(frames) - 1
                self.texture = frames[self._frame]
                return True
        self.texture = frames[self._frame]
        return False

    def hit(self):
        """Apply one hit. Returns True if it was the killing blow."""
        if self.state in ("dying", "dead") or self._invuln > 0:
            return False
        self.hp -= 1
        self._invuln = self.HURT_TIME
        self._frame = 0
        self._tick = 0
        self.state = "dying" if self.hp <= 0 else "hurt"
        return self.hp <= 0

    def update_boss(self, player_x, player_y, dt):
        if self.state == "dead":
            return
        if self._invuln > 0:
            self._invuln -= dt

        if self.state == "dying":
            if self._advance("dead", loop=False, rate=self.DEATH_RATE):
                self.state = "dead"
            return
        if self.state == "hurt":
            if self._advance("hurt", loop=False, rate=self.ANIM_RATE):
                self.state = "chase"
            return

        dx = player_x - self.center_x
        dist = abs(dx)
        if dist > 1:
            self.facing_right = dx > 0
        step = 1 if dx > 0 else -1

        # Mid-swing: finish the (stationary) attack, then drop into recovery.
        if self.state == "attack":
            if self._advance("attack", loop=False, rate=self.ANIM_RATE):
                self.state = "recover"
                self._recover = self.RECOVER_TIME
                self._attack_cd = self.ATTACK_COOLDOWN
            return

        # Recovering: stand still and vulnerable for a beat.
        if self._recover > 0:
            self._recover -= dt
            self.state = "recover"
            self._advance("idle", loop=True, rate=self.ANIM_RATE)
            return
        if self._attack_cd > 0:
            self._attack_cd -= dt

        if dist > self.ACTIVATE_DIST:
            self.state = "idle"
            self._advance("idle", loop=True, rate=self.ANIM_RATE)
        elif dist <= self.ATTACK_RANGE and self._attack_cd <= 0:
            # Start a single telegraphed swing (no forward lunge — easy to dodge).
            self.state = "attack"
            self._frame = 0
            self._tick = 0
            self._advance("attack", loop=False, rate=self.ANIM_RATE)
        else:
            # Close the gap, but stop just outside attack range.
            self.state = "chase"
            if dist > self.ATTACK_RANGE * 0.9:
                self.center_x += self.SPEED * step
            self._advance("run", loop=True, rate=self.ANIM_RATE)
