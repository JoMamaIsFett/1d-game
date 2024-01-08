import pygame
import sys
import math
import json
import socket
import threading
import random
import pkg_resources
import io

with open("ip_config.txt") as file:
    server_ip_data = json.load(file)

server_ip = server_ip_data["ip"]
server_port = server_ip_data["port"]

pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("Ray Shooter")
icon = pygame.image.load(io.BytesIO(pkg_resources.resource_string(__name__, "resources/Icon.png")))
pygame.display.set_icon(icon)
clock = pygame.time.Clock()
fps = 120
running = True
is_shooting = False
is_ability = False
death_menu = False
start_menu = True
name_menu = False
width = screen.get_width()
height = screen.get_height()
font_256 = pygame.font.Font(None, 256)
font_128 = pygame.font.Font(None, 128)
font_26 = pygame.font.Font(None, 26)
start_screen = pygame.image.load(io.BytesIO(pkg_resources.resource_string(__name__, "resources/startmenu.png")))

startpos = (-10, -10)
obstacle_number = 40
max_distance = 1000
iterations = 40
angle = 0
player_size = 10
player_speed = 3
bullet_speed = 15
bullet_lifetime = 1
bullet_size = 4
ability_cooldown = 5
deathzone_lifetime = 1
deathzone_time_offset = 0.1
deaths = 0
name = ""
BUTTON_COLOR = (15, 15, 35)
TEXT_COLOR = (206, 207, 235)
PLAYER_COLOR = (200, 200, 200)
render_tag = ""
ignore_objects = False
cursor_speed = 0.75

players = {}
player_lock = threading.Lock()

bullets = []
abilities = []
cooldown = fps * ability_cooldown

