from time import perf_counter

from pathlib import Path
from lxml import etree
from lxml.etree import _Element
import json

import xml_utils as xml
from hash_utils import joaat, parse_hash_string, format_hash, HashMap
from utils import delta_time_ms, ANSI, script_dir, data_dir, out_dir
        
def GetStreamingSoundInfo(sounds_index: xml.TypeIndex, streamingSoundName: str):
    if sounds_index == None:
        return {}

    streaming_sound: _Element = sounds_index.get("StreamingSound", streamingSoundName, True)
    if streaming_sound == None:
        print(ANSI(f"Missing sound ref: {streamingSoundName}").yellow())
        return {}
    
    duration = None
    path = None
    duration_el = streaming_sound.xpath("./Duration")[0]
    if duration_el != None:
        duration = duration_el.get("value")
    
    child_items: _Element = streaming_sound.xpath("./ChildSounds/Item")
    for item in child_items:
        if not item.text:
            continue

        simple_sound: _Element = sounds_index.get("SimpleSound", item.text)
        container_name = simple_sound.xpath("./ContainerName")[0]
        path = container_name.text
    return {"Path": path, "Duration": int(duration)}

def GetTrackMarkers(type_index: xml.TypeIndex, trackName: str) -> _Element:
    str_is_hash = parse_hash_string(trackName) # check if trackName is a hash string
    if str_is_hash: # that means the rtt and rtb will also be a hash string instead
        rtt_id = format_hash(joaat(f"rtt_{str_is_hash:08x}"))
        rtb_id = format_hash(joaat(f"rtb_{str_is_hash:08x}"))
    else:
        hash_val = joaat(trackName)
        rtt_id = f"rtt_{hash_val:08x}"
        rtb_id = f"rtb_{hash_val:08x}"

    rtt = type_index.get("RadioTrackTextIDs", rtt_id)
    rtb = type_index.get("RadioTrackTextIDs", rtb_id)

    res = {}
    if rtt != None:
        res["Track"] = xml.markerDict(rtt.xpath("./Events")[0], True)
    if rtb != None:
        res["Beat"] = xml.markerDict(rtb.xpath("./Events")[0])

    return res

def filter_dict(dict: dict[str, any], keep_filter: set[str]):
    return {k: v for k, v in dict.items() if k in keep_filter}

