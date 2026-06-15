# ===========================================================================
# main.py  —  the entry point: this is the file you run to start the game.
# ---------------------------------------------------------------------------
# It does the bare minimum: create the game window, load everything, then hand
# control to arcade's event loop. All the actual game lives in game.py.
# (play.py is an identical launcher kept for convenience.)
# ===========================================================================
import arcade
from game import MyGame

# This `if` is only True when you run THIS file directly (not when it's
# imported). It's the standard Python way to mark "start here".
if __name__ == "__main__":
    window = MyGame()    # build the window + all the game state
    window.setup()       # load textures, sounds, levels, show the menu
    arcade.run()         # start the loop: repeatedly calls on_update + on_draw
