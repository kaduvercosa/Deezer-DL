import asyncio
import aiohttp
import urllib.parse
from pick import pick
from pathlib import Path

from api import DeezerAPI
from downloader import download_track, extract_all_artists

# ==================================
# CONFIGURAÇÕES BASE
# ==================================
ARL = "689ba2ca30e2687dea0bbce98d4b2e786aec59f8a14be9058ae84cb37835cd60219f4d306344a26a2e9db119b012ba7c404542fa475f13f8a8089a90cd5e53b9a83612025033723ec04636361be1aea8cb55414135538d772141f1a0a71b2141"

# Pode colocar o nome de uma pasta que o script cria para si, ou um caminho absoluto do iSH (ex: "/root/deezer-teste/Downloads")
PASTA_DESTINO = "/root/icloud/Deezer" 

# Cores ANSI clássicas para o terminal
class Tema:
    CYAN = '\033[36m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    OFF = '\033[0m'
    BOLD = '\033[1m'

async def search(query: str, search_type: str) -> list:
    q = urllib.parse.quote(query)
    url = f"https://api.deezer.com/search/{search_type}?q={q}&limit=20"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            return (await r.json()).get("data", [])

async def get_album_tracks(album_id: str) -> list:
    url = f"https://api.deezer.com/album/{album_id}/tracks"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            return (await r.json()).get("data", [])

def clean_name(name: str) -> str:
    """Remove caracteres inválidos para a criação de pastas."""
    return "".join(c for c in name if c not in r'<>:"/\|?*')

async def main():
    print(f"\n{Tema.CYAN}{Tema.BOLD}🎵 =================================== 🎵{Tema.OFF}")
    print(f"{Tema.CYAN}{Tema.BOLD}        DEEZER-DL CLI MASTER{Tema.OFF}")
    print(f"{Tema.CYAN}{Tema.BOLD}🎵 =================================== 🎵{Tema.OFF}\n")
    
    # 1. Seleção do Modo
    opcoes_modo = ["🎵 Faixa Única", "💿 Álbum Completo"]
    _, t_idx = pick(opcoes_modo, "Selecione o modo de descarga:", indicator="=>")
    stype = "track" if t_idx == 0 else "album"
    
    # 2. Pesquisa
    query = input(f"🔍 Digite a pesquisa: ")
    print(f"\n{Tema.YELLOW}A pesquisar na base de dados...{Tema.OFF}")
    
    results = await search(query, stype)
    
    if not results:
        print(f"{Tema.RED}❌ Nenhum resultado encontrado.{Tema.OFF}")
        return
        
    # 3. Menu de Resultados
    options = []
    for i in results:
        if t_idx == 0:
            options.append(f"{i['title']} - {i['artist']['name']} ({i['album']['title']})")
        else:
            options.append(f"Álbum: {i['title']} - {i['artist']['name']}")
            
    _, r_idx = pick(options, "Resultados encontrados (Use as setas):", indicator="=>")
    choice = results[r_idx]
    
    # 4. Compilação da Fila
    if t_idx == 0:
        tracks = [str(choice["id"])]
        print(f"\n{Tema.GREEN}▶ Alvo selecionado:{Tema.OFF} {choice['title']}")
    else:
        print(f"\n{Tema.YELLOW}📂 A extrair tracklist do álbum...{Tema.OFF}")
        album_tracks = await get_album_tracks(choice["id"])
        tracks = [str(t["id"]) for t in album_tracks]
        print(f"{Tema.GREEN}▶ Álbum selecionado:{Tema.OFF} {choice['title']} ({len(tracks)} faixas)")
    
    # 5. Arranque do Motor
    api = DeezerAPI(ARL)
    try:
        await api.start()
        print(f"{Tema.CYAN}📡 Sessão autenticada. A iniciar descargas...{Tema.OFF}\n")
        
        for idx, tid in enumerate(tracks, 1):
            data = await api.get_track_data(tid)
            if not data: continue
            
            art = clean_name(extract_all_artists(data))
            alb = clean_name(data.get("ALB_TITLE", "Unknown Album"))
            tit = clean_name(data.get("SNG_TITLE", "Unknown Track"))
            num = str(data.get("TRACK_NUMBER", "1")).zfill(2)
            
            # Organização padrão Qobuz-DL: Destino / Artista / Álbum / Ficheiro
            dir_path = Path(PASTA_DESTINO) / art / alb
            dir_path.mkdir(parents=True, exist_ok=True)
            
            base_file = str(dir_path / f"{num} - {art} - {tit}")
            
            print(f"{Tema.BOLD}Faixa {idx}/{len(tracks)}:{Tema.OFF} {tit}")
            
            sucesso, final_path = await download_track(api, tid, base_file)
            
            if sucesso:
                print(f"{Tema.GREEN}✅ Concluído.{Tema.OFF}\n")
            else:
                print(f"{Tema.RED}❌ Falha na extração.{Tema.OFF}\n")
                
    except Exception as e:
        print(f"\n{Tema.RED}⚠️ Erro de execução: {e}{Tema.OFF}")
    finally:
        await api.close()
        print(f"{Tema.CYAN}{Tema.BOLD}Operação Finalizada.{Tema.OFF}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{Tema.YELLOW}⚠️ Cancelado pelo utilizador.{Tema.OFF}")