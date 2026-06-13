import arcade
from constants import SLIME_SCALE, SLIME_PATROL, SLIME_FOOT_OFFSET, TILE_SIZE


class SlimeEnemy(arcade.Sprite):
    ANIM_RATE = 7

    def __init__(self, x, y, walk_right, walk_left, eid=None):
        super().__init__()
        self.eid         = eid          # stable "level:index" id for save tracking
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
