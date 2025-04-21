import math
from lxml.etree import _Element
from time import perf_counter

from hash_utils import joaat, format_hash, get_trackid_table

class TypeIndex:
    def __init__(self, xml_root: _Element, valid_types: list[str]):
        if len(valid_types) == 0:
            raise ValueError("valid_types cannot be empty")

        start_time = perf_counter()
        self.index = {t: {} for t in valid_types}

        for type_name in valid_types:
            for item in xml_root.xpath(f".//Item[@type='{type_name}']"):
                name_elem = item.find("Name")
                if name_elem is not None and name_elem.text:
                    self.index[type_name][name_elem.text] = item

        print(f"Building xml index took {round((perf_counter() - start_time) * 1000, 3)}ms")

    def get(self, type_name: str, name: str, try_hash: bool = False) -> _Element | None:
        items = self.index.get(type_name, {})
        if name in items:
            return items[name]
        if try_hash:
            return items.get(format_hash(joaat(name)))
        return None
    
def to_dict(elem: _Element, depth_limit = 0, depth = 0):
    text = None
    if isinstance(elem.text, str) and (not elem.text.isspace()):
        text = elem.text.strip()

    if text and not elem.attrib and not list(elem):
        return text
    
    d = dict(elem.attrib)
    if text:
        d["Text"] = elem.text

    if depth_limit == 0 or depth_limit > depth:
        for child in elem:
            new_dict = to_dict(child, depth_limit, depth + 1)

            if not new_dict:
                continue

            if child.tag in d:
                if type(d[child.tag]) is list:
                    d[child.tag].append(new_dict)
                else:
                    d[child.tag] = [d[child.tag], new_dict]
                continue

            d[child.tag] = new_dict

    if len(list(d.keys())) == 1:
        return list(d.values())[0]
            
    return d

def resolve_marker_trackid(marker: dict[str, any], text_id: str):
    marker["Title"] = get_trackid_table().resolve(joaat(text_id + "S"))
    marker["Artist"] = get_trackid_table().resolve(joaat(text_id + "A"))

def marker_dict_awc(markers_container: _Element, stream_info: dict):
    markers_dict = to_dict(markers_container)
    if not (type(markers_dict) is list):
        markers_dict = [markers_dict]

    result: dict[str, list[str]] = {}
    sample_rate = float(stream_info.get("SampleRate") or 48000)
    for marker in markers_dict:
        if "Name" not in marker: # some awc xml files have missing values? (hei4_mlr_mm_p3)
            continue

        match marker["Name"]:
            case "trackid":
                marker_type = "Track"
            case "beat":
                marker_type = "Beat"
            case "rockout":
                marker_type = "Rockout"
            case "dj":
                marker_type = "DJ"
            case _:
                continue

        if "Value" not in marker: # some awc xml files have missing values? (flylo_part2)
            continue

        new_marker = {}
        new_marker["Offset"] = math.floor((float(marker["SampleOffset"]) * 1000) / sample_rate)

        if marker_type == "Track":
            resolve_marker_trackid(new_marker, marker["Value"])
        else:
            value = marker["Value"]
            if value.isdigit():
                value = int(value)
            new_marker["Value"] = value

        if marker_type not in result:
            result[marker_type] = []
        
        result[marker_type].append(new_marker)

    return result
    
def marker_dict_xml(markers_container: _Element, isTrackType = False):
    markers_dict = to_dict(markers_container)
    if not (type(markers_dict) is list):
        markers_dict = [markers_dict]

    result = []
    prev_marker = None
    for marker in markers_dict:
        new_marker = {}
        new_marker["Offset"] = int(marker["OffsetMs"])

        TextId = marker["TextId"]
        if isTrackType:
            resolve_marker_trackid(new_marker, TextId)
        else:
            new_marker["Value"] = int(TextId)

        if new_marker == prev_marker:
            continue

        result.append(new_marker)
        prev_marker = new_marker

    return result