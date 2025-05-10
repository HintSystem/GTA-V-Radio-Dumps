from time import perf_counter

from pathlib import Path
from lxml import etree
from lxml.etree import _Element
import json

import xml_utils as xml
from hash_utils import joaat, parse_hash_string, format_hash, HashMap
from utils import delta_time_ms, save_json, ANSI, script_dir, data_dir, out_dir

dlcname_paths = {'base': ['audio/sfx'], 'dlcbeach': ['dlcpacks/mpbeach'], 'dlcvalentines': ['dlcpacks/mpvalentines'], 'dlcupdate': ['dlcpacks/patchday2bng'], 'dlcbusiness': ['dlcpacks/mpbusiness'], 'dlcbusi2': ['dlcpacks/mpbusiness2'], 'dlcpd03': ['dlcpacks/patchday3ng'], 'dlcthelab': ['dlcpacks/patchday3ng', 'dlcpacks/mpluxe2'], 'dlchipster': ['dlcpacks/mphipster'], 'dlcindependence': ['dlcpacks/mpindependence'], 'dlcpilotschool': ['dlcpacks/mppilot'], 'dlcmplts': ['dlcpacks/mplts'], 'dlcxmas2': ['dlcpacks/mpchristmas2'], 'dlcmpheist': ['dlcpacks/mpheist'], 'dlcluxe': ['dlcpacks/mpluxe'], 'dlcsfx1': ['dlcpacks/mpreplay'], 'dlclowrider': ['dlcpacks/mplowrider'], 'dlchalloween': ['dlcpacks/mphalloween'], 'dlcapartment': ['dlcpacks/mpapartment'], 'dlcxmas3': ['dlcpacks/mpxmas_604490'], 'dlcjanuary2016': ['dlcpacks/mpjanuary2016'], 'mpvalentines2': ['dlcpacks/mpvalentines2'], 'dlclow2': ['dlcpacks/mplowrider2'], 'dlcexec1': ['dlcpacks/mpexecutive'], 'dlcstunt': ['dlcpacks/mpstunt'], 'dlcbiker': ['dlcpacks/mpbiker'], 'dlcimportexport': ['dlcpacks/mpimportexport'], 'dlcspecialraces': ['dlcpacks/mpspecialraces'], 'dlcgunrunning': ['dlcpacks/mpgunrunning'], 'dlcairraces': ['dlcpacks/mpairraces'], 'dlcsmuggler': ['dlcpacks/mpsmuggler'], 'dlcchristmas2017': ['dlcpacks/mpchristmas2017'], 'dlcassault': ['dlcpacks/mpassault'], 'dlcbattle': ['dlcpacks/mpbattle'], 'dlcawxm2018': ['dlcpacks/mpchristmas2018'], 'dlcvinewood': ['dlcpacks/mpvinewood'], 'dlcheist3': ['dlcpacks/mpheist3'], 'dlcsum20': ['dlcpacks/mpsum'], 'dlchei4': ['dlcpacks/mpheist4'], 'dlctuner': ['dlcpacks/mptuner'], 'dlcsecurity': ['dlcpacks/mpsecurity'], 'dlcg9ec': ['dlcpacks/mpg9ec'], 'dlcmpsum2': ['dlcpacks/mpsum2'], 'dlccm2022': ['dlcpacks/mpchristmas3'], 'dlcmp2023_1': ['dlcpacks/mp2023_01'], 'dlc23_2': ['dlcpacks/mp2023_02'], 'dlc24-1': ['dlcpacks/mp2024_01'], 'dlc24-2': ['dlcpacks/mp2024_02']}
def full_dlc_path(dlcpath: str):
    dlcpath: Path = Path(dlcpath)
    if dlcpath.parent.name == "dlcpacks":
        return f"update/%PLATFORM%/{dlcpath.as_posix()}"
    return f"%PLATFORM%/{dlcpath.as_posix()}"

def resolve_dlc_path(dlcname: str, file_path: str):
    if dlcname not in dlcname_paths:
        return file_path
    return f"{full_dlc_path(dlcname_paths[dlcname][0])}/{file_path}"

