import pygame as pg
import pytmx
from pytmx.util_pygame import load_pygame
import sys
import os

def load_image(name):
    image = pg.image.load(name)
    return image

class TiledMap:
    def __init__(self, filename):
        tm = load_pygame(filename)
        self.width = tm.width * tm.tilewidth
        self.height = tm.height * tm.tileheight
        self.tm = tm

    def render(self, surface):
        ti = self.tm.get_tile_image_by_gid
        for layer in self.tm.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    tile = ti(gid)
                    if tile:
                        surface.blit(tile, (x * self.tm.tilewidth, y * self.tm.tileheight))

    def make_map(self):
        self.surface = pg.Surface((self.width, self.height))
        self.render(self.surface)
        return self.surface

class Fursa_sprite(pg.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.frame_index = 0
        self.upload_frames()
        self.current_images = self.idle_images
        self.image = self.idle_images[0]
        self.rect = self.image.get_rect()
        self.key_pressed = False
        # self.change_state = True

    def upload_frames(self):
        self.idle_images = []
        self.walk_images = []
        self.all_images = [self.idle_images, self.walk_images]
        self.directories = ["C:/Users/Andrew/Desktop/Python_Projects/Kismet/Furas/Idle"   # Idle Animation
                           ,"C:/Users/Andrew/Desktop/Python_Projects/Kismet/Furas/Walk"]  # Walking Animation

        for i, directory in enumerate(self.directories):
            os.chdir(directory)
            for file in os.listdir(directory):
                self.all_images[i].append(pg.transform.scale(load_image(file), (156, 156)))
        self.frame_index_max = 12

    def idle(self):
        return True

    def walk(self):
        return False

    def change_state(self):
        if self.key_pressed:
            self.current_images = self.walk_images
        else:
            self.current_images = self.idle_images

    def handle_keys(self):
        pg.event.pump()
        keys = pg.key.get_pressed()
        dist = 6
        if keys[pg.K_UP]:
            self.rect.y -= dist
        if keys[pg.K_RIGHT]:
            self.rect.x += dist
        if keys[pg.K_DOWN]:
            self.rect.y += dist
        if keys[pg.K_LEFT]:
            self.rect.x -= dist


    def update(self):
        self.handle_keys()
        self.change_state()
        self.image = self.current_images[self.frame_index]
        self.frame_index += 1
        if self.frame_index == self.frame_index_max:
            self.frame_index = 0

class Level_Start:
    def __init__(self):
        os.chdir("C:/Users/Andrew/Desktop/Python_Projects/Kismet/Level Start")
        self.map = TiledMap('Starting_Area.tmx')
        self.music = pg.mixer.music.load('301 - Good Memories.mp3')
        pg.mixer.music.play(loops = -1, start = 0.0)
        self.map.make_map()

# Game Loop
def main():
    pg.init()
    os.chdir("C:/Users/Andrew/Desktop/Python_Projects/Kismet")
    screen = pg.display.set_mode((1280, 640))
    Sprite_surface = pg.Surface((1280, 640))
    pg.display.set_caption('Kismet')
    clock = pg.time.Clock()

    Starting_Area = Level_Start()
    Fursa = Fursa_sprite()
    Sprites_list = pg.sprite.Group()
    Sprites_list.add(Fursa)


    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()
            if event.type == pg.KEYDOWN:
                Fursa.key_pressed = True
            else:
                Fursa.key_pressed = False

        # Screen Background Refresh
        screen.blit(Starting_Area.map.surface, (0,0))
        Sprites_list.update()
        Sprites_list.draw(screen)

        clock.tick(10)
        pg.display.flip()

if __name__ == '__main__':
    main()
