from flask import Flask, request, send_from_directory, render_template
from flask_cors import CORS
from pynput.mouse import Controller as MouseController, Button
from evdev import UInput, ecodes as e
import uinput
import queue
import time
import subprocess
import os
import getpass
import threading
import socket
import qrcode
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox
import io
from tkinter import PhotoImage
from tkinter import font

# =========================================================
# UINPUT - DISPOSITIVO DE TECLADO REAL
# =========================================================

# Nota: intento crear el device con las teclas que usas.
device = uinput.Device([
    uinput.KEY_A, uinput.KEY_B, uinput.KEY_C, uinput.KEY_D,
    uinput.KEY_E, uinput.KEY_F, uinput.KEY_G, uinput.KEY_H,
    uinput.KEY_I, uinput.KEY_J, uinput.KEY_K, uinput.KEY_L,
    uinput.KEY_M, uinput.KEY_N, uinput.KEY_O, uinput.KEY_P,
    uinput.KEY_Q, uinput.KEY_R, uinput.KEY_S, uinput.KEY_T,
    uinput.KEY_U, uinput.KEY_V, uinput.KEY_W, uinput.KEY_X,
    uinput.KEY_Y, uinput.KEY_Z,

    uinput.KEY_1, uinput.KEY_2, uinput.KEY_3, uinput.KEY_4, uinput.KEY_5,
    uinput.KEY_6, uinput.KEY_7, uinput.KEY_8, uinput.KEY_9, uinput.KEY_0,

    uinput.KEY_ENTER,
    uinput.KEY_LEFTSHIFT,
    uinput.KEY_SPACE,
    uinput.KEY_BACKSPACE,
    uinput.KEY_ESC, 

    uinput.KEY_UP,
    uinput.KEY_DOWN,
    uinput.KEY_LEFT,
    uinput.KEY_RIGHT,

    # TECLAS MULTIMEDIA REALES
    uinput.KEY_PLAYPAUSE,
    uinput.KEY_NEXTSONG,
    uinput.KEY_PREVIOUSSONG,
    uinput.KEY_VOLUMEUP,
    uinput.KEY_VOLUMEDOWN,
    uinput.KEY_MUTE,
])

# mouse_device usando evdev.UInput (está bien mezclar si lo necesitas)
mouse_device = UInput({
    e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT],
    e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL]
}, name="jinkani-mouse")


def send_real_key(key):
    """Enviar tecla real PRESIONAR + SOLTAR (teclado físico)."""
    try:
        device.emit(key, 1)   # PRESIONAR
        time.sleep(0.005)
        device.emit(key, 0)   # SOLTAR
        time.sleep(0.005)
    except Exception as exc:
        print("Error al enviar tecla (send_real_key):", exc)


def press_key(key):
    """Pulsación corta (wrapper). Usar para multimedia y pulsaciones que no se mantienen."""
    # simple wrapper por compatibilidad
    send_real_key(key)


def send_real_key(key):
    """Enviar tecla real PRESIONAR + SOLTAR (teclado físico)."""
    try:
        print(f"send_real_key: {key}")
        device.emit(key, 1)   # PRESIONAR
        time.sleep(0.02)     # un poco más para ser visible
        device.emit(key, 0)   # SOLTAR
        time.sleep(0.01)
    except Exception as exc:
        print("Error al enviar tecla (send_real_key):", exc)


# Estado y lock
teclas_presionadas = {}
teclas_lock = threading.Lock()


# --------------------------
# HOLD KEY + REPETIDOR REAL
# --------------------------

teclas_presionadas = {}
teclas_lock = threading.Lock()

def hold_key(key, estado):
    """Presionar o soltar tecla correctamente con UINPUT."""
    try:
        with teclas_lock:
            prev = teclas_presionadas.get(key, False)

            if estado == "down":
                teclas_presionadas[key] = True
                print(f"hold_key DOWN -> {key} (prev {prev})")

                # 🔥 IMPORTANTE: enviar PRESIONAR
                try:
                    device.emit(key, 1)
                except:
                    pass

            else:
                teclas_presionadas[key] = False
                print(f"hold_key UP -> {key} (prev {prev})")

                # 🔥 IMPORTANTE: enviar SOLTAR solo si estaba presionada
                if prev:
                    try:
                        device.emit(key, 0)
                    except:
                        pass

    except Exception as exc:
        print("Error en hold_key:", exc)


