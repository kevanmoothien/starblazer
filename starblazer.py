from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

__version__ = "0.1"

import json
import math
import os
import random
import sys

import six
import sge
import xsge_gui
import xsge_physics


if getattr(sys, "frozen", False):
    __file__ = sys.executable

DATA = os.path.join(os.path.dirname(__file__), "data")
CONFIG = os.path.join(os.path.expanduser("~"), ".config", "star_blazer")

SCREEN_SIZE = [320, 240]
TILE_SIZE = 16
FPS = 60

ARENA_Y = 25
ARENA_HEIGHT = 200

PLAYER_ORIGIN_X = 5
PLAYER_ORIGIN_Y = 40
PLAYER_FPS = 12
PLAYER_BBOX_X = 50
PLAYER_BBOX_Y = 3
PLAYER_BBOX_WIDTH = 11
PLAYER_BBOX_HEIGHT = 11
PLAYER_BULLET_X = 16
PLAYER_BULLET_Y = 0
PLAYER_WALK_SPEED = 1
PLAYER_INVINCIBLE_TIME = 180

BULLET_COST = 20
BULLET_SPEED = 4

ENEMY_SPEED = 0.375
GREENKOOPA_SPEED = 0.375
SPINY_SPEED = 0.375
REDKOOPA_SPEED = 0.75
HAMMERBRO_SPEED = 0.25
SHELL_SPEED = 2

HAMMER_INTERVAL = 60
HAMMER_WARMUP = 30
HAMMER_FOLLOWTHROUGH = 15
HAMMER_SPEED = 3

SPAWN_INTERVAL = 30

SCORETITLE_Y = 4
SCORE_X = 160
SCORE_Y = 16

loaded_music = {}

fullscreen = False
sound_enabled = True
music_enabled = True
fps_enabled = False
joystick_threshold = 0.1
left_key = ["left", "a"]
right_key = ["right", "d"]
up_key = ["up", "w"]
down_key = ["down", "s"]
bomb_key = ["b"]
action_key = ["space"]
pause_key = ["enter", "p"]
left_js = [(0, "axis-", 0), (0, "hat_left", 0)]
right_js = [(0, "axis+", 0), (0, "hat_right", 0)]
up_js = [(0, "axis-", 1), (0, "hat_up", 0)]
down_js = [(0, "axis+", 1), (0, "hat_down", 0)]
action_js = [(0, "button", 1), (0, "button", 3)]
pause_js = [(0, "button", 9)]

score = 0
highscores = [0, 0, 0, 0, 0]
tank = False
fuelship = False
deploy = False

class Game(sge.dsp.Game):
    fps_time = 0
    fps_frames = 0
    fps_text = ""
    def event_step(self, time_passed, delta_mult):
        if fps_enabled:
            self.fps_time += time_passed
            self.fps_frames += 1
            if self.fps_time >= 250:
                self.fps_text = str(int(round((1000 * self.fps_frames) /
                                              self.fps_time)))
                self.fps_time = 0
                self.fps_frames = 0

            self.project_text(font, self.fps_text, self.width - 4,
                              self.height - 4, z=1000,
                              color=sge.gfx.Color("green"), halign="right",
                              valign="bottom")
    def event_key_press(self, key, char):
        if key == "f11":
            if self.fullscreen:
                self.scale = 2
                self.fullscreen = False
                self.scale = None
            else:
                self.fullscreen = True
    def event_mouse_button_press(self, button):
        if button == "middle":
            self.event_close()
    def event_close(self):
        self.end()
    def event_paused_close(self):
        self.event_close()

class TitleScreen(sge.dsp.Room):
    def __init__(self):
        super(TitleScreen, self).__init__(background=background)
    def event_room_start(self):
        self.add(gui_handler)
        self.event_room_resume()
    def event_room_resume(self):
        sge.snd.Music.clear_queue()
        sge.snd.Music.stop(1000)
        MainMenu.create()
    def event_step(self, time_passed, delta_mult):
        sge.game.project_text(font, "High Score", SCORE_X - 35, SCORETITLE_Y,
                              color=sge.gfx.Color("white"), halign="center")
        sge.game.project_text(font, str(score), SCORE_X + 35, SCORETITLE_Y,
                              color=sge.gfx.Color("blue"), halign="center")

