# ===========================================================================
# enemy.py  —  the enemy types.
# ---------------------------------------------------------------------------
#   SlimeEnemy   : the small patrolling slimes (most of the levels)
#   MonsterEnemy : faster monsters that chase the player and attack (levels 4-10)
#   BossNinja    : the Samurai Commander boss at the end of level 10
# All are arcade.Sprite subclasses, meaning each one IS a drawable sprite that
# also carries its own movement/animation logic.
# ===========================================================================
import arcade
from constants import SLIME_SCALE, SLIME_PATROL, SLIME_FOOT_OFFSET, TILE_SIZE, MONSTER_FRAME


class SlimeEnemy(arcade.Sprite):
    """A slime that walks back and forth, turning at cliffs and walls.

    It holds two sets of animation frames (walking, dying), each in a
    right-facing and a flipped left-facing version.
    """
    ANIM_RATE  = 7   # game ticks between walk frames (higher = slower wobble)
    DEATH_RATE = 4   # game ticks between death frames

    def __init__(self, x, y, walk_right, walk_left,
                 death_right=None, death_left=None, eid=None):
        super().__init__()
        self.eid          = eid         # stable "level:index" id for save tracking
        self._walk_right  = walk_right  # list of textures, facing right
        self._walk_left   = walk_left   # same frames, mirrored
        self._death_right = death_right or walk_right
        self._death_left  = death_left or walk_left
        self.texture      = walk_right[0]   # start on the first walk frame
        self.scale        = SLIME_SCALE
        self.center_x     = x
        self.center_y     = y
        self._spawn_x     = x           # remembered so it patrols around here
        self.change_x     = 0.9         # current horizontal speed (+ = right)
        self._frame       = 0           # which walk frame we're showing
        self._tick        = 0           # counts up to ANIM_RATE, then advances

        # Death-animation bookkeeping (unused until the slime is killed).
        self.dying        = False
        self._death_frames = None
        self._dframe      = 0
        self._dtick       = 0

    def start_death(self):
        """Begin the death animation; the slime stops moving and plays it out."""
        self.dying = True
        facing_right = self.change_x >= 0           # remember which way it faced
        self.change_x = 0                           # freeze in place
        self._death_frames = self._death_right if facing_right else self._death_left
        self._dframe = 0
        self._dtick = 0
        self.texture = self._death_frames[0]

    def update_death(self):
        """Advance the death animation. Returns True once it has finished."""
        self._dtick += 1
        if self._dtick >= self.DEATH_RATE:          # time for the next frame?
            self._dtick = 0
            self._dframe += 1
            if self._dframe >= len(self._death_frames):
                return True                         # animation done -> remove me
            self.texture = self._death_frames[self._dframe]
        return False

    def update_patrol(self, ground_tile_set, player_x=None, player_y=None):
        """Walk one step; turn around at the edge of a platform or at a wall.

        `ground_tile_set` is the set of (x, y) tile centres that are solid, so
        the slime can "feel" the floor ahead without a real physics engine.
        (player_x/player_y are accepted for a common call signature with the
        monsters, but slimes ignore the player — they just patrol.)
        """
        lead = 1 if self.change_x >= 0 else -1      # which way we're facing

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
            self.center_x += self.change_x          # take the step
            # Also turn around if we've wandered too far from where we spawned.
            if abs(self.center_x - self._spawn_x) >= SLIME_PATROL:
                self.change_x *= -1

        # Advance the walk animation every ANIM_RATE ticks, picking the frame
        # set that matches the direction we're now facing.
        self._tick += 1
        if self._tick >= self.ANIM_RATE:
            self._tick  = 0
            self._frame = (self._frame + 1) % len(self._walk_right)
            frames      = self._walk_right if self.change_x >= 0 else self._walk_left
            self.texture = frames[self._frame]