solved_sounds: dict[str, str] = {}
def GetStreamingSoundInfo(sound_index: xml.TypeIndex, sound_id: str, dlcname: str, tracklist_id: str):
    if sound_index == None:
        return {}

    streaming_sound: _Element = sound_index.get("StreamingSound", sound_id, True)
    if streaming_sound == None:
        if sound_id in solved_sounds:
            equivalent_track_list = solved_sounds[sound_id]
            print(ANSI(f"Sound ref '{ANSI(sound_id).bold()}' is identical to sound in track list '{ANSI(solved_sounds[sound_id]).bold()}'").yellow())
            return {"TrackList": equivalent_track_list}
        
        print(ANSI(f"Missing sound ref: '{ANSI(sound_id).bold()}'").yellow())
        return {}
    else:
        solved_sounds[sound_id] = tracklist_id
    
    duration = None
    path = None
    duration_el = streaming_sound.xpath("./Duration")[0]
    if duration_el != None:
        duration = duration_el.get("value")
    
    child_items: _Element = streaming_sound.xpath("./ChildSounds/Item")
    for item in child_items:
        if not item.text:
            continue

        simple_sound: _Element = sound_index.get("SimpleSound", item.text)
        container_name = simple_sound.xpath("./ContainerName")[0]
        path = container_name.text

        special_path = Path(path).parent.name.replace("_", "")
        if special_path != dlcname and special_path in dlcname_paths: # special case where some tracks contain a path that goes outside of current dlc
            print(ANSI(f"Sound path '{ANSI(path).bold()}' is not part of dlc '{ANSI(dlcname).bold()}'").yellow())
            return {"DlcPath": full_dlc_path(dlcname_paths[special_path][0]), "Path": path, "Duration": int(duration)}
        
        return {"Path": path, "Duration": int(duration)}
    
    print(ANSI(f"Sound path not found: {sound_id}").yellow())
    return {}

speech_full_lookup_hashes = {
    "DJ_RADIO_01_CLASS_ROCK_TIMEEVENING": "hash_94860776",
    "DJ_RADIO_03_HIPHOP_NEW_TIMEMORNING": "hash_9D2EBFE7",
    "DJ_RADIO_03_HIPHOP_NEW_TOTO_NEWS": "hash_BC0D19AE",
    "DJ_RADIO_16_SILVERLAKE_TOTO_NEWS": "hash_F4B00F49"
}

speech_context_lookup_hashes = { # some intro speech hashes are calculated incorrectly so we need to correct them temporarily (these are not guaranteed to be correct but do have the right amount of variations and belong to the right container)
    # RADIO_01_CLASS_ROCK
    "fortunate_son": "hash_C2B7DAA9",
    "peace_of_mind": "hash_B5305BDE",
    # RADIO_02_POP
    "adult_education": "hash_5E9215DB",
    "bad_girls": "hash_7197FF12",
    "circle_in_the_sand": "hash_B3021ACB",
    "kids": "hash_67DBA112",
    "me_and_you": "hash_DF70D30D",
    "tape_loop": "hash_A52104F5",
    "tape_loop_alt": "hash_A52104F5",
    "tell_to_my_heart": "hash_9226104B",
    "the_time_is_now": "hash_4E4B7EC6",
    "with_every_heartbeat": "hash_740A6C34",
    "work": "hash_B215308B",
    # RADIO_03_HIPHOP_NEW
    "illuminate": "hash_EC3039FB",
    # RADIO_04_PUNK
    "lexicon_devil": "hash_73D453B0",
    # RADIO_09_HIPHOP_OLD
    "gin_and_juice": "hash_FDEFB15F",
    "no_more_questions": "hash_F55916E4",
    "so_you_want_to_be_a_gangster": "hash_228D7ED7",
    # RADIO_12_REGGAE
    "grumblin_dub": "hash_6B9A5F84",
    "nobody_move_get_hurt": "hash_D1165638",
    # RADIO_15_MOTOWN
    "hercules": "hash_DD744275",
    "i_believe_in_miracles": "hash_B33CEB37",
    # RADIO_16_SILVERLAKE
    "old_love": "hash_765071BF",
    # RADIO_17_FUNK
    # "cant_hold_back": "???" - before it was removed
    "heart_beat": "hash_B66D01A2",
    # RADIO_18_90S_ROCK
    "nine_is_god": "hash_4B5B10F2"
}

