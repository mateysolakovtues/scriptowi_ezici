import arcade

RIGHT_FACING = 0
LEFT_FACING = 1
UPDATES_PER_FRAME = 6

class PlayerCharacter(arcade.Sprite):
    def __init__(self):
        super().__init__()

        self.facing_direction = RIGHT_FACING
        self.cur_texture = 0

        self.is_attacking = False
        self.attack_type = 0  

        self.idle_textures = [[], []]
        self.walk_textures = [[], []]
        
        self.attack_textures = [
            [[], []],  
            [[], []],  
            [[], []]   
        ]

    def update_animation(self, delta_time: float = 1 / 60):
        if self.change_x < 0 and self.facing_direction == RIGHT_FACING:
            self.facing_direction = LEFT_FACING
        elif self.change_x > 0 and self.facing_direction == LEFT_FACING:
            self.facing_direction = RIGHT_FACING

        if self.is_attacking:
            self.cur_texture += 1
            
            current_attack_frames = self.attack_textures[self.attack_type][self.facing_direction]
            max_frames = len(current_attack_frames) * UPDATES_PER_FRAME
            
            if self.cur_texture >= max_frames:
                self.is_attacking = False
                self.cur_texture = 0
            else:
                frame = self.cur_texture // UPDATES_PER_FRAME
                self.texture = current_attack_frames[frame]
                return

        if self.change_x == 0 and self.change_y == 0:
            self.texture = self.idle_textures[self.facing_direction][0]
            self.cur_texture = 0  
            return

        self.cur_texture += 1
        
        max_walk_frames = len(self.walk_textures[self.facing_direction]) * UPDATES_PER_FRAME
        if self.cur_texture >= max_walk_frames:
            self.cur_texture = 0
            
        frame = self.cur_texture // UPDATES_PER_FRAME
        direction = self.facing_direction
        self.texture = self.walk_textures[direction][frame]