class MonsterEnemy(arcade.Sprite):
    """A fast monster: patrols, but chases the player on sight and attacks.

    Same "interface" as SlimeEnemy (eid, dying, start_death, update_death,
    update_patrol) so game.py can treat them the same way in collisions.

    `anims` is a dict of state -> (right_frames, left_frames) for
    'run', 'attack' and 'death'.
    """
    SCALE       = 3.0
    SPEED       = 2.4                 # noticeably faster than a slime (~0.9)
    DETECT_DIST = 340                 # chases the player within this x-distance
    ATTACK_DIST = 60                  # swings when this close
    Y_TOL       = 45                  # only if on roughly the same level
    PATROL      = TILE_SIZE * 4
    ANIM_RATE   = 6
    DEATH_RATE  = 5

    def __init__(self, x, y, anims, eid=None):
        super().__init__()
        self.eid = eid                # stable "level:index" id for save tracking
        self._anim = anims
        self.scale = self.SCALE
        self.center_x = x
        self.center_y = y
        self._spawn_x = x
        self.facing_right = True
        self._frame = 0
        self._tick = 0
        self.dying = False
        self.texture = anims["run"][0][0]

    # -- animation helpers (same pattern as the boss) ------------------------
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

    # -- death (same interface as the slime) ---------------------------------
    def start_death(self):
        self.dying = True
        self._frame = 0
        self._tick = 0
        self.texture = self._frames("death")[0]

    def update_death(self):
        """Advance the death animation; return True when it has finished."""
        return self._advance("death", loop=False, rate=self.DEATH_RATE)

    # -- "feel" the floor/walls ahead, like the slime does -------------------
    def _blocked(self, lead, ground_tile_set):
        """True if there's a cliff (no floor) or a wall just ahead."""
        foot = self.center_y - (MONSTER_FRAME * self.SCALE) / 2     # bottom of sprite
        # cliff: is there ground under the spot we'd step onto?
        cx = self.center_x + lead * (TILE_SIZE * 0.7)
        ctx = int(cx // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
        cty = int((foot - 6) // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
        if (ctx, cty) not in ground_tile_set:
            return True
        # wall: is a solid tile blocking us at knee height?
        wx = self.center_x + lead * (TILE_SIZE * 0.6)
        wtx = int(wx // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
        wty = int((foot + 20) // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
        return (wtx, wty) in ground_tile_set

    def update_patrol(self, ground_tile_set, player_x=None, player_y=None):
        """Move + animate one frame. Chases the player if seen, else patrols."""
        # Can we see the player? (same level, within detection range)
        sees = (player_x is not None
                and abs(player_y - self.center_y) < self.Y_TOL
                and abs(player_x - self.center_x) <= self.DETECT_DIST)

        if sees:
            self.facing_right = player_x > self.center_x
            lead = 1 if self.facing_right else -1
            if abs(player_x - self.center_x) <= self.ATTACK_DIST:
                # Right next to the player: swing in place.
                self._advance("attack", loop=True, rate=self.ANIM_RATE)
                return
            # Chase, but don't run off a ledge or into a wall.
            if not self._blocked(lead, ground_tile_set):
                self.center_x += self.SPEED * lead
            self._advance("run", loop=True, rate=self.ANIM_RATE)
            return

        # Default: patrol back and forth, turning at edges/walls/patrol limit.
        lead = 1 if self.facing_right else -1
        if self._blocked(lead, ground_tile_set) or \
                abs(self.center_x - self._spawn_x) >= self.PATROL:
            self.facing_right = not self.facing_right
        else:
            self.center_x += self.SPEED * lead
        self._advance("run", loop=True, rate=self.ANIM_RATE)


class BossNinja(arcade.Sprite):
    """End-of-game boss: chases the player, swings its weapon, and takes 5 hits.

    It fights in a readable rhythm — close in, do a single telegraphed swing
    (only the swing is lethal), then recover for a beat (during which it can be
    hit safely) before attacking again.

    `anims` maps a state name to a (right_frames, left_frames) pair:
    'idle', 'run', 'attack', 'hurt', 'dead'.
    """
    # --- tuning knobs (change these to make the boss easier/harder) ---------
    MAX_HP         = 5      # hits needed to kill it
    SPEED          = 1.8    # chase speed, pixels/frame (player is 5, so slower)
    ACTIVATE_DIST  = 750    # starts chasing once the player is this close
    ATTACK_RANGE   = 120    # closes to here, then swings
    ATTACK_HIT_RANGE = 135  # the swing is only lethal within this reach
    ATTACK_COOLDOWN = 1.6   # seconds between swings
    RECOVER_TIME    = 0.8   # vulnerable pause after a swing
    ANIM_RATE      = 5      # ticks between animation frames
    DEATH_RATE     = 8      # ticks between death frames (slower = more dramatic)
    HURT_TIME      = 0.4    # seconds of invulnerability / flinch after a hit
    SCALE          = 2.8    # drawn bigger than the player

    def __init__(self, x, y, anims):
        super().__init__()
        # `anims` is a dict: state name -> (right_frames, left_frames).
        self._anim = anims
        self.scale = self.SCALE
        self.center_x = x
        self.center_y = y
        self.hp = self.MAX_HP
        # The boss is a little state machine; this is its current state:
        self.state = "idle"     # idle | chase | attack | recover | hurt | dying | dead
        self.facing_right = False
        self._tick = 0          # animation tick counter
        self._frame = 0         # current animation frame index
        self._invuln = 0.0      # seconds left of post-hit invulnerability
        self._attack_cd = self.ATTACK_COOLDOWN   # don't swing the instant you arrive
        self._recover = 0.0     # seconds left of the vulnerable recovery pause
        self.texture = anims["idle"][1][0]       # start on first idle (left) frame

    @property
    def attacking(self):
        # game.py reads this: only the actual swing is dangerous to touch.
        return self.state == "attack"

    def _frames(self, state):
        """Return the correct frame list for a state, flipped for facing."""
        right, left = self._anim[state]
        return right if self.facing_right else left

    def _advance(self, state, loop, rate):
        """Step the animation for `state`. Returns True when a one-shot ends.

        loop=True  -> animation repeats forever (idle/run).
        loop=False -> plays once and stops on the last frame (attack/hurt/dead).
        """
        frames = self._frames(state)
        self._tick += 1
        if self._tick < rate:                    # not time for the next frame yet
            self.texture = frames[min(self._frame, len(frames) - 1)]
            return False
        self._tick = 0
        self._frame += 1
        if self._frame >= len(frames):           # ran past the last frame
            if loop:
                self._frame = 0                  # ...start over
            else:
                self._frame = len(frames) - 1    # ...hold the last frame
                self.texture = frames[self._frame]
                return True                      # signal "one-shot finished"
        self.texture = frames[self._frame]
        return False

    def hit(self):
        """Take one hit. Returns True if it was the killing blow."""
        # Ignore hits while already dying/dead or briefly invulnerable.
        if self.state in ("dying", "dead") or self._invuln > 0:
            return False
        self.hp -= 1
        self._invuln = self.HURT_TIME            # brief flinch / i-frames
        self._frame = 0
        self._tick = 0
        self.state = "dying" if self.hp <= 0 else "hurt"
        return self.hp <= 0

    def update_boss(self, player_x, player_y, dt):
        """Run the boss's "brain" for one frame. `dt` = seconds since last frame.

        Called by game.py every frame while the boss is alive. It decides
        whether to idle, chase, swing, recover, flinch, or die.
        """
        if self.state == "dead":
            return                               # nothing more to do
        if self._invuln > 0:
            self._invuln -= dt                   # count down i-frames

        # --- one-shot states that must finish before anything else ----------
        if self.state == "dying":
            if self._advance("dead", loop=False, rate=self.DEATH_RATE):
                self.state = "dead"              # death animation done
            return
        if self.state == "hurt":
            if self._advance("hurt", loop=False, rate=self.ANIM_RATE):
                self.state = "chase"             # recovered from the flinch
            return

        # Work out where the player is relative to us and face them.
        dx = player_x - self.center_x
        dist = abs(dx)
        if dist > 1:
            self.facing_right = dx > 0
        step = 1 if dx > 0 else -1               # +1 to move right, -1 for left

        # Mid-swing: finish the (stationary) attack, then drop into recovery.
        if self.state == "attack":
            if self._advance("attack", loop=False, rate=self.ANIM_RATE):
                self.state = "recover"
                self._recover = self.RECOVER_TIME
                self._attack_cd = self.ATTACK_COOLDOWN
            return

        # Recovering: stand still and vulnerable for a beat (your window to hit).
        if self._recover > 0:
            self._recover -= dt
            self.state = "recover"
            self._advance("idle", loop=True, rate=self.ANIM_RATE)
            return
        if self._attack_cd > 0:
            self._attack_cd -= dt                # tick down the swing cooldown

        # --- the main decision: idle / attack / chase -----------------------
        if dist > self.ACTIVATE_DIST:
            self.state = "idle"                  # player too far: wait
            self._advance("idle", loop=True, rate=self.ANIM_RATE)
        elif dist <= self.ATTACK_RANGE and self._attack_cd <= 0:
            # In range and cooled down: start a single telegraphed swing
            # (no forward lunge, so it's easy to dodge by backing up).
            self.state = "attack"
            self._frame = 0
            self._tick = 0
            self._advance("attack", loop=False, rate=self.ANIM_RATE)
        else:
            # Otherwise walk toward the player, stopping just outside attack range.
            self.state = "chase"
            if dist > self.ATTACK_RANGE * 0.9:
                self.center_x += self.SPEED * step
            self._advance("run", loop=True, rate=self.ANIM_RATE)
