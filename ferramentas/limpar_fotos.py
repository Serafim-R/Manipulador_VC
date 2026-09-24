from pathlib import Path

PASTA_IMAGENS = Path("capturas")
EXTENSOES = {".jpg", ".jpeg", ".png"}

def limpar_imagens():
    imagens = [
        arquivo
        for arquivo in PASTA_IMAGENS.iterdir()
        if arquivo.is_file() and arquivo.suffix.lower() in EXTENSOES
    ]

    if not imagens:
        print("Nenhuma imagem para excluir.")
        return

    for imagem in imagens:
        imagem.unlink()

    print(f"{len(imagens)} imagem(ns) excluída(s).")