def export_dlc_radio_info(station_list: list[str], dlcname: str = "base", data_path: Path = data_dir, out_path: Path = out_dir):
    if dlcname == "base":
        dlcname = ""
    if dlcname:
        dlcname += "_"

    game_path = data_path / (dlcname + "game.dat151.rel.xml")
    if not game_path.is_file():
        print(ANSI(f"Game data file '{game_path.name}' does not exist, export cancelled").yellow())
        return False
    game_root = etree.parse(game_path).getroot().find("Items")
    game_index = xml.TypeIndex(game_root, ["RadioTrackTextIDs", "RadioStationTrackList", "RadioStationSettings"])


    sound_path = data_path / (dlcname + "sounds.dat54.rel.xml")
    if not sound_path.is_file():
        print(ANSI(f"Sound data file '{sound_path.name}' does not exist, sound path and duration will not be loaded").red())
    else:
        sound_root = etree.parse(sound_path).getroot().find("Items")
        sound_index = xml.TypeIndex(sound_root, ["StreamingSound", "SimpleSound"])


    nametables = HashMap()
    nametables.load_nametable(data_path / (dlcname + "game.dat151.nametable"))
    nametables.load_nametable(data_path / (dlcname + "sounds.dat54.nametable"))

    dlcname = dlcname or "base_"

    time_start = perf_counter()
    export_track_info = {"Stations": {}, "TrackLists": {}}
    unique_track_lists = []

    for station_name in station_list:
        station_time_start = perf_counter()

        station_el: _Element = game_index.get("RadioStationSettings", station_name, True)
        if station_el == None:
            continue

        track_list_items = station_el.xpath("./TrackList/Item")
        station_track_lists = []
        for track_list in track_list_items:
            station_track_lists.append(nametables.resolve_string(track_list.text))
            if track_list.text not in unique_track_lists:
                unique_track_lists.append(track_list.text)
        
        station_info = filter_dict(xml.to_dict(station_el, 1), {"Flags", "RadioName", "Genre", "AmbientRadioVol"})
        station_info["TrackLists"] = station_track_lists
        export_track_info["Stations"][station_name] = station_info

        print(f"[{delta_time_ms(station_time_start)}ms] Processed station '{station_name}' with {len(station_track_lists)} track lists")

    print(f"\n[{delta_time_ms(time_start)}ms] Processed all stations for '{dlcname}'")
    time_start = perf_counter()

    if len(export_track_info["Stations"]) == 0:
        print(ANSI(f"No stations exist for '{dlcname}', export cancelled").red())
        return False

    for track_list_id in unique_track_lists:
        track_list_el = game_index.get("RadioStationTrackList", track_list_id)
        if track_list_el == None:
            continue
        track_list = track_list_el.xpath("./Tracks/Item/SoundRef")

        collected_tracks = []
        for track in track_list:
            id_fix = track.text
            prefix = "hei4_radio_kult_" # fix for kult fm caused by unique bank layout
            if id_fix.startswith(prefix):
                id_fix = "dlc_hei4_music_" + id_fix[len(prefix):]

            track_info = {"Id": nametables.resolve_string(track.text)} | GetStreamingSoundInfo(sound_index, track.text)

            markers = GetTrackMarkers(game_index, id_fix)
            if markers:
                track_info["Markers"] = markers

            collected_tracks.append(track_info)

        track_list_info = filter_dict(xml.to_dict(track_list_el, 1), {"Flags", "Category"})
        track_list_info["Tracks"] = collected_tracks
        export_track_info["TrackLists"][nametables.resolve_string(track_list_id)] = track_list_info

    print(f"[{delta_time_ms(time_start)}ms] Processed all track lists for '{dlcname}'")

    with open(out_path / (dlcname + "info.json"), "w", encoding="utf-8") as f:
        json.dump(export_track_info, f, indent=2, ensure_ascii=False)

    return True

def merge_exports(dlc_names: list[str] = None):
    merged_out_path = script_dir / "info_merged.json"
    merged_data = {"Stations": {}, "TrackLists": {}}
    conflicts = []

    dlc_paths = []
    if dlc_names == None:
        dlc_paths = out_dir.rglob("*_info.json")
    else:
        for dlc in dlc_names:
            dlc_path = out_dir / f"{dlc}_info.json"
            if not dlc_path.is_file():
                print(ANSI(f"Could not merge with export '{dlc_path.name}', because it does not exist").red())
                continue
            dlc_paths.append(dlc_path)

    for path in dlc_paths:
        data: dict
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for station_id, station in data.get("Stations", {}).items():
            if station_id not in merged_data["Stations"]:
                merged_data["Stations"][station_id] = station
                continue

            merged_station = merged_data["Stations"][station_id]
            for property, value in station.items():
                if property not in merged_station:
                    merged_station[property] = value
                    continue

                if property == "TrackLists":
                    for track in value:
                        if track not in merged_station[property]:
                            merged_station[property].append(track)
                    continue
                
                if merged_station[property] != value:
                    merged_station[property] = value
                    conflicts.append((["Stations", station_id, property], path.name))


        for track_list_id, track_list in data.get("TrackLists", {}).items():
            if track_list_id not in merged_data["TrackLists"]:
                merged_data["TrackLists"][track_list_id] = track_list
                continue

            conflicts.append((["Stations", track_list_id], path.name))

    with open(merged_out_path, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)

    print(ANSI(f"Merged processed files into '{merged_out_path.name}'").green())
    if conflicts:
        print(ANSI(f"\n{len(conflicts)} conflict(s) detected during merge.").red())
        for section, source in conflicts:
            print(f"- In {ANSI(repr('/'.join(section))).bold()} (from file '{source}')")

    return merged_data, conflicts

