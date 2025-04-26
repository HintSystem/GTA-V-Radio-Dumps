# GTA V Radio Dumps

This repository contains raw data dumps, scripts and processed JSON files related to GTA V's radio stations.

## 📦 Repository Structure

- **Root Directory**: Contains all Python scripts for parsing, hash reversing, and XML processing. `info_merged.json` includes all data from `/processed` merged into a single file.
- `/raw`: Holds raw XML data parsed from audio metadata files *(dat151.rel, dat54.rel, dat4.rel)* and AWC files (in `/raw/tracks`) using [CodeWalker](https://github.com/dexyfex/CodeWalker). Nametables and global text tables are also extracted with CodeWalker, but some missing nametables are sourced from [Monkys-Audio-Research](https://github.com/Monkeypolice188/Monkys-Audio-Research/tree/main/.nametables) *(game.dat151.nametable, sounds.dat54.nametable)*
- `/processed`: Final JSON output for each DLC, ready for use

## 📁 JSON Output Format

Each JSON file in `/processed` follows this structure:

### Radio Station
- `Flags` – *(unprocessed)*
- `Genre`
- `AmbientRadioVol`
- `RadioName` – Alternative to index
- `TrackLists` – Collection of tracklists tied to this station
- `Speech` - *(optional)* Dictionary of DJ `Speech Context`, indexed first by category and then context

### TrackList
- `DlcPath` - *(merged JSON only)* Absolute path to the DLC's audio folder 
- `Flags` – *(unprocessed)*
- `Category` – Usage context (e.g., music, id, mono_solo, ad)
- `Tracks` – Array of tracks included

### Speech Context
- `Variations` - Number of available variations
- `ContainerPath` - Absolute path to the speech container

### Track
- `Id`
- `DlcPath` - *(optional)* Absolute DLC audio path, if the track is from a different folder 
- `TrackList` - *(optional)* Indicates which tracklist this audio is duplicated from 
- `Path` – Path relative to the DLC folder
- `Duration` – Length of the track (in ms)
- `Intro` - *(optional)* Describes exclusive intro speeches
- `Markers` - Dictionary of:
  -  Track Markers
  -  Beat Markers
  -  DJ Markers
  -  Rockout Markers

### Intro
- `Variations` - Number of exclusive intro variations
- `ContainerPath` - Relative path to the intro container within the DLC

### Track Marker
- `Offset` – Timestamp of the marker (in ms)
- `Id` - Internal ID for track title/artist lookup from text table
- `Title` – Track title (for talkshows might be `Artist` instead)
- `Artist` – Track artist 

### Beat Marker
- `Offset` – Timestamp of the beat (in ms)
- `Value` – Beat type

### DJ Marker
- `Offset` - Timestamp of the marker (in ms)
- `Value` - String that describes if an intro or outro is starting or ending (`"{intro/outro}_{start/end}"`)

### Rockout Marker
- `Offset` - Timestamp of the marker (in ms)
- `Value` - String `"start"` or `"end"`

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
    export_dlc_radio_info(all_stations, dlc)
    ```
  - **First argument**: the set of stations to process *(defaults to all)*
  - **Second argument**: the DLC name to process:

  DLC Tag|Files Processed
  :---|:---
  "" (empty)|`game.dat151.rel.xml`; `sounds.dat54.rel.xml`; `speech.dat4.rel.xml`|
  "dlchei4"|`dlchei4_game.dat151.rel.xml`; `dlchei4_sounds.dat54.rel.xml`; `dlchei4_speech.dat4.rel.xml`
* `xml_utils.py` - Utilities for handling XML
  * **TypeIndex** - Caches lookups for XML elements to speed up parsing
  * **to_dict** - Recursively converts an XML element to Python dictionary
  * **marker_dict_awc()** / **marker_dict_xml()** - Converts marker containers into readable dictionaries
* `hash_utils.py` - Utilities for hash operations
  * **HashMap** - Loads `.nametable` and `.gxt2` files into a hash lookup table
  * **gxt2_binary** - Parses `.gxt2` binary files (global text table) and turns them into hash maps
  * **joaat()** - Hashes strings using JOAAT (case-insensitive)
  * **format_hash()** / **parse_hash_string()** - Converts hashes to/from string representations (`1048674328 <=> "hash_3E818018"`)

## 📚 Related Projects
- GTA V Radio implementation repository - [HintSystem/GTA-V-Radio](https://github.com/HintSystem/GTA-V-Radio)