def repetir_teclas():
    """Envia EV_REPEAT mientras una tecla esté presionada."""
    while True:
        with teclas_lock:
            activas = [k for k, v in teclas_presionadas.items() if v]

        for key in activas:
            try:
                # 🔥 Emitir repetición (EV_REPEAT)
                device.emit(key, 2)
            except:
                pass

        time.sleep(0.05)


# Lanzar repetidor
threading.Thread(target=repetir_teclas, daemon=True).start()


# =========================================================
# SERVIDOR FLASK - JINKANI
# =========================================================

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

mouse = MouseController()


@app.route('/')
def home():
    return render_template('index.html')


# --------------------------
# TECLAS ESPECIALES (UINPUT)
# --------------------------
@app.route('/special', methods=['POST'])
def special():
    data = request.json or {}
    action = data.get('action')
    estado = data.get('state', None)  # "down", "up" o None

    special_map = {
        'enter': uinput.KEY_ENTER,
        'shift': uinput.KEY_LEFTSHIFT,
        'space': uinput.KEY_SPACE,
        'backspace': uinput.KEY_BACKSPACE,
        'up': uinput.KEY_UP,
        'down': uinput.KEY_DOWN,
        'left': uinput.KEY_LEFT,
        'right': uinput.KEY_RIGHT,
        'esc': uinput.KEY_ESC 
    }

    if action in special_map:
        keycode = special_map[action]

        # Caso nuevo: controles con hold
        if estado in ('down', 'up'):
            hold_key(keycode, estado)

        # Caso viejo: cliente sin "state"
        else:
            send_real_key(keycode)

    return 'ok'
# --------------------------
# TECLAS NORMALES (UINPUT)
# --------------------------
@app.route('/key', methods=['POST'])
def key():
    data = request.json or {}
    k = data.get('key')
    estado = data.get('state', None)  # "down", "up" o None

    if not k:
        return 'missing key', 400

    letter_map = {
        'a': uinput.KEY_A, 'b': uinput.KEY_B, 'c': uinput.KEY_C,
        'd': uinput.KEY_D, 'e': uinput.KEY_E, 'f': uinput.KEY_F,
        'g': uinput.KEY_G, 'h': uinput.KEY_H, 'i': uinput.KEY_I,
        'j': uinput.KEY_J, 'k': uinput.KEY_K, 'l': uinput.KEY_L,
        'm': uinput.KEY_M, 'n': uinput.KEY_N, 'o': uinput.KEY_O,
        'p': uinput.KEY_P, 'q': uinput.KEY_Q, 'r': uinput.KEY_R,
        's': uinput.KEY_S, 't': uinput.KEY_T, 'u': uinput.KEY_U,
        'v': uinput.KEY_V, 'w': uinput.KEY_W, 'x': uinput.KEY_X,
        'y': uinput.KEY_Y, 'z': uinput.KEY_Z,
        '0': uinput.KEY_0, '1': uinput.KEY_1, '2': uinput.KEY_2,
        '3': uinput.KEY_3, '4': uinput.KEY_4, '5': uinput.KEY_5,
        '6': uinput.KEY_6, '7': uinput.KEY_7, '8': uinput.KEY_8,
        '9': uinput.KEY_9,
    }

    if k.lower() in letter_map:
        keycode = letter_map[k.lower()]
        if estado in ("down", "up"):
            hold_key(keycode, estado)
        else:
            send_real_key(keycode)

    return 'ok'

# --------------------------
# MOUSE
# --------------------------
def move_mouse_rel(dx, dy):
    mouse_device.write(e.EV_REL, e.REL_X, dx)
    mouse_device.write(e.EV_REL, e.REL_Y, dy)
    mouse_device.syn()


mouse_queue = queue.Queue()


def mouse_worker():
    while True:
        btn = mouse_queue.get()
        if btn is None:
            break

        mouse_device.write(e.EV_KEY, btn, 1)
        mouse_device.syn()

        time.sleep(0.02)

        mouse_device.write(e.EV_KEY, btn, 0)
        mouse_device.syn()


threading.Thread(target=mouse_worker, daemon=True).start()


@app.route('/moveMouse', methods=['POST'])
def move_mouse():
    data = request.json or {}
    dx = int(data.get('dx', 0))
    dy = int(data.get('dy', 0))

    move_mouse_rel(dx, dy)

    return 'ok'


