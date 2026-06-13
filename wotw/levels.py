def _make_grid(rows):
    w = max(len(r) for r in rows)
    return [r.ljust(w) for r in rows]


# Tile key:
#   B = brown block    F = pink cupcake platform    H = pink frosting solid
#   b = burger    d = donut    j = hot dog    c = cup    l = lollipop    k = cake    n = nacho    s = sausage
#   P = player spawn

LEVELS = {
    1: {
        # Row 5  platforms: FFF @18-20, HHHH @40-43, FFFF @62-65
        # Row 8  platforms: FFFF @16-19, FFFFF @35-39, FFFF @58-61, HHHH @80-83
        # Row 10 pillars:   BBBBB @20-24, BBBBBB @55-60
        "grid": _make_grid([
            "                                                                                        ",  # 0  sky
            "                                                                                        ",  # 1  sky
            "     b           d           j           b           c           d           b        ",  # 2  collectible row
            "                                                                                        ",  # 3
            "                   l                     l                     l                      ",  # 4  lollipops on row-5 platforms
            "                  FFF                   HHHH                  FFFF                      ",  # 5  upper platforms
            "                                                                                        ",  # 6
            "                 l                   l                     l                     l    ",  # 7  lollipops on row-8 platforms
            "                FFFF               FFFFF                  FFFF                  HHHH   ",  # 8  mid platforms
            "                      l                                  l                            ",  # 9  lollipops on pillar tops
            "                    BBBBB                              BBBBBB                          ",  # 10 pillars
            "                    BBBBB                              BBBBBB                          ",  # 11
            "  P   c             BBBBB               c              BBBBBB             c            ",  # 12 player + cups on ground
            "BBBBBBBBB   BBBBBBBBBBBBBBB    BBBBBBBBBBBBBB    BBBBBBBBBBBBBBBBB    BBBBBBBBBBBBBBBBBB",  # 13 ground
            "BBBBBBBBB   BBBBBBBBBBBBBBB    BBBBBBBBBBBBBB    BBBBBBBBBBBBBBBBB    BBBBBBBBBBBBBBBBBB",  # 14
            "BBBBBBBBB   BBBBBBBBBBBBBBB    BBBBBBBBBBBBBB    BBBBBBBBBBBBBBBBB    BBBBBBBBBBBBBBBBBB",  # 15
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
            "                                                                                        ",  # 0  sky
            "                                                                                        ",  # 1  sky
            "     k           s           n           k           l           s           k        ",  # 2  collectible row
            "                                                                                        ",  # 3
            "                   l                      l                       l                  ",  # 4  lollipops on row-5 platforms
            "                  HHHH                  FFFFF                    HHHH                   ",  # 5  upper platforms
            "                                                                                        ",  # 6
            "          l              l             l                  l              l             ",  # 7  lollipops on row-8 platforms
            "         FFFF          FFFFF        HHHHHHHH            FFFFFF         FFFFF            ",  # 8  mid platforms
            "                   l                              l                                   ",  # 9  lollipops on pillar tops
            "               BBBBBBBB                        BBBBBBBB                                 ",  # 10 pillars
            "               BBBBBBBB                        BBBBBBBB                                 ",  # 11
            "  P     c      BBBBBBBB            c           BBBBBBBB          c                     ",  # 12 player + cups on ground
            "BBBBBBBB    BBBBBBBBBBB    BBBBBBBBB        BBBBBBBBBBBB     BBBBBBBBBB    BBBBBBBBBBBBB",  # 13 ground
            "BBBBBBBB    BBBBBBBBBBB    BBBBBBBBB        BBBBBBBBBBBB     BBBBBBBBBB    BBBBBBBBBBBBB",  # 14
            "BBBBBBBB    BBBBBBBBBBB    BBBBBBBBB        BBBBBBBBBBBB     BBBBBBBBBB    BBBBBBBBBBBBB",  # 15
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
    }
}