class Arena(sge.dsp.Room):
    def __init__(self, difficulty=0):
        super(Arena, self).__init__(
            background=background, object_area_width=TILE_SIZE,
            object_area_height=TILE_SIZE)
        self.difficulty = difficulty
        self.stage = -1
        self.spawn_chance = 0
        self.spawn_limit = 2
        self.spawn_choices = [Plane]
        self.gameover = False
        self.infrastructure = [Cactus, Building, Tower]
        if difficulty == 0:
            self.brick_columns = 5
            self.recover_time = 0
            self.stage_interval = 90 * FPS
        elif difficulty == 1:
            self.brick_columns = 4
            self.recover_time = 3
            self.stage_interval = 45 * FPS
            self.stage = 0
        elif difficulty == 2:
            self.brick_columns = 3
            self.recover_time = 5
            self.stage_interval = 30 * FPS
            self.stage = 1
        else:
            self.brick_columns = 1
            self.recover_time = 10
            self.stage_interval = 10 * FPS
            self.stage = 5

        self.event_alarm("next_stage")
        self.alarms["spawn"] = SPAWN_INTERVAL

    def pause(self):
        global highscores
        highscores[self.difficulty] = max(highscores[self.difficulty], score)
        sge.snd.Music.pause()
        PauseMenu.create()

    def event_room_start(self):
        global score
        self.add(gui_handler)
        score = 0
        w = SCREEN_SIZE[0]
        y = ARENA_Y - TILE_SIZE
        xsge_physics.Solid.create(0, y, bbox_width=w, bbox_height=TILE_SIZE)
        y = ARENA_Y + ARENA_HEIGHT
        xsge_physics.Solid.create(0, y, bbox_width=w, bbox_height=TILE_SIZE)

        tile_w = brick_sprite.width
        tile_h = brick_sprite.height

        x = tile_w + TILE_SIZE
        y = ARENA_Y + ARENA_HEIGHT / 2

        Player.create(x, y)

        self.event_room_resume()

    def event_room_resume(self):
        play_music("music.mid")

    def event_step(self, time_passed, delta_mult):
        # score
        sge.game.project_text(font, "Score", SCORE_X, SCORETITLE_Y,
                              color=sge.gfx.Color("white"), halign="center")
        sge.game.project_text(font, str(score), SCORE_X + 35, SCORETITLE_Y,
                              color=sge.gfx.Color("blue"), halign="center")
        # level
        sge.game.project_text(font, "Level", 30, SCORETITLE_Y,
                              color=sge.gfx.Color("white"), halign="center")
        sge.game.project_text(font, str(1), 60, SCORETITLE_Y,
                              color=sge.gfx.Color("blue"), halign="center")
        # Fuel
        sge.game.project_text(font, "Fuel", 260, SCORETITLE_Y,
                              color=sge.gfx.Color("white"), halign="center")
        sge.game.project_text(font, str(10), 290, SCORETITLE_Y,
                              color=sge.gfx.Color("blue"), halign="center")
    def event_alarm(self, alarm_id):
        global highscores
        global tank
        global fuelship

        if alarm_id == "next_stage":
            self.stage += 1

            if self.stage <= 0:
                self.spawn_chance = 0.1
                self.spawn_limit = 2
                self.spawn_choices = [Plane, Tanker, Fuelship]
            elif self.stage <= 1:
                self.spawn_chance = 0.15
                self.spawn_limit = 3
                self.spawn_choices = [Plane, Tanker, Fuelship]
            elif self.stage <= 2:
                self.spawn_chance = 0.25
                self.spawn_limit = 4
                self.spawn_choices = [Plane, Plane, Plane, Tanker, Tanker, Fuelship, Fuelship]
            elif self.stage <= 3:
                self.spawn_chance = 0.5
                self.spawn_limit = 5
                self.spawn_choices = [Plane, Plane, Plane, Plane, Plane, Tanker, Tanker, Fuelship, Fuelship]
            elif self.stage <= 4:
                self.spawn_chance = 0.5
                self.spawn_limit = 6
                self.spawn_choices = [Plane, Plane, Plane, Plane, Plane,
                                      GreenKoopa, GreenKoopa, Spiny, RedKoopa]
            elif self.stage <= 5:
                self.spawn_chance = 0.5
                self.spawn_limit = 6
                self.spawn_choices = [Plane, Plane, Plane, Plane, Plane,
                                      Plane, Plane, Plane, GreenKoopa,
                                      GreenKoopa, GreenKoopa, GreenKoopa,
                                      Spiny, Spiny, Spiny, Spiny, RedKoopa,
                                      RedKoopa, HammerBro]
            elif self.stage <= 6:
                self.spawn_chance = 0.5
                self.spawn_limit = 6
                self.spawn_choices = [Plane, Plane, Plane, Plane, Plane,
                                      Plane, GreenKoopa, GreenKoopa, Spiny,
                                      Spiny, Spiny, Spiny, Spiny, Spiny,
                                      RedKoopa, RedKoopa, HammerBro]
            else:
                self.spawn_chance = 1 - ((1 - self.spawn_chance) / 2)
                self.spawn_limit = 7

                self.spawn_choices.append(random.choice([
                    Spiny, RedKoopa, RedKoopa, RedKoopa, HammerBro, HammerBro,
                    HammerBro]))

            self.alarms["next_stage"] = self.stage_interval

        elif alarm_id == "spawn":
            enemies = list(filter(lambda o: isinstance(o, Enemy), self.objects))
            if (random.random() < self.spawn_chance and
                    len(enemies) < self.spawn_limit):
                cls = random.choice(self.spawn_choices)
                y = random.uniform(ARENA_Y + TILE_SIZE,
                                   ARENA_Y + ARENA_HEIGHT - TILE_SIZE)
                if cls == Tanker:
                    if tank == False:
                        tank = True
                        Tanker.create(0, 255)
                elif cls == Fuelship:
                    if fuelship == False:
                        fuelship = True
                        deploy = False
                        Fuelship.create(0, 30)
                else:
                    cls.create(self.width + TILE_SIZE, y)

                infra = random.choice(self.infrastructure)
                infra.create(300, 255)

            self.alarms["spawn"] = SPAWN_INTERVAL

        elif alarm_id == "gameover":
            highscores[self.difficulty] = max(highscores[self.difficulty],
                                              score)
            room = GameOverScreen()
            room.start()

    def event_key_press(self, key, char):
        if key == "escape":
            self.pause()

