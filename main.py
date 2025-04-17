from time import perf_counter

from pathlib import Path
from lxml import etree
from lxml.etree import _Element
import json

import xml_utils as xml
from hash_utils import joaat, parse_hash_string, format_hash, HashMap
from utils import delta_time_ms, data_dir, script_dir
        
def GetStreamingSoundInfo(sounds_index: xml.TypeIndex, streamingSoundName: str):
    streaming_sound: _Element = sounds_index.get("StreamingSound", streamingSoundName, True)
    if streaming_sound == None:
        print(f"missing sound: {streamingSoundName}")
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

def exportStationTrackInfo(station_list: list[str], filename: str):
    if filename:
        filename += "_"

    nametables = HashMap()

    sound_root = etree.parse(data_dir / (filename + "sounds.dat54.rel.xml")).getroot().find("Items")
    sound_index = xml.TypeIndex(sound_root, ["StreamingSound", "SimpleSound"])

    game_root = etree.parse(data_dir / (filename + "game.dat151.rel.xml")).getroot().find("Items")
    game_index = xml.TypeIndex(game_root, ["RadioTrackTextIDs", "RadioStationTrackList", "RadioStationSettings"])

    nametables.load_nametable(data_dir / (filename + "game.dat151.nametable"))
    nametables.load_nametable(data_dir / (filename + "sounds.dat54.nametable"))

    filename = filename or "base_"

    time_start = perf_counter()
    export_track_info = {"Stations": {}, "TrackLists": {}}
    track_list_set = set()

    for station_name in station_list:
        station_time_start = perf_counter()

        station_el: _Element = game_index.get("RadioStationSettings", station_name, True)
        if station_el == None:
            continue

        track_list_items = station_el.xpath("./TrackList/Item")
        station_track_lists = []
        for track_list in track_list_items:
            station_track_lists.append(nametables.resolve_string(track_list.text))
            track_list_set.add(track_list.text)
        
        station_info = filter_dict(xml.to_dict(station_el, 1), {"Flags", "RadioName", "Genre", "AmbientRadioVol"})
        station_info["TrackLists"] = station_track_lists
        export_track_info["Stations"][station_name] = station_info

        print(f"[{delta_time_ms(station_time_start)}ms] Processed station '{station_name}' with {len(station_track_lists)} track lists")

    print(f"\n[{delta_time_ms(time_start)}ms] Processed all stations for '{filename}'")
    time_start = perf_counter()

    for track_list_id in track_list_set:
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

    print(f"[{delta_time_ms(time_start)}ms] Processed all track lists for '{filename}'")

    with open(script_dir / "processed" / (filename + "info.json"), "w", encoding="utf-8") as f:
        json.dump(export_track_info, f, indent=2, ensure_ascii=False)


all_stations = ["radio_01_class_rock", "radio_02_pop", "radio_03_hiphop_new", "radio_04_punk", "radio_05_talk_01", "radio_06_country", "radio_07_dance_01", "radio_08_mexican", "radio_09_hiphop_old", "radio_11_talk_02", "radio_12_reggae", "radio_13_jazz", "radio_14_dance_02", "radio_15_motown", "radio_16_silverlake", "radio_17_funk", "radio_18_90s_rock", "radio_19_user", "radio_20_thelab", "radio_21_dlc_xm17", "radio_23_dlc_xm19_radio", "radio_27_dlc_prhei4", "radio_34_dlc_hei4_kult", "radio_35_dlc_hei4_mlr", "radio_36_audioplayer", "radio_37_motomami"]
exportStationTrackInfo(all_stations, "")