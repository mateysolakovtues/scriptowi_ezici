import arcade

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Wok of the worior - Platformer Example"
CHARACTER_SCALING = 1
TILE_SCALING = 0.5
PLAYER_MOVEMENT_SPEED = 5
GRAVITY = 1
PLAYER_JUMP_SPEED = 20

class MyGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        self.player_list = None
        self.wall_list = None
        self.player_sprite = None
        self.physics_engine = None

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.wall_list = arcade.SpriteList()

        self.player_sprite = arcade.Sprite(":resources:images/animated_characters/female_adventurer/femaleAdventurer_idle.png", CHARACTER_SCALING)
        self.player_sprite.center_x = 64
        self.player_sprite.center_y = 128
        self.player_list.append(self.player_sprite)

        for x in range(0, 1250, 64):
            wall = arcade.Sprite(":resources:images/tiles/boxCrate_double.png", TILE_SCALING)
            wall.center_x = x
            wall.center_y = 32
            self.wall_list.append(wall)

        self.create_boundary_walls()  # <-- call it here, before the physics engine

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player_sprite, gravity_constant=GRAVITY, walls=self.wall_list
        )

    def create_boundary_walls(self):
        """Create invisible walls at screen edges to keep the player on screen."""
        # Left wall
        left_wall = arcade.SpriteSolidColor(20, SCREEN_HEIGHT * 2, arcade.color.WHITE)
        left_wall.center_x = -10
        left_wall.center_y = SCREEN_HEIGHT // 2
        left_wall.alpha = 0
        self.wall_list.append(left_wall)

        # Right wall
        right_wall = arcade.SpriteSolidColor(20, SCREEN_HEIGHT * 2, arcade.color.WHITE)
        right_wall.center_x = SCREEN_WIDTH + 10
        right_wall.center_y = SCREEN_HEIGHT // 2
        right_wall.alpha = 0
        self.wall_list.append(right_wall)

        # Ceiling (so the player can't jump off the top either)
        ceiling = arcade.SpriteSolidColor(SCREEN_WIDTH * 2, 20, arcade.color.WHITE)
        ceiling.center_x = SCREEN_WIDTH // 2
        ceiling.center_y = SCREEN_HEIGHT + 10
        ceiling.alpha = 0
        self.wall_list.append(ceiling)

    def on_draw(self):
        self.clear()
        self.wall_list.draw()
        self.player_list.draw()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.UP or key == arcade.key.SPACE or key == arcade.key.W:
            if self.physics_engine.can_jump():
                self.player_sprite.change_y = PLAYER_JUMP_SPEED
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.player_sprite.change_x = -PLAYER_MOVEMENT_SPEED
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.player_sprite.change_x = PLAYER_MOVEMENT_SPEED

    def on_key_release(self, key, modifiers):
        if key == arcade.key.LEFT or key == arcade.key.A:
            self.player_sprite.change_x = 0
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.player_sprite.change_x = 0

    def on_update(self, delta_time):
        self.physics_engine.update()

def main():
    window = MyGame()
    window.setup()
    arcade.run()

if __name__ == "__main__":
    main()