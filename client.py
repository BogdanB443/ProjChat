import socket
import tkinter as tk
from tkinter import scrolledtext, messagebox, font
from tkinter import ttk
import threading
import json
import struct

class ChatClient:
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.local_ip = self.get_local_ip()
        self.nickname = None
        self.selected_private_chat_user = None
        self.private_chat_windows = {}

        self.root = tk.Tk()
        self.root.title(f"Универсальный Чат | Мой IP: {self.local_ip}")
        self.root.geometry("800x600")
        self.root.configure(bg="#222222")

        self.font_normal = font.Font(family="Arial", size=10)
        self.font_bold = font.Font(family="Arial", size=10, weight="bold")
        self.font_large = font.Font(family="Arial", size=12, weight="bold")

        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure("TNotebook", background="#222222", borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#333333", foreground="white",
                             lightcolor="#444444", darkcolor="#222222", padding=[10, 5])
        self.style.map("TNotebook.Tab", background=[("selected", "#555555")],
                       foreground=[("selected", "white")])
        self.style.configure("TFrame", background="#222222")

        self.auth_frame = None
        self.chat_frame = None
        self.online_users_listbox = None
        self.private_chat_label = None
        self.notebook = None
        self.general_chat_tab = None
        self.private_chat_tab_frame = None
        self.current_active_chat_area = None

        self.show_auth_screen()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def show_auth_screen(self):
        if self.chat_frame:
            self.chat_frame.destroy()
        if self.auth_frame:
            self.auth_frame.destroy()

        self.auth_frame = tk.Frame(self.root, bg="#222222")
        self.auth_frame.pack(expand=True, fill=tk.BOTH)

        tk.Label(self.auth_frame, text="Добро пожаловать в Чат", font=("Arial", 16, "bold"),
                 bg="#222222", fg="white").pack(pady=20)

        tk.Label(self.auth_frame, text="Никнейм:", bg="#222222", fg="white", font=self.font_normal).pack(pady=(10, 0))
        self.auth_nickname_entry = tk.Entry(self.auth_frame, font=self.font_normal, bg="#444444", fg="white",
                                            insertbackground="white", width=30)
        self.auth_nickname_entry.pack(pady=5)

        tk.Label(self.auth_frame, text="Пароль:", bg="#222222", fg="white", font=self.font_normal).pack(pady=(10, 0))
        self.auth_password_entry = tk.Entry(self.auth_frame, font=self.font_normal, bg="#444444", fg="white",
                                            insertbackground="white", show="*", width=30)
        self.auth_password_entry.pack(pady=5)

        button_style = {
            'bg': '#444444', 'fg': 'white',
            'activebackground': '#666666',
            'activeforeground': 'white',
            'font': self.font_bold,
            'width': 20
        }

        tk.Button(self.auth_frame, text="Войти", command=self.attempt_login, **button_style).pack(pady=10)
        tk.Button(self.auth_frame, text="Зарегистрироваться", command=self.attempt_register, **button_style).pack(pady=10)

        self.status_bar = tk.Label(
            self.auth_frame, text="Подключение к серверу...",
            anchor=tk.W, bg="#111111", fg="white", font=self.font_normal
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.connect_to_server()

    def connect_to_server(self):
        SERVER_ADDR = '192.168.8.125'
        PORT = 5555

        try:
            self.update_status(f"Попытка подключения к {SERVER_ADDR}:{PORT}...")
            self.client_socket.connect((SERVER_ADDR, PORT))
            self.update_status("Подключено к серверу. Введите данные.")

            receive_thread = threading.Thread(target=self.receive_auth_response)
            receive_thread.daemon = True
            receive_thread.start()

        except Exception as e:
            self.update_status(f"Ошибка подключения к серверу: {e}. Проверьте, запущен ли сервер и доступен ли IP {SERVER_ADDR}.")
            messagebox.showerror("Ошибка подключения", f"Не удалось подключиться к серверу: {e}")

    def _send_message(self, sock, message_type, data):
        try:
            payload = json.dumps({"type": message_type, "data": data})
            payload_bytes = payload.encode('utf-8')
            length_prefix = struct.pack('>I', len(payload_bytes))
            sock.sendall(length_prefix + payload_bytes)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось отправить данные: {e}")
            self.on_close()

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

    def send_auth_request(self, req_type, nickname, password):
        self._send_message(self.client_socket, req_type, {"nickname": nickname, "password": password})

    def attempt_login(self):
        nickname = self.auth_nickname_entry.get().strip()
        password = self.auth_password_entry.get().strip()
        if not nickname or not password:
            messagebox.showwarning("Внимание", "Пожалуйста, введите никнейм и пароль.")
            return
        self.send_auth_request("login", nickname, password)

    def attempt_register(self):
        nickname = self.auth_nickname_entry.get().strip()
        password = self.auth_password_entry.get().strip()
        if not nickname or not password:
            messagebox.showwarning("Внимание", "Пожалуйста, введите никнейм и пароль.")
            return
        self.send_auth_request("register", nickname, password)

    def receive_auth_response(self):
        while True:
            try:
                response_raw = self._receive_message(self.client_socket)
                if response_raw is None:
                    raise Exception("Соединение разорвано сервером")

                response = json.loads(response_raw)
                if response["type"] == "auth_response":
                    status = response["data"]["status"]
                    message = response["data"]["message"]
                    if status == "success":
                        self.nickname = response["data"].get("nickname", self.auth_nickname_entry.get())
                        messagebox.showinfo("Успех", message)
                        self.root.after(0, self.show_chat_screen)
                        break
                    else:
                        messagebox.showerror("Ошибка аутентификации", message)
                else:
                    print(f"Получен неожиданный тип сообщения во время аутентификации: {response['type']}")
            except json.JSONDecodeError:
                self.update_status("Ошибка: Неверный формат данных от сервера (аутентификация).")
            except Exception as e:
                self.update_status(f"[Система] Отключено от сервера: {e}")
                self.root.after(0, self.on_close)
                break

    def show_chat_screen(self):
        if self.auth_frame:
            self.auth_frame.destroy()

        self.chat_frame = tk.Frame(self.root, bg="#222222")
        self.chat_frame.pack(expand=True, fill=tk.BOTH)

        online_users_sidebar = tk.Frame(self.chat_frame, bg="#222222", bd=2, relief=tk.GROOVE)
        online_users_sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        tk.Label(online_users_sidebar, text="Онлайн пользователи:", bg="#222222", fg="white", font=self.font_bold).pack(pady=(0, 5))
        self.online_users_listbox = tk.Listbox(online_users_sidebar, bg="#333333", fg="white", font=self.font_normal,
                                               selectbackground="#666666", selectforeground="white", width=25, height=20)
        self.online_users_listbox.pack(expand=True, fill=tk.BOTH)
        self.online_users_listbox.bind("<<ListboxSelect>>", self.open_private_chat_tab)

        self.notebook = ttk.Notebook(self.chat_frame)
        self.notebook.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=(0, 10), pady=10)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        self.general_chat_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.general_chat_tab, text="Общий чат")

        general_chat_area_frame = tk.Frame(self.general_chat_tab, bg="#222222")
        general_chat_area_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        self.general_chat_text = scrolledtext.ScrolledText(general_chat_area_frame, state='disabled', wrap=tk.WORD,
                                                 bg="#333333", fg="white", insertbackground="white",
                                                 font=self.font_normal)
        self.general_chat_text.pack(expand=True, fill=tk.BOTH)
        self.general_chat_text.tag_config('private_sent', foreground='#FFD700')
        self.general_chat_text.tag_config('private_received', foreground='#ADFF2F')
        self.general_chat_text.tag_config('system', foreground='#87CEEB')
        self.general_chat_text.tag_config('general', foreground='white')
        self.current_active_chat_area = self.general_chat_text

        bottom_frame = tk.Frame(self.root, bg="#222222")
        bottom_frame.pack(padx=10, pady=10, fill=tk.X, side=tk.BOTTOM)

        self.entry = tk.Entry(bottom_frame, font=self.font_normal, bg="#444444", fg="white",
                            insertbackground="white")
        self.entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))
        self.entry.bind("<Return>", self.send_message)

        button_style = {
            'bg': '#444444', 'fg': 'white',
            'activebackground': '#666666',
            'activeforeground': 'white',
            'font': self.font_bold
        }
        self.send_btn = tk.Button(bottom_frame, text="Отправить", command=self.send_message, **button_style)
        self.send_btn.pack(side=tk.RIGHT)

        self.ip_label = tk.Label(
            self.root, text=f"Ваш IP: {self.local_ip}",
            anchor=tk.W, bg="#111111", fg="white", font=self.font_normal
        )
        self.ip_label.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_bar = tk.Label(
            self.root, text=f"Статус: Подключено как {self.nickname}",
            anchor=tk.W, bg="#111111", fg="white", font=self.font_normal
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.daemon = True
        receive_thread.start()

        self._send_message(self.client_socket, "request_online_users", {})
        self.load_general_chat_history()

    def update_status(self, text):
        if self.status_bar:
            self.status_bar.config(text=f"Статус: {text}")

    def display_message(self, chat_area_widget, message, tag='general'):
        chat_area_widget.config(state='normal')
        chat_area_widget.insert(tk.END, message + "\n", tag)
        chat_area_widget.config(state='disabled')
        chat_area_widget.yview(tk.END)

    def load_general_chat_history(self):
        self._send_message(self.client_socket, "request_general_history", {})

    def open_private_chat_tab(self, event):
        selection = self.online_users_listbox.curselection()
        if selection:
            index = selection[0]
            selected_user = self.online_users_listbox.get(index)
            if selected_user == self.nickname:
                messagebox.showwarning("Внимание", "Нельзя открыть личный чат с самим собой.")
                return

            self.selected_private_chat_user = selected_user

            if selected_user not in self.private_chat_windows:
                private_chat_frame = ttk.Frame(self.notebook, style="TFrame")
                private_chat_area = scrolledtext.ScrolledText(private_chat_frame, state='disabled', wrap=tk.WORD,
                                                            bg="#333333", fg="white", insertbackground="white",
                                                            font=self.font_normal)
                private_chat_area.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
                private_chat_area.tag_config('private_sent', foreground='#FFD700')
                private_chat_area.tag_config('private_received', foreground='#ADFF2F')
                private_chat_area.tag_config('system', foreground='#87CEEB')
                private_chat_area.tag_config('general', foreground='white')

                self.notebook.add(private_chat_frame, text=selected_user)
                self.private_chat_windows[selected_user] = private_chat_area
                print(f"Открыта новая вкладка для ЛС с {selected_user}")

            tab_index = self.notebook.index(self.notebook.select())
            for i, tab_id in enumerate(self.notebook.tabs()):
                if self.notebook.tab(tab_id, "text") == selected_user:
                    tab_index = i
                    break
            self.notebook.select(tab_index)

            self._send_message(self.client_socket, "request_private_history", {"target_user": self.selected_private_chat_user})


    def on_tab_change(self, event):
        selected_tab_id = self.notebook.select()
        tab_text = self.notebook.tab(selected_tab_id, "text")

        if tab_text == "Общий чат":
            self.selected_private_chat_user = None
            self.current_active_chat_area = self.general_chat_text
            self.online_users_listbox.selection_clear(0, tk.END)
            print("Переключено на общий чат.")
        else:
            self.selected_private_chat_user = tab_text
            self.current_active_chat_area = self.private_chat_windows[tab_text]
            users_in_listbox = [self.online_users_listbox.get(i) for i in range(self.online_users_listbox.size())]
            if tab_text in users_in_listbox:
                idx = users_in_listbox.index(tab_text)
                self.online_users_listbox.selection_clear(0, tk.END)
                self.online_users_listbox.selection_set(idx)
                self.online_users_listbox.see(idx)
            print(f"Переключено на ЛС с {tab_text}.")


    def send_message(self, event=None):
        message = self.entry.get()
        if not message:
            return

        if self.selected_private_chat_user and self.selected_private_chat_user != self.nickname:
            self._send_message(self.client_socket, "private_message", {
                "recipient": self.selected_private_chat_user,
                "message": message
            })
            self.display_message(self.current_active_chat_area,
                                 f"[ЛС -> {self.selected_private_chat_user}] Вы: {message}", 'private_sent')
        else:
            self._send_message(self.client_socket, "chat_message", message)
            self.display_message(self.general_chat_text, f"Вы: {message}", 'general')

        self.entry.delete(0, tk.END)

    def update_online_users(self, users):
        if self.online_users_listbox:
            self.online_users_listbox.delete(0, tk.END)
            sorted_users = sorted([u for u in users if u != self.nickname])
            for user in sorted_users:
                self.online_users_listbox.insert(tk.END, user)

            open_tabs = [self.notebook.tab(tab_id, "text") for tab_id in self.notebook.tabs()]
            for tab_text in open_tabs:
                if tab_text != "Общий чат" and tab_text not in users:
                    try:
                        tab_id_to_close = self.notebook.tabs()[open_tabs.index(tab_text)]
                        self.notebook.forget(tab_id_to_close)
                        del self.private_chat_windows[tab_text]
                        print(f"Закрыта вкладка для {tab_text}, так как пользователь вышел.")
                    except Exception as e:
                        print(f"Ошибка при закрытии вкладки: {e}")

            if self.selected_private_chat_user and self.selected_private_chat_user not in users:
                self.notebook.select(self.general_chat_tab)
                self.selected_private_chat_user = None
                self.current_active_chat_area = self.general_chat_text


    def process_server_message(self, message_obj):
        msg_type = message_obj.get("type")
        msg_data = message_obj.get("data")

        if msg_type == "chat_message":
            nickname = msg_data.get("nickname")
            message = msg_data.get("message")
            self.display_message(self.general_chat_text, f"{nickname}: {message}", 'general')
        elif msg_type == "private_message":
            sender = msg_data.get("sender")
            message = msg_data.get("message")

            if sender not in self.private_chat_windows:
                private_chat_frame = ttk.Frame(self.notebook, style="TFrame")
                private_chat_area = scrolledtext.ScrolledText(private_chat_frame, state='disabled', wrap=tk.WORD,
                                                            bg="#333333", fg="white", insertbackground="white",
                                                            font=self.font_normal)
                private_chat_area.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
                private_chat_area.tag_config('private_sent', foreground='#FFD700')
                private_chat_area.tag_config('private_received', foreground='#ADFF2F')
                private_chat_area.tag_config('system', foreground='#87CEEB')
                private_chat_area.tag_config('general', foreground='white')

                self.notebook.add(private_chat_frame, text=sender)
                self.private_chat_windows[sender] = private_chat_area
                print(f"Автоматически открыта новая вкладка для входящего ЛС от {sender}")

            self.display_message(self.private_chat_windows[sender], f"[ЛС от {sender}] {message}", 'private_received')

        elif msg_type == "chat_history" or msg_type == "request_general_history":
            self.general_chat_text.config(state='normal')
            self.general_chat_text.delete('1.0', tk.END)
            for msg in msg_data:
                self.display_message(self.general_chat_text, msg, 'general')
            self.general_chat_text.config(state='disabled')
        elif msg_type == "private_chat_history":
            target_user = self.selected_private_chat_user
            if target_user in self.private_chat_windows:
                chat_area = self.private_chat_windows[target_user]
                chat_area.config(state='normal')
                chat_area.delete('1.0', tk.END)
                for msg_line in msg_data:
                    if f"[ЛС -> {target_user}] Вы:" in msg_line:
                        self.display_message(chat_area, msg_line, 'private_sent')
                    elif f"[ЛС от {target_user}]" in msg_line:
                        self.display_message(chat_area, msg_line, 'private_received')
                    else:
                        self.display_message(chat_area, msg_line, 'general')
                chat_area.config(state='disabled')
        elif msg_type == "user_joined":
            self.display_message(self.general_chat_text, f"[Система] {msg_data} присоединился к чату.", 'system')
            self._send_message(self.client_socket, "request_online_users", {})
        elif msg_type == "user_left":
            self.display_message(self.general_chat_text, f"[Система] {msg_data} покинул чат.", 'system')
            self._send_message(self.client_socket, "request_online_users", {})
        elif msg_type == "online_users":
            self.update_online_users(msg_data)
        elif msg_type == "system_message":
            if self.current_active_chat_area:
                self.display_message(self.current_active_chat_area, f"[Система] {msg_data}", 'system')
            else:
                self.display_message(self.general_chat_text, f"[Система] {msg_data}", 'system')
        else:
            print(f"Неизвестный тип сообщения от сервера: {msg_type}")


    def receive_messages(self):
        while True:
            try:
                raw_message = self._receive_message(self.client_socket)
                if raw_message is None:
                    raise Exception("Соединение разорвано сервером")

                message_obj = json.loads(raw_message)
                self.root.after(0, self.process_server_message, message_obj)

            except json.JSONDecodeError:
                self.root.after(0, self.display_message, self.current_active_chat_area, "[Ошибка] Неверный формат данных от сервера.", 'system')
            except Exception as e:
                self.root.after(0, self.display_message, self.current_active_chat_area, f"[Система] Отключено от сервера: {e}", 'system')
                self.client_socket.close()
                self.root.after(0, self.update_status, "Отключено")
                self.root.after(0, self.show_auth_screen)
                break

    def on_close(self):
        try:
            self.client_socket.close()
        except:
            pass
        self.root.destroy()

if __name__ == "__main__":
    ChatClient()