# Ordered list of DLCs that contain .dat151 or .dat54 metadata files.
# Each entry is a pair: [DLC folder name, DLC .dat file name]
# The order reflects their chronological release, with '' representing base game content.
all_dlc = [['base', ''], ['dlcbeach', 'mpbeach'], ['dlcvalentines', 'mpvalentines'], ['dlcbusiness', 'mpbusiness'], ['dlcbusi2', 'mpbusiness2'], ['dlcthelab', 'patchday3ng'], ['dlchipster', 'mphipster'], ['dlcindependence', 'mpindependence'], ['dlcpilotschool', 'mppilot'], ['dlcmplts', 'mplts'], ['dlcxmas2', 'mpchristmas2'], ['dlcmpheist', 'mpheist'], ['dlcluxe', 'mpluxe'], ['dlcthelab', 'mpluxe2'], ['dlcsfx1', 'mpreplay'], ['dlclowrider', 'mplowrider'], ['dlchalloween', 'mphalloween'], ['dlcapartment', 'mpapartment'], ['dlcxmas3', 'mpxmas_604490'], ['dlcjanuary2016', 'mpjanuary2016'], ['mpvalentines2', 'mpvalentines2'], ['dlclow2', 'mplowrider2'], ['dlcexec1', 'mpexecutive'], ['dlcstunt', 'mpstunt'], ['dlcbiker', 'mpbiker'], ['dlcimportexport', 'mpimportexport'], ['dlcspecialraces', 'mpspecialraces'], ['dlcgunrunning', 'mpgunrunning'], ['dlcairraces', 'mpairraces'], ['dlcsmuggler', 'mpsmuggler'], ['dlcchristmas2017', 'mpchristmas2017'], ['dlcassault', 'mpassault'], ['dlcbattle', 'mpbattle'], ['dlcawxm2018', 'mpchristmas2018'], ['dlcvinewood', 'mpvinewood'], ['dlcheist3', 'mpheist3'], ['dlcsum20', 'mpsum'], ['dlchei4', 'mpheist4'], ['dlctuner', 'mptuner'], ['dlcsecurity', 'mpsecurity'], ['dlcg9ec', 'mpg9ec'], ['dlcmpsum2', 'mpsum2'], ['dlccm2022', 'mpchristmas3'], ['dlcmp2023_1', 'mp2023_01'], ['dlc23_2', 'mp2023_02'], ['dlc24-1', 'mp2024_01'], ['dlc24-2', 'mp2024_02']]
# Subset of the above DLCs that contain radio station metadata
all_radio_dlc = [['base', ''], ['dlcthelab', 'patchday3ng'], ['dlcchristmas2017', 'mpchristmas2017'], ['dlcheist3', 'mpheist3'], ['dlcsum20', 'mpsum'], ['dlchei4', 'mpheist4'], ['dlctuner', 'mptuner'], ['dlcsecurity', 'mpsecurity'], ['dlcmpsum2', 'mpsum2'], ['dlc23_2', 'mp2023_02'], ['dlc24-1', 'mp2024_01']]
# List of all known radio station identifiers (excluding ones not shown on radio wheel)
all_stations = ["radio_01_class_rock", "radio_02_pop", "radio_03_hiphop_new", "radio_04_punk", "radio_05_talk_01", "radio_06_country", "radio_07_dance_01", "radio_08_mexican", "radio_09_hiphop_old", "radio_11_talk_02", "radio_12_reggae", "radio_13_jazz", "radio_14_dance_02", "radio_15_motown", "radio_16_silverlake", "radio_17_funk", "radio_18_90s_rock", "radio_19_user", "radio_20_thelab", "radio_21_dlc_xm17", "radio_23_dlc_xm19_radio", "radio_27_dlc_prhei4", "radio_34_dlc_hei4_kult", "radio_35_dlc_hei4_mlr", "radio_36_audioplayer", "radio_37_motomami"]

for dlc, dlc_folder in all_radio_dlc:
    print(ANSI(f"\n\nLoading radio dlc: '{dlc or "game"}'").green())
    export_dlc_radio_info(all_stations, dlc)

merge_exports([dlc for dlc, _ in all_radio_dlc])