found_speech_context = {}
def get_speech_context(speech_index: xml.TypeIndex, voice_name: str, context_name: str):
    if speech_index == None:
        return {}

    if context_name in speech_context_lookup_hashes:
        lookup_string = speech_context_lookup_hashes[context_name]
    elif (voice_name + context_name).upper() in speech_full_lookup_hashes:
        lookup_string = speech_full_lookup_hashes[(voice_name + context_name).upper()]
    else:
        context_name_hash = joaat(context_name)
        voice_name_hash = joaat(voice_name)

        lookup_hash = context_name_hash
        if context_name_hash != voice_name_hash:
            lookup_hash = (context_name_hash ^ voice_name_hash) & 0xFFFFFFFF
        lookup_string = f"{lookup_hash:08x}"

    el = speech_index.get("ByteArray", lookup_string, True)
    if el != None:
        speech_context = xml.SpeechContext(el)

    #DEBUG
    if not voice_name in found_speech_context:
        found_speech_context[voice_name] = {"Count": 0, "Variations": 0, "Items": [], "Lost": []}

    if el == None:
        found_speech_context[voice_name]["Lost"].append([context_name, context_name])
        return {}
        
    found_speech_context[voice_name]["Count"] += 1
    found_speech_context[voice_name]["Variations"] += speech_context.num_variations
    found_speech_context[voice_name]["Items"].append([format_hash(joaat(lookup_string)), context_name, voice_name, speech_context.container_index])
    #DEBUG END

    container_path = None
    container = speech_index.get("Container", str(speech_context.container_index), True)
    if container != None:
        container_path = container.find("ContainerHash").text

    return {
        "Variations": speech_context.num_variations,
        "ContainerPath": container_path 
    }

def GetIntroInfo(speech_index: xml.TypeIndex, radio_name: str, sound_path: str):
    if not sound_path:
        return {}
    return get_speech_context(speech_index, f"DJ_{radio_name}_INTRO", Path(sound_path).name)

def GetStationSpeechInfo(speech_index: xml.TypeIndex, radio_name: str, dlcname: str = None):
    speech_categories = {"GENERAL": [], "TAKEOVER_GENERAL": [], "DD_GENERAL": [], "PL_GENERAL": [],
                         "TIME": ["MORNING", "AFTERNOON", "EVENING", "NIGHT"],
                         "TO": ["TO_AD", "TO_NEWS", "TO_WEATHER"]}
    speech_info = {}
    for category, context_list in speech_categories.items():
        voice_name = f"DJ_{radio_name}_{category}"

        for context_name in context_list or [category]:
            speech_context_info = get_speech_context(speech_index, voice_name, context_name)
            if not speech_context_info:
                continue

            if dlcname and "ContainerPath" in speech_context_info:
                speech_context_info["ContainerPath"] = resolve_dlc_path(dlcname, speech_context_info["ContainerPath"])

            if len(context_list) == 0:
                speech_info[category] = speech_context_info
            else:
                if category not in speech_info:
                    speech_info[category] = {}
                speech_info[category][context_name] = speech_context_info

    return speech_info


trackinfo_path = data_dir / "tracks"
def GetAwcMarkers(tracklist_id: str, track_path: str):
    if not track_path:
        return

    track_info_path = trackinfo_path / tracklist_id / (Path(track_path).name + ".awc.xml")
    if not track_info_path.is_file():
        return

    awc_info = etree.parse(track_info_path)

    if track_info_path.is_file():
        markers: _Element = awc_info.xpath("//Markers")
        if not markers:
            return

        stream_info = awc_info.xpath("//StreamFormat")[0]
        return xml.marker_dict_awc(markers[0], xml.to_dict(stream_info))
    
    return

def GetRelMarkers(type_index: xml.TypeIndex, track_id: str):
    id_is_hash = parse_hash_string(track_id) # check if track_id is a hash string
    if id_is_hash: # that means the rtt and rtb will also be a hash string instead
        rtt_id = format_hash(joaat(f"rtt_{id_is_hash:08x}"))
        rtb_id = format_hash(joaat(f"rtb_{id_is_hash:08x}"))
    else:
        hash_val = joaat(track_id)
        rtt_id = f"rtt_{hash_val:08x}"
        rtb_id = f"rtb_{hash_val:08x}"

    rtt = type_index.get("RadioTrackTextIDs", rtt_id)
    rtb = type_index.get("RadioTrackTextIDs", rtb_id)

    res = {}
    if rtt != None:
        res["Track"] = xml.marker_dict_xml(rtt.xpath("./Events")[0], True)
    if rtb != None:
        res["Beat"] = xml.marker_dict_xml(rtb.xpath("./Events")[0])

    return res