class Player(xsge_physics.Collider):
    def __init__(self, x, y):
        super(Player, self).__init__(
            x, y, z=y, sprite=player_stand_sprite, checks_collisions=False,
            bbox_x=PLAYER_BBOX_X, bbox_y=PLAYER_BBOX_Y, bbox_width=PLAYER_BBOX_WIDTH,
            bbox_height=PLAYER_BBOX_HEIGHT)
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.shooting = False
        self.dead = False
        self.recovering = False
        self.recover_timer = None

    def refresh_input(self):
        key_controls = [left_key, right_key, up_key, down_key]
        js_controls = [left_js, right_js, up_js, down_js]
        states = [0 for i in key_controls]

        for i in six.moves.range(len(key_controls)):
            for choice in key_controls[i]:
                value = sge.keyboard.get_pressed(choice)
                states[i] = max(states[i], value)

        for i in six.moves.range(len(js_controls)):
            for choice in js_controls[i]:
                j, t, c = choice
                value = min(sge.joystick.get_value(j, t, c), 1)
                states[i] = max(states[i], value)

        self.left_pressed = states[0]
        self.right_pressed = states[1]
        self.up_pressed = states[2]
        self.down_pressed = states[3]

    def action(self):
        global score

        if not self.dead and not self.recovering:
            play_sound(shoot_sound)
            self.shooting = True
            self.alarms["shoot_end"] = 2 * FPS / PLAYER_FPS
            Bullet.create(self.x + PLAYER_BULLET_X, self.y + PLAYER_BULLET_Y)
            score = max(0, score - BULLET_COST)

    def bomb(self):
        global score

        if not self.dead and not self.recovering:
            play_sound(shoot_sound)
            self.shooting = True
            self.alarms["shoot_end"] = 2 * FPS / PLAYER_FPS
            Bomb.create(self.x + PLAYER_BULLET_X, self.y + PLAYER_BULLET_Y)
            score = max(0, score - BULLET_COST)

    def kill(self):
        if not self.dead and ("invincible" not in self.alarms or
                              sge.game.current_room.gameover):
            self.dead = True
            self.xvelocity = 0
            self.yvelocity = 0
            self.sprite = player_die_sprite
            self.image_index = 0
            play_sound(die_sound)

    def recover(self):
        if self.dead and not self.recovering:
            self.recovering = True
            self.recover_timer = None
            self.sprite = player_recover_sprite
            self.image_index = 0
            self.image_fps = None

    def event_step(self, time_passed, delta_mult):
        if not self.dead and not self.recovering:
            self.refresh_input()

            # Set speed
            self.xvelocity = ((self.right_pressed - self.left_pressed) *
                              PLAYER_WALK_SPEED)
            self.yvelocity = ((self.down_pressed - self.up_pressed) *
                              PLAYER_WALK_SPEED)
            self.speed = min(self.speed, PLAYER_WALK_SPEED)

            # Set image
            if self.shooting:
                if self.xvelocity or self.yvelocity:
                    self.sprite = player_walk_shoot_sprite
                else:
                    self.sprite = player_stand_shoot_sprite
            else:
                if self.xvelocity or self.yvelocity:
                    self.sprite = player_walk_sprite
                else:
                    self.sprite = player_stand_sprite

            # Set Z value
            self.z = self.bbox_bottom

        if self.bbox_left < 0:
            self.bbox_left = 0
        elif self.bbox_right > sge.game.current_room.width:
            self.bbox_right = sge.game.current_room.width

        # Recovery countdown
        if self.recover_timer:
            y = self.bbox_bottom + 4
            sge.game.current_room.project_text(
                font, str(self.recover_timer), self.x, y, 1000,
                color=sge.gfx.Color("navy"), halign="center")

        if "invincible" in self.alarms:
            self.image_alpha = 128
        else:
            self.image_alpha = 255

    def event_alarm(self, alarm_id):
        if alarm_id == "shoot_end":
            self.shooting = False
        elif alarm_id == "recover":
            if (self.recover_timer is not None and
                    not sge.game.current_room.gameover):
                self.recover_timer -= 1
                if self.recover_timer <= 0:
                    self.recover()
                else:
                    self.alarms["recover"] = FPS
            else:
                self.recover_timer = None

    def event_animation_end(self):
        if self.recovering:
            self.dead = False
            self.recovering = False
            self.recover_timer = None
            self.sprite = player_stand_sprite
            self.image_index = 0
            self.image_fps = None
            self.alarms["invincible"] = PLAYER_INVINCIBLE_TIME

            if sge.game.current_room.gameover:
                self.kill()
        elif self.dead:
            self.image_index = self.sprite.frames - 1
            self.image_fps = 0
            if not sge.game.current_room.gameover:
                if sge.game.current_room.recover_time > 0:
                    self.recover_timer = sge.game.current_room.recover_time
                    self.alarms["recover"] = FPS
                else:
                    self.recover_timer = 0
                    self.alarms["recover"] = FPS / 4

    def event_key_press(self, key, char):
        if key in action_key:
            self.action()
        if key in pause_key:
            sge.game.current_room.pause()
        if key in bomb_key:
            self.bomb()

