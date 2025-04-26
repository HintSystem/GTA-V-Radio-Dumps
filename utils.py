import json
from pathlib import Path
from time import perf_counter

script_dir = Path(__file__).resolve().parent
data_dir = script_dir / "raw"
out_dir = script_dir / "processed"

def delta_time_ms(start: float):
    return round((perf_counter() - start)*1000, 3)
    
def save_json(file_path: Path | str, object: object):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(object, f, indent=2, ensure_ascii=False)
    
class ANSI:
    BOLD = "\033[1m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RED = "\033[91m"

    def __init__(self, text: str, *codes: str):
        self.text = text
        self.codes = list(codes)
        
    def __str__(self):
        reset = "\033[0m"
        codes = ''.join(self.codes)
        text = self.text

        index = text.find(reset)
        while index >= 0:
            # Reinsert codes immediately after each reset to allow nesting
            insert_pos = index + len(reset)
            text = text[:insert_pos] + codes + text[insert_pos:]
            index = text.find(reset, insert_pos + len(codes))

        return f"{codes}{text}{reset}"

    
    def bold(self):
        self.codes.append(ANSI.BOLD)
        return self

    def yellow(self):
        self.codes.append(ANSI.YELLOW)
        return self

    def green(self):
        self.codes.append(ANSI.GREEN)
        return self

    def red(self):
        self.codes.append(ANSI.RED)
        return self