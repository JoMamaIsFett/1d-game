import pygame
import sys
import math
import random
import pyautogui
import ctypes


# you can change these values

startpos = (400, 400)
angle = 0
fov = 90
resolution = 200
max_distance = 1000
max_iterations = 40
move_speed = 6
obstacle_number = 20
fps = 120


# don't change these values

pygame.init()
screen = pygame.display.set_mode((800, 800))
clock = pygame.time.Clock()
running = True
in_map = False
move_speed *= 120 / fps

ctypes.windll.user32.ShowCursor(False)
screen_width, screen_height = pyautogui.size()
center_x, center_y = screen_width // 2, screen_height // 2
pyautogui.moveTo(center_x, center_y)

circle_list = []
rect_list = []
for i in range(obstacle_number):
    ran = random.randint(1, 2)
    if ran == 1:
        circle_list.append(((random.randint(0, 800), random.randint(0, 800)), random.randint(10, 40)))
    elif ran == 2:
        rect_list.append(((random.randint(0, 800), random.randint(0, 800)), (random.randint(10, 40), random.randint(10, 40))))

pixel_distance = []
pixels = []
width = screen.get_width() // resolution
middle_y = screen.get_height() / 2
for pixel in range(screen.get_width() // width):
    rect = pygame.Rect(0, 0, width, max(width, 10))
    rect.midleft = (pixel * width, middle_y)
    pixels.append(rect)


def sdf_circle(start, pos, r):
    delta_x = start[0] - pos[0]
    delta_y = start[1] - pos[1]
    distance = math.sqrt(delta_x ** 2 + delta_y ** 2) - r
    return distance


def sdf_rect(start, pos, size):
    delta_x = abs(start[0] - pos[0])
    delta_y = abs(start[1] - pos[1])
    x_distance = max(delta_x - size[0], 0)
    y_distance = max(delta_y - size[1], 0)
    distance = math.sqrt(x_distance ** 2 + y_distance ** 2)
    return distance


def return_max_distance(start):
    distances = []
    for circle in circle_list:
        pos, r = circle
        distance = sdf_circle(start, pos, r)
        distances.append(distance)
    for rect in rect_list:
        pos, size = rect
        distance = sdf_rect(start, pos, size)
        distances.append(distance)
    return min(distances)


def render():
    global pixel_distance
    screen.fill((10, 10, 30))

    angles = []
    step = math.radians(fov / resolution)
    for j in range(resolution):
        angles.append(angle + (j - resolution // 2) * step)

    pixel_distance.clear()
    for ang in angles:
        pixel_distance.append(ray_march(ang))

    if in_map:
        render_obstacles()
    else:
        distance_threshold = max_distance / 2
        color_scale = distance_threshold / 255
        for pix in range(len(pixels)):
            pixel_distance[pix] = min(pixel_distance[pix], distance_threshold)
            g = min(255 - pixel_distance[pix] / color_scale, 255)
            pygame.draw.rect(screen, (50, g, 100), pixels[pix])

    pygame.display.flip()


def render_obstacles():
    for circle in circle_list:
        pos, r = circle
        pygame.draw.circle(screen, (50, 125, 100), pos, r)
    for rect in rect_list:
        pos, size = rect
        rect = pygame.Rect(0, 0, size[0] * 2, size[1] * 2)
        rect.center = pos
        pygame.draw.rect(screen, (75, 100, 150), rect)


def ray_march(direction):
    length = 0
    new_pos = startpos
    for j in range(max_iterations):
        step = return_max_distance(new_pos)
        length += step

        new_pos = (math.cos(direction) * length + startpos[0], math.sin(direction) * length + startpos[1])

        if step < 0.01 or length > max_distance:
            break

    if in_map:
        end_pos = (math.cos(direction) * length + startpos[0], math.sin(direction) * length + startpos[1])
        pygame.draw.line(screen, (255, 0, 0), startpos, end_pos)

    return length


def get_mouse_angle():
    global angle
    pos = pyautogui.position()
    delta_x = pos[0] - center_x
    delta_x /= 500
    angle += delta_x
    pyautogui.moveTo(center_x, center_y)


def move_start_pos_relative(move_angle):
    global startpos

    angle_radian = math.radians(move_angle) + angle

    x_movement = move_speed * math.cos(angle_radian)
    y_movement = move_speed * math.sin(angle_radian)

    x, y = startpos
    x += x_movement
    y += y_movement
    startpos = (x, y)


def key_handler(keys):
    global running, startpos, in_map
    if keys[pygame.K_ESCAPE]:
        running = False
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        move_start_pos_relative(0)
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        move_start_pos_relative(180)
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        move_start_pos_relative(270)
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        move_start_pos_relative(90)


while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            key = pygame.key.get_pressed()
            if key[pygame.K_m]:
                in_map = not in_map

    key_handler(pygame.key.get_pressed())
    get_mouse_angle()

    render()
    clock.tick(120)

pygame.quit()
sys.exit()