class Brick(xsge_physics.Solid):
    def __init__(self, x, y):
        super(Brick, self).__init__(x, y, z=0, sprite=brick_sprite,
                                    checks_collisions=False)
    def kill(self):
        Corpse.create(self.x, self.y, sprite=brick_shard_sprite, xvelocity=-2,
                      yvelocity=-3, yacceleration=0.25)
        Corpse.create(self.x + 8, self.y, sprite=brick_shard_sprite,
                      xvelocity=2, yvelocity=-3, yacceleration=0.25)
        play_sound(brick_break_sound)
        self.destroy()

class Bullet(sge.dsp.Object):
    def __init__(self, x, y):
        super(Bullet, self).__init__(
            x, y, z=y, sprite=bullet_sprite, xvelocity=BULLET_SPEED,
            checks_collisions=False)
    def event_step(self, time_passed, delta_mult):
        if self.bbox_left > sge.game.current_room.width:
            self.destroy()
    def event_collision(self, other, xdirection, ydirection):
        if isinstance(other, Enemy):
            Corpse.create(self.x, self.y, z=(other.z + 1),
                          sprite=bullet_dead_sprite, life=8)
            self.destroy()
            other.hurt()

class Bomb(sge.dsp.Object):
    def __init__(self, x, y, sprite=None, visible=True, xvelocity=0,
                 yvelocity=0):
        super(Bomb, self).__init__(
            x, y, sprite=bomb_sprite,
            xvelocity=1, yvelocity=2)
    def event_step(self, time_passed, delta_mult):
        if self.y > sge.game.current_room.height + self.image_origin_y:
            Corpse.create(self.x, sge.game.current_room.height - 20,
                          sprite=explosion_sprite, life=8)
            self.destroy()
    def event_collision(self, other, xdirection, ydirection):
        if isinstance(other, Enemy):
            Corpse.create(self.x, self.y, z=(other.z + 1),
                          sprite=explosion_sprite, life=8)
            self.destroy()
            other.hurt()

class Enemy(xsge_physics.Collider):
    health = 1
    points = 100
    def hurt(self):
        self.health -= 1
        if self.health > 0:
            play_sound(enemy_hit_sound)
        else:
            self.kill()
    def kill(self):
        global score
        play_sound(kick_sound)
        Corpse.create(self.x, self.y, sprite=self.sprite, yvelocity=-2,
                      yacceleration=0.25, image_yscale=-1, image_fps=0)
        score += self.points
        self.destroy()
    def event_create(self):
        if self.bbox_top < ARENA_Y:
            self.bbox_top = ARENA_Y
        elif self.bbox_bottom > ARENA_Y + ARENA_HEIGHT:
            self.bbox_bottom = ARENA_Y + ARENA_HEIGHT
    def event_step(self, time_passed, delta_mult):
        self.z = self.bbox_bottom
        if self.x - self.image_origin_x + self.sprite.width < 0:
            # if not sge.game.current_room.gameover:
            #     sge.game.current_room.gameover = True
            #     for obj in sge.game.current_room.objects[:]:
            #         if isinstance(obj, (Player, Brick)):
            #             obj.kill()
            #     sge.game.current_room.alarms["gameover"] = 5 * FPS
            #     sge.snd.Music.clear_queue()
            #     sge.snd.Music.stop(5000)
            self.destroy()
    def event_collision(self, other, xdirection, ydirection):
        if isinstance(other, Brick):
            self.kill()
            other.kill()
        elif isinstance(other, Player):
            other.kill()
    def event_physics_collision_left(self, other, move_loss):
        self.event_collision(other, -1, 0)
    def event_physics_collision_right(self, other, move_loss):
        self.event_collision(other, 1, 0)
    def event_physics_collision_top(self, other, move_loss):
        self.event_collision(other, 0, -1)
    def event_physics_collision_bottom(self, other, move_loss):
        self.event_collision(other, 0, 1)

class Goomba(Enemy):
    def __init__(self, x, y):
        super(Goomba, self).__init__(x, y, z=y, sprite=goomba_sprite,
                                     xvelocity=-ENEMY_SPEED)
class Plane(Enemy):
    def __init__(self, x, y):
        super(Plane, self).__init__(x, y, z=y, sprite=planes_sprite,
                                     xvelocity=-ENEMY_SPEED)

class Fuelship(Enemy):
    def __init__(self, x, y):
        super(Fuelship, self).__init__(x, y, z=y, sprite=fuelship_sprite,
                                    xvelocity=ENEMY_SPEED)
    def event_step(self, time_passed, delta_mult):
        global fuelship
        global deploy
        if self.x > 300:
            fuelship = False
            self.destroy()
        if self.x > 180 and deploy == False:
            deploy = True
            Fuel.create(self.x, self.y)

