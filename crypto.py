import hashlib
from Crypto.Cipher import Blowfish

class DeezerCrypto:
    SECRET = b'g4el58wc0zvf9na1'

    def __init__(self, track_id: str):
        self.track_id = str(track_id)
        self.bf_key = self._generate_key()
        self.iv = bytes([0, 1, 2, 3, 4, 5, 6, 7])
        self.chunk_size = 2048
        self.buffer = bytearray()
        self.chunk_index = 0

    def _generate_key(self) -> bytes:
        m = hashlib.md5(self.track_id.encode('ascii')).hexdigest()
        key = bytearray(16)
        for i in range(16):
            key[i] = ord(m[i]) ^ self.SECRET[i] ^ ord(m[i + 16])
        return bytes(key)

    def decrypt_chunk(self, data: bytes) -> bytes:
        self.buffer.extend(data)
        out = bytearray()
        
        while len(self.buffer) >= self.chunk_size:
            chunk = bytes(self.buffer[:self.chunk_size])
            del self.buffer[:self.chunk_size]
            
            if self.chunk_index % 3 == 0:
                cipher = Blowfish.new(self.bf_key, Blowfish.MODE_CBC, self.iv)
                out.extend(cipher.decrypt(chunk))
            else:
                out.extend(chunk)
            self.chunk_index += 1
            
        return bytes(out)

    def flush(self) -> bytes:
        remains = bytes(self.buffer)
        self.buffer.clear()
        return remains
