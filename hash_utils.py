from io import BufferedReader
from pathlib import Path
from time import perf_counter
import struct

from utils import delta_time_ms, ANSI, data_dir

def joaat(s: str) -> int:
    k = s.lower()
    h = 0

    for char in k:
        h += ord(char)
        h &= 0xFFFFFFFF  # Ensure 32-bit
        h += (h << 10)
        h &= 0xFFFFFFFF
        h ^= (h >> 6)

    h += (h << 3)
    h &= 0xFFFFFFFF
    h ^= (h >> 11)
    h += (h << 15)
    h &= 0xFFFFFFFF

    return h

hash_string_prefix = "hash_"
def parse_hash_string(string: str) -> int | None:
    """Given `"hash_FFFFFFFF"` returns `FFFFFFFF` as an integer. Returns None if string is not a hash string"""
    if string.startswith(hash_string_prefix):
        return int(string[len(hash_string_prefix):], 16)
    return None

def format_hash(hash_val: int) -> str:
    """Format a hash as `"hash_FFFFFFFF"`"""
    return f"hash_{hash_val:08X}"

class gxt2_binary:
    def swap_endian(self, i: bytes):
        if self.isBigEndian:
            return struct.unpack("<L", i)[0]
        return struct.unpack(">L", i)[0]
    
    def read_uint4(self):
        return self.swap_endian(self.data.read(4))
    
    def set_endian(self, header: bytes, error: str):
        if header == b"2TXG":
            self.isBigEndian = True
        elif header == b"GXT2":
            self.isBigEndian = False
        else:
            raise ValueError(error)

    def __init__(self, data: BufferedReader):
        self.data = data
        self.hash_map = {}

        self.set_endian(data.read(4), "GXT2 file format is invalid")
        
        entry_count = self.read_uint4()
        entries = []
        for _ in range(entry_count):
            hash = self.read_uint4()
            offset = self.read_uint4()
            entries.append((hash, offset))

        self.set_endian(data.read(4), "Incorrect GXT2 header after entries, file may be corrupted")

        data_length = self.read_uint4()
        for x in range(entry_count):
            entry = entries[x]
            offset = entry[1]
            hash = entry[0]

            next_offset = data_length
            if len(entries) > x+1:
                next_offset = entries[x+1][1]
            
            self.hash_map[hash] = data.read(next_offset - offset).rstrip(b"\x00").decode(encoding="utf-8")
    
class HashMap:
    def __init__(self):
        self.map: dict[int, str] = {}

    def load_hashmap(self, hash_map: dict[int, str]):
        for k, v in hash_map.items():
            if k in self.map and self.map[k] != v:
                print(ANSI(f"⚠️ Hashmap conflict '{k}': '{self.map[k]}' != '{v}'").yellow())
            self.map[k] = v
        return self

    def load_nametable(self, file_path: Path | str):
        time_start = perf_counter()
        file_path = Path(file_path)
        if not file_path.exists():
            print(ANSI(f"Nametable '{ANSI(file_path.name).bold()}' does not exist").yellow())
            return

        if file_path.suffix == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                hash_map = {}
                for line in f:
                    line = line.strip()
                    hash_map[joaat(line)] = line
                
                self.load_hashmap(hash_map)
        elif file_path.suffix == ".nametable":
            with open(file_path, "rb") as f:
                lines = [s.decode("utf-8") for s in f.read().split(b"\x00") if s] 

            self.load_hashmap({joaat(s): s for s in lines})
        else:
            raise ValueError(f"Nametable only supports file types of .nametable or .txt ({file_path})")

        print(f"[{delta_time_ms(time_start)}ms] Loaded nametable '{file_path.name}'")
        return self

    def load_gxt2(self, file_path: Path | str):
        time_start = perf_counter()
        file_path = Path(file_path)
        if not file_path.exists():
            print(ANSI(f"Global text table '{ANSI(file_path.name).bold()}' does not exist").yellow())
            return
        
        if file_path.suffix == ".txt":
            with open(file_path, 'r', encoding='utf-8') as f:
                hash_map = {}
                for line in f:
                    line = line.strip()
                    if not line or '=' not in line:
                        continue
                    hex_code, value = map(str.strip, line.split('=', 1))
                    hash_map[int(hex_code, 16)] = value

                self.load_hashmap(hash_map)
        elif file_path.suffix == ".gxt2":
            with open(file_path, 'rb') as f:
                self.load_hashmap(gxt2_binary(f).hash_map)
        else:
            raise ValueError(f"Global text table only supports file types of .gxt2 or .txt ({file_path})")

        print(f"[{delta_time_ms(time_start)}ms] Loaded global text table '{ANSI(file_path.name).bold()}'") 
        return self 

    def resolve(self, hash: int):
        """Attempts to resolve a hash to a known name using the hash map."""
        if hash in self.map:
            return self.map[hash]
        return None

    def resolve_string(self, hash_str: str):
        """Attempts to resolve a `"hash_FFFFFFFF"` to a known name using the hash map. Returns the same string otherwise"""
        hash = parse_hash_string(hash_str)
        if not hash:
            return hash_str

        return self.resolve(hash) or hash_str
    

trackid_table = None
def get_trackid_table() -> HashMap:
    global trackid_table
    if trackid_table == None:
        trackid_table = HashMap().load_gxt2(data_dir / "trackid.gxt2")
    return trackid_table