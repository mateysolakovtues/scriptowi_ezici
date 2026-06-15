# ===========================================================================
# play.py  —  an alternate launcher, identical to main.py.
# Run either `python main.py` or `python play.py` to start the game.
# ===========================================================================
import arcade
from game import MyGame

if __name__ == "__main__":
    window = MyGame()    # build the window + all the game state
    window.setup()       # load textures, sounds, levels, show the menu
    arcade.run()         # start the loop: repeatedly calls on_update + on_draw