death_menu_rects = [pygame.Rect(width // 2 - width // 4, height // 3 - 75, width // 2, 150),
                    pygame.Rect(width // 3 - width // 12, 5 * (height // 9) - height // 16, width // 6, height // 8),
                    pygame.Rect(2 * (width // 3) - width // 12, 5 * (height // 9) - height // 16, width // 6,
                                height // 8)]
death_menu_texts = [("Game Over", font_256, (255, 0, 0)), ("Restart", font_128, TEXT_COLOR),
                    ("Quit", font_128, TEXT_COLOR)]

start_menu_rect = pygame.Rect(0, 0, width // 3, height // 4)
start_menu_rect.center = (width // 2 - 45, 7 * (height // 10) + 10)

name_menu_text = font_128.render("Continue", True, TEXT_COLOR)
name_menu_text_rect = name_menu_text.get_rect(center=(width // 2, 2 * (height // 3)))
name_menu_rect = pygame.Rect(0, 0, name_menu_text_rect.width + 20, name_menu_text_rect.height + 20)
name_menu_rect.center = name_menu_text_rect.center
cursor_timer = fps * cursor_speed


class Bullet:
    def __init__(self, pos, direction, player):
        self.pos = pos
        self.direction = direction
        self.lifetime = fps * bullet_lifetime
        self.player = player

    def render(self):
        pygame.draw.circle(screen, (1, 235, 229), self.pos, bullet_size)

    def move_in_direction(self):
        new_pos = (
            math.cos(self.direction) * bullet_speed + self.pos[0],
            math.sin(self.direction) * bullet_speed + self.pos[1])
        if not collision(new_pos, bullet_size):
            self.pos = new_pos
        else:
            self.lifetime = 0

    def tick(self):
        self.lifetime -= 1
        self.move_in_direction()
        if self.lifetime > 1:
            return True
        else:
            return False


class Deathzone:
    def __init__(self, pos, size, player):
        self.pos = pos
        self.size = size
        self.lifetime = fps * deathzone_lifetime
        self.player = player

    def render(self):
        pygame.draw.circle(screen, (82, 48, 92), self.pos, self.size)

    def tick(self):
        self.lifetime -= 1
        if self.lifetime > 1:
            return True
        else:
            return False

    def kill(self):
        if return_distance(self.pos, startpos) < (self.size + player_size) and str(self.player) != str(self_player_id):
            return True
        return False


class Ability:
    def __init__(self, pos, direction, player):
        self.pos = pos
        self.direction = direction
        self.player = player
        self.deathzone_spawn_time = fps * deathzone_time_offset
        self.deathzone_list = []
        self.planed_deathzone = []
        length = 0
        new_pos = pos
        for j in range(iterations):
            step = return_max_distance(new_pos)
            length += step

            self.planed_deathzone.append((new_pos, step))

            new_pos = (math.cos(direction) * length + pos[0], math.sin(direction) * length + pos[1])

            if step < 0.01 or length > max_distance:
                break
        self.next_deathzone()

    def next_deathzone(self):
        pos, size = self.planed_deathzone[0]
        self.deathzone_list.append(Deathzone(pos, size, self.player))
        self.planed_deathzone.pop(0)

    def tick(self):
        self.deathzone_spawn_time -= 1
        if self.deathzone_spawn_time < 1 and len(self.planed_deathzone) != 0:
            self.next_deathzone()
            self.deathzone_spawn_time = fps * deathzone_time_offset
        for deathzone in self.deathzone_list:
            alive = deathzone.tick()
            if not alive:
                self.deathzone_list.pop(self.deathzone_list.index(deathzone))

        if len(self.deathzone_list) == 0 and len(self.planed_deathzone) == 0:
            return False
        return True

    def render(self):
        for deathzone in self.deathzone_list:
            deathzone.render()

    def check_kill(self):
        for deathzone in self.deathzone_list:
            kill = deathzone.kill()
            if kill:
                return True, self.player
        return False, -1


def sdf_circle(start, pos, r):
    distance = return_distance(start, pos) - r
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


def return_distance(a, b):
    delta_x = a[0] - b[0]
    delta_y = a[1] - b[1]
    distance = math.sqrt(delta_x ** 2 + delta_y ** 2)
    return distance


def collision(pos, r):
    if return_max_distance(pos) < r:
        return True
    else:
        return False


def spawn():
    global startpos
    pos = (random.randint(1, width), random.randint(1, height))
    if collision(pos, player_size):
        spawn()
    else:
        startpos = pos


def hit():
    for bullet in bullets:
        distance = return_distance(bullet.pos, startpos)
        if distance < (player_size + bullet_size) and str(bullet.player) != str(self_player_id):
            bullet.lifetime = 0
            return True, bullet.player

    for ability in abilities:
        kill, player = ability.check_kill()
        if kill:
            return True, player

    return False, -1


def death():
    global death_menu, startpos, deaths, cooldown
    startpos = (-10, -10)
    deaths += 1
    cooldown = fps * ability_cooldown
    death_menu = True


def update():
    global cooldown, cursor_timer
    for player_id, player_info in players.items():
        pos, player_angle, player_is_shooting, player_is_ability, player_name, player_deaths = player_info
        if player_is_shooting:
            bullets.append(Bullet(pos, player_angle, player_id))
        if player_is_ability:
            abilities.append(Ability(pos, player_angle, player_id))

    is_hit, player = hit()
    if is_hit:
        print(f"You were hit by player {player}")
        death()

    for ability in abilities:
        alive = ability.tick()
        if not alive:
            abilities.pop(abilities.index(ability))
    for bullet in bullets:
        alive = bullet.tick()
        if not alive:
            bullets.pop(bullets.index(bullet))

    if not death_menu and not start_menu and not name_menu:
        cooldown -= 1

    if name_menu:
        cursor_timer -= 1
        if cursor_timer < (0 - cursor_speed * fps):
            cursor_timer = cursor_speed * fps


def hacks():
    global name, player_speed, ability_cooldown, cooldown, render_tag, ignore_objects
    if name == "speeeeeeeeeeeeed":
        player_speed = 6
        name = "#hacks"
    elif name == "empty":
        name = " "
    elif name == "GAY":
        player_speed = -3
    elif name == "godmode":
        ability_cooldown = 0
        cooldown = 0
        name = "#hacks"
    elif name == "hugeballs69":
        render_tag = "balls"
    elif name == "invisible":
        render_tag = "invis"
        name = "invis"
    elif name == "emc2":
        ignore_objects = True
        name = "#hacks"
    elif name == "motionless":
        player_speed = 0


def render():
    screen.fill((10, 10, 30))

    if not (start_menu or name_menu):

        for ability in abilities:
            ability.render()

        render_obstacles()

        if not death_menu:
            ray_march(get_mouse_angle(pygame.mouse.get_pos()))

        render_players()

        for bullet in bullets:
            bullet.render()

        render_scoreboard()

        if death_menu:
            pygame.draw.rect(screen, BUTTON_COLOR, death_menu_rects[1])
            pygame.draw.rect(screen, BUTTON_COLOR, death_menu_rects[2])
            for ind in range(len(death_menu_rects)):
                text, font, color = death_menu_texts[ind]
                text = font.render(text, True, color)
                text_rect = text.get_rect(center=death_menu_rects[ind].center)
                screen.blit(text, text_rect)

    if start_menu:
        render_start_menu()

    if name_menu:
        render_name_menu()

    pygame.display.flip()


def render_players():
    with player_lock:
        for player_id, player_info in players.items():
            position = player_info[0]
            player_name = player_info[4]

            if render_tag == "":
                player_name_text = font_26.render(player_name, True, PLAYER_COLOR)
                player_name_rect = player_name_text.get_rect(center=(position[0], position[1] - 20))
                screen.blit(player_name_text, player_name_rect)
                pygame.draw.circle(screen, PLAYER_COLOR, (position[0], position[1]), player_size)
            elif render_tag == "balls":
                pygame.draw.circle(screen, PLAYER_COLOR, (position[0] + player_size, position[1]), player_size)
                pygame.draw.circle(screen, PLAYER_COLOR, (position[0] - player_size, position[1]), player_size)
                pygame.draw.circle(screen, PLAYER_COLOR, (position[0], position[1] - player_size), player_size)
                pygame.draw.circle(screen, PLAYER_COLOR, (position[0], position[1] - player_size - 40), player_size)
                pygame.draw.rect(screen, PLAYER_COLOR, pygame.Rect(position[0] - player_size,
                                                                   position[1] - player_size - 40,
                                                                   player_size * 2, player_size + 40))
            elif render_tag == "invis":
                pass


def render_start_menu():
    screen.blit(start_screen, ((width - start_screen.get_width()) // 2, (height - start_screen.get_height()) // 2))
    start_text = font_256.render("Start", True, TEXT_COLOR)
    start_text_rect = start_text.get_rect(center=start_menu_rect.center)
    screen.blit(start_text, start_text_rect)


def render_name_menu():
    name_menu_text_name = font_128.render("Name:", True, TEXT_COLOR)
    name_menu_text_rect_name = name_menu_text_name.get_rect(center=(width // 2, height // 3))
    screen.blit(name_menu_text_name, name_menu_text_rect_name)

    name_background_rect = pygame.Rect(width // 2 - width // 4, height // 2 - height // 14, width // 2, height // 8)
    pygame.draw.rect(screen, BUTTON_COLOR, name_background_rect)
    name_text = font_128.render(name, True, TEXT_COLOR)
    name_text_rect = name_text.get_rect(center=name_background_rect.center)
    screen.blit(name_text, name_text_rect)

    cursor = pygame.Rect(0, 0, 10, name_text_rect.height)
    cursor.topleft = name_text_rect.topright

    pygame.draw.rect(screen, BUTTON_COLOR, name_menu_rect)
    screen.blit(name_menu_text, name_menu_text_rect)
    if cursor_timer > 0:
        pygame.draw.rect(screen, PLAYER_COLOR, cursor)


def render_obstacles():
    for circle in circle_list:
        pos, r = circle
        pygame.draw.circle(screen, (50, 125, 100), pos, r)

    for rect in rect_list:
        pos, size = rect
        rect = pygame.Rect(0, 0, size[0] * 2, size[1] * 2)
        rect.center = pos
        pygame.draw.rect(screen, (75, 100, 150), rect)


def render_scoreboard():
    sorted_players = sorted(players, key=lambda x: players[x][5], reverse=True)

    for player in range(len(sorted_players)):
        player_id = sorted_players[player]
        player_name = players[player_id][4]
        player_deaths = players[player_id][5]
        text = font_26.render(f"{player_name} {player_deaths}", True, PLAYER_COLOR)
        rect = text.get_rect(topright=(width - 10, 10 + player * 20))
        screen.blit(text, rect)


def ray_march(direction):
    ray_march_circles = []
    length = 0
    new_pos = startpos
    for j in range(iterations):
        step = return_max_distance(new_pos)
        length += step

        ray_march_circles.append((new_pos, step))

        new_pos = (math.cos(direction) * length + startpos[0], math.sin(direction) * length + startpos[1])

        if step < 0.01 or length > max_distance:
            break
    end_pos = (math.cos(direction) * length + startpos[0], math.sin(direction) * length + startpos[1])
    pygame.draw.line(screen, (255, 0, 0), startpos, end_pos)

    if cooldown < 1:
        for circle in ray_march_circles:
            pos, r = circle
            pygame.draw.circle(screen, (225, 208, 50), pos, r, 1)


def get_mouse_angle(pos):
    global angle
    x = pos[0] - startpos[0]
    y = pos[1] - startpos[1]
    angle = math.atan2(y, x)
    return angle


def move_start_pos(x_movement, y_movement):
    global startpos
    x, y = startpos
    x += x_movement
    y += y_movement
    new_pos = (x, y)
    if not collision(new_pos, player_size) or ignore_objects:
        startpos = new_pos


def key_handler(keys):
    global running, startpos, name_menu
    if keys[pygame.K_ESCAPE]:
        running = False
    if not death_menu and not start_menu and not name_menu:
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move_start_pos(0, -player_speed)
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move_start_pos(0, player_speed)
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move_start_pos(-player_speed, 0)
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move_start_pos(player_speed, 0)
    if name_menu and keys[pygame.K_RETURN]:
        spawn()
        if allow_hacks:
            hacks()
        name_menu = False


def write_name(event):
    global name
    if event.unicode.isalnum() and len(name) < 16:
        name += event.unicode
    elif event.key == pygame.K_BACKSPACE:
        name = name[:-1]


def mouse_handler(button):
    global cooldown, is_ability, is_shooting, death_menu, running, start_menu, name_menu
    if button == 1 and not death_menu and not start_menu and not name_menu:
        bullets.append(Bullet(startpos, angle, self_player_id))
        is_shooting = True
    if button == 3 and cooldown < 1 and not death_menu and not start_menu and not name_menu:
        abilities.append(Ability(startpos, angle, self_player_id))
        cooldown = fps * ability_cooldown
        is_ability = True

    if button == 1 and death_menu:
        mouse_pos = pygame.mouse.get_pos()
        if death_menu_rects[1].collidepoint(mouse_pos):
            spawn()
            death_menu = False
        if death_menu_rects[2].collidepoint(mouse_pos):
            running = False

    if button == 1 and start_menu:
        if start_menu_rect.collidepoint(pygame.mouse.get_pos()):
            start_menu = False
            name_menu = True

    if button == 1 and name_menu:
        if name_menu_rect.collidepoint(pygame.mouse.get_pos()) and len(name) != 0:
            spawn()
            if allow_hacks:
                hacks()
            name_menu = False


def receive_data(sock):
    global players
    buffer = b""

    try:
        while True:
            data = sock.recv(2048)
            if not data:
                print("Die Verbindung wurde geschlossen.")
                break

            buffer += data

            while b'}' in buffer:
                start = buffer.find(b'{')
                end = buffer.find(b'}', start) + 1

                if start != -1 and end != 0:
                    json_data = buffer[start:end]
                    buffer = buffer[end:]
                    try:
                        player_data = json.loads(json_data.decode('utf-8'))

                        if player_data.get("action") == "close_connection":
                            print(f"Der Server hat das Spiel beendet.")
                            return
                        else:
                            with player_lock:
                                players = player_data
                    except json.decoder.JSONDecodeError as e:
                        print(f"Error decoding JSON: {e}")
    except ConnectionAbortedError:
        print("Die Verbindung wurde abgebrochen.")
    except Exception as e:
        print(f"Fehler beim Empfangen von Daten: {e}")


def receive_initial_lists(sock):
    buffer = b""
    while True:
        data = sock.recv(2048)
        if not data:
            return None

        buffer += data

        if b'}' in buffer:
            start = buffer.find(b'{')
            end = buffer.find(b'}', start) + 1

            if start != -1 and end != 0:
                json_data = buffer[start:end]
                buffer = buffer[end:]

                try:
                    initial_data = json.loads(json_data.decode('utf-8'))
                    return initial_data.get("circles", []), initial_data.get("rectangles", [])
                except json.decoder.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")


def quit_game(sock):
    try:
        data = {"action": "close_connection", "player_id": self_player_id}
        serialized_data = json.dumps(data).encode('utf-8')
        sock.send(serialized_data)

        sock.close()
    except Exception as e:
        print(f"Fehler beim Beenden des Spiels: {e}")


client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((server_ip, server_port))

self_player_id = int(client.recv(1024).decode('utf-8'))
print(f"Connected as Player {self_player_id}")

allow_hacks = client.recv(1024).decode('utf-8')
if allow_hacks == "True":
    allow_hacks = True
else:
    allow_hacks = False

circle_list, rect_list = receive_initial_lists(client)

data_receiver = threading.Thread(target=receive_data, args=(client,))
data_receiver.start()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_handler(event.button)
        if event.type == pygame.KEYDOWN and name_menu:
            write_name(event)

    key_handler(pygame.key.get_pressed())

    data = {"player_id": self_player_id, "pos": startpos, "direction": angle, "is_shooting": is_shooting,
            "is_ability": is_ability, "name": name, "deaths": deaths}
    serialized_data = json.dumps(data).encode('utf-8')
    client.send(serialized_data)

    update()

    if is_shooting:
        is_shooting = False
    if is_ability:
        is_ability = False

    render()
    clock.tick(120)

quit_game(client)
pygame.quit()
sys.exit()
