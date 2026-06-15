# ===========================================================================
# levels.py  —  the level designs.
# ---------------------------------------------------------------------------
# Each level is a dict with:
#   "grid"       : a list of text rows describing the map (one letter = one tile)
#   "enemies"    : list of (column, floor_row, slime_type) to spawn
#   "boss_col"   : column to put the boss (only level 10), or None

#   "burger_col" : column for the secret invincibility burger, or None
#   "fake_walls" : passable walls hiding secrets
#
# game.py reads these and turns the letters into real sprites.
#
# Tile key (the letters used in a grid row):
#   B = brown block (solid terrain)   F = pink platform   H = brown platform
#   X = fake wall (looks solid, walk through)   P = player spawn   space = empty
# The bottom three rows are one continuous floor; pillars and floating
# platforms sit on top of it.
# ===========================================================================
from itertools import cycle


def _make_grid(rows):
    """Pad every row to the same length so the grid is a clean rectangle."""
    w = max(len(r) for r in rows)
    return [r.ljust(w) for r in rows]


_GROUND = "B" * 88   # a full row of solid floor (88 tiles wide)

# ---------------------------------------------------------------- level builder
# Instead of typing out 16x88 grids by hand, _make_level() builds one from a
# short description (where the pillars/platforms/spawn go). These say how big
# the map is and which rows are what.
GRID_W      = 88     # columns (width in tiles)
GRID_H      = 16     # rows (height in tiles)
_GROUND_ROWS = (13, 14, 15)   # the bottom 3 rows are the solid floor
_SPAWN_ROW  = 12     # one row above the ground surface (where 'P' goes)
_FLOOR_ROW  = 13     # ground surface row enemies stand on


