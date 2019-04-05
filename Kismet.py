import pygame as pg
import pygame.freetype
import pytmx
from pytmx.util_pygame import load_pygame
import sys
import os
from time import sleep
import random

# Function to load images.
def load_image(name):
    image = pg.image.load(name).convert_alpha()
    return image

# Filter function.
def rect_filter(list):
    for rect in list:
        if rect is None:
            return False
        else:
            return True

# Spritesheet class to split sprite sheets into proper single frames.
class spritesheet(object):
    def __init__(self, filename):
        self.sheet = pg.image.load(filename).convert()

    # Load a specific image from a specific rectangle.
    def image_at(self, rectangle, colorkey = None):
        "Loads image from x,y,x+offset,y+offset"
        rect = pg.Rect(rectangle)
        image = pg.Surface(rect.size).convert()
        image.blit(self.sheet, (0, 0), rect)
        if colorkey is not None:
            if colorkey is -1:
                colorkey = image.get_at((0,0))
            image.set_colorkey(colorkey, pg.RLEACCEL)
        return image

    # Load a whole bunch of images and return them as a list
    def images_at(self, rects, colorkey = None):
        "Loads multiple images, supply a list of coordinates"
        return [self.image_at(rect, colorkey) for rect in rects]

    # Load a whole strip of images
    def load_strip(self, rect, image_count, colorkey = None):
        "Loads a strip of images and returns them as a list"
        tups = [(rect[0]+rect[2]*x, rect[1], rect[2], rect[3])
                for x in range(image_count)]
        return self.images_at(tups, colorkey)

# TiledMap class to properly render Tiled maps by layer to surfaces.
class TiledMap:
    def __init__(self, filename):
        tm = load_pygame(filename)
        self.width = tm.width * tm.tilewidth
        self.height = tm.height * tm.tileheight
        self.tm = tm
        self.blockers = []
        self.battle_spawns = []

    # Renders two surfaces. back_surface is the surface that sprites appear in front of. top_surface vice versa.
    def render(self, back_surface, top_surface):
        first_time = True
        ti = self.tm.get_tile_image_by_gid
        self.last_layer = 0
        self.layer_counter = 0
        # Determine last tile layer.
        for layer in self.tm.visible_tile_layers:
            self.last_layer += 1
        for layer in self.tm.visible_layers:
            self.layer_counter += 1

            # Create a surface of tiles for back and front surfaces.
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    tile = ti(gid)
                    if tile:
                        if self.layer_counter != self.last_layer:
                            back_surface.blit(tile, (x * self.tm.tilewidth, y * self.tm.tileheight))
                        else:
                            top_surface.blit(tile, (x * self.tm.tilewidth, y * self.tm.tileheight))

            # Create a list of platforms and walls by rect.
            elif isinstance(layer, pytmx.TiledObjectGroup) and first_time:
                for object in layer:
                    new_rect = pg.Rect(object.x, object.y, object.width, object.height)
                    self.blockers.append(new_rect)
                first_time = False

            # Create a list of spawn locations by rect for battle maps.
            elif isinstance(layer, pytmx.TiledObjectGroup):
                for object in layer:
                    new_rect = pg.Rect(object.x, object.y, object.width, object.height)
                    self.battle_spawns.append(new_rect)

    def make_map(self):
        self.pre_back_surface = pg.Surface((self.width, self.height)).convert()
        self.pre_front_surface = pg.Surface((self.width, self.height), pg.SRCALPHA, 32).convert_alpha()
        self.render(self.pre_back_surface, self.pre_front_surface)
        # self.back_surface = self.pre_back_surface.subsurface((0,0,1920,1080))
        # self.front_surface = self.pre_front_surface.subsurface((0,0,1920,1080))
        # self.back_surface = pg.Surface((self.width, 1080)).convert()
        # self.front_surface = pg.Surface((self.width, 1080), pg.SRCALPHA, 32).convert_alpha()
        # self.back_surface.blit(self.back_surface_x, (0,0))
        # self.front_surface.blit(self.front_surface_x, (0,0))
        self.back_surface = self.pre_back_surface
        self.front_surface = self.pre_front_surface
        return self.back_surface, self.front_surface

