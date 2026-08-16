import pygame
import sys
import random

# Initialize Pygame
try:
    pygame.init()
except Exception as e:
    print(f"Error initializing Pygame: {e}")
    sys.exit(1)

# Set up some constants
WIDTH, HEIGHT = 800, 600
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Set up the display
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))

# Set up the font
FONT = pygame.font.Font(None, 24)

# Set up the clock
CLOCK = pygame.time.Clock()

class Player(pygame.Rect):
    def __init__(self):
        super().__init__(WIDTH / 2, HEIGHT - 50, 50, 50)
        self.speed = 5
        self.projectiles = []
        self.fire_rate = 10
        self.fire_timer = 0

    def move(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x += self.speed

        if self.x < 0:
            self.x = 0
        if self.x > WIDTH - self.width:
            self.x = WIDTH - self.width

    def fire(self):
        self.fire_timer += 1
        if self.fire_timer >= self.fire_rate:
            self.projectiles.append(Projectile(self.centerx, self.top))
            self.fire_timer = 0

class Projectile(pygame.Rect):
    def __init__(self, x, y):
        super().__init__(x, y, 10, 20)
        self.speed = 10

    def move(self):
        self.y -= self.speed

class Alien(pygame.Rect):
    def __init__(self, speed, fire_rate):
        super().__init__(random.randint(0, WIDTH - 50), 0, 50, 50)
        self.speed = speed
        self.projectiles = []
        self.fire_rate = fire_rate
        self.fire_timer = 0

    def move(self):
        self.x += self.speed
        if self.x < 0 or self.x > WIDTH - self.width:
            self.speed *= -1
            self.y += 50
            if self.y > HEIGHT:
                self.y = 0

    def fire(self):
        self.fire_timer += 1
        if self.fire_timer >= self.fire_rate:
            self.projectiles.append(AlienProjectile(self.centerx, self.bottom))
            self.fire_timer = 0

class AlienProjectile(pygame.Rect):
    def __init__(self, x, y):
        super().__init__(x, y, 10, 20)
        self.speed = 5

    def move(self):
        self.y += self.speed

class Level:
    def __init__(self, number):
        self.number = number
        self.alien_speed = 2 + (number * 0.5)
        self.alien_fire_rate = 20 - (number * 2)
        self.alien_spawn_rate = 100 - (number * 5)

def draw_text(text, x, y):
    text_surface = FONT.render(text, True, WHITE)
    SCREEN.blit(text_surface, (x, y))

def main():
    player = Player()
    aliens = [Alien(2, 20)]
    score = 0
    lives = 3
    level = Level(1)
    alien_spawn_timer = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.fire()

        SCREEN.fill(BLACK)

        player.move()
        pygame.draw.rect(SCREEN, WHITE, player)

        for alien in aliens:
            alien.move()
            pygame.draw.rect(SCREEN, WHITE, alien)
            alien.fire()

            for projectile in alien.projectiles:
                projectile.move()
                pygame.draw.rect(SCREEN, WHITE, projectile)
                if projectile.y > HEIGHT:
                    alien.projectiles.remove(projectile)
                if projectile.colliderect(player):
                    lives -= 1
                    alien.projectiles.remove(projectile)

            if alien.y > HEIGHT:
                lives -= 1
                aliens.remove(alien)

        for projectile in player.projectiles:
            projectile.move()
            pygame.draw.rect(SCREEN, WHITE, projectile)
            if projectile.y < 0:
                player.projectiles.remove(projectile)

            for alien in aliens:
                if projectile.colliderect(alien):
                    score += 1
                    player.projectiles.remove(projectile)
                    aliens.remove(alien)

        alien_spawn_timer += 1
        if alien_spawn_timer >= level.alien_spawn_rate:
            aliens.append(Alien(level.alien_speed, level.alien_fire_rate))
            alien_spawn_timer = 0

        if len(aliens) == 0:
            level.number += 1
            score += 100
            level.alien_speed = 2 + (level.number * 0.5)
            level.alien_fire_rate = 20 - (level.number * 2)
            level.alien_spawn_rate = 100 - (level.number * 5)
            aliens.append(Alien(level.alien_speed, level.alien_fire_rate))

        draw_text(f"Score: {score}", 10, 10)
        draw_text(f"Lives: {lives}", WIDTH - 100, 10)
        draw_text(f"Level: {level.number}", WIDTH / 2 - 50, 10)

        if lives <= 0:
            SCREEN.fill(BLACK)
            draw_text("Game Over", WIDTH / 2 - 100, HEIGHT / 2)
            draw_text(f"Final Score: {score}", WIDTH / 2 - 100, HEIGHT / 2 + 50)
            pygame.display.flip()
            pygame.time.wait(2000)
            break

        pygame.display.flip()
        CLOCK.tick(FPS)

if __name__ == "__main__":
    main()