def _make_level(pillars=(), platforms=(), spawn_col=2,
                ground_enemy_cols=(), stypes=(1, 2, 3), boss_col=None,
                burger_col=None, fake_walls=()):
    """Build a level grid + enemy list from a structural description.

    pillars:    (col, width, height) raised blocks growing up from the ground.
    platforms:  (row, col, width, kind) floating platforms ('F' / 'H').
    fake_walls: (col, width, height) look like terrain but are passable ('X').
    Enemies are auto-placed on every pillar top, every platform, and the
    given ground columns, so they always stand on a real surface.
    """
    # Start with an all-empty grid (spaces), then stamp things into it.
    grid = [[" "] * GRID_W for _ in range(GRID_H)]

    # 1) lay the solid floor along the bottom rows
    for r in _GROUND_ROWS:
        for c in range(GRID_W):
            grid[r][c] = "B"
    # 2) raise pillars up from the floor (height rows tall)
    for (col, width, height) in pillars:
        for h in range(height):
            for c in range(col, col + width):
                grid[_SPAWN_ROW - h][c] = "B"
    # 3) place floating platforms ('F' or 'H')
    for (row, col, width, kind) in platforms:
        for c in range(col, col + width):
            grid[row][c] = kind
    # 4) place passable fake walls ('X') that hide secrets
    for (col, width, height) in fake_walls:
        for h in range(height):
            for c in range(col, col + width):
                grid[_SPAWN_ROW - h][c] = "X"
    # 5) mark the player's start tile
    grid[_SPAWN_ROW][spawn_col] = "P"

    # Auto-place enemies on solid surfaces so none ever float in mid-air.
    # `cycle(stypes)` repeats the slime-type list forever (1,2,3,1,2,3,...).
    cyc = cycle(stypes)
    enemies = []
    for (col, width, height) in pillars:          # one on top of each pillar
        top = _SPAWN_ROW - (height - 1)
        enemies.append((col + width // 2, top, next(cyc)))
    for (row, col, width, kind) in platforms:     # one on each platform
        enemies.append((col + width // 2, row, next(cyc)))
    for c in ground_enemy_cols:                   # plus any on the open ground
        enemies.append((c, _FLOOR_ROW, next(cyc)))

    # Join each row of characters back into a string and return the level dict.
    return {"grid": ["".join(r) for r in grid], "enemies": enemies,
            "boss_col": boss_col, "burger_col": burger_col}


# ===========================================================================
# THE LEVELS THEMSELVES
# ---------------------------------------------------------------------------
# Levels 1 & 2 are written out as hand-drawn grids (you can literally see the
# shapes). Levels 3-10 use the _make_level() builder above. Level 10 is the
# finale with the boss and the secret burger.
# ===========================================================================
LEVELS = {
    1: {
        # Row 5  platforms: FFF @18-20, HHHH @40-43, FFFF @62-65
        # Row 8  platforms: FFFF @16-19, FFFFF @35-39, FFFF @58-61, HHHH @80-83
        # Row 10 pillars:   BBBBB @20-24, BBBBBB @55-60
        "grid": _make_grid([
            "",                                                                                          # 0  sky
            "",                                                                                          # 1  sky
            "",                                                                                          # 2  sky
            "",                                                                                          # 3  sky
            "",                                                                                          # 4  sky
            "                  FFF                   HHHH                  FFFF                      ",   # 5  upper platforms
            "",                                                                                          # 6
            "",                                                                                          # 7
            "                FFFF               FFFFF                  FFFF                  HHHH   ",    # 8  mid platforms
            "",                                                                                          # 9
            "                    BBBBB                              BBBBBB",                              # 10 pillars
            "                    BBBBB                              BBBBBB",                              # 11
            "  P" + " " * 17 + "BBBBB" + " " * 30 + "BBBBBB",                                            # 12 spawn + pillars
            _GROUND,                                                                                     # 13 ground
            _GROUND,                                                                                     # 14
            _GROUND,                                                                                     # 15
        ]),
        "enemies": [
            # ground (clear of the cols 20-24 / 55-60 pillars)
            ( 4, 13, 1),
            (15, 13, 2),
            (35, 13, 1),
            (41, 13, 3),
            (52, 13, 2),
            (63, 13, 1),
            (74, 13, 3),
            (83, 13, 2),
            # on the pillar tops
            (22, 10, 2),
            (57, 10, 1),
            # on the floating platforms
            (17,  8, 1),
            (37,  8, 3),
            (59,  8, 2),
        ],
    },

    2: {
        # Row 5  platforms: HHHH @18-21, FFFFF @40-44, HHHH @65-68
        # Row 8  platforms: FFFF @9-12, FFFFF @23-27, HHHHHHHH @36-43, FFFFFF @56-61, FFFFF @71-75
        # Row 10 pillars:   BBBBBBBB @15-22, BBBBBBBB @47-54
        "grid": _make_grid([
            "",                                                                                          # 0  sky
            "",                                                                                          # 1  sky
            "",                                                                                          # 2  sky
            "",                                                                                          # 3  sky
            "",                                                                                          # 4  sky
            "                  HHHH                  FFFFF                    HHHH                   ",   # 5  upper platforms
            "",                                                                                          # 6
            "",                                                                                          # 7
            "         FFFF          FFFFF        HHHHHHHH            FFFFFF         FFFFF            ",    # 8  mid platforms
            "",                                                                                          # 9
            "               BBBBBBBB                        BBBBBBBB",                                    # 10 pillars
            "               BBBBBBBB                        BBBBBBBB",                                    # 11
            "  P" + " " * 12 + "BBBBBBBB" + " " * 24 + "BBBBBBBB",                                        # 12 spawn + pillars
            _GROUND,                                                                                     # 13 ground
            _GROUND,                                                                                     # 14
            _GROUND,                                                                                     # 15
        ]),
        "enemies": [
            # ground (clear of the cols 15-22 / 47-54 pillars)
            ( 4, 13, 1),
            (13, 13, 2),
            (31, 13, 1),
            (45, 13, 3),
            (65, 13, 2),
            (78, 13, 1),
            (84, 13, 3),
            # on the pillar tops
            (18, 10, 2),
            (50, 10, 1),
            # on the floating platforms
            (25,  8, 1),
            (39,  8, 3),
            (58,  8, 2),
            (73,  8, 1),
        ],
    },

    # 3 — Pyramid staircase: pillars rise to a peak then fall.
    3: _make_level(
        pillars=[(10, 6, 1), (20, 6, 2), (30, 6, 3),
                 (40, 6, 4), (50, 6, 3), (60, 6, 2), (70, 6, 1)],
        ground_enemy_cols=[5, 17, 47, 80],
        stypes=(1, 2, 3),
    ),

    # 4 — Floating maze: no pillars, three tiers of platforms to hop.
    4: _make_level(
        platforms=[(11, 14, 4, "F"), (11, 34, 4, "H"), (11, 56, 4, "F"), (11, 74, 4, "H"),
                   (8,   8, 4, "F"), (8,  26, 4, "H"), (8,  46, 4, "F"), (8,  66, 4, "H"),
                   (5,  18, 4, "F"), (5,  40, 4, "H"), (5,  62, 4, "F")],
        ground_enemy_cols=[4, 30, 52, 82],
        # types 1-3 = slimes, 4-6 = fast monsters (mixed from level 4 on)
        stypes=(1, 4, 2, 5, 3, 6),
    ),

    # 5 — Twin towers with a bridge of platforms between them.
    5: _make_level(
        pillars=[(20, 10, 4), (58, 10, 4)],
        platforms=[(8, 38, 6, "F"), (5, 38, 6, "H")],
        ground_enemy_cols=[6, 14, 50, 82],
        stypes=(2, 5, 3, 6, 1, 4),
    ),

    # 6 — Rolling bumps: lots of short pillars, two long platforms.
    6: _make_level(
        pillars=[(8, 4, 1), (16, 4, 2), (26, 5, 1), (36, 4, 2),
                 (46, 5, 1), (56, 4, 2), (66, 5, 1), (76, 5, 2)],
        platforms=[(8, 30, 5, "F"), (8, 60, 5, "H")],
        ground_enemy_cols=[4, 22, 42, 72],
        stypes=(3, 6, 1, 4, 2, 5),
    ),

    # 7 — Sky bridges: long high platforms over a couple of pillars.
    7: _make_level(
        pillars=[(30, 6, 3), (54, 6, 3)],
        platforms=[(8, 10, 8, "F"), (8, 38, 10, "H"), (8, 66, 8, "F"),
                   (5, 24, 8, "H"), (5, 50, 8, "F")],
        ground_enemy_cols=[4, 46, 82],
        stypes=(1, 5, 2, 6, 3, 4),
    ),

    # 8 — Zigzag: tall/short pillars alternating, high platforms.
    8: _make_level(
        pillars=[(10, 5, 3), (20, 5, 1), (30, 5, 3), (40, 5, 1),
                 (50, 5, 3), (60, 5, 1), (70, 5, 3)],
        platforms=[(5, 15, 4, "F"), (5, 35, 4, "H"), (5, 55, 4, "F")],
        ground_enemy_cols=[4, 25, 45, 65, 82],
        stypes=(2, 6, 3, 4, 1, 5),
    ),

    # 9 — Canyon: two huge towers with a climb of platforms in the middle.
    9: _make_level(
        pillars=[(16, 8, 4), (64, 8, 4)],
        platforms=[(11, 30, 6, "F"), (8, 40, 6, "H"),
                   (5, 30, 6, "F"), (8, 50, 6, "F")],
        ground_enemy_cols=[6, 28, 60, 82],
        stypes=(3, 4, 1, 5, 2, 6),
    ),

    # 10 — Finale: fight through to the boss ninja waiting at the end.
    #      Secret: walk back to the very start for an invincibility burger.
    10: _make_level(
        pillars=[(12, 5, 2), (24, 5, 3), (40, 8, 4)],
        platforms=[(8, 18, 4, "F"), (5, 32, 6, "H")],
        spawn_col=8,
        ground_enemy_cols=[34],
        stypes=(5, 1, 3),
        boss_col=74,
        burger_col=1,
        fake_walls=[(0, 3, 3)],   # passable wall hiding the burger at the start
    ),
}