@app.route('/click', methods=['POST'])
def click():
    data = request.json or {}
    button = data.get('button')

    if button == 'left':
        mouse_queue.put(e.BTN_LEFT)
    elif button == 'right':
        mouse_queue.put(e.BTN_RIGHT)

    return 'ok'


# --------------------------
# ACCIONES DEL SISTEMA
# --------------------------
@app.route('/action', methods=['POST'])
def action():
    data = request.json or {}
    act = data.get('action')
    user = getpass.getuser()

    if act == 'brave':
        args = ['/usr/bin/brave-browser']
        if user == 'root':
            args.append('--no-sandbox')
        subprocess.Popen(args)
    elif act == 'vlc':
        if user == 'root':
            return 'Cannot run VLC as root', 403
        subprocess.Popen(['/usr/bin/vlc'])
    elif act == 'shutdown':
        os.system("sudo poweroff")
    return 'ok'


# --------------------------
# MEDIOS (NO CAMBIA)
# --------------------------
@app.route('/media', methods=['POST'])
def media():
    data = request.json or {}
    act = data.get('action')

    media_map = {
        'playpause': uinput.KEY_PLAYPAUSE,
        'next': uinput.KEY_NEXTSONG,
        'prev': uinput.KEY_PREVIOUSSONG,
        'volup': uinput.KEY_VOLUMEUP,
        'voldown': uinput.KEY_VOLUMEDOWN,
        'mute': uinput.KEY_MUTE,
    }

    if act in media_map:
        press_key(media_map[act])
    return 'ok'
# =========================================================
# AUXILIARES
# =========================================================
def obtener_ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# =========================================================
# INTERFAZ TKINTER (NO TOCADA)
# =========================================================
def lanzar_gui():
    root = tk.Tk()
    root.title("Jinkani 0.1")
    root.geometry("260x350")
    root.configure(bg="#ffffff")
    root.resizable(False, False)
    root.attributes('-alpha', 0.0)
    icono = PhotoImage(file="static/images/logo.png")
    root.iconphoto(True, icono)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TLabel", background="#ffffff", foreground="#222", font=("Segoe UI", 10))
    style.configure("Title.TLabel", background="#ffffff", foreground="#0d6efd", font=("Segoe UI Semibold", 9))
    style.configure("Sub.TLabel", background="#ffffff", foreground="#6c757d", font=("Segoe UI", 9))
    style.configure("TButton", font=("Segoe UI", 10), padding=8, relief="flat",
                    background="#0d6efd", foreground="#ffffff")
    style.map("TButton",
              background=[("active", "#0b5ed7")],
              relief=[("pressed", "sunken")])

    bold_font = font.Font(family="Helvetica", size=11, weight="bold")
    style.configure("Bold.TLabel", font=bold_font)

    bold_font1 = font.Font(family="Helvetica", size=8, weight="bold")
    style.configure("BoldSmall.TLabel", font=bold_font1)

    img = Image.open("static/images/cubito1.png")
    img = img.resize((23, 23))
    logo = ImageTk.PhotoImage(img)

    ip = obtener_ip_local()
    server_id = "JINKANI-FREE-LNX-001"
    data_qr = f"http://{ip}:5000"

    qr = qrcode.make(data_qr)
    bio = io.BytesIO()
    qr.save(bio, format="PNG")
    bio.seek(0)
    img = Image.open(bio).resize((200, 200))
    qr_img = ImageTk.PhotoImage(img)

    ttk.Label(root, text="Jinkani", style="Title.TLabel").pack(pady=(1, 1))
    ttk.Label(root, text=f"Ingresa en tu navegador:", style="Sub.TLabel").pack(pady=(1, 1))
    ttk.Label(root, text=f"{ip}:5000", justify="center", style="Bold.TLabel").pack(pady=(0,0))

    lbl_img = ttk.Label(root, image=qr_img, background="#ffffff")
    lbl_img.image = qr_img
    lbl_img.pack(pady=(0, 0))

    ttk.Label(
        root,
        text="Ó escanea el código QR desde tu móvil\npara usarlo como control remoto.",
        style="Sub.TLabel",
        justify="center",
        wraplength=400
    ).pack(pady=(1, 1))

    ttk.Label(
        root,
        text="Ideas en cubitos ©",
        image=logo,
        compound="left",
        style="BoldSmall.TLabel",
        justify="center"
    ).pack(side="bottom", pady=(1, 1))

    root.mainloop()


# =========================================================
# LANZAMIENTO
# =========================================================
if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000), daemon=True).start()

    lanzar_gui()