def get_station_flags_list(hex_str: str, station_id: str):
    station_id = station_id.upper()
    forced_flags = {
        "RADIO_03_HIPHOP_NEW": ["USERANDOMIZEDSTRIDESELECTION"],
        "RADIO_09_HIPHOP_OLD": ["USERANDOMIZEDSTRIDESELECTION"],
        "RADIO_22_DLC_BATTLE_MIX1_CLUB": ["ISMIXSTATION"],
        "RADIO_37_MOTOMAMI": ["USERANDOMIZEDSTRIDESELECTION"]
    }
    flags = [
        "NOBACK2BACKMUSIC",
        "BACK2BACKADS",
        "PLAYWEATHER",
        "PLAYNEWS",
        "SEQUENTIALMUSIC",
        "IDENTSINSTEADOFADS",
        "LOCKED",
        "HIDDEN",
        "PLAYSUSERSMUSIC",
        "HASREVERBCHANNEL",
        "ISMIXSTATION",
    ]

    AUD_TRISTATE_TRUE = 1
    value = int(hex_str, 16)

    enabled_flags = []
    for flag_id, name in enumerate(flags):
        tristate = (value >> (flag_id * 2)) & 0x03
        if tristate == AUD_TRISTATE_TRUE:
            enabled_flags.append(name)
    
    if station_id and station_id in forced_flags:
        for flag in forced_flags[station_id]:
            if flag in enabled_flags:
                continue
            enabled_flags.append(flag)

    return enabled_flags

def filter_dict(dict: dict[str, any], keep_filter: set[str]):
    return {k: v for k, v in dict.items() if k in keep_filter}

def dlc_file(dlcname, filename):
    dlcprefix = "" if dlcname == "base" else f"{dlcname}_"
    return dlcprefix + filename

def try_load_data(dlcname: str, data_path: Path, filename: str, saved_types: list[str]):
    nametable = HashMap()
    if filename == "speech.dat4.rel.xml" and dlcname == "base":
        nametable.load_nametable(data_path / "speech.dat4.nametable")

    file_path = data_path / dlc_file(dlcname, filename)
    if not file_path.is_file():
        return None, file_path
    
    root = etree.parse(file_path).getroot().find("Items")
    return xml.TypeIndex(root, saved_types, nametable), file_path

def get_news_tracklists(game_index: xml.TypeIndex, sound_index: xml.TypeIndex, nametables: HashMap):
    tracklists_result = {}
    for index in range(1, 64):
        tracklist_id = f"RADIO_NEWS_{index:02d}"
        tracklist_el = game_index.get("RadioStationTrackList", tracklist_id, True)
        if tracklist_el == None:
            continue

        tracklist_info = filter_dict(xml.to_dict(tracklist_el, 1), {"Flags", "Category"})
        tracklist_info["Tracks"] = []

        for track in tracklist_el.xpath("./Tracks/Item/SoundRef"):
            track_id: str = track.text
            track_id_resolved = nametables.resolve_string(track_id)

            track_info = {"Id": track_id_resolved} | GetStreamingSoundInfo(sound_index, track_id, "base", tracklist_id)
            tracklist_info["Tracks"].append(track_info)

        tracklists_result[tracklist_id] = tracklist_info

    if len(tracklists_result) != 0:
        print(ANSI("\n\nLoaded news track lists").green())

    return tracklists_result

