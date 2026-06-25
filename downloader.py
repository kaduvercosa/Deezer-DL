import aiohttp
import aiofiles
from tqdm import tqdm
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TDRC, TSRC, APIC, USLT
from mutagen.mp3 import MP3

from api import DeezerAPI
from crypto import DeezerCrypto

async def get_cover(session: aiohttp.ClientSession, alb_picture: str) -> bytes:
    if not alb_picture: return b""
    url = f"https://e-cdns-images.dzcdn.net/images/cover/{alb_picture}/1000x1000-000000-80-0-0.jpg"
    try:
        async with session.get(url) as r:
            if r.status == 200: return await r.read()
    except: pass
    return b""

def extract_all_artists(data: dict) -> str:
    """Extrai todos os artistas (Main, Feat, etc.) em vez de apenas o principal."""
    artists_list = data.get("ARTISTS", [])
    if artists_list:
        return ", ".join([a.get("ART_NAME") for a in artists_list])
    return data.get("ART_NAME", "Unknown Artist")

def tag_file(path: str, data: dict, cover: bytes, lyrics: str):
    title = data.get("SNG_TITLE", "")
    artist = extract_all_artists(data)
    album = data.get("ALB_TITLE", "")
    track_num = str(data.get("TRACK_NUMBER", "1"))
    isrc = data.get("ISRC", "")
    year = data.get("PHYSICAL_RELEASE_DATE", "")[:4]

    if path.endswith(".flac"):
        audio = FLAC(path)
        audio.delete()
        if title: audio["title"] = title
        if artist: audio["artist"] = artist
        if album: audio["album"] = album
        if track_num: audio["tracknumber"] = track_num
        if year: audio["date"] = year
        if isrc: audio["isrc"] = isrc
        
        # Injeção dupla de letras para garantir compatibilidade com qualquer leitor
        if lyrics:
            audio["lyrics"] = lyrics
            audio["unsyncedlyrics"] = lyrics
            
        if cover:
            pic = Picture()
            pic.type, pic.mime, pic.data = 3, "image/jpeg", cover
            audio.add_picture(pic)
        audio.save()
        
    elif path.endswith(".mp3"):
        audio = MP3(path, ID3=ID3)
        if audio.tags is None: audio.add_tags()
        if title: audio.tags.add(TIT2(encoding=3, text=title))
        if artist: audio.tags.add(TPE1(encoding=3, text=artist))
        if album: audio.tags.add(TALB(encoding=3, text=album))
        if track_num: audio.tags.add(TRCK(encoding=3, text=track_num))
        if year: audio.tags.add(TDRC(encoding=3, text=year))
        if isrc: audio.tags.add(TSRC(encoding=3, text=isrc))
        
        # USLT: Unsynchronised lyric/text transcription (Padrão ID3v2)
        if lyrics:
            audio.tags.add(USLT(encoding=3, lang='eng', desc='', text=lyrics))
            
        if cover:
            audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover))
        audio.save()

async def download_track(api: DeezerAPI, track_id: str, base_path: str) -> tuple:
    data = await api.get_track_data(track_id)
    token = data.get("TRACK_TOKEN")
    title = data.get("SNG_TITLE", "Unknown")
    
    if not token:
        print(f"❌ Faixa regionalmente bloqueada: {title}")
        return False, ""

    url, ext, fmt = None, ".flac", "FLAC"
    try:
        url = await api.get_media_url(token, "FLAC")
    except ValueError:
        try:
            url = await api.get_media_url(token, "MP3_320")
            ext, fmt = ".mp3", "MP3_320"
        except ValueError:
            print(f"❌ Formatos de alta qualidade indisponíveis para: {title}")
            return False, ""

    filepath = f"{base_path}{ext}"
    crypto = DeezerCrypto(track_id)
    
    async with api.session.get(url) as r:
        if r.status != 200: return False, ""
        total = int(r.headers.get("content-length", 0))
        
        # Interface de download profissional
        custom_bar = "{desc}: {percentage:3.0f}% |\033[36m{bar:20}\033[0m| {n_fmt}/{total_fmt} [{rate_fmt}]"
        
        async with aiofiles.open(filepath, 'wb') as f:
            with tqdm(total=total, unit="B", unit_scale=True, desc=f"⬇️ {fmt}", leave=False, bar_format=custom_bar, ascii=" ▏▎▍▌▋▊▉█") as bar:
                async for chunk in r.content.iter_chunked(262144):
                    decrypted = crypto.decrypt_chunk(chunk)
                    if decrypted: await f.write(decrypted)
                    bar.update(len(chunk))
                remains = crypto.flush()
                if remains: await f.write(remains)
    
    # Processamento Premium pós-download
    print(f"   ↳ A extrair Letras e Metadados...")
    cover = await get_cover(api.session, data.get("ALB_PICTURE", ""))
    lyrics = await api.get_lyrics(track_id)
    
    tag_file(filepath, data, cover, lyrics)
    return True, filepath