from pathlib import Path
from time import perf_counter

script_dir = Path(__file__).resolve().parent
data_dir = script_dir / "raw"
out_dir = script_dir / "processed"

def delta_time_ms(start: float):
    return round((perf_counter() - start)*1000, 3)
    
class ANSI:
    BOLD = "\033[1m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RED = "\033[91m"

    def __init__(self, text: str, *codes: str):
        self.text = text
        self.codes = list(codes)
        
    def __str__(self):
        return f"{''.join(self.codes)}{self.text}\033[0m"
    
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