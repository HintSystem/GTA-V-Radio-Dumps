# GTA V Radio Dumps

This repository contains raw data dumps, scripts and processed JSON files related to GTA V's radio stations.

## 📦 Repository Structure

- `/raw` – Contains XML data parsed from audio metadata *(dat151.rel, dat54.rel)* using [CodeWalker](https://github.com/dexyfex/CodeWalker). Nametables and global text tables are also extracted from the game with CodeWalker, but some missing nametables are sourced from [Monkys-Audio-Research](https://github.com/Monkeypolice188/Monkys-Audio-Research/tree/main/.nametables) *(game.dat151.nametable, sounds.dat54.nametable)*
- `/scripts` – Python scripts used for parsing, reversing hashes, and processing XML data
- `/processed` – Final output in JSON format, ready for use

## 📁 JSON Output Format

Each JSON file in `/processed` follows this general structure:

### Radio Station
- `Flags` – *(unprocessed)*
- `Genre`
- `AmbientRadioVol`
- `RadioName` – Alternative to id
- `TrackLists` – Collection of track lists tied to this station

### TrackList
- `Flags` – *(unprocessed)*
- `Category` – Usage context (e.g., music, id, mono_solo)
- `Tracks` – Array of tracks included

### Track
- `Id` – Internal track identifier
- `Path` – File path reference to the audio asset
- `Duration` – Length of the track (in ms)
- `Markers` - (`Track Markers` and `Beat Markers`)

### Track Marker
- `Offset` – Timestamp of the marker (in ms)
- `Title` – Track title (for talkshows might be `Artist` instead)
- `Artist` – Track artist 

### Beat Marker
- `Offset` – Timestamp of the beat (in ms)
- `Value` – Beat type

## 📜 Scripts

**Requirements:**
* **Python** `>= 3.10`
* **lxml**:\
    Install with pip:
    ```bash
    pip install lxml
    ```


**Usage:**
* `main.py` - The main entry point. This script processes radio data from the `/raw` directory.
\
\
    At the bottom of `main.py`, you'll find this line:
    ```py
    exportStationTrackInfo(all_stations, "")
    ```
    The first argument specifies which stations to look for in the data *(default of all is given)*\
    The second argument specifies the DLC tag to process:

    DLC Tag|Files Processed
    :---|:---
    "" (empty)|`game.dat151.rel.xml`; `sounds.dat54.rel.xml`|
    "dlchei4"|`dlchei4_game.dat151.rel.xml`; `dlchei4_sounds.dat54.rel.xml`
* `xml_utils.py` - Utility functions for parsing XML data.
  * **TypeIndex** - Caches lookups for required types to speed up parsing
  * **to_dict** - Recursively converts an XML element to Python dictionary
  * **markerDict** - converts the XML marker container to a dictionary in a more readable format
* `hash_utils.py` - Utility functions for generating, parsing and resolving hashes.
  * **HashMap** - Loads .nametable and .gxt2 files into a hash lookup table
  * **gxt2_binary** - Parses a .gxt2 binary file (global text table) and turns it into a usable hash map
  * **joaat()** - Hashes strings using the JOAAT algorithm (case-insensitive)
  * **format_hash()** / **parse_hash_string()** - Converts hashes to/from string representations (`1048674328 <=> "hash_3E818018"`)

## 📚 Related Projects
- GTA V Radio implementation repository - [HintSystem/GTA-V-Radio](https://github.com/HintSystem/GTA-V-Radio)