def export_dlc_radio_info(station_list: list[str], dlcname: str = "base", data_path: Path = data_dir, out_path: Path = out_dir):
    game_index, game_path = try_load_data(
        dlcname, data_path, "game.dat151.rel.xml",
        ["RadioTrackTextIDs", "RadioStationTrackList", "RadioStationSettings"]
    )
    if game_index == None:
        print(ANSI(f"Game data file '{game_path.name}' does not exist, export cancelled").yellow())
        return False
    
    sound_index, sound_path = try_load_data(
        dlcname, data_path, "sounds.dat54.rel.xml",
        ["StreamingSound", "SimpleSound"]
    )
    if sound_index == None:
        print(ANSI(f"Sound data file '{sound_path.name}' does not exist, sound path and duration will not be loaded").red())

    speech_index, speech_path = try_load_data(
        dlcname, data_path, "speech.dat4.rel.xml",
        ["ByteArray", "Hash", "Container"]
    )
    if speech_index == None:
        print(ANSI(f"Speech data file '{speech_path.name}' does not exist, dj speeches will not be loaded").red())


    nametables = HashMap()
    nametables.load_nametable(data_path / dlc_file(dlcname, "game.dat151.nametable"))
    nametables.load_nametable(data_path / dlc_file(dlcname, "sounds.dat54.nametable"))

    time_start = perf_counter()
    export_track_info = {"Stations": {}, "TrackLists": get_news_tracklists(game_index, sound_index, nametables)}
    unique_track_lists = []

    for station_id in station_list:
        station_time_start = perf_counter()

        station_el: _Element = game_index.get("RadioStationSettings", station_id, True)
        if station_el == None:
            continue

        track_list_items = station_el.xpath("./TrackList/Item")
        station_track_lists = []
        for track_list in track_list_items:
            station_track_lists.append(nametables.resolve_string(track_list.text))
            if track_list.text not in unique_track_lists:
                unique_track_lists.append((track_list.text, station_id))
        
        station_info = {"FlagsValue": None, "Flags": []} | filter_dict(xml.to_dict(station_el, 1), {"Flags", "RadioName", "Genre", "AmbientRadioVol"})
        station_info["FlagsValue"] = station_info["Flags"]
        station_info["Flags"] = get_station_flags_list(station_info["FlagsValue"], station_id)

        station_info["TrackLists"] = station_track_lists

        speech_info = GetStationSpeechInfo(speech_index, station_info["RadioName"] or station_id, dlcname)
        if speech_info:
            station_info["Speech"] = speech_info

        export_track_info["Stations"][station_id] = station_info

        print(f"[{delta_time_ms(station_time_start)}ms] Processed station '{station_id}' with {len(station_track_lists)} track lists")

    print(f"\n[{delta_time_ms(time_start)}ms] Processed all stations for '{dlcname}'")
    time_start = perf_counter()

    if len(export_track_info["Stations"]) == 0:
        print(ANSI(f"No stations exist for '{dlcname}', export cancelled").red())
        return False

    for tracklist_id, station_id in unique_track_lists:
        tracklist_el = game_index.get("RadioStationTrackList", tracklist_id)
        if tracklist_el == None:
            continue
        
        tracklist_id = nametables.resolve_string(tracklist_id)
        tracklist_info = {"FlagsValue": None} | filter_dict(xml.to_dict(tracklist_el, 1), {"Flags", "Category"})

        tracklist_info["FlagsValue"] = tracklist_info["Flags"]
        del tracklist_info["Flags"]

        collected_tracks = []
        for track in tracklist_el.xpath("./Tracks/Item/SoundRef"):
            track_id: str = track.text
            track_id_marker = track_id
            track_id_resolved = nametables.resolve_string(track_id)

            KULT_PREFIX  = "hei4_radio_kult_" # Special handling for Kult FM due to unique bank layout
            if track_id_marker.startswith(KULT_PREFIX):
                track_id_marker = "dlc_hei4_music_" + track_id_marker[len(KULT_PREFIX):]

            track_info = {"Id": track_id_resolved} | GetStreamingSoundInfo(sound_index, track_id, dlcname, tracklist_id)
            
            markers = None
            if tracklist_info["Category"] in ("0", "2"):
                markers = GetAwcMarkers(tracklist_id, track_info.get("Path"))
                
                radio_name = export_track_info['Stations'][station_id].get("RadioName") or station_id
                intro_info = GetIntroInfo(speech_index, radio_name, track_info.get("Path"))
                if intro_info:
                    track_info["Intro"] = intro_info

            if not markers:
                markers = GetRelMarkers(game_index, track_id_marker)

            if markers:
                track_info["Markers"] = markers

            collected_tracks.append(track_info)

        tracklist_info["Tracks"] = collected_tracks
        export_track_info["TrackLists"][tracklist_id] = tracklist_info

    print(f"[{delta_time_ms(time_start)}ms] Processed all track lists for '{dlcname}'")
    save_json(out_path / f"{dlcname}_info.json", export_track_info)

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

                if property == "Speech":
                    for category_name, category in value.items():
                        if category_name in merged_station[property]:
                            conflicts.append((["Stations", station_id, property, category_name], path.name))
                        merged_station[property][category_name] = category
                    continue
                
                if merged_station[property] != value:
                    merged_station[property] = value
                    conflicts.append((["Stations", station_id, property], path.name))


        for tracklist_id, track_list in data.get("TrackLists", {}).items():
            if tracklist_id not in merged_data["TrackLists"]:
                dlcname = path.name.rsplit("_", 1)[0]
                if dlcname in dlcname_paths:
                    track_list = {"DlcPath": full_dlc_path(dlcname_paths[dlcname][0])} | track_list
                else:
                    print(ANSI(f"Could not find DlcPath for dlc '{ANSI(dlcname).bold()}'").red())
                merged_data["TrackLists"][tracklist_id] = track_list
                continue

            conflicts.append((["Stations", tracklist_id], path.name))

    print(ANSI(f"Merged processed files into '{ANSI(merged_out_path.name).bold()}'").green())
    save_json(merged_out_path, merged_data)

    if conflicts:
        print(ANSI(f"\n{len(conflicts)} conflict(s) detected during merge").red())
        for section, source in conflicts:
            print(f"- '{ANSI('/'.join(section)).bold()}' (from file '{source}')")

    return merged_data, conflicts


