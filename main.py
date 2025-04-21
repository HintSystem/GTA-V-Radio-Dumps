from time import perf_counter

from pathlib import Path
from lxml import etree
from lxml.etree import _Element
import json

import xml_utils as xml
from hash_utils import joaat, parse_hash_string, format_hash, HashMap
from utils import delta_time_ms, ANSI, script_dir, data_dir, out_dir

dlcname_paths = {'base': ['audio/sfx'], 'dlcbeach': ['dlcpacks/mpbeach'], 'dlcvalentines': ['dlcpacks/mpvalentines'], 'dlcupdate': ['dlcpacks/patchday2bng'], 'dlcbusiness': ['dlcpacks/mpbusiness'], 'dlcbusi2': ['dlcpacks/mpbusiness2'], 'dlcthelab': ['dlcpacks/patchday3ng', 'dlcpacks/mpluxe2'], 'dlchipster': ['dlcpacks/mphipster'], 'dlcindependence': ['dlcpacks/mpindependence'], 'dlcpilotschool': ['dlcpacks/mppilot'], 'dlcmplts': ['dlcpacks/mplts'], 'dlcxmas2': ['dlcpacks/mpchristmas2'], 'dlcmpheist': ['dlcpacks/mpheist'], 'dlcluxe': ['dlcpacks/mpluxe'], 'dlcsfx1': ['dlcpacks/mpreplay'], 'dlclowrider': ['dlcpacks/mplowrider'], 'dlchalloween': ['dlcpacks/mphalloween'], 'dlcapartment': ['dlcpacks/mpapartment'], 'dlcxmas3': ['dlcpacks/mpxmas_604490'], 'dlcjanuary2016': ['dlcpacks/mpjanuary2016'], 'mpvalentines2': ['dlcpacks/mpvalentines2'], 'dlclow2': ['dlcpacks/mplowrider2'], 'dlcexec1': ['dlcpacks/mpexecutive'], 'dlcstunt': ['dlcpacks/mpstunt'], 'dlcbiker': ['dlcpacks/mpbiker'], 'dlcimportexport': ['dlcpacks/mpimportexport'], 'dlcspecialraces': ['dlcpacks/mpspecialraces'], 'dlcgunrunning': ['dlcpacks/mpgunrunning'], 'dlcairraces': ['dlcpacks/mpairraces'], 'dlcsmuggler': ['dlcpacks/mpsmuggler'], 'dlcchristmas2017': ['dlcpacks/mpchristmas2017'], 'dlcassault': ['dlcpacks/mpassault'], 'dlcbattle': ['dlcpacks/mpbattle'], 'dlcawxm2018': ['dlcpacks/mpchristmas2018'], 'dlcvinewood': ['dlcpacks/mpvinewood'], 'dlcheist3': ['dlcpacks/mpheist3'], 'dlcsum20': ['dlcpacks/mpsum'], 'dlchei4': ['dlcpacks/mpheist4'], 'dlctuner': ['dlcpacks/mptuner'], 'dlcsecurity': ['dlcpacks/mpsecurity'], 'dlcg9ec': ['dlcpacks/mpg9ec'], 'dlcmpsum2': ['dlcpacks/mpsum2'], 'dlccm2022': ['dlcpacks/mpchristmas3'], 'dlcmp2023_1': ['dlcpacks/mp2023_01'], 'dlc23_2': ['dlcpacks/mp2023_02'], 'dlc24-1': ['dlcpacks/mp2024_01'], 'dlc24-2': ['dlcpacks/mp2024_02']}
def full_dlc_path(dlcpath: str):
    dlcpath: Path = Path(dlcpath)
    if dlcpath.parent.name == "dlcpacks":
        return f"update/%PLATFORM%/{dlcpath.as_posix()}"
    return f"%PLATFORM%/{dlcpath.as_posix()}"

def GetStreamingSoundInfo(sounds_index: xml.TypeIndex, streamingSoundName: str, dlcname: str):
    if sounds_index == None:
        return {}

    streaming_sound: _Element = sounds_index.get("StreamingSound", streamingSoundName, True)
    if streaming_sound == None:
        print(ANSI(f"Missing sound ref: '{ANSI(streamingSoundName).bold()}'").yellow())
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

        special_path = Path(path).parent.name.replace("_", "")
        if special_path != dlcname and special_path in dlcname_paths: #special case where some tracks contain a path that goes outside of current dlc
            print(ANSI(f"Sound path '{ANSI(path).bold()}' is not part of dlc '{ANSI(dlcname).bold()}'").yellow())
            return {"DlcPath": full_dlc_path(dlcname_paths[special_path][0]), "Path": path, "Duration": int(duration)}
        
        return {"Path": path, "Duration": int(duration)}
    
    print(ANSI(f"Sound path not found: {streamingSoundName}").yellow())
    return {}

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

def dlc_file(dlcname, filename):
    if dlcname == "base" or dlcname == "game":
        dlcname = ""
    if dlcname:
        dlcname += "_"

    return dlcname + filename

