import socket
import json
import threading
import random
import time


def get_ipv4_address():
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        return ip_address

    except Exception as e:
        print(f"Fehler beim Abrufen der IPv4-Adresse: {e}")
        return None


def handle_client(client_socket, player_data):
    buffer = b""

    while True:
        try:
            data = client_socket.recv(2048)
            if not data:
                break

            buffer += data

            while b'}' in buffer:
                start = buffer.find(b'{')
                end = buffer.find(b'}', start) + 1

                if start != -1 and end != 0:
                    json_data = buffer[start:end].decode('utf-8')
                    buffer = buffer[end:]

                    received_data = json.loads(json_data)
                    if received_data.get("action") == "close_connection":
                        player_id = received_data['player_id']
                        print(f"Client {player_id} hat das Spiel verlassen.")
                        clients.remove(client_socket)
                        client_socket.close()
                        del player_data[player_id]
                        return
                    else:
                        player_data[received_data["player_id"]] = received_data["pos"], received_data["direction"], received_data["is_shooting"], received_data["is_ability"], received_data["name"], received_data["deaths"]

                    broadcast_data = json.dumps(player_data).encode('utf-8')
                    for c in clients:
                        c.send(broadcast_data)

        except Exception as e:
            print(f"Error handling client: {e}")
            break


def start_server():
    global current_id
    print(f"IP: {get_ipv4_address()}\nPort: {port}\n")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', port))
    server.listen(queue)

    end_time = time.time()
    print(f"[*] Server started in {end_time - start_time} seconds")

    while True:
        client, addr = server.accept()
        print(f"[*] Accepted connection from {addr[0]}:{addr[1]}")

        player_id = current_id
        current_id += 1

        player_data[player_id] = [[-10, -10], 0, False, False, "", 0]

        client.send(str(player_id).encode('utf-8'))
        client.send(str(allow_hacks).encode('utf-8'))
        send_initial_lists(client)

        client_handler = threading.Thread(target=handle_client, args=(client, player_data))
        client_handler.start()

        clients.append(client)


def send_initial_lists(client_socket):
    initial_data = {"circles": circle_list, "rectangles": rect_list}
    serialized_data = json.dumps(initial_data).encode('utf-8')

    try:
        client_socket.send(serialized_data)
    except socket.error as e:
        print(f"Error sending initial lists: {e}")


def generate_map(number):
    for i in range(number):
        ran = random.randint(1, 2)
        if ran == 1:
            circle_list.append(((random.randint(0, width), random.randint(0, height)), random.randint(10, 40)))
        elif ran == 2:
            rect_list.append(
                ((random.randint(0, width), random.randint(0, height)),
                 (random.randint(10, 40), random.randint(10, 40))))


if __name__ == "__main__":
    start_time = time.time()

    with open("server_config.txt") as file:
        server_data = json.load(file)

    port = server_data["port"]
    queue = server_data["queue"]
    width, height = server_data["width"], server_data["height"]
    objects = server_data["objects"]
    allow_hacks = server_data["hacks"]

    clients = []
    player_data = {}

    circle_list = []
    rect_list = [((width // 2, -5), (width // 2, 5)), ((-5, height // 2), (5, height // 2)),
                 ((width + 5, height // 2), (5, height // 2)), ((width // 2, height + 5), (width // 2, 5))]
    current_id = 1

    generate_map(objects)
    start_server()
