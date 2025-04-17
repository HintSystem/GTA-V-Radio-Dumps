from pathlib import Path
from time import perf_counter

script_dir = Path(__file__).resolve().parent
data_dir = script_dir / "raw"

def delta_time_ms(start: float):
    return round((perf_counter() - start)*1000, 3)