import logging
import random

import pygame
from pygame.locals import *

from pytmx import *
from pytmx.util_pygame import load_pygame
import pyganim

import conf

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.WARN)
logger.addHandler(ch)
logger.setLevel(logging.WARN)


def init_screen(width, height):
    """ Set the screen mode
    This function is used to handle window resize events
    """
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


class TiledRenderer(object):
    """
    Super simple way to render a tiled map
    """

    def __init__(self, filename):
        tm = load_pygame(filename)

        # self.size will be the pixel size of the map
        # this value is used later to render the entire map to a pygame surface
        self.pixel_size = tm.width * tm.tilewidth, tm.height * tm.tileheight
        # TODO: Screen modes
        screen = init_screen(conf.scale*tm.width*tm.tilewidth, conf.scale*tm.height*tm.tileheight)
        self.tmx_data = tm
        self.animate_tiles()
        self.characters = self.build_character_index()
        self.spawns = self.build_spawn_index()

    def render_map(self, surface):
        """ Render our map to a pygame surface

        Feel free to use this as a starting point for your pygame app.
        This method expects that the surface passed is the same pixel
        size as the map.

        Scrolling is a often requested feature, but pytmx is a map
        loader, not a renderer!  If you'd like to have a scrolling map
        renderer, please see my pyscroll project.
        """

        # fill the background color of our render surface
        if self.tmx_data.background_color:
            surface.fill(pygame.Color(self.tmx_data.background_color))

        # iterate over all the visible layers, then draw them
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, TiledTileLayer):
                self.render_tile_layer(surface, layer)
            elif isinstance(layer, TiledImageLayer):
                self.render_image_layer(surface, layer)

    def render_tile_layer(self, surface, layer):
        """ Render all TiledTiles in this layer
        """
        # deref these heavily used references for speed
        tw = self.tmx_data.tilewidth
        th = self.tmx_data.tileheight
        surface_blit = surface.blit

        # iterate over the tiles in the layer, and blit them
        for x, y, image in layer.tiles():
            if isinstance(image, pyganim.PygAnimation):
                image.blit(surface, (x * tw, y * th))
            else:
                surface_blit(image, (x * tw, y * th))

    def render_image_layer(self, surface, layer):
        if layer.image:
            surface.blit(layer.image, (0, 0))

    def build_character_index(self):
        characters = {}
        for gid, props in self.tmx_data.tile_properties.items():
            if not ("team" in props and
                    "character" in props and
                    "mode" in props):
                continue

            name = props["character"]
            team = props["team"]
            mode = props["mode"]
            if team not in characters:
                characters[team] = {}
            if team not in characters[team]:
                characters[team][name] = {}
            characters[team][name][mode] = gid
        return characters

    def build_spawn_index(self):
        spawns = {}
        for gid, props in self.tmx_data.tile_properties.items():
            if "spawn" not in props:
                continue
            spawns[props["spawn"]] = gid
        return spawns

    def animate_tiles(self):
        for gid, props in self.tmx_data.tile_properties.items():
            if "frames" not in props:
                continue
            frames = [(self.tmx_data.get_tile_image_by_gid(frame.gid), frame.duration)
                      for frame in props['frames']]
            if frames:
                surface = pyganim.PygAnimation(frames)
                surface.play()
                self.tmx_data.images[gid] = surface


class SimpleTest(object):
    """ Basic app to display a rendered Tiled map
    """

    def __init__(self, filename):
        self.renderer = None
        self.running = False
        self.exit_status = 0
        self.clock = pygame.time.Clock()
        self.load_map(filename)
        self.selection = None

        # Custom, per-map setup:
        for color, gid in self.renderer.spawns.items():
            tiles = list(self.renderer.tmx_data.get_tile_locations_by_gid(gid))
            if tiles:
                random.shuffle(tiles)
                self.renderer.tmx_data.layers[tiles[0][2]].data[tiles[0][1]][tiles[0][0]] = self.renderer.characters[color]["dudess"]["idle"]
                self.renderer.tmx_data.layers[tiles[1][2]].data[tiles[1][1]][tiles[1][0]] = self.renderer.characters[color]["dude"]["idle"]
                for tile in tiles[2:]:
                    self.renderer.tmx_data.layers[tile[2]].data[tile[1]][tile[0]] = 0


    def load_map(self, filename):
        """ Create a renderer, load data, and print some debug info
        """
        self.renderer = TiledRenderer(filename)

        logger.info("Objects in map:")
        for obj in self.renderer.tmx_data.objects:
            logger.info(obj)
            for k, v in obj.properties.items():
                logger.info("%s\t%s", k, v)

        logger.info("GID (tile) properties:")
        for k, v in self.renderer.tmx_data.tile_properties.items():
            logger.info("%s\t%s", k, v)

    def draw(self, surface):
        """ Draw our map to some surface (probably the display)
        """
        # first we make a temporary surface that will accommodate the entire
        # size of the map.
        # because this demo does not implement scrolling, we render the
        # entire map each frame
        temp = pygame.Surface(self.renderer.pixel_size)

        # render the map onto the temporary surface
        self.renderer.render_map(temp)

        # now resize the temporary surface to the size of the display
        # this will also 'blit' the temp surface to the display
        pygame.transform.scale(temp, surface.get_size(), surface)

        # display a bit of use info on the display
        f = pygame.font.Font(pygame.font.get_default_font(), 20)
        i = f.render('press ESC to quit',
                     1, (180, 0, 0))
        surface.blit(i, (0, 0))

    def run(self):
        """ This is our app main loop
        """
        self.running = True
        self.exit_status = 1

        while self.running:
            self.clock.tick(15)
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.exit_status = 0
                    self.running = False

                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        self.exit_status = 0
                        self.running = False

                elif event.type == VIDEORESIZE:
                    #init_screen(event.w, event.h)
                    pass

                elif event.type == MOUSEBUTTONUP:
                    pos = pygame.mouse.get_pos()
                    x = int(pos[0]/(self.renderer.tmx_data.tilewidth*conf.scale))
                    y = int(pos[1]/(self.renderer.tmx_data.tileheight*conf.scale))
                    layer = self.renderer.tmx_data.get_layer_by_name("Sprite Layer")
                    tile = self.renderer.tmx_data.get_layer_by_name("World Layer").data[y][x]
                    terrain = self.renderer.tmx_data.get_tile_properties_by_gid(tile)["terrain"]
                    if self.selection:
                        if layer.data[y][x] != 0:
                            print("Something already here.")
                        elif terrain == "water":
                            print("oh no is water")
                        elif terrain == "mountains":
                            print("oh no is mountain")
                        else:
                            layer.data[y][x] = self.selection[2]
                            layer.data[self.selection[1]][self.selection[0]] = 0
                            self.selection = None
                    else:
                        if layer.data[y][x] != 0:
                            self.selection = (x, y, layer.data[y][x])


            self.draw(screen)
            pygame.display.flip()

        return self.exit_status


if __name__ == '__main__':
    pygame.init()
    pygame.font.init()
    screen = init_screen(conf.window["width"], conf.window["height"])
    pygame.display.set_caption('Honk')

    SimpleTest("assets/maps/river_bend_demo.tmx").run()