# Ordered list of DLCs that contain .dat151 or .dat54 metadata files.
# The order reflects their chronological release, with 'base' representing base game content.
all_dlc = ['base', 'dlcbeach', 'dlcvalentines', 'dlcbusiness', 'dlcbusi2', 'dlcpd03', 'dlcthelab', 'dlchipster', 'dlcindependence', 'dlcpilotschool', 'dlcmplts', 'dlcxmas2', 'dlcmpheist', 'dlcluxe', 'dlcthelab', 'dlcsfx1', 'dlclowrider', 'dlchalloween', 'dlcapartment', 'dlcxmas3', 'dlcjanuary2016', 'mpvalentines2', 'dlclow2', 'dlcexec1', 'dlcstunt', 'dlcbiker', 'dlcimportexport', 'dlcspecialraces', 'dlcgunrunning', 'dlcairraces', 'dlcsmuggler', 'dlcchristmas2017', 'dlcassault', 'dlcbattle', 'dlcawxm2018', 'dlcvinewood', 'dlcheist3', 'dlcsum20', 'dlchei4', 'dlctuner', 'dlcsecurity', 'dlcg9ec', 'dlcmpsum2', 'dlccm2022', 'dlcmp2023_1', 'dlc23_2', 'dlc24-1', 'dlc24-2']
# Subset of the above DLCs that contain radio station metadata
all_radio_dlc = ['base', 'dlcpd03', 'dlcthelab', 'dlcchristmas2017', 'dlcbattle', 'dlcheist3', 'dlcsum20', 'dlchei4', 'dlctuner', 'dlcsecurity', 'dlcmpsum2', 'dlc23_2', 'dlc24-1']
# List of all known radio station identifiers (excluding ones not shown on radio wheel)
all_stations = ["radio_01_class_rock", "radio_02_pop", "radio_03_hiphop_new", "radio_04_punk", "radio_05_talk_01", "radio_06_country", "radio_07_dance_01", "radio_08_mexican", "radio_09_hiphop_old", "radio_11_talk_02", "radio_12_reggae", "radio_13_jazz", "radio_14_dance_02", "radio_15_motown", "radio_16_silverlake", "radio_17_funk", "radio_18_90s_rock", "radio_19_user", "radio_20_thelab", "radio_21_dlc_xm17", "radio_22_dlc_battle_mix1_radio", "radio_23_dlc_xm19_radio", "radio_27_dlc_prhei4", "radio_34_dlc_hei4_kult", "radio_35_dlc_hei4_mlr", "radio_36_audioplayer", "radio_37_motomami"]

for dlc in all_radio_dlc:
    print(ANSI(f"\n\nLoading radio dlc: '{ANSI(dlc).bold()}'").green())
    export_dlc_radio_info(all_stations, dlc)

merge_exports(all_radio_dlc)