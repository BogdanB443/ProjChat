
import socket
import threading
import time
import os
from database import ChatDatabase
from server import ChatServer

SERVER_IP = "192.168.8.125"
SERVER_PORT = 5555

def test_database_register_and_login():
    db = ChatDatabase("test_chat.db")
    nickname = "test_user"
    password = "1234"

    db.cursor.execute("DELETE FROM users WHERE nickname=?", (nickname,))
    db.conn.commit()

    assert db.register_user(nickname, password) is True
    assert db.check_credentials(nickname, password) is True
    db.close()
    os.remove("test_chat.db")
    print("Регистрация и вход в БД: Success")

def test_server_runs_and_accepts_connection():
    def run_server():
        ChatServer()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(1)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(2)
        sock.connect((SERVER_IP, SERVER_PORT))
        print(f"Сервер доступен на {SERVER_IP}:{SERVER_PORT}: Success")
        assert True
    except Exception:
        print(f"Сервер не отвечает на {SERVER_IP}:{SERVER_PORT}")
        assert False
    finally:
        sock.close()

if __name__ == "__main__":
    test_database_register_and_login()
    test_server_runs_and_accepts_connection()