class Fuel(sge.dsp.Object):
    def __init__(self, x, y, sprite=None, visible=True, xvelocity=0,
                 yvelocity=0):
        super(Fuel, self).__init__(
            x, y, sprite=fuelbox_sprite,
            xvelocity=1, yvelocity=2)
    def event_step(self, time_passed, delta_mult):
        if self.y > sge.game.current_room.height + self.image_origin_y:
            # Corpse.create(self.x, sge.game.current_room.height - 20,
            #               sprite=explosion_sprite, life=8)
            self.destroy()
    # def event_collision(self, other, xdirection, ydirection):
    #     if isinstance(other, Enemy):
    #         Corpse.create(self.x, self.y, z=(other.z + 1),
    #                       sprite=explosion_sprite, life=8)
    #         self.destroy()
    #         other.hurt()

class Tanker(Enemy):
    def __init__(self, x, y):
        super(Tanker, self).__init__(x, y, z=y, sprite=tank_sprite,
                                     xvelocity=ENEMY_SPEED)
    def event_step(self, time_passed, delta_mult):
        global tank
        if self.x > 300:
            tank = False
            self.destroy()
    def kill(self):
        global score
        global tank
        play_sound(kick_sound)
        Corpse.create(self.x, self.y, sprite=self.sprite, yvelocity=-2,
                      yacceleration=0.25, image_yscale=-1, image_fps=0)
        score += self.points
        tank = False
        self.destroy()

class Corpse(sge.dsp.Object):
    def __init__(self, x, y, z=1000, sprite=None, visible=True, xvelocity=0,
                 yvelocity=0, xacceleration=0, yacceleration=0,
                 xdeceleration=0, ydeceleration=0, image_index=0,
                 image_origin_x=None, image_origin_y=None, image_fps=None,
                 image_xscale=1, image_yscale=1, image_rotation=0,
                 image_alpha=255, image_blend=None, life=None):
        super(Corpse, self).__init__(
            x, y, z=z, sprite=sprite, visible=visible, tangible=False,
            xvelocity=xvelocity, yvelocity=yvelocity,
            xacceleration=xacceleration, yacceleration=yacceleration,
            xdeceleration=xdeceleration, ydeceleration=ydeceleration,
            image_index=image_index, image_origin_x=image_origin_x,
            image_origin_y=image_origin_y, image_fps=image_fps,
            image_xscale=image_xscale, image_yscale=image_yscale,
            image_rotation=image_rotation, image_alpha=image_alpha,
            image_blend=image_blend)
        self.life = life
    def event_step(self, time_passed, delta_mult):
        if self.life is not None:
            self.life -= delta_mult
            if self.life <= 0:
                self.destroy()
        if self.y > sge.game.current_room.height + self.image_origin_y:
            self.destroy()

class Infrastructure(xsge_physics.Collider):
    health = 1
    points = 100
    def hurt(self):
        self.health -= 1
        if self.health > 0:
            play_sound(enemy_hit_sound)
        else:
            self.kill()
    def kill(self):
        global score
        play_sound(kick_sound)
        Corpse.create(self.x, self.y, sprite=self.sprite, yvelocity=-2,
                      yacceleration=0.25, image_yscale=-1, image_fps=0)
        score += self.points
        self.destroy()
    def event_create(self):
        if self.bbox_top < ARENA_Y:
            self.bbox_top = 10
            # self.bbox_top = 170
        elif self.bbox_bottom > ARENA_Y + ARENA_HEIGHT:
            self.bbox_bottom = 230
            # self.bbox_bottom = 200
    def event_step(self, time_passed, delta_mult):
        self.z = self.bbox_bottom
        if self.x - self.image_origin_x + self.sprite.width < 0:
            # if not sge.game.current_room.gameover:
            #     sge.game.current_room.gameover = True
            #     for obj in sge.game.current_room.objects[:]:
            #         if isinstance(obj, (Player, Brick)):
            #             obj.kill()
            #     sge.game.current_room.alarms["gameover"] = 5 * FPS
            #     sge.snd.Music.clear_queue()
            #     sge.snd.Music.stop(5000)
            self.destroy()
    def event_collision(self, other, xdirection, ydirection):
        if isinstance(other, Brick):
            self.kill()
            other.kill()
        elif isinstance(other, Player):
            other.kill()
    def event_physics_collision_left(self, other, move_loss):
        self.event_collision(other, -1, 0)
    def event_physics_collision_right(self, other, move_loss):
        self.event_collision(other, 1, 0)
    def event_physics_collision_top(self, other, move_loss):
        self.event_collision(other, 0, -1)
    def event_physics_collision_bottom(self, other, move_loss):
        self.event_collision(other, 0, 1)

class Cactus(Infrastructure):
    def __init__(self, x, y):
        super(Cactus, self).__init__(x, y, z=y, sprite=cactus_sprite,
                                     xvelocity=-1.0)
class Building(Infrastructure):
    def __init__(self, x, y):
        super(Building, self).__init__(x, y, z=y, sprite=building_sprite,
                                     xvelocity=-1.0)
class Tower(Enemy):
    def __init__(self, x, y):
        super(Tower, self).__init__(x, y, z=y, sprite=tower_sprite,
                                     xvelocity=-1.0)

