import threading
import time
import datetime
import sys
import os
import winreg
import requests
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageDraw
import pystray

# ===== CONFIG (via .env) =====
# Garante que o .env é lido tanto rodando como .py quanto como .exe compilado
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent          # onde fica o .env
    ASSETS_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR)) / "assets"  # onde o PyInstaller extrai os dados embutidos
else:
    BASE_DIR = Path(__file__).parent
    ASSETS_DIR = BASE_DIR / "assets"

load_dotenv(BASE_DIR / ".env")

APP_ID = os.getenv("DISCORD_APP_ID")
USER_ID = os.getenv("DISCORD_USER_ID")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
INTERVAL_MINUTES = int(os.getenv("UPDATE_INTERVAL_MINUTES", "10"))

if not all([APP_ID, USER_ID, BOT_TOKEN]):
    print("ERRO: variáveis de ambiente faltando. Confira o arquivo .env")
    sys.exit(1)

URL = f"https://discord.com/api/v9/applications/{APP_ID}/users/{USER_ID}/identities/0/profile"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bot {BOT_TOKEN}",
    "User-Agent": "DiscordBot (https://github.com/discord/discord-api-docs, 1.0.0)",
}

running = True
last_progress = 0.0


def get_day_progress() -> float:
    now = datetime.datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds = (now - midnight).total_seconds()
    return round(seconds / 86400, 4)


def update_progress():
    global last_progress
    progress = get_day_progress()
    body = {"data": {"dynamic": [{"type": 2, "name": "progress", "value": progress}]}}

    try:
        resp = requests.patch(URL, headers=HEADERS, json=body, timeout=10)
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 5)
            print(f"[{datetime.datetime.now()}] Rate limited, aguardando {retry_after}s")
            time.sleep(float(retry_after) + 1)
            return update_progress()
        resp.raise_for_status()
        last_progress = progress
        print(f"[{datetime.datetime.now()}] progress = {progress}")
    except requests.RequestException as e:
        print(f"[{datetime.datetime.now()}] Erro: {e}")


def worker_loop():
    while running:
        update_progress()
        for _ in range(INTERVAL_MINUTES * 60):
            if not running:
                break
            time.sleep(1)


# ===== ÍCONE DA BANDEJA =====
def load_icon_image():
    icon_path = ASSETS_DIR / "icon.png"
    if icon_path.exists():
        try:
            return Image.open(icon_path).convert("RGBA")
        except Exception as e:
            print(f"Erro ao carregar icone customizado: {e}. Usando icone padrao.")
    return make_fallback_icon()


def make_fallback_icon():
    img = Image.new("RGB", (64, 64), "black")
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), fill=(88, 101, 242))
    d.text((20, 24), "D", fill="white")
    return img


def on_quit(icon, item):
    global running
    running = False
    icon.stop()


def on_update_now(icon, item):
    threading.Thread(target=update_progress, daemon=True).start()


# ===== AUTO START NO WINDOWS =====
STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "DiscordDayProgress"


def is_autostart_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False


def enable_autostart():
    exe_path = get_exe_path()
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
    winreg.CloseKey(key)


def disable_autostart():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass


def get_exe_path() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    script = os.path.abspath(__file__)
    return f'"{pythonw}" "{script}"'


def on_toggle_autostart(icon, item):
    if is_autostart_enabled():
        disable_autostart()
    else:
        enable_autostart()


def autostart_checked(item):
    return is_autostart_enabled()


# ===== MENU =====
def build_menu():
    return pystray.Menu(
        pystray.MenuItem("Atualizar agora", on_update_now),
        pystray.MenuItem("Abrir com o Windows", on_toggle_autostart, checked=autostart_checked),
        pystray.MenuItem("Sair", on_quit),
    )


def main():
    threading.Thread(target=worker_loop, daemon=True).start()
    icon = pystray.Icon("discord_progress", load_icon_image(), "Discord Day Progress", build_menu())
    icon.run()


if __name__ == "__main__":
    main()