# ----------------------------------------------------PLAYERS-------------------------------------------------------------------
# Fursa sprite. The main character of the game.
class Fursa_sprite(pg.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.frame_index = 0
        self.upload_frames() # Uploads all frames. Function found below.
        self.current_images = self.all_images[0]
        self.image = self.current_images[0]
        self.prev_state = 0
        self.state = 0
        self.facing_right = True
        self.frame_override = True
        self.rect = pg.Rect((200, 200), (128, 128)) # Spawn point and collision size.
        self.hitbox_rect = pg.Rect((self.rect.x + 52 , self.rect.y + 36), (18, 64))

        # States
        self.key_pressed = False
        self.gravity_dt = 0
        self.frame_dt = 0
        self.jump_dt = 0
        self.fall_rate = 1
        self.jump_rate = 20
        self.jump_index = 0
        self.speed = 1 # @pixel/frame. At approx 80 fps --> 80 pixel/sec
        self.jump = False
        self.attack = False
        self.frame_speed = 200
        self.hit = False
        self.hp = 3
        self.cutscene_enter = False
        self.map_forward = False
        self.battle = False
        self.walking = False
        self.running = False
        self.on_ground = False

        # Load sound effects.
        os.chdir("C:/Users/Andrew/Desktop/Python_Projects/Kismet/Players/Fursa")
        self.jump_noise = pg.mixer.Sound("jump_02.wav")
        self.attack_noise = pg.mixer.Sound("Electro_Current_Magic_Spell.wav")
        self.attack_charge = pg.mixer.Sound("charge_up.wav")
        self.walk_dirt = pg.mixer.Sound("stepdirt_7.wav")
        self.walk_dirt.set_volume(0.15)
        self.teleport_noise = pg.mixer.Sound('teleport.wav')
        self.walking = False
        self.running = False
        self.on_ground = False

        # Battle Transition Sounds.
        os.chdir("C:/Users/Andrew/Desktop/Python_Projects/Kismet/Maps")
        self.battle_sword_aftersound = pg.mixer.Sound('battle_sword_aftersound.wav')
        self.battle_impact_noise = pg.mixer.Sound('battle_start.wav')
        self.battle_impact_noise.set_volume(0.50)
        resolution = width, height = 1920,1080
        black = (0,0,0)
        self.battle_transition = pg.Surface(resolution)
        self.battle_transition.fill(black)

    # Function that uploads and stores all possible frames Fursa may use. Is called in __init__.
    # Created separately for organizational purposes.
    def upload_frames(self):
        idle_images = []
        walk_images = []
        run_images = []
        attack_images = []
        shield_images = []
        hit_images = []
        death_images = []

        # State IDs
        #-----------------------0------------1------------2------------3--------------4--------------5-----------6-------#
        self.all_images = [idle_images, walk_images, run_images, attack_images, shield_images, death_images, hit_images]

        directories =      ["C:/Users/Andrew/Desktop/Python_Projects/Kismet/Players/Fursa/Idle"          # Idle animation.
                           ,"C:/Users/Andrew/Desktop/Python_Projects/Kismet/Players/Fursa/Walk"          # Walking animation.
                           ,"C:/Users/Andrew/Desktop/Python_Projects/Kismet/Players/Fursa/Run"           # Run animation.
                           ,"C:/Users/Andrew/Desktop/Python_Projects/Kismet/Players/Fursa/Attack_01"     # Attack animation.
                           ,"C:/Users/Andrew/Desktop/Python_Projects/Kismet/Players/Fursa/Attack_02"     # Shield animation.
                           ,"C:/Users/Andrew/Desktop/Python_Projects/Kismet/Players/Fursa/Death"]        # Hit & Death animation.

        # Create a list containing lists with all animation frames. Each list is referenceable by the state ID shown above.
        for i, directory in enumerate(directories):
            os.chdir(directory)
            for file in os.listdir(directory):
                self.all_images[i].append(pg.transform.scale(load_image(file), (128, 128)))

        self.all_images[6] = (self.all_images[5][0:7])

        # Create a list of number of frames for each animation.
        self.frame_maxes = [len(images) for images in self.all_images]

    # Function that changes Fursa's animation depending on the action performed.
    # Continuously called in self.update().
    def change_state_keys(self):

        # Each frame list has a state ID that can be found outlined in self.upload_frames().
        # Each animation type has its own fps.
        self.prev_state = self.state

        if self.hit:
            self.state = 6
            self.frame_speed = 25
            self.walking = False
            self.running = False
        elif self.attack:
            self.state = 3
            self.frame_speed = 75
            self.walking = False
            self.running = False
        elif self.key_pressed and self.shift:
            self.state = 2
            self.frame_speed = 100
            self.walking = False
            self.running = True
        elif self.key_pressed:
            self.state = 1
            self.frame_speed = 125
            self.walking = True
            self.running = False
        else:
            self.state = 0
            self.frame_speed = 200
            self.walking = False
            self.running = False

        self.current_images = self.all_images[self.state]

        if self.prev_state != self.state:
            self.frame_index = 0

    """
        Function that handles Fursa's key inputs. Called in update().
        Split into two sections:
        1. Monitoring held down keys and combinations.
        2. Monitoring single key press events.
        Due to the nature of pygame, both have to be used in tandem to
        create fluid game controls.
    """

    def handle_keys(self, time, dt, map):

        # Monitor held down keys. (movement)
        # If attack animation is not in progress, move in the direction of the pressed key.

        if self.attack == False:
            keys = pg.key.get_pressed()
            if keys[pg.K_d]:
                self.rect.x += self.speed
                self.key_pressed = True  # Self.key_pressed() is fed back to change_state(). Found several times throughout handle_keys().
            elif keys[pg.K_a]:
                self.rect.x -= self.speed
                self.key_pressed = True
            # Running changes speed by holding down shift.
            # Self.shift is fed back to change_state().
            if keys[pg.K_LSHIFT]:
                self.shift = True
                self.speed = 2 * dt
            else:
                self.shift = False
                self.speed = 1 * dt

        # Pygame event loop.
        for event in pg.event.get():

            # Monitor single key presses. (actions)
            # If a key is pressed and an attack animation is not in progress, register the key press.
            if event.type == pg.KEYDOWN and self.attack == False:

                self.key_pressed = True
                self.frame_index = 0 # Frame reset when key is pressed.

                # Registers which way Fursa should be facing. Fed to self.update().
                if event.key == pg.K_d:
                    self.facing_right = True
                    self.walking = True
                elif event.key == pg.K_a:
                    self.facing_right = False
                    self.walking = True

                # Enables attack animation.
                # Self.attack set to True prevents other key inputs to be registered until the animation is completed.
                elif event.key == pg.K_r:
                    self.attack = True
                    self.attack_charge.play()

                # Jump input.
                elif event.key == pg.K_SPACE:
                    self.jump_noise.play()
                    self.jump = True    # ----------------> Jump starts.

                elif event.key == pg.K_w:
                    if self.rect.collidepoint(map.portal_rect.centerx, map.portal_rect.centery):
                        for sound in map.end_sounds:
                            sound.stop()
                        self.teleport_noise.play()
                        self.map_forward = True

                elif event.key == pg.K_ESCAPE:
                     pg.quit()
                     sys.exit()

            # Frame reset when key is no longer held down. Self.key_pressed set to False to change state to idle.
            elif event.type == pg.KEYUP and self.attack == False:
                self.frame_index = 0
                self.key_pressed = False

            else:
                self.key_pressed = False

        # Jumping animation triggered by space key press.
        # Jump code is placed outside event loop so that the animation can carry out.
        # Decelerates every 60 ms.
        if self.jump is True:
            if (time - self.jump_dt) >= 60:
                self.jump_dt = time
                self.jump_rate *= 0.8 # Jump deceleration.
                self.jump_index += 1
                for i in range(int(self.jump_rate)):
                    self.rect.y -= 1
                    if self.jump_index == 5:
                        self.jump = False   # ----------------> Jump finishes.
                        self.jump_rate = 20
                        self.jump_index = 0
                        break

    def change_state_battle(self):
        pass

    def battle_controls(self):
        pass

    # Function that updates Fursa's frames and positioning. Called continuously in game loop main().
    # Must be fed the blockers of the current map.
    def update(self, blockers, time, dt, cutscene, screen, map, map_travel, character_sprites, enemy_sprites, particle_sprites, particle_frames):

        normalized_dt = round(dt / 11)

        if self.facing_right:
            self.hitbox_rect = pg.Rect((self.rect.x + 52 , self.rect.y + 36), (18, 64))
        else:
            self.hitbox_rect = pg.Rect((self.rect.x + 58 , self.rect.y + 36), (18, 64))

        # Disallow any key input if cutscene is in progress. Revert Fursa into a idle state.
        if map.battle is True:
            self.change_state_battle()
            self.battle_controls()
        elif cutscene is False:
            self.handle_keys(time, normalized_dt, map)
            self.change_state_keys()
            self.cutscene_enter = True
            if map_travel:
                self.map_forward = False
        elif cutscene:
            self.state = 0
            self.frame_speed = 200
            self.walking = False
            self.running = False
            self.current_images = self.all_images[self.state]
            if self.cutscene_enter:
                self.frame_index = 0
                self.cutscene_enter = False

        """
            Cycle through frames depending on self.frame_speed that is set in self.change_state().
            Flip the frame image vertically depending on which direction Fursa is facing.
            Self.frame_override is a boolean representing the previous state of self.facing_right.
            If the direction that Fursa is facing has changed before a frame can be refreshed,
            bypasses frame timer and resets the to avoid Fursa momentarily moving facing the wrong direction.
        """

        if (time - self.frame_dt) >= self.frame_speed or self.facing_right != self.frame_override:
            self.frame_dt = time

            # Resets frame index if the max for a certain animation is reached.
            # Also, sets attack animation back to False in case the action was an attack.
            if self.frame_index == self.frame_maxes[self.state]:
                self.attack = False
                self.hit = False
                self.frame_index = 0

            if self.facing_right:
                self.image = self.current_images[self.frame_index]
                self.frame_index += 1
                self.frame_override = True
            else:
                self.image = pg.transform.flip(self.current_images[self.frame_index], True, False)
                self.frame_index += 1
                self.frame_override = False

            # Play attack noise at the correct frame.
            if self.walking and self.on_ground:
                if self.frame_index == 2 or self.frame_index == 8:
                    self.walk_dirt.play()

            elif self.running and self.on_ground:
                if self.frame_index == 4 or self.frame_index == 11:
                    self.walk_dirt.play()

            elif self.attack == True and self.frame_index == 8:
                self.attack_noise.play()
                blast = Fursa_blast(particle_frames, self.facing_right, self.rect.x, self.rect.y)
                particle_sprites.add(blast)


        """ ----------------------SKIP POS 1 ----------------------------------------
         |  Enemy collision detection. Transition to turn-based combat.
         |  All code pertaining to transitioning into combat mode is located here.
         |  Each individual sprite's combat behavior is located in its own respective class.
        """
        for enemy in enemy_sprites:
            if enemy.attack:
                if self.hitbox_rect.colliderect(enemy.rect) and enemy.frame_index == 8:

                    self.image = self.all_images[6][2]

                    # Transition screen.
                    self.battle_impact_noise.play()
                    enemy_sprites.draw(screen)
                    character_sprites.draw(screen)
                    screen.blit(map.map.front_surface, (0,0))
                    pg.display.flip()
                    pg.time.wait(1000)
                    screen.blit(self.battle_transition, (0,0))
                    enemy_sprites.draw(screen)
                    character_sprites.draw(screen)
                    pg.display.flip()
                    self.battle_sword_aftersound.play()
                    pg.time.wait(1000)

                    # Spawn and music start.
                    self.facing_right = True
                    enemy.facing_right = False
                    os.chdir("C:/Users/Andrew/Desktop/Python_Projects/Kismet/Maps")
                    battle_music = pg.mixer.music.load('300-B - Blood of Lilith (Loop, MP3).mp3')
                    pg.mixer.music.play(loops = -1, start = 0.0)
                    self.rect.centerx = map.battle_spawn_pos[1].centerx
                    self.rect.centery = map.battle_spawn_pos[1].centery
                    enemy.rect.centerx = map.battle_spawn_pos[3].centerx
                    enemy.rect.centery = map.battle_spawn_pos[3].centery
                    self.frame_index = 0
                    self.hp -= 1
                    self.hit = True
                    self.battle = True


        """ ---------------------------- END OF BATTLE CODE -------------------------------"""


        # Gravity emulation with current map blockers.
        for block in blockers:
            # Checks to see if Fursa is in contact with the ground.
            if self.hitbox_rect.colliderect(block):
                self.on_ground = True
                break
            else:
                self.on_ground = False

        if self.on_ground is False:
            # If not in contact with the ground, accelerates falling down every 20 ms.
            # Gravity is disabled when a jump animation is in progress.
            if (time - self.gravity_dt) >= 20 and self.jump is False:
                self.gravity_dt = time
                self.fall_rate *= 1.1 # Acceleration rate.
                for i in range(int(self.fall_rate)):
                    self.rect.y += 1
                    self.hitbox_rect.y += 1
                    # Halts falling when Fursa lands on a block.
                    for block in blockers:
                        if self.hitbox_rect.colliderect(block):
                            self.fall_rate = 1
                            self.on_ground = True
                            break
                    if self.on_ground is True:
                        break

# Class simply containing projectile frames of various attacks.
# Created to avoid having to load from the hard drive every time a projectile is created.
class blast_frames():
    def __init__(self):

        # Fursa's attack blast properly separated into frames into a list from a spritesheet.
        os.chdir("C:/Users/Andrew/Desktop/Python_Projects/Kismet/Players/Fursa")
        coordinates = [(128 * i, 0, 128, 128) for i in range(0,8)]
        blast_image_ss = spritesheet('EnergyBall.png')
        blast_images_separate = blast_image_ss.images_at(coordinates, colorkey = (0, 0, 0))
        self.blast_images_r = [pg.transform.scale(blast_images_separate[i], (48, 48)) for i in range(0, len(blast_images_separate))]
        self.blast_images_l = [pg.transform.flip(self.blast_images_r[i], True, False) for i in range(0, len(self.blast_images_r))]

        # Impact frames.
        coordinates = [(0, 128 * i, 128, 128) for i in range(0,8)]
        impact_images_ss = spritesheet('energyBallImpact.png')
        impact_images_separate = impact_images_ss.images_at(coordinates, colorkey = (0, 0, 0))
        self.impact_images_r = [pg.transform.scale(impact_images_separate[i], (48, 48)) for i in range(0, len(impact_images_separate))]
        self.impact_images_l = [pg.transform.flip(self.impact_images_r[i], True, False) for i in range(0, len(self.impact_images_r))]

        self.frames = [self.blast_images_r, self.blast_images_l, self.impact_images_r, self.impact_images_l]

# Fursa's blast projectile sprite.
class Fursa_blast(pg.sprite.Sprite):
    def __init__(self, frames, Fursa_facing_right, Fursa_x, Fursa_y):
        super().__init__()
        self.blast_images_r = frames[0]
        self.blast_images_l = frames[1]
        self.impact_images_r = frames[2]
        self.impact_images_l = frames[3]

        self.flowing_right = True if Fursa_facing_right else False

        if self.flowing_right:
            self.rect = pg.Rect(Fursa_x + 70, Fursa_y + 52, 64, 64)
            self.images = self.blast_images_r
            self.impact = self.impact_images_r
        else:
            self.rect = pg.Rect(Fursa_x + 20, Fursa_y + 52, 64, 64)
            self.images = self.blast_images_l
            self.impact = self.impact_images_l

        self.image = self.images[0]
        self.spawn = True
        self.i = 0
        self.e = 0
        #self.already_spawned = False
        self.flow_right = True
        self.particle_hit = False

    def update(self, Fursa, dt, particle_sprites, enemy_sprites):

        normalized_dt = round(dt / 11)
        dt = normalized_dt

        # Once blast is spawned by Fursa, will keep traveling across map until it hits the
        # right of left edge of the map in which case the sprite will be killed.
        if self.particle_hit is False and self.flowing_right:
            self.rect.x += 4 * dt
        else:
            self.rect.x -= 4 * dt

        self.image = self.images[self.i] # Frame changing.
        self.i += 1
        if self.i == 8: self.i = 0

        if self.rect.right > 1920 or self.rect.left < 0:
            self.spawn = False
            self.kill()

        elif self.spawn and self.particle_hit:
            self.images = self.impact
            self.image = self.images[self.e] # Frame changing.
            self.e += 1
            if self.e == 8:
                self.kill()
                self.particle_hit = False

        for enemy in enemy_sprites:
            if self.flow_right:
                if self.rect.collidepoint(enemy.rect.x + 50, enemy.rect.centery + 20):
                    self.particle_hit = True
            elif self.flow_right is False:
                if self.rect.collidepoint(enemy.rect.x + 20, enemy.rect.centery + 20):
                    self.particle_hit = True

# ----------------------------------------------------ENEMIES-------------------------------------------------------------------
class skeleton(pg.sprite.Sprite):
    def __init__(self, frames, spawnx, spawny):
        super().__init__()
        self.frames = frames.skeleton_frames
        self.frame_maxes = frames.skeleton_frame_maxes
        self.current_images = self.frames[0] # Idle
        self.image = self.current_images[0]
        self.prev_state = 0
        self.state = 0
        self.rect = pg.Rect(spawnx, spawny, 72, 96)
        self.frame_index = 0
        self.frame_dt = 0
        self.frame_speed = 100
        self.facing_right = True
        self.frame_override = True
        self.gravity_dt = 0
        self.fall_rate = 1
        self.jump = False
        self.aggroed = False
        self.reaction_done = False
        self.chase = False
        self.attack = False
        self.pre_engaged_dt = 0
        self.one_shot = True
        self.change_state = False
        self.pstate = 0
        self.cstate = 0
        self.hit = False
        self.hp = 3
        self.on_ground = False

        os.chdir("C:/Users/Andrew/Desktop/Python_Projects/Kismet/Enemies/Skeleton")
        self.swing_sound = pg.mixer.Sound('swing.wav')

    # Skeleton AI.
    def AI(self, blockers, time, character, particle_sprites):

        self.prev_state = self.state

        if self.hit is False:
            # When not aggroed, pace back and forth spawn location.
            if not self.aggroed:
                if (time - self.pre_engaged_dt) >= 2500:
                    self.pre_engaged_dt = time
                    self.state ^= 1
                    if self.state == 0: # Idle
                        pass
                    if self.state == 1:
                        self.facing_right = not self.facing_right
                    self.frame_index = 0
                if self.state == 1:
                    if self.facing_right:
                        self.rect.x += 1
                    else:
                        self.rect.x -= 1

            # for block in blockers:
            #     if self.rect.left <= block.left or self.rect.right >= block.right:
            #         self.state == 0

            # If within aggro range, switch animation to react.
            if abs(self.rect.centerx - character.rect.centerx) < 200 and not self.aggroed:
                self.frame_speed = 400
                self.state = 2
                self.aggroed = True
                self.frame_index = 0

            # Allow for reaction frames to finish.
            if self.state == 2 and self.frame_index == 4:
                self.chase = True
                self.frame_index = 0

            # When aggroed and reaction is done, move towards the player.
            if self.attack == False:
                if self.aggroed and self.chase:
                    self.state = 1
                    self.frame_speed = 100
                    if (self.rect.centerx - character.rect.centerx) > 0:
                        self.facing_right = False
                        self.rect.x -= 1
                    else:
                        self.facing_right = True
                        self.rect.x += 1

            # Start attack animation.
            if abs(self.rect.centerx - character.rect.centerx) < 100 and self.chase:
                self.attack = True
                self.frame_speed = 100
                self.state = 3

            for particle in particle_sprites:
                if particle.particle_hit is True:
                    self.chase = True
                    self.aggroed = True
                    self.hit = True
                    self.frame_speed = 150
                    self.state = 4
                    self.hp -= 1

        if self.hp <= 0:
            self.state = 5

        if self.prev_state != self.state:
            self.change_state = True
            self.pstate = self.prev_state
            self.cstate = self.state

    def change_rect_by_state(self, old_state, new_state, self_facing):
        self.frame_index = 0
        sizes = [(72,96), (66,99), (66,96), (129,111), (90,96), (99,96)]
        old_size_x = sizes[old_state][0]
        new_size_x = sizes[new_state][0]
        old_size_y = sizes[old_state][1]
        new_size_y = sizes[new_state][1]
        x_dt = new_size_x - old_size_x
        y_dt = new_size_y - old_size_y
        self.rect.width = old_size_x + x_dt
        self.rect.height = old_size_y + y_dt
        self.rect.y -= y_dt
        if self.facing_right is not True and new_state != 4: self.rect.x -= x_dt

    def battle(self):
        pass

    def update(self, blockers, time, character, particle_sprites):

        if character.battle is False:
            self.AI(blockers, time, character, particle_sprites)
        else:
            self.state = 0
            self.battle()

        # Frame update and flipping.

        if (time - self.frame_dt) >= self.frame_speed or self.facing_right != self.frame_override:
            self.frame_dt = time

            self.current_images = self.frames[self.state]

            if self.change_state is True:
                self.change_rect_by_state(self.pstate, self.cstate, self.facing_right)
                self.change_state = False

            if self.facing_right:
                self.image = self.current_images[self.frame_index]
                self.frame_index += 1
                self.frame_override = True
            else:
                self.image = pg.transform.flip(self.current_images[self.frame_index], True, False)
                self.frame_index += 1
                self.frame_override = False

            if self.state == 3 and self.frame_index == 7:
                self.swing_sound.play()

            if self.frame_index == self.frame_maxes[self.state]:
                if self.state == 2:
                    pass
                elif self.state == 5:
                    self.kill()
                else:
                    self.attack = False
                    self.hit = False
                    self.frame_index = 0


        # Gravity emulation with current map blockers.
        for block in blockers:
            # Checks to see if Fursa is in contact with the ground.
            if self.rect.colliderect(block):
                self.on_ground = True
                break
            else:
                self.on_ground = False

        if self.on_ground is False:
            # If not in contact with the ground, accelerates falling down every 20 ms.
            # Gravity is disabled when a jump animation is in progress.
            if (time - self.gravity_dt) >= 20:
                self.gravity_dt = time
                self.fall_rate *= 1.1 # Acceleration rate.
                for i in range(int(self.fall_rate)):
                    self.rect.y += 1
                    # Halts falling when Fursa lands on a block.
                    for block in blockers:
                        if self.rect.colliderect(block):
                            self.fall_rate = 1
                            self.on_ground = True
                            break
                    if self.on_ground is True:
                        break
class enemy_frames():
    def __init__(self):
        self.skeleton_frames = []
        self.skeleton_frames_func()

    def skeleton_frames_func(self):
        directory = "C:/Users/Andrew/Desktop/Python_Projects/Kismet/Enemies/Skeleton/Sprite Sheets"
        os.chdir(directory)

        # Spritesheet coordinates.                                                               Indexes
        coordinates = [
                         [(24 * i, 0, 24, 32) for i in range(0, 11)]       # Idle. -----------------0
                        ,[(22 * i, 0, 22, 33) for i in range(0, 13)]       # Walking----------------1
                        ,[(22 * i, 0, 22, 32) for i in range(0, 4 )]       # React------------------2
                        ,[(43 * i, 0, 43, 37) for i in range(0, 18)]       # Attacking--------------3
                        ,[(30 * i, 0, 30, 32) for i in range(0, 8 )]       # Hit--------------------4
                        ,[(33 * i, 0, 33, 32) for i in range(0, 15)]       # Death------------------5
                      ]

        sizes = [(72,96), (66,99), (66,96), (129,111), (90,96), (99,96)]

        self.skeleton_frame_maxes = [len(frame_amount) for frame_amount in coordinates]

        spritesheets = [spritesheet(file) for file in os.listdir(directory)]
        spritesheets_separate = [spritesheet.images_at(coordinates[i], colorkey = (0, 0, 0)) for i, spritesheet in enumerate(spritesheets)]

        for i, ss_sep in enumerate(spritesheets_separate):
            scaled_frames = [pg.transform.scale(ss_sep[e], sizes[i]) for e in range(0, len(ss_sep))]
            self.skeleton_frames.append(scaled_frames)

# -------------------------------------------------------NPCS-------------------------------------------------------------------
class Masir_sprite(pg.sprite.Sprite):
    def __init__(self, spawnx, spawny):
        super().__init__()
        self.frame_index = 0
        self.upload_frames()
        self.current_images = self.all_images[0]
        self.image = self.current_images[0]
        self.state = 0
        self.facing_right = True
        self.frame_override = True
        self.frame_dt = 0
        self.frame_speed = 300
        self.gravity_dt = 0
        self.fall_rate = 1
        self.rect = pg.Rect((spawnx, spawny), (256, 198)) # Spawn point and collision size.
        self.attack = False
        self.walk = False
        self.on_ground = False


    def upload_frames(self):
        idle_images = []
        walk_images = []
        action_images = []

        # State IDs
        #-----------------------0-------------1------------2----------
        self.all_images = [idle_images, walk_images, action_images]

        directories =           ["C:/Users/Andrew/Desktop/Python_Projects/Kismet/NPCs/Masir/Idle_Png"       # Idle animation.
                                ,"C:/Users/Andrew/Desktop/Python_Projects/Kismet/NPCs/Masir/Walk_Png"       # Walk animation.
                                ,"C:/Users/Andrew/Desktop/Python_Projects/Kismet/NPCs/Masir/Action_Png"]    # Action animation.


        # Create a list containing lists with all animation frames. Each list is referenceable by the state ID shown above.
        for i, directory in enumerate(directories):
            os.chdir(directory)
            for file in os.listdir(directory):
                self.all_images[i].append(pg.transform.scale(load_image(file), (256, 256)))

        # Create a list of number of frames for each animation.
        self.frame_maxes = [len(images) for images in self.all_images]

    def change_state(self):
        if self.attack:
            self.state = 2
            self.frame_speed = 125
        elif self.walk:
            self.state = 1
            self.frame_speed = 200
        else:
            self.state = 0
            self.frame_speed = 300

        self.current_images = self.all_images[self.state]

    def update(self, blockers, time):
        self.change_state()
        if (time - self.frame_dt) >= self.frame_speed or self.facing_right != self.frame_override:
            self.frame_dt = time

            if self.facing_right:
                self.image = self.current_images[self.frame_index]
                self.frame_index += 1
                self.frame_override = True
            else:
                self.image = pg.transform.flip(self.current_images[self.frame_index], True, False)
                self.frame_index += 1
                self.frame_override = False

            if self.frame_index == self.frame_maxes[self.state]:
                self.attack = False
                self.frame_index = 0

        # Gravity emulation with current map blockers.
        for block in blockers:
            # Checks to see if Fursa is in contact with the ground.
            if self.rect.colliderect(block):
                self.on_ground = True
                break
            else:
                self.on_ground = False

        if self.on_ground is False:
            # If not in contact with the ground, accelerates falling down every 20 ms.
            # Gravity is disabled when a jump animation is in progress.
            if (time - self.gravity_dt) >= 20:
                self.gravity_dt = time
                self.fall_rate *= 1.1 # Acceleration rate.
                for i in range(int(self.fall_rate)):
                    self.rect.y += 1
                    # Halts falling when Fursa lands on a block.
                    for block in blockers:
                        if self.rect.colliderect(block):
                            self.fall_rate = 1
                            self.on_ground = True
                            break
                    if self.on_ground is True:
                        break

# -------------------------------------------------------MAPS-------------------------------------------------------------------
# Starting area.
class Map_01:
    def __init__(self, npc_sprites, dialog_package):
        # Map graphics and music.
        os.chdir("C:/Users/Andrew/Desktop/Python_Projects/Kismet/Maps/Map_01")
        self.map = TiledMap('Map_01_1920x1080.tmx')
        self.music = pg.mixer.music.load('296 - The Tea Garden (Loop).mp3')
        pg.mixer.music.play(loops = -1, start = 0.0)
        self.map.make_map()
        self.cutscene = False
        self.first_stage = True
        self.battle = False
        self.event = 0
        self.Masir_dead = False
        coordinates = []

        # Portal animation.
        for i in range(0,7):
            coordinates.extend([(100 * e, 100 * i, 100, 100) for e in range(0, 8)])
        coordinates.extend([(100 * e, 700, 100, 100) for e in range(0, 5)])

        portal_images_ss = spritesheet('12_nebula_spritesheet.png')
        portal_images_separate = portal_images_ss.images_at(coordinates, colorkey = (0, 0, 0))
        self.portal_images = [pg.transform.scale(portal_images_separate[i], (160, 160)) for i in range(0, len(portal_images_separate))]
        self.p_index = 0
        self.portal_start = False
        self.portal_blast = pg.mixer.Sound('portal_noise.wav')
        self.portal_blast.set_volume(0.50)
        self.portal_aura = pg.mixer.Sound('portal_aura_noise.wav')
        self.portal_aura.set_volume(0.40)
        self.portal_blast_start = True
        self.portal_aura_start = True
        self.portal_rect = pg.Rect(1115,660,160,160)

        self.end_sounds = [self.portal_aura]

        # Declare npcs.
        self.Masir = Masir_sprite(800, 600)
        npc_sprites.add(self.Masir)

        # Dialog dictionary.
        self.dialog_start = True
        self.dialog_box = dialog_package[0]
        self.dialog_font = dialog_package[1]
        self.dialog_noise = dialog_package[2]
        self.e = 0
        self.a = 0
        self.script = {                0: ["Where am I?",   'Boy'],
                                       1: ["... Who am I?", 'Boy'],
                                       2: ["So you\'ve awakened, my child.", '???'],
                                       3: ["... Do you know me?", 'Boy'],
                                       4: ["... It seems you\'ve lost more of your memory than I would have liked.", '???'],
                                       5: ["Please explain. I'm so confused. Who am I?", 'Boy'],
                                       6: ["Your name is Fursa. You are the son of Chaos.", '???'],
                                      #7 is Masir portal scene.
                                       8: ["In the ancient tongue, your name means... chance.", '???'],
                                       9: ["Please follow me, as we have much to accomplish.", '???'],
                                       10:["Wait. What is your name?", 'Fursa'],
                                       11:["You may call me Masir, little one.", 'Masir']}


    def black_edges(self, screen):
        black = (0,0,0)
        pg.draw.rect(screen, black, (0,0,1920,200))
        pg.draw.rect(screen, black, (0,880,1920,200))

    # Function to render and blit dialog.
    def dialog(self, text, name, screen):
        self.black_edges(screen)
        screen.blit(self.dialog_box, (550,880))
        load_text = ''
        if self.dialog_start:
            self.dialog_noise.play()
            self.e = 0
            self.a = 0

        if len(text) > 50:
            i = 50
            while text[i] != ' ':
                i += 1
            if i > 52:
                i = 50
                while text[i] != ' ':
                    i -= 1

            new_text = [text[0:i], text[i+1:]]
            load_text_1 = new_text[0][0:self.e]
            load_text_2 = new_text[1][0:self.a]
            dialog_text_1, rect_1 = self.dialog_font.render(load_text_1)
            dialog_text_2, rect_2 = self.dialog_font.render(load_text_2)
            screen.blit(dialog_text_1, (600, 955))
            screen.blit(dialog_text_2, (600, 1005))
            self.e += 1
            if self.e >= i:
                self.a += 1

        else:
            load_text_1 = text[0:self.e]
            dialog_text_1, rect_1 = self.dialog_font.render(load_text_1)
            screen.blit(dialog_text_1, (600,955))
            self.e += 1

        name_text, rect_3 = self.dialog_font.render(name)
        screen.blit(name_text, (600,905))

    def cutscene_event(self, character, screen):

        if self.cutscene is False:
            if self.first_stage and character.state != 0:
                self.cutscene = True
                self.first_stage = False

            if abs(character.rect.centerx - self.Masir.rect.centerx) < 150:
                if self.Masir_dead is False:
                    self.cutscene = True

        if self.cutscene:
            if self.event < 7:
                self.dialog(self.script[self.event][0], self.script[self.event][1], screen)
                self.dialog_start = False
            elif self.event == 7:
                self.Masir.attack = True
                self.event += 1
                self.black_edges(screen)
            elif self.Masir.attack is False and self.event < 12:
                self.dialog(self.script[self.event][0], self.script[self.event][1], screen)
                self.dialog_start = False
            elif self.event >= 12:
                self.Masir.walk = True
                self.Masir.rect.x += 1
                self.black_edges(screen)
            else:
                self.black_edges(screen)

            if self.Masir.attack is True:
                if self.Masir.frame_index == 16:
                    self.portal_start = True
                    if self.portal_aura_start:
                        self.portal_aura.play(loops = -1)
                        self.portal_aura_start = False
                elif self.Masir.frame_index == 3 and self.portal_blast_start:
                    self.portal_blast.play()
                    self.portal_blast_start = False

            if self.Masir.rect.centerx == self.portal_rect.centerx:
                self.Masir.kill()
                self.cutscene = False
                self.Masir_dead = True

            # Allow exiting the game during a cutscene.
            for event in pg.event.get():
                # Allow to quit game. Included in this portion to be able to keep only one event loop.

                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                         pg.quit()
                         sys.exit()

                # Navigating cutscenes.
                elif event.type == pg.MOUSEBUTTONDOWN:
                    self.dialog_start = True
                    self.event += 1
                    if self.event == 2:
                        self.cutscene = False

        if self.portal_start is True:
            screen.blit(self.portal_images[self.p_index], (1115,660))
            self.p_index += 1
            if self.p_index == len(self.portal_images):
                self.p_index = 0


    def update(self, character, screen):
        self.cutscene_event(character, screen)

# Area 2
class Map_02:
    def __init__(self, npc_sprites, dialog_package, enemy_frames, enemy_sprites):
        # Map graphics and music.
        os.chdir("C:/Users/Andrew/Desktop/Python_Projects/Kismet/Maps/Map_02")
        self.map = TiledMap('Map_02.tmx')
        self.map.make_map()
        self.cutscene = False
        self.first_stage = True
        self.battle = False
        self.event = 0
        self.spawnx = 100
        self.spawny = 500
        coordinates = []

        # Battle Scene.
        os.chdir("C:/Users/Andrew/Desktop/Python_Projects/Kismet/Maps")
        self.battle_map = TiledMap('battle_scene.tmx')
        self.battle_map.make_map()
        self.battle_spawn_pos = self.battle_map.battle_spawns
        os.chdir("C:/Users/Andrew/Desktop/Python_Projects/Kismet/UI/Combat")
        self.combat_box = load_image('Combat UI Box.png')
        self.combat_box = pg.transform.scale(self.combat_box, (960,300))

        # Declare enemys.
        skeleton_01 = skeleton(enemy_frames, 600, 500)
        enemy_sprites.add(skeleton_01)

        # Dialog dictionary.
        self.dialog_start = True
        self.dialog_box = dialog_package[0]
        self.dialog_font = dialog_package[1]
        self.dialog_noise = dialog_package[2]
        self.e = 0
        self.a = 0
        self.script = {                0: ["Where'd you go?",   'Fursa'],
                                       1: ["*A voice starts to sound in Fursa's mind.*", ''],
                                       2: ["I am watching from afar, my child.", 'Masir'],
                                       3: ["I am afraid I must limit my aid. You must learn how to use your powers again.", 'Masir'],
                                       4: ["An evil enemy is up ahead. Go and vanquish it.", 'Masir']
                                      #  5  exits dialogue.

                                      #  6: ["Your name is Fursa. You are the son of Chaos.", '???'],
                                      # #7 is Masir portal scene.
                                      #  8: ["In the ancient tongue, your name means... chance.", '???'],
                                      #  9: ["Please follow me, as we have much to accomplish.", '???'],
                                      #  10:["Wait. What is your name?", 'Fursa'],
                                      #  11:["You may call me Masir, little one.", 'Masir']
                                      }

    def black_edges(self, screen):
        black = (0,0,0)
        pg.draw.rect(screen, black, (0,0,1920,200))
        pg.draw.rect(screen, black, (0,880,1920,200))

    # Function to render and blit dialog.
    def dialog(self, text, name, screen):
        self.black_edges(screen)
        screen.blit(self.dialog_box, (550,880))
        load_text = ''
        if self.dialog_start:
            self.dialog_noise.play()
            self.e = 0
            self.a = 0

        if len(text) > 50:
            i = 50
            while text[i] != ' ':
                i += 1
            if i > 52:
                i = 50
                while text[i] != ' ':
                    i -= 1

            new_text = [text[0:i], text[i+1:]]
            load_text_1 = new_text[0][0:self.e]
            load_text_2 = new_text[1][0:self.a]
            dialog_text_1, rect_1 = self.dialog_font.render(load_text_1)
            dialog_text_2, rect_2 = self.dialog_font.render(load_text_2)
            screen.blit(dialog_text_1, (600, 955))
            screen.blit(dialog_text_2, (600, 1005))
            self.e += 1
            if self.e >= i:
                self.a += 1

        else:
            load_text_1 = text[0:self.e]
            dialog_text_1, rect_1 = self.dialog_font.render(load_text_1)
            screen.blit(dialog_text_1, (600,955))
            self.e += 1

        name_text, rect_3 = self.dialog_font.render(name)
        screen.blit(name_text, (600,905))

    def cutscene_event(self, character, screen):
        if self.cutscene is False:
            if self.first_stage and character.state != 0:
                self.cutscene = True
                self.first_stage = False

        if self.cutscene:
            if self.event < 5:
                self.dialog(self.script[self.event][0], self.script[self.event][1], screen)
                self.dialog_start = False
            else:
                self.black_edges(screen)

            # Allow exiting the game during a cutscene.
            for event in pg.event.get():
                # Allow to quit game. Included in this portion to be able to keep only one event loop.
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                         pg.quit()
                         sys.exit()

                # Navigating cutscenes.
                elif event.type == pg.MOUSEBUTTONDOWN:
                    self.dialog_start = True
                    self.event += 1
                    if self.event == 5:
                        self.cutscene = False

    def battle_event(self, character, screen):
        self.map = self.battle_map
        screen.blit(self.combat_box, (0,780))
        screen.blit(self.combat_box, (960,780))


        # Allow exiting the game during a cutscene.
        for event in pg.event.get():
            # Allow to quit game. Included in this portion to be able to keep only one event loop.
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                     pg.quit()
                     sys.exit()

            # Navigating cutscenes.
            elif event.type == pg.MOUSEBUTTONDOWN:
                pass


    def update(self, character, screen):
        if character.battle is False:
            self.battle = False
            self.cutscene_event(character, screen)
        else:
            self.battle = True
            self.battle_event(character, screen)



# Game Start.
def main():

    # Game parameters.
    pg.mixer.pre_init(44100, -16, 2, 1024)
    pg.init()
    pg.event.set_allowed([pg.KEYDOWN, pg.KEYUP, pg.MOUSEBUTTONDOWN])
    resolution = width, height = 1920,1080
    flags = pg.FULLSCREEN | pg.HWSURFACE | pg.DOUBLEBUF
    screen = pg.display.set_mode(resolution, flags)
    screen.set_alpha(None)
    pg.display.set_caption('Kismet')
    clock = pg.time.Clock()
    os.chdir("C:/Users/Andrew/Desktop/Python_Projects/Kismet/UI/Dialog")
    dialog_box = load_image('dialogue_box.png')
    dialog_box = pg.transform.scale(dialog_box, (795, 195))
    dialog_font = pg.freetype.Font('eight-bit-dragon.otf', size = 24)
    dialog_noise = pg.mixer.Sound('chat_noise.wav')
    dialog_package = [dialog_box, dialog_font, dialog_noise]
    os.chdir("C:/Users/Andrew/Desktop/Python_Projects/Kismet/UI/Fonts")
    fps_font = pg.freetype.Font('digital-7.ttf', size = 48)

    # Declare character sprites.
    Fursa = Fursa_sprite()
    character_sprites = pg.sprite.GroupSingle()
    character_sprites.add(Fursa)

    # Declare npc sprites.
    npc_sprites = pg.sprite.Group()

    # Declare enemy sprites.
    enemy_images = enemy_frames()
    enemy_sprites = pg.sprite.Group()

    # Declare particle sprites.
    blast_particle_frames = blast_frames()
    particle_sprites = pg.sprite.Group()

    # Declare Initial Map.

    # Test
    current_map = Tutorial_Area = Map_02(npc_sprites, dialog_package, enemy_images, enemy_sprites)

    # Normal
    # Starting_Area = Map_01(npc_sprites, dialog_package)
    # current_map = Starting_Area

    map_index = 0
    map_travel = False

    # Game Loop
    while True:

        pg.event.pump()

        time = pg.time.get_ticks()
        dt = clock.tick(90) # Framerate.

        # Surfaces are blit and updated in order of back to front on screen.

        # Layer 1-------- Screen background back surface refresh.
        screen.blit(current_map.map.back_surface, (0,0))

        # Layer 2-------- Particle sprites update.
        particle_sprites.update(Fursa, dt, particle_sprites, enemy_sprites)
        particle_sprites.draw(screen)

        enemy_sprites.update(current_map.map.blockers, time, Fursa, particle_sprites)
        enemy_sprites.draw(screen)

        # Layer 4-------- Character sprites update.
        character_sprites.update(current_map.map.blockers, time, dt, current_map.cutscene, screen,
                                 current_map, map_travel, character_sprites, enemy_sprites, particle_sprites, blast_particle_frames.frames)
        character_sprites.draw(screen)

        # Layer 5-------- NPC sprites update.
        npc_sprites.update(current_map.map.blockers, time)
        npc_sprites.draw(screen)

        # Layer 6-------- Screen background front surface refresh.
        screen.blit(current_map.map.front_surface, (0,0))

        current_map.update(Fursa, screen)

        # Print FPS on top right corner of the screen.
        fps_text, rect = fps_font.render(str(int(round(clock.get_fps()))))
        screen.blit(fps_text, (1860, 10))
        print(clock.get_fps())


        # Handle transitioning to and from different maps.
        """ Map Index -------------------- Map --------------
           |   00                      Starting_Area     |
           |   01                      Tutorial_Area     |
         --------------------------------------------------- """
        if Fursa.map_forward is True:
            map_index += 1
            if map_index == 1:
                current_map = Tutorial_Area = Map_02(npc_sprites, dialog_package, enemy_images, enemy_sprites)
            Fursa.rect.x = current_map.spawnx
            Fursa.rect.y = current_map.spawny
            map_travel = True
        else:
            map_travel = False

        pg.display.flip()


if __name__ == '__main__':
    main()
