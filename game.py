# game.py
import pygame
import sys
import math
import random

pygame.init()
WIDTH, HEIGHT = 960, 640
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Terraria-like Platformer - Patched")
CLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont("consolas", 20)

# ----- CONFIG -----
GRAVITY = 0.35
PLAYER_SPEED = 3.0
PLAYER_JUMP = -8.0
PLAYER_DOUBLE_JUMP = -7.0
CAMERA_LERP = 0.12
WORLD_WIDTH, WORLD_HEIGHT = 3000, 1600
DASH_SPEED = 8.0
DASH_DURATION = 200  # ms
DASH_COOLDOWN = 300  # ms
WALL_SLIDE_FRICTION = 0.15

# Colors
BG = (10, 20, 30)
PLAYER_COL = (200, 170, 120)
PLAT_COL = (80, 120, 90)
MOVPLAT_COL = (90, 70, 130)
SLOPE_COL = (120, 100, 70)
LADDER_COL = (140, 100, 60)
ENEMY_COL = (200, 80, 80)
COIN_COL = (230, 190, 40)
UI_COL = (220, 220, 220)

# ----- UTILS -----
def clamp(v, a, b):
    return max(a, min(b, v))

# ----- CAMERA -----
class Camera:
    def __init__(self, w, h):
        self.x = 0
        self.y = 0
        self.w = w
        self.h = h

    def apply(self, rect):
        return pygame.Rect(rect.x - self.x, rect.y - self.y, rect.width, rect.height)

    def update(self, target_rect):
        # center target with lerp
        target_x = clamp(target_rect.centerx - WIDTH // 2, 0, WORLD_WIDTH - WIDTH)
        target_y = clamp(target_rect.centery - HEIGHT // 2, 0, WORLD_HEIGHT - HEIGHT)
        self.x += (target_x - self.x) * CAMERA_LERP
        self.y += (target_y - self.y) * CAMERA_LERP

# ----- GAME OBJECTS -----
class Platform:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = PLAT_COL
        self.movable = False
        self.delta = pygame.Vector2(0, 0)

    def update(self, dt):
        self.delta = pygame.Vector2(0, 0)

    def draw(self, surf, cam):
        r = cam.apply(self.rect)
        pygame.draw.rect(surf, self.color, r)

class MovingPlatform(Platform):
    def __init__(self, x, y, w, h, path, speed=1.2):
        super().__init__(x, y, w, h)
        self.path = path  # list of (x,y)
        self.speed = speed
        self.color = MOVPLAT_COL
        self.movable = True
        self.pos = pygame.Vector2(x, y)
        self._idx = 0
        self.delta = pygame.Vector2(0, 0)
        self.prev_pos = pygame.Vector2(x, y)

    def update(self, dt):
        # normalize dt to ~60fps scale (16.67 ms)
        dtf = dt / 16.67
        self.prev_pos = pygame.Vector2(self.pos)
        if len(self.path) < 2:
            self.delta = pygame.Vector2(0, 0)
            return
        target = pygame.Vector2(self.path[self._idx])
        direction = target - self.pos
        dist = direction.length()
        if dist < 1:
            self._idx = (self._idx + 1) % len(self.path)
            target = pygame.Vector2(self.path[self._idx])
            direction = target - self.pos
            dist = direction.length()
            if dist == 0:
                self.delta = pygame.Vector2(0, 0)
                return
        direction = direction.normalize()
        self.pos += direction * self.speed * dtf
        self.rect.topleft = (round(self.pos.x), round(self.pos.y))
        self.delta = self.pos - self.prev_pos

class Slope:
    """
    Basic slope represented as a right triangle.
    slope_type: 'left' (up to left) or 'right' (up to right)
    """
    def __init__(self, x, y, w, h, slope_type='right'):
        self.rect = pygame.Rect(x, y, w, h)
        self.type = slope_type
        self.color = SLOPE_COL
        if self.type == 'right':
            p1 = (x, y + h)
            p2 = (x + w, y)
        else:
            p1 = (x, y)
            p2 = (x + w, y + h)
        self.p1 = p1
        self.p2 = p2
        dx = self.p2[0] - self.p1[0]
        dy = self.p2[1] - self.p1[1]
        self.m = dy / dx if dx != 0 else 0
        self.b = self.p1[1] - self.m * self.p1[0]

    def get_y_at(self, world_x):
        return self.m * world_x + self.b

    def draw(self, surf, cam):
        r = cam.apply(self.rect)
        if self.type == 'right':
            points = [
                (r.left, r.bottom),
                (r.right, r.top),
                (r.right, r.bottom)
            ]
        else:
            points = [
                (r.left, r.top),
                (r.left, r.bottom),
                (r.right, r.bottom)
            ]
        pygame.draw.polygon(surf, self.color, points)

class Ladder:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = LADDER_COL

    def draw(self, surf, cam):
        r = cam.apply(self.rect)
        pygame.draw.rect(surf, self.color, r)
        rung_count = max(2, self.rect.height // 40)
        for i in range(rung_count):
            ry = r.top + (i+1) * (r.height / (rung_count + 1))
            pygame.draw.line(surf, (100, 80, 50), (r.left+6, ry), (r.right-6, ry), 2)

class Enemy:
    def __init__(self, x, y, w=36, h=36, patrol=(0, 120), speed=1.0):
        self.rect = pygame.Rect(x, y, w, h)
        self.start_x = x
        self.patrol = patrol  # (left_offset, right_offset)
        self.speed = speed
        self.dir = 1
        self.color = ENEMY_COL
        self.alive = True
        self.health = 1

    def update(self, dt):
        # normalize dt to ~60fps
        dtf = dt / 16.67
        # move horizontally using dtf scalar
        move = int(self.dir * self.speed * dtf)
        # ensure at least 1 px movement if speed is non-zero to keep motion smooth
        if move == 0 and self.speed * dtf > 0:
            move = 1 * self.dir
        self.rect.x += move
        if self.rect.x < self.start_x - self.patrol[0]:
            self.rect.x = self.start_x - self.patrol[0]
            self.dir *= -1
        elif self.rect.x > self.start_x + self.patrol[1]:
            self.rect.x = self.start_x + self.patrol[1]
            self.dir *= -1

    def draw(self, surf, cam):
        r = cam.apply(self.rect)
        pygame.draw.rect(surf, self.color, r)
        eye_w = max(2, r.width // 6)
        pygame.draw.rect(surf, (20,20,20), (r.x+6, r.y+8, eye_w, eye_w))
        pygame.draw.rect(surf, (20,20,20), (r.x+ r.width-12, r.y+8, eye_w, eye_w))

class Particle:
    """Simple particle system for dust, sparks, etc."""
    def __init__(self, x, y, vx, vy, lifetime, color, radius=3):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(vx, vy)
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.color = color
        self.radius = radius

    def update(self, dt):
        self.pos += self.vel * (dt / 16.67)
        self.vel.y += GRAVITY * (dt / 16.67)
        self.lifetime -= dt

    def draw(self, surf, cam):
        if self.lifetime <= 0:
            return
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        sx = self.pos.x - cam.x
        sy = self.pos.y - cam.y
        color = tuple(min(255, int(c * (alpha / 255))) for c in self.color)
        pygame.draw.circle(surf, color, (int(sx), int(sy)), max(1, self.radius))

    def is_alive(self):
        return self.lifetime > 0

class Coin:
    def __init__(self, x, y, radius=10):
        self.pos = pygame.Vector2(x, y)
        self.radius = radius
        self.collected = False
        self.bob_phase = random.random() * math.pi * 2

    def update(self, dt):
        self.bob_phase += dt * 0.01

    def draw(self, surf, cam):
        if self.collected:
            return
        sx = self.pos.x - cam.x
        sy = self.pos.y - cam.y + math.sin(self.bob_phase) * 6
        pygame.draw.circle(surf, COIN_COL, (int(sx), int(sy)), self.radius)
        pygame.draw.circle(surf, (255,255,200), (int(sx-3), int(sy-4)), max(2, self.radius//3))

# ----- PLAYER -----
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 36, 56)
        self.vel = pygame.Vector2(0,0)
        self.speed = PLAYER_SPEED
        self.on_ground = False
        self.jump_count = 0
        self.max_jumps = 2  # double jump
        self.ladder = None
        self.facing = 1
        self.health = 3
        self.invincible = 0.0
        self.anim_timer = 0.0
        self.anim_frame = 0
        self.standing_on = None  # reference to platform we're standing on (moving platform handling)
        # dash system
        self.dash_active = False
        self.dash_timer = 0.0
        self.dash_cooldown = 0.0
        self.dash_dir = pygame.Vector2(1, 0)
        # wall slide system
        self.wall_slide = False
        self.wall_side = 0  # -1 left, 1 right
        self.screen_shake = 0.0
        self.particles = []

    def spawn_particles(self, x, y, count=8, color=(200, 170, 120), speed_range=(1, 3)):
        """Create particles for visual effects."""
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(speed_range[0], speed_range[1])
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            p = Particle(x, y, vx, vy, random.uniform(300, 600), color, radius=random.randint(2, 4))
            self.particles.append(p)

    def update(self, keys, dt, world):
        dtf = dt / 16.67  # normalize dt to ~60fps scale
        
        # update particles
        self.particles = [p for p in self.particles if p.is_alive()]
        for p in self.particles:
            p.update(dt)

        # update dash cooldown
        if self.dash_cooldown > 0:
            self.dash_cooldown -= dt

        # handle dash
        if self.dash_active:
            self.dash_timer -= dt
            self.vel = self.dash_dir * DASH_SPEED
            if self.dash_timer <= 0:
                self.dash_active = False
                self.dash_cooldown = DASH_COOLDOWN
        else:
            # horizontal movement
            ax = 0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                ax -= 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                ax += 1
            if ax != 0:
                self.facing = ax
            self.vel.x = ax * self.speed

        # ladder detection
        self.ladder = None
        for ladder in world.ladders:
            if self.rect.colliderect(ladder.rect):
                self.ladder = ladder
                break

        if self.ladder:
            # climbing; cancel gravity
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                self.vel.y = -self.speed
            elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
                self.vel.y = self.speed
            else:
                self.vel.y = 0
            self.wall_slide = False
        else:
            # wall slide detection
            self.wall_slide = False
            if not self.on_ground and not self.dash_active:
                # check for wall on sides
                for plat in world.platforms + world.moving_platforms:
                    # right wall
                    if self.vel.x > 0 and self.rect.right > plat.rect.left and self.rect.left < plat.rect.left:
                        if self.rect.centery > plat.rect.top and self.rect.centery < plat.rect.bottom:
                            self.wall_slide = True
                            self.wall_side = 1
                            self.vel.y *= WALL_SLIDE_FRICTION
                    # left wall
                    elif self.vel.x < 0 and self.rect.left < plat.rect.right and self.rect.right > plat.rect.right:
                        if self.rect.centery > plat.rect.top and self.rect.centery < plat.rect.bottom:
                            self.wall_slide = True
                            self.wall_side = -1
                            self.vel.y *= WALL_SLIDE_FRICTION

            if not self.wall_slide:
                self.vel.y += GRAVITY * dtf

        # limit falling speed
        self.vel.y = clamp(self.vel.y, -100, 10)

        # apply horizontal move
        self.rect.x += int(self.vel.x * dtf)
        self.collide_x(world)

        # apply vertical move
        prev_y = self.rect.y
        self.rect.y += int(self.vel.y * dtf)
        self.on_ground = False
        self.standing_on = None
        self.collide_y(world)

        # if standing on a moving platform, carry the player by platform delta
        if self.standing_on and getattr(self.standing_on, "delta", None) is not None:
            d = self.standing_on.delta
            # apply delta.x and delta.y (mostly x)
            self.rect.x += int(round(d.x))
            self.rect.y += int(round(d.y))

        # invincibility timer
        if self.invincible > 0:
            self.invincible -= dt
            if self.invincible < 0: self.invincible = 0

        # screen shake decay
        if self.screen_shake > 0:
            self.screen_shake -= dt

        # animation
        self.anim_timer += dt
        if self.anim_timer > 140:
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % 3

    def collide_x(self, world):
        # collision with static & moving platforms (rect collision)
        for plat in world.platforms + world.moving_platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel.x > 0:
                    self.rect.right = plat.rect.left
                elif self.vel.x < 0:
                    self.rect.left = plat.rect.right

        # world bounds
        self.rect.left = clamp(self.rect.left, 0, WORLD_WIDTH - self.rect.width)
        self.rect.right = clamp(self.rect.right, self.rect.width, WORLD_WIDTH)

    def collide_y(self, world):
        # moving platforms and static platforms
        for plat in world.moving_platforms + world.platforms:
            if self.rect.colliderect(plat.rect):
                # coming down onto platform
                if self.vel.y > 0 and (self.rect.bottom - self.vel.y) <= (plat.rect.top + 6):
                    self.rect.bottom = plat.rect.top
                    self.vel.y = 0
                    self.on_ground = True
                    self.jump_count = 0
                    self.standing_on = plat  # remember which platform we stand on
                    # spawn landing particles
                    self.spawn_particles(self.rect.centerx, self.rect.bottom, count=6, color=(150, 150, 150))
                    self.screen_shake = 100.0
                elif self.vel.y < 0 and (self.rect.top - self.vel.y) >= (plat.rect.bottom - 6):
                    # hit head
                    self.rect.top = plat.rect.bottom
                    self.vel.y = 0
                else:
                    # side case or overlapping; try to separate horizontally handled elsewhere
                    pass

        # slopes:
        for slope in world.slopes:
            if self.rect.colliderect(slope.rect):
                px = self.rect.centerx
                y_on_slope = slope.get_y_at(px)
                if self.rect.bottom > y_on_slope:
                    self.rect.bottom = int(y_on_slope)
                    self.vel.y = 0
                    self.on_ground = True
                    self.jump_count = 0
                    self.standing_on = slope
                    self.spawn_particles(self.rect.centerx, self.rect.bottom, count=6, color=(150, 150, 150))
                    self.screen_shake = 100.0

        # floor bound
        if self.rect.bottom > WORLD_HEIGHT:
            self.rect.bottom = WORLD_HEIGHT
            self.vel.y = 0
            self.on_ground = True
            self.jump_count = 0
            self.standing_on = None
            self.spawn_particles(self.rect.centerx, self.rect.bottom, count=8, color=(150, 150, 150))
            self.screen_shake = 100.0

    def jump(self):
        # if on ladder, jump off
        if self.ladder:
            self.ladder = None
            self.vel.y = PLAYER_JUMP
            self.jump_count = 1
            self.spawn_particles(self.rect.centerx, self.rect.centery, count=5, color=(200, 170, 120))
            return True

        # wall slide jump
        if self.wall_slide:
            self.vel.y = PLAYER_JUMP
            self.vel.x = self.wall_side * 5  # kick off wall
            self.jump_count = 1
            self.on_ground = False
            self.wall_slide = False
            self.spawn_particles(self.rect.centerx, self.rect.centery, count=6, color=(200, 170, 120))
            return True

        if self.on_ground or self.jump_count < self.max_jumps:
            if self.on_ground:
                self.vel.y = PLAYER_JUMP
            else:
                self.vel.y = PLAYER_DOUBLE_JUMP
            self.jump_count += 1
            self.on_ground = False
            self.standing_on = None
            self.spawn_particles(self.rect.centerx, self.rect.centery, count=6, color=(200, 170, 120))
            return True
        return False

    def dash(self, direction):
        """Activate dash in given direction."""
        if self.dash_cooldown > 0 or self.dash_active:
            return False
        if direction.length() == 0:
            direction = pygame.Vector2(self.facing, 0)
        self.dash_dir = direction.normalize() if direction.length() > 0 else pygame.Vector2(1, 0)
        self.dash_active = True
        self.dash_timer = DASH_DURATION
        self.spawn_particles(self.rect.centerx, self.rect.centery, count=12, color=(100, 200, 255), speed_range=(2, 5))
        self.screen_shake = 80.0
        return True

    def hurt(self, source_rect):
        if self.invincible > 0:
            return
        self.health -= 1
        self.invincible = 1200  # ms
        # simple knockback
        if source_rect.centerx > self.rect.centerx:
            self.vel.x = -6
        else:
            self.vel.x = 6
        self.vel.y = -6
        self.spawn_particles(self.rect.centerx, self.rect.centery, count=10, color=(255, 100, 100))
        self.screen_shake = 150.0

    def draw(self, surf, cam):
        # draw particles
        for p in self.particles:
            p.draw(surf, cam)

        r = cam.apply(self.rect)
        base = PLAYER_COL
        t = self.anim_frame
        shade = (clamp(base[0] - t*10, 0, 255), clamp(base[1] + t*5, 0, 255), clamp(base[2] + t*12, 0, 255))
        color = shade if self.invincible == 0 else (255, 255, 255)
        
        # dash trail effect
        if self.dash_active:
            trail_alpha = int(100 * (self.dash_timer / DASH_DURATION))
            pygame.draw.rect(surf, (100, 200, 255, trail_alpha), r, border_radius=6)
        
        pygame.draw.rect(surf, color, r, border_radius=6)
        
        # eyes
        eye_y = r.y + 10
        if self.facing >= 0:
            pygame.draw.rect(surf, (20,20,20), (r.x + r.width - 12, eye_y, 6, 6))
        else:
            pygame.draw.rect(surf, (20,20,20), (r.x + 6, eye_y, 6, 6))
        
        # wall slide visual
        if self.wall_slide:
            pygame.draw.circle(surf, (100, 150, 255), (r.centerx, r.centery), 20, 2)

# ----- LEVEL / WORLD -----
class World:
    def __init__(self):
        self.platforms = []
        self.moving_platforms = []
        self.slopes = []
        self.ladders = []
        self.enemies = []
        self.coins = []
        self.spawn_point = (120, WORLD_HEIGHT - 200)
        self.create_demo_world()

    def create_demo_world(self):
        self.platforms.append(Platform(0, WORLD_HEIGHT - 64, WORLD_WIDTH, 64))
        # some floating platforms
        for i in range(10):
            x = 200 + i * 250
            y = random.randint(300, WORLD_HEIGHT-300)
            self.platforms.append(Platform(x, y, 150, 20))
        # moving platforms
        mp = MovingPlatform(800, WORLD_HEIGHT-280, 140, 20,
                            path=[(800, WORLD_HEIGHT-280),(1200, WORLD_HEIGHT-380),(1600, WORLD_HEIGHT-280)],
                            speed=1.2)
        self.moving_platforms.append(mp)
        mp2 = MovingPlatform(2200, WORLD_HEIGHT-500, 150, 20,
                             path=[(2200, WORLD_HEIGHT-500),(2200, WORLD_HEIGHT-420)],
                             speed=0.8)
        self.moving_platforms.append(mp2)

        # slopes
        self.slopes.append(Slope(400, WORLD_HEIGHT-160, 300, 160, slope_type='right'))
        self.slopes.append(Slope(1500, WORLD_HEIGHT-200, 360, 200, slope_type='left'))

        # ladders
        self.ladders.append(Ladder(2500, WORLD_HEIGHT-300, 40, 180))
        self.ladders.append(Ladder(600, WORLD_HEIGHT-200, 40, 120))

        # enemies
        for i in range(8):
            ex = 300 + i * 340
            ey = WORLD_HEIGHT - 64 - 36
            e = Enemy(ex, ey, patrol=(40, 160), speed=1.1 + random.random()*0.4)
            self.enemies.append(e)

        # coins
        for i in range(40):
            cx = random.randint(100, WORLD_WIDTH-100)
            cy = random.randint(100, WORLD_HEIGHT-200)
            self.coins.append(Coin(cx, cy, radius=10))

    def update(self, dt):
        for mp in self.moving_platforms:
            mp.update(dt)
        for p in self.platforms:
            p.update(dt)
        for e in self.enemies:
            e.update(dt)
        for c in self.coins:
            c.update(dt)

    def draw(self, surf, cam):
        for p in self.platforms:
            p.draw(surf, cam)
        for mp in self.moving_platforms:
            mp.draw(surf, cam)
        for s in self.slopes:
            s.draw(surf, cam)
        for ladder in self.ladders:
            ladder.draw(surf, cam)
        for e in self.enemies:
            e.draw(surf, cam)
        for c in self.coins:
            c.draw(surf, cam)

# ----- GAME -----
def draw_ui(surf, score, lives, cam):
    text = FONT.render(f"Score: {score}", True, UI_COL)
    surf.blit(text, (12, 8))
    text2 = FONT.render(f"Lives: {lives}", True, UI_COL)
    surf.blit(text2, (12, 34))
    pos = FONT.render(f"Cam: {int(cam.x)},{int(cam.y)}", True, UI_COL)
    surf.blit(pos, (12, 60))

def main():
    world = World()
    player = Player(*world.spawn_point)
    cam = Camera(WORLD_WIDTH, WORLD_HEIGHT)
    score = 0
    lives = 3
    paused = False
    show_hitboxes = False

    while True:
        dt = CLOCK.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_SPACE:
                    player.jump()
                if event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                    # dash in facing direction or input direction
                    keys = pygame.key.get_pressed()
                    dash_dir = pygame.Vector2(0, 0)
                    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                        dash_dir.x -= 1
                    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                        dash_dir.x += 1
                    if keys[pygame.K_w] or keys[pygame.K_UP]:
                        dash_dir.y -= 1
                    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                        dash_dir.y += 1
                    player.dash(dash_dir)
                if event.key == pygame.K_p:
                    paused = not paused
                if event.key == pygame.K_h:
                    show_hitboxes = not show_hitboxes

        keys = pygame.key.get_pressed()

        if not paused:
            world.update(dt)
            player.update(keys, dt, world)
            cam.update(player.rect)

            # coin pickups
            for coin in world.coins:
                if not coin.collected:
                    if player.rect.collidepoint(coin.pos.x, coin.pos.y):
                        coin.collected = True
                        score += 1

            # enemy collisions with a slightly reduced hitbox to avoid corner-tunneling
            for enemy in world.enemies:
                if enemy.alive:
                    # shrink enemy hitbox a bit for fairness and reliability
                    hitbox = enemy.rect.inflate(-6, -6)
                    if player.rect.colliderect(hitbox):
                        # if player is falling and hits enemy from above -> enemy dies
                        if player.vel.y > 0 and player.rect.bottom <= enemy.rect.top + 12:
                            enemy.alive = False
                            # bounce the player up a little
                            player.vel.y = PLAYER_JUMP / 2
                            player.on_ground = False
                        else:
                            player.hurt(enemy.rect)

            # remove dead enemies
            world.enemies = [e for e in world.enemies if e.alive]

            # death / respawn if below world
            if player.rect.top > WORLD_HEIGHT + 300:
                lives -= 1
                player = Player(*world.spawn_point)
                if lives <= 0:
                    # reset everything
                    lives = 3
                    score = 0
                    world = World()

        # DRAW
        SCREEN.fill(BG)

        # screen shake effect
        shake_offset = (0, 0)
        if player.screen_shake > 0:
            shake_x = random.randint(-3, 3)
            shake_y = random.randint(-2, 2)
            shake_offset = (shake_x, shake_y)

        # background grid for scale
        grid_spacing = 160
        start_x = -(cam.x % grid_spacing) + shake_offset[0]
        start_y = -(cam.y % grid_spacing) + shake_offset[1]
        for gx in range(int(WIDTH / grid_spacing) + 2):
            pygame.draw.line(SCREEN, (20,30,40), (start_x + gx * grid_spacing, 0), (start_x + gx * grid_spacing, HEIGHT))
        for gy in range(int(HEIGHT / grid_spacing) + 2):
            pygame.draw.line(SCREEN, (20,30,40), (0, start_y + gy * grid_spacing), (WIDTH, start_y + gy * grid_spacing))

        # apply camera with shake offset
        cam_temp = Camera(WORLD_WIDTH, WORLD_HEIGHT)
        cam_temp.x = cam.x - shake_offset[0]
        cam_temp.y = cam.y - shake_offset[1]
        
        world.draw(SCREEN, cam_temp)
        player.draw(SCREEN, cam_temp)

        if show_hitboxes:
            pr = cam_temp.apply(player.rect)
            pygame.draw.rect(SCREEN, (255,0,0), pr, 1)
            for p in world.platforms + world.moving_platforms:
                r = cam_temp.apply(p.rect)
                pygame.draw.rect(SCREEN, (0,255,0), r, 1)
            for s in world.slopes:
                r = cam_temp.apply(s.rect)
                pygame.draw.rect(SCREEN, (255,255,0), r, 1)
            for e in world.enemies:
                r = cam_temp.apply(e.rect)
                pygame.draw.rect(SCREEN, (255,100,0), r.inflate(-6, -6), 1)

        draw_ui(SCREEN, score, lives, cam)
        
        # dash cooldown indicator
        if player.dash_cooldown > 0:
            cooldown_pct = player.dash_cooldown / DASH_COOLDOWN
            bar_width = int(100 * cooldown_pct)
            pygame.draw.rect(SCREEN, (200, 100, 100), (WIDTH - 120, 8, bar_width, 12))
            pygame.draw.rect(SCREEN, (150, 80, 80), (WIDTH - 120, 8, 100, 12), 1)
            txt = FONT.render("Dash", True, UI_COL)
            SCREEN.blit(txt, (WIDTH - 115, 28))
        else:
            pygame.draw.rect(SCREEN, (100, 200, 100), (WIDTH - 120, 8, 100, 12))
            txt = FONT.render("Dash Ready", True, UI_COL)
            SCREEN.blit(txt, (WIDTH - 125, 28))
        
        help_txt = FONT.render("Arrows/A-D move • Space jump • Shift dash • W/S climb • P pause • H hitboxes", True, UI_COL)
        SCREEN.blit(help_txt, (WIDTH//2 - help_txt.get_width()//2, HEIGHT - 28))

        pygame.display.flip()

if __name__ == "__main__":
    main()
