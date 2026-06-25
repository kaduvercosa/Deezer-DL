import aiohttp

class DeezerAPI:
    def __init__(self, arl: str):
        self.arl = arl.strip()
        self.api_token = "null"
        self.license_token = ""
        self.session = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": f"arl={self.arl}"
        }

    async def start(self) -> None:
        self.session = aiohttp.ClientSession(headers=self.headers)
        url = f"https://www.deezer.com/ajax/gw-light.php?method=deezer.getUserData&api_version=1.0&api_token={self.api_token}"
        
        async with self.session.post(url, json={}) as resp:
            data = await resp.json()
            results = data.get("results", {})
            self.api_token = results.get("checkForm")
            
            user_data = results.get("USER", {})
            if user_data.get("USER_ID", 0) == 0:
                raise PermissionError("ARL inválido, expirado ou sessão terminada no navegador.")
            
            self.license_token = user_data.get("OPTIONS", {}).get("license_token", "")

    async def get_track_data(self, track_id: str) -> dict:
        url = "https://www.deezer.com/ajax/gw-light.php"
        params = {"method": "song.getData", "api_version": "1.0", "api_token": self.api_token}
        async with self.session.post(url, params=params, json={"SNG_ID": track_id}) as resp:
            data = await resp.json()
            return data.get("results", {})

    async def get_lyrics(self, track_id: str) -> str:
        """Busca as letras oficiais da música na API do Deezer."""
        url = "https://www.deezer.com/ajax/gw-light.php"
        params = {"method": "song.getLyrics", "api_version": "1.0", "api_token": self.api_token}
        async with self.session.post(url, params=params, json={"SNG_ID": track_id}) as resp:
            data = await resp.json()
            results = data.get("results", {})
            return results.get("LYRICS_TEXT", "")

    async def get_media_url(self, track_token: str, format_name: str = "FLAC") -> str:
        payload = {
            "license_token": self.license_token,
            "media": [{
                "type": "FULL",
                "formats": [{"cipher": "BF_CBC_STRIPE", "format": format_name}]
            }],
            "track_tokens": [track_token]
        }
        async with self.session.post("https://media.deezer.com/v1/get_url", json=payload) as resp:
            data = await resp.json()
            try:
                return data["data"][0]["media"][0]["sources"][0]["url"]
            except (KeyError, IndexError):
                raise ValueError(f"Formato {format_name} bloqueado pela editora nesta faixa.")

    async def close(self) -> None:
        if self.session:
            await self.session.close()