class Menu(xsge_gui.MenuWindow):
    items = []
    @classmethod
    def create(cls, default=0):
        if cls.items:
            self = cls.from_text(
                gui_handler, sge.game.width / 2, sge.game.height * 2 / 3,
                cls.items, font_normal=font,
                color_normal=sge.gfx.Color("white"),
                color_selected=sge.gfx.Color("red"),
                background_color=sge.gfx.Color("black"), margin=4,
                halign="center", valign="middle")
            default %= len(self.widgets)
            self.keyboard_focused_widget = self.widgets[default]
            self.show()
            return self

class MainMenu(Menu):
    # items = ["Start Game", "Options", "Scores", "Credits", "Quit"]
    items = ["Start Game", "Options", "Scores", "Quit"]

    def event_choose(self):
        if self.choice == 0:
            StartGameMenu.create(default=0)
        elif self.choice == 1:
            OptionsMenu.create_page()
        elif self.choice == 2:
            scores_room = ScoresScreen()
            scores_room.start()
        # elif self.choice == 3:
        #     credits_room = CreditsScreen()
        #     credits_room.start()
        else:
            sge.game.end()

class StartGameMenu(Menu):
    items = ["Easy", "Normal", "Hard", "Back"]
    def event_choose(self):
        if self.choice in {0, 1, 2}:
            arena = Arena(self.choice)
            arena.start()
        else:
            MainMenu.create(default=0)

class OptionsMenu(Menu):
    @classmethod
    def create_page(cls, default=0):
        cls.items = [
            "Fullscreen: {}".format("On" if sge.game.fullscreen else "Off"),
            "Sound: {}".format("On" if sound_enabled else "Off"),
            "Music: {}".format("On" if music_enabled else "Off"),
            "Show FPS: {}".format("On" if fps_enabled else "Off"),
            "Configure keyboard",
            "Back"]
        return cls.create(default)

    def event_choose(self):
        global fullscreen
        global sound_enabled
        global music_enabled
        global fps_enabled

        if self.choice == 0:
            fullscreen = not fullscreen
            sge.game.fullscreen = fullscreen
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 1:
            sound_enabled = not sound_enabled
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 2:
            music_enabled = not music_enabled
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 3:
            fps_enabled = not fps_enabled
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 4:
            KeyboardMenu.create_page()
        else:
            MainMenu.create(default=1)

class KeyboardMenu(Menu):
    page = 0
    @classmethod
    def create_page(cls, default=0, page=0):
        def format_key(key):
            if key:
                return " ".join(key).replace("_", "-")
            else:
                return None

        cls.items = ["Left: {}".format(format_key(left_key)),
                     "Right: {}".format(format_key(right_key)),
                     "Up: {}".format(format_key(up_key)),
                     "Down: {}".format(format_key(down_key)),
                     "Bomb: {}".format(format_key(bomb_key)),
                     "Action: {}".format(format_key(action_key)),
                     "Pause: {}".format(format_key(pause_key)),
                     "Back"]
        self = cls.create(default)
        return self

    def event_choose(self):
        def toggle_key(key, new_key):
            if new_key in key:
                key.remove(new_key)
            else:
                key.append(new_key)
                while len(key) > 2:
                    key.pop(0)

        if self.choice == 0:
            k = wait_key()
            if k is not None:
                toggle_key(left_key, k)
                set_gui_controls()
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 1:
            k = wait_key()
            if k is not None:
                toggle_key(right_key, k)
                set_gui_controls()
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 2:
            k = wait_key()
            if k is not None:
                toggle_key(up_key, k)
                set_gui_controls()
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 3:
            k = wait_key()
            if k is not None:
                toggle_key(down_key, k)
                set_gui_controls()
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 4:
            k = wait_key()
            if k is not None:
                toggle_key(action_key, k)
                set_gui_controls()
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 5:
            k = wait_key()
            if k is not None:
                toggle_key(pause_key, k)
                set_gui_controls()
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        else:
            OptionsMenu.create_page(default=5)

class ModalMenu(xsge_gui.MenuDialog):
    items = []
    @classmethod
    def create(cls, default=0):
        if cls.items:
            self = cls.from_text(
                gui_handler, sge.game.width / 2, sge.game.height / 2,
                cls.items, font_normal=font,
                color_normal=sge.gfx.Color("white"),
                color_selected=sge.gfx.Color("red"),
                background_color=sge.gfx.Color("black"), margin=4,
                halign="center", valign="middle")
            default %= len(self.widgets)
            self.keyboard_focused_widget = self.widgets[default]
            self.show()
            return self

class PauseMenu(ModalMenu):
    items = ["Continue", "Quit"]
    def event_choose(self):
        sge.snd.Music.unpause()

        if self.choice == 1:
            sge.game.start_room.start()

def play_sound(sound, *args, **kwargs):
    if sound_enabled and sound:
        sound.play(*args, **kwargs)