def export_dlc_radio_info(station_list: list[str], dlcname: str = "base", data_path: Path = data_dir, out_path: Path = out_dir):
    game_path = data_path / dlc_file(dlcname, "game.dat151.rel.xml")
    if not game_path.is_file():
        print(ANSI(f"Game data file '{game_path.name}' does not exist, export cancelled").yellow())
        return False
    game_root = etree.parse(game_path).getroot().find("Items")
    game_index = xml.TypeIndex(game_root, ["RadioTrackTextIDs", "RadioStationTrackList", "RadioStationSettings"])


    sound_path = data_path / dlc_file(dlcname, "sounds.dat54.rel.xml")
    if not sound_path.is_file():
        print(ANSI(f"Sound data file '{sound_path.name}' does not exist, sound path and duration will not be loaded").red())
    else:
        sound_root = etree.parse(sound_path).getroot().find("Items")
        sound_index = xml.TypeIndex(sound_root, ["StreamingSound", "SimpleSound"])


    nametables = HashMap()
    nametables.load_nametable(data_path / dlc_file(dlcname, "game.dat151.nametable"))
    nametables.load_nametable(data_path / dlc_file(dlcname, "sounds.dat54.nametable"))

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

            track_info = {"Id": nametables.resolve_string(track.text)} | GetStreamingSoundInfo(sound_index, track.text, dlcname)

            markers = GetTrackMarkers(game_index, id_fix)
            if markers:
                track_info["Markers"] = markers

            collected_tracks.append(track_info)

        track_list_info = filter_dict(xml.to_dict(track_list_el, 1), {"Flags", "Category"})
        track_list_info["Tracks"] = collected_tracks
        export_track_info["TrackLists"][nametables.resolve_string(track_list_id)] = track_list_info

    print(f"[{delta_time_ms(time_start)}ms] Processed all track lists for '{dlcname}'")

    with open(out_path / f"{dlcname}_info.json", "w", encoding="utf-8") as f:
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
                print(ANSI(f"Could not merge with export '{ANSI(dlc_path.name).bold()}', because it does not exist").red())
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
                dlcname = path.name.rsplit("_", 1)[0]
                if dlcname in dlcname_paths:
                    track_list = {"DlcPath": full_dlc_path(dlcname_paths[dlcname][0])} | track_list
                else:
                    print(ANSI(f"Could not find DlcPath for dlc '{ANSI(dlcname).bold()}'").red())
                merged_data["TrackLists"][track_list_id] = track_list
                continue

            conflicts.append((["Stations", track_list_id], path.name))

    with open(merged_out_path, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)

    print(ANSI(f"Merged processed files into '{ANSI(merged_out_path.name).bold()}'").green())
    if conflicts:
        print(ANSI(f"\n{len(conflicts)} conflict(s) detected during merge").red())
        for section, source in conflicts:
            print(f"- '{ANSI('/'.join(section)).bold()}' (from file '{source}')")

    return merged_data, conflicts


# Ordered list of DLCs that contain .dat151 or .dat54 metadata files.
# The order reflects their chronological release, with 'base' representing base game content.
all_dlc = ['base', 'dlcbeach', 'dlcvalentines', 'dlcbusiness', 'dlcbusi2', 'dlcthelab', 'dlchipster', 'dlcindependence', 'dlcpilotschool', 'dlcmplts', 'dlcxmas2', 'dlcmpheist', 'dlcluxe', 'dlcthelab', 'dlcsfx1', 'dlclowrider', 'dlchalloween', 'dlcapartment', 'dlcxmas3', 'dlcjanuary2016', 'mpvalentines2', 'dlclow2', 'dlcexec1', 'dlcstunt', 'dlcbiker', 'dlcimportexport', 'dlcspecialraces', 'dlcgunrunning', 'dlcairraces', 'dlcsmuggler', 'dlcchristmas2017', 'dlcassault', 'dlcbattle', 'dlcawxm2018', 'dlcvinewood', 'dlcheist3', 'dlcsum20', 'dlchei4', 'dlctuner', 'dlcsecurity', 'dlcg9ec', 'dlcmpsum2', 'dlccm2022', 'dlcmp2023_1', 'dlc23_2', 'dlc24-1', 'dlc24-2']
# Subset of the above DLCs that contain radio station metadata
all_radio_dlc = ['base', 'dlcthelab', 'dlcchristmas2017', 'dlcheist3', 'dlcsum20', 'dlchei4', 'dlctuner', 'dlcsecurity', 'dlcmpsum2', 'dlc23_2', 'dlc24-1']
# List of all known radio station identifiers (excluding ones not shown on radio wheel)
all_stations = ["radio_01_class_rock", "radio_02_pop", "radio_03_hiphop_new", "radio_04_punk", "radio_05_talk_01", "radio_06_country", "radio_07_dance_01", "radio_08_mexican", "radio_09_hiphop_old", "radio_11_talk_02", "radio_12_reggae", "radio_13_jazz", "radio_14_dance_02", "radio_15_motown", "radio_16_silverlake", "radio_17_funk", "radio_18_90s_rock", "radio_19_user", "radio_20_thelab", "radio_21_dlc_xm17", "radio_23_dlc_xm19_radio", "radio_27_dlc_prhei4", "radio_34_dlc_hei4_kult", "radio_35_dlc_hei4_mlr", "radio_36_audioplayer", "radio_37_motomami"]

for dlc in all_radio_dlc:
    print(ANSI(f"\n\nLoading radio dlc: '{ANSI(dlc).bold()}'").green())
    export_dlc_radio_info(all_stations, dlc)

merge_exports(all_radio_dlc)