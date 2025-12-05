import pygame

pygame.init()
screen = pygame.display.set_mode((640, 640))
potato = pygame.image.load('potato.png').convert()
running = True
x = 0
while running:
    screen.blit(potato, (x, 30))
    x +=1
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
pygame.quit()