def play_music(music, force_restart=False):
    """Play the given music file, starting with its start piece."""
    if music_enabled and music:
        music_object = loaded_music.get(music)
        if music_object is None:
            try:
                music_object = sge.snd.Music(os.path.join(DATA, "music",
                                                          music))
            except IOError:
                sge.snd.Music.clear_queue()
                sge.snd.Music.stop()
                return
            else:
                loaded_music[music] = music_object

        name, ext = os.path.splitext(music)
        music_start = ''.join([name, "-start", ext])
        music_start_object = loaded_music.get(music_start)
        if music_start_object is None:
            try:
                music_start_object = sge.snd.Music(os.path.join(DATA, "music",
                                                                music_start))
            except IOError:
                pass
            else:
                loaded_music[music_start] = music_start_object

        if (force_restart or (not music_object.playing and
                              (music_start_object is None or
                               not music_start_object.playing))):
            sge.snd.Music.clear_queue()
            sge.snd.Music.stop()
            if music_start_object is not None:
                music_start_object.play()
                music_object.queue(loops=None)
            else:
                music_object.play(loops=None)
    else:
        sge.snd.Music.clear_queue()
        sge.snd.Music.stop()

def write_to_disk():
    keys_cfg = {"left": left_key, "right": right_key, "up": up_key,
                "down": down_key, "action": action_key, "pause": pause_key}

    cfg = {"version": 0, "fullscreen": fullscreen,
           "sound_enabled": sound_enabled, "music_enabled": music_enabled,
           "fps_enabled": fps_enabled, "keys": keys_cfg, "highscores": highscores}

    with open(os.path.join(CONFIG, "config.json"), 'w') as f:
        json.dump(cfg, f, indent=4)

def set_gui_controls():
    # Set the controls for xsge_gui based on the player controls.
    xsge_gui.next_widget_keys = ["tab"] + down_key
    xsge_gui.previous_widget_keys = up_key
    xsge_gui.enter_keys = ["enter"] + action_key + pause_key

def wait_key():
    # Wait for a key press and return it.
    while True:
        # Input events
        sge.game.pump_input()
        while sge.game.input_events:
            event = sge.game.input_events.pop(0)
            if isinstance(event, sge.input.KeyPress):
                sge.game.pump_input()
                sge.game.input_events = []
                if event.key == "escape":
                    return None
                else:
                    return event.key

        # Regulate speed
        sge.game.regulate_speed(fps=10)

        # Project text
        text = "Press the key you wish to use for this function, or Escape to cancel."
        sge.game.project_text(font, text, sge.game.width / 2,
                              sge.game.height / 2, width=sge.game.width,
                              height=sge.game.height,
                              color=sge.gfx.Color("white"),
                              halign="center", valign="middle")

        # Refresh
        sge.game.refresh()

# init the game
Game(SCREEN_SIZE[0], SCREEN_SIZE[1], scale=2, fps=FPS,
     window_text="Star Blazer {}".format(__version__),
     window_icon=os.path.join(DATA, "icon.png"))
sge.game.scale = None

xsge_gui.init()
gui_handler = xsge_gui.Handler()


player_stand_sprite = sge.gfx.Sprite("ship0", DATA, transparent=True)
player_stand_shoot_sprite = sge.gfx.Sprite("ship0", DATA, transparent=True)
player_walk_sprite = sge.gfx.Sprite("ship1", DATA, transparent=True)
player_walk_shoot_sprite = sge.gfx.Sprite("ship1", DATA, transparent=True)
player_die_sprite = sge.gfx.Sprite("ship0", DATA, transparent=True)
player_recover_sprite = sge.gfx.Sprite("ship0", DATA, transparent=True)

cactus_sprite = sge.gfx.Sprite("cactus", DATA, transparent=True, width=10, height=20)
building_sprite = sge.gfx.Sprite("building", DATA, transparent=True)
tower_sprite = sge.gfx.Sprite("tower", DATA, transparent=True, bbox_x=6, bbox_y=7,
                                    width=10, height=45, bbox_width=10, bbox_height=25)

planes_sprite = sge.gfx.Sprite(
    "planes", DATA, origin_x=20, origin_y=10, fps=3, bbox_x=-6, bbox_y=-7,
    bbox_width=12, bbox_height=14)
fuelship_sprite = sge.gfx.Sprite(
    "fuelship", DATA, origin_x=20, origin_y=10, fps=3, bbox_x=-6, bbox_y=-7,
    bbox_width=12, bbox_height=14, height=10)
tank_sprite = sge.gfx.Sprite(
    "tank0", DATA, origin_x=20, origin_y=10, fps=3, bbox_x=-6, bbox_y=-7,
    bbox_width=12, bbox_height=7, width=40, height=20)
explosion_sprite = sge.gfx.Sprite(
    "explosion", DATA, origin_x=2,
    origin_y=2)
bullet_sprite = sge.gfx.Sprite("bullet", DATA, origin_x=1, origin_y=-5,
                               bbox_x=-2, bbox_y=-2, bbox_width=5,
                               bbox_height=5)
bullet_dead_sprite = sge.gfx.Sprite(
    "bullet_dead", DATA, transparent=sge.gfx.Color("black"), origin_x=2,
    origin_y=2)
brick_sprite = sge.gfx.Sprite("brick", DATA, transparent=False)
bomb_sprite = sge.gfx.Sprite("bomb", DATA, transparent=True)

