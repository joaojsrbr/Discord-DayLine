"""Converte assets/icon.png em assets/icon.ico para uso no PyInstaller."""
import sys
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).parent
PNG_PATH = BASE_DIR / "assets" / "icon.png"
ICO_PATH = BASE_DIR / "assets" / "icon.ico"

def main():
    if not PNG_PATH.exists():
        print(f"ERRO: {PNG_PATH} nao encontrado. Coloque sua imagem ali antes de buildar.")
        sys.exit(1)

    img = Image.open(PNG_PATH).convert("RGBA")
    # gera varios tamanhos dentro do .ico (padrao Windows)
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ICO_PATH, format="ICO", sizes=sizes)
    print(f"Icone gerado: {ICO_PATH}")

if __name__ == "__main__":
    main()