import socket
import threading
import json
import struct
from database import ChatDatabase

PORT = 5555
SERVER_IP = '192.168.8.125'

class ChatServer:
    def __init__(self):
        self.clients = {}
        self.nicknames_to_sockets = {}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.server_socket.bind((SERVER_IP, PORT))
            print(f"Сервер пытается запуститься на {SERVER_IP}:{PORT}")
        except OSError as e:
            print(f"Ошибка привязки к IP {SERVER_IP}: {e}")
            print(f"Убедитесь, что {SERVER_IP} является действительным IP-адресом вашего компьютера.")
            print("Сервер не может быть запущен по указанному адресу.")
            exit()

        self.server_socket.listen()

        self.db = ChatDatabase()

        print(f"Сервер запущен и слушает на {SERVER_IP}:{PORT}")
        print("Для подключения используйте этот IP и порт.")
        self.accept_connections()

    def _send_message(self, sock, message_type, data):
        try:
            payload = json.dumps({"type": message_type, "data": data})
            payload_bytes = payload.encode('utf-8')
            length_prefix = struct.pack('>I', len(payload_bytes))
            sock.sendall(length_prefix + payload_bytes)
        except Exception as e:
            print(f"Ошибка отправки данных: {e}")
            self.remove_client(sock)

    def _receive_message(self, sock):
        raw_length = sock.recv(4)
        if not raw_length:
            return None
        length = struct.unpack('>I', raw_length)[0]

        data = b''
        while len(data) < length:
            packet = sock.recv(length - len(data))
            if not packet:
                return None
            data += packet
        return data.decode('utf-8')

    def broadcast(self, message_type, data, sender_socket=None):
        for client_socket, nickname in list(self.clients.items()):
            if client_socket != sender_socket:
                self._send_message(client_socket, message_type, data)

    def send_to_client(self, client_socket, message_type, data):
        self._send_message(client_socket, message_type, data)

    def remove_client(self, client_socket):
        if client_socket in self.clients:
            nickname = self.clients[client_socket]
            del self.clients[client_socket]
            if nickname in self.nicknames_to_sockets and self.nicknames_to_sockets[nickname] == client_socket:
                del self.nicknames_to_sockets[nickname]
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
                client_socket.close()
            except OSError as e:
                print(f"Ошибка при закрытии сокета для {nickname}: {e}")
            print(f"{nickname} отключился.")
            self.broadcast("user_left", nickname)
            self.broadcast("online_users", list(self.clients.values()))

    def handle_client(self, client_socket):
        authenticated = False
        nickname = None

        while not authenticated:
            try:
                raw_data = self._receive_message(client_socket)
                if raw_data is None:
                    raise Exception("Client disconnected during authentication")

                request = json.loads(raw_data)
                req_type = request.get("type")
                req_data = request.get("data")

                if req_type == "register":
                    nickname = req_data.get("nickname")
                    password = req_data.get("password")
                    if self.db.register_user(nickname, password):
                        self.send_to_client(client_socket, "auth_response", {"status": "success", "message": "Регистрация успешна! Теперь войдите."})
                    else:
                        self.send_to_client(client_socket, "auth_response", {"status": "error", "message": "Никнейм уже занят."})
                elif req_type == "login":
                    nickname = req_data.get("nickname")
                    password = req_data.get("password")
                    if self.db.check_credentials(nickname, password):
                        if nickname in self.clients.values():
                            self.send_to_client(client_socket, "auth_response", {"status": "error", "message": "Этот пользователь уже онлайн."})
                        else:
                            self.clients[client_socket] = nickname
                            self.nicknames_to_sockets[nickname] = client_socket
                            authenticated = True
                            self.send_to_client(client_socket, "auth_response", {"status": "success", "message": "Вход выполнен успешно!", "nickname": nickname})
                            print(f"{nickname} подключился.")
                            self.broadcast("user_joined", nickname, client_socket)
                            self.broadcast("online_users", list(self.clients.values()))
                            self.send_history(client_socket)
                    else:
                        self.send_to_client(client_socket, "auth_response", {"status": "error", "message": "Неверный никнейм или пароль."})
                else:
                    self.send_to_client(client_socket, "auth_response", {"status": "error", "message": "Неизвестный тип запроса."})

            except json.JSONDecodeError:
                print(f"Неверный формат JSON от клиента во время аутентификации.")
                self.send_to_client(client_socket, "auth_response", {"status": "error", "message": "Неверный формат данных."})
                self.remove_client(client_socket)
                return
            except Exception as e:
                print(f"Ошибка аутентификации клиента: {e}")
                self.remove_client(client_socket)
                return

        while True:
            try:
                raw_message = self._receive_message(client_socket)
                if raw_message is None:
                    raise Exception("Соединение разорвано клиентом")

                message_obj = json.loads(raw_message)
                msg_type = message_obj.get("type")
                msg_data = message_obj.get("data")

                if msg_type == "chat_message":
                    self.db.save_message(nickname, msg_data)
                    self.broadcast("chat_message", {"nickname": nickname, "message": msg_data}, client_socket)
                elif msg_type == "private_message":
                    recipient_nickname = msg_data.get("recipient")
                    private_msg_content = msg_data.get("message")
                    
                    if recipient_nickname == nickname:
                        self.send_to_client(client_socket, "system_message", "Вы не можете отправить личное сообщение самому себе.")
                        continue

                    recipient_socket = self.nicknames_to_sockets.get(recipient_nickname)
                    if recipient_socket:
                        self._send_message(recipient_socket, "private_message", {"sender": nickname, "message": private_msg_content})
                    else:
                        self.send_to_client(client_socket, "system_message", f"Пользователь '{recipient_nickname}' не в сети.")
                elif msg_type == "request_online_users":
                    self.send_to_client(client_socket, "online_users", list(self.clients.values()))
                else:
                    print(f"Неизвестный тип сообщения от {nickname}: {msg_type}")

            except json.JSONDecodeError:
                print(f"Неверный формат JSON от {nickname}")
            except Exception as e:
                print(f"Ошибка при обработке сообщения от {nickname}: {e}")
                self.remove_client(client_socket)
                break

    def send_history(self, client_socket):
        try:
            history = self.db.get_history()
            formatted_history = []
            for entry in reversed(history):
                nickname, message, timestamp = entry
                formatted_history.append(f"[{timestamp}] {nickname}: {message}")
            self.send_to_client(client_socket, "chat_history", formatted_history)
        except Exception as e:
            print(f"Ошибка отправки истории: {e}")

    def accept_connections(self):
        while True:
            client, addr = self.server_socket.accept()
            print(f"Попытка подключения от {addr}")
            thread = threading.Thread(target=self.handle_client, args=(client,))
            thread.daemon = True
            thread.start()

if __name__ == "__main__":
    ChatServer()