fuelbox_sprite = sge.gfx.Sprite("fuelbox0", DATA, transparent=True)

brick_shard_sprite = sge.gfx.Sprite("brick_shard", DATA)
goomba_sprite = sge.gfx.Sprite(
    "goomba", DATA, origin_x=8, origin_y=8, fps=3, bbox_x=-6, bbox_y=-7,
    bbox_width=12, bbox_height=14)
greenkoopa_sprite = sge.gfx.Sprite(
    "greenkoopa", DATA, origin_x=8, origin_y=19, fps=4, bbox_x=1, bbox_y=-17,
    bbox_width=8, bbox_height=25)
greenshell_sprite = sge.gfx.Sprite(
    "greenshell", DATA, origin_x=8, origin_y=8, bbox_x=-6, bbox_y=-7,
    bbox_width=10, bbox_height=14)
greenshelldash_sprite = sge.gfx.Sprite(
    "greenshelldash", DATA, origin_x=8, origin_y=8, fps=8, bbox_x=-6,
    bbox_y=-7, bbox_width=10, bbox_height=14)
redkoopa_sprite = sge.gfx.Sprite(
    "redkoopa", DATA, origin_x=8, origin_y=19, fps=6, bbox_x=1, bbox_y=-17,
    bbox_width=8, bbox_height=25)
redshell_sprite = sge.gfx.Sprite(
    "redshell", DATA, origin_x=8, origin_y=8, bbox_x=-6, bbox_y=-7,
    bbox_width=10, bbox_height=14)
redshelldash_sprite = sge.gfx.Sprite(
    "redshelldash", DATA, origin_x=8, origin_y=8, fps=8, bbox_x=-6, bbox_y=-7,
    bbox_width=10, bbox_height=14)
spiny_sprite = sge.gfx.Sprite(
    "spiny", DATA, origin_x=9, origin_y=9, fps=3, bbox_x=-7, bbox_y=-7,
    bbox_width=15, bbox_height=15)
hammerbro_sprite = sge.gfx.Sprite(
    "hammerbro", DATA, origin_x=17, origin_y=19, fps=3, bbox_x=-5, bbox_y=-1,
    bbox_width=11, bbox_height=23)
hammerbro_throw_sprite = sge.gfx.Sprite(
    "hammerbro_throw", DATA, origin_x=17, origin_y=19, fps=3, bbox_x=-5,
    bbox_y=-1, bbox_width=11, bbox_height=23)
hammer_sprite = sge.gfx.Sprite("hammer", DATA, origin_x=8, origin_y=8, fps=15,
                               bbox_x=-4, bbox_y=0, bbox_width=8,
                               bbox_height=4)

# Load sounds
shoot_sound = sge.snd.Sound(os.path.join(DATA, "shoot.wav"), volume=0.5)
enemy_hit_sound = sge.snd.Sound(os.path.join(DATA, "enemy_hit.wav"), volume=0.5)
kick_sound = sge.snd.Sound(os.path.join(DATA, "kick.wav"))
hammer_throw_sound = sge.snd.Sound(os.path.join(DATA, "hammer_throw.wav"),
                                   volume=0.5)
die_sound = sge.snd.Sound(os.path.join(DATA, "die.wav"), volume=0.5)
brick_break_sound = sge.snd.Sound(os.path.join(DATA, "brick_break.wav"))
# Load backgrounds
layers = [sge.gfx.BackgroundLayer(
    sge.gfx.Sprite("background", DATA, transparent=False), 0, 0, -100000)]
background = sge.gfx.Background(layers, sge.gfx.Color((85, 170, 255)))
# Load fonts
chars = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-*!")
font_sprite = sge.gfx.Sprite("font", DATA, transparent=sge.gfx.Color("black"))
font = sge.gfx.Font.from_sprite(font_sprite, chars, size=8)

########################
brick_sprite = sge.gfx.Sprite("brick", DATA, transparent=False)
########################


# Create rooms
sge.game.start_room = TitleScreen()

sge.game.mouse.visible = False

if not os.path.exists(CONFIG):
    os.makedirs(CONFIG)
try:
    with open(os.path.join(CONFIG, "config.json")) as f:
        cfg = json.load(f)
except (IOError, ValueError):
    cfg = {}
finally:
    cfg_version = cfg.get("version", 0)

    highscores = list(cfg.get("highscores", highscores))
    fullscreen = cfg.get("fullscreen", fullscreen)
    sge.game.fullscreen = fullscreen
    sound_enabled = cfg.get("sound_enabled", sound_enabled)
    music_enabled = cfg.get("music_enabled", music_enabled)
    fps_enabled = cfg.get("fps_enabled", fps_enabled)

    keys_cfg = cfg.get("keys", {})
    left_key = keys_cfg.get("left", left_key)
    right_key = keys_cfg.get("right", right_key)
    up_key = keys_cfg.get("up", up_key)
    down_key = keys_cfg.get("down", down_key)
    action_key = keys_cfg.get("action", action_key)
    pause_key = keys_cfg.get("pause", pause_key)

    set_gui_controls()

if __name__ == "__main__":
    try:
        sge.game.start()
    finally:
        write_to_disk()
