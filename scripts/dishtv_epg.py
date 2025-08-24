import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
import shutil
from datetime import datetime

input_file = "epg/dishtv.xml"
output_file = "epg/dishtv.xml"
gzip_file = "epg/dishtv.xml.gz"

# Helper: just relabel to +0530 without shifting
def relabel_as_ist(dt_str):
    try:
        dt = datetime.strptime(dt_str[:14], "%Y%m%d%H%M%S")
        return dt.strftime("%Y%m%d%H%M%S +0530")
    except ValueError:
        return dt_str

# Parse XML
tree = ET.parse(input_file)
root = tree.getroot()

# Convert <tv> date (relabel only)
if "date" in root.attrib:
    root.set("date", relabel_as_ist(root.attrib["date"]))

# --- Collect and clean programmes ---
programmes = []
for programme in root.findall("programme"):
    # Relabel start/stop attributes to +0530
    for attr in ("start", "stop"):
        if attr in programme.attrib:
            programme.set(attr, relabel_as_ist(programme.attrib[attr]))

    # Keep only English titles
    titles = programme.findall("title")
    if len(titles) > 1:
        for t in titles:
            if t.attrib.get("lang") != "en":
                programme.remove(t)

    # Keep only English descriptions
    descs = programme.findall("desc")
    if len(descs) > 1:
        for d in descs:
            if d.attrib.get("lang") != "en":
                programme.remove(d)

    # Remove other tags (like <icon>, <url>)
    for child in list(programme):
        if child.tag not in ("title", "desc"):
            programme.remove(child)

    # Remove empty title/desc
    for tag in ("title", "desc"):
        element = programme.find(tag)
        if element is not None and (element.text is None or element.text.strip() == ""):
            programme.remove(element)

    programmes.append(programme)

# --- Collect channels ---
channels = root.findall("channel")

# --- Remove existing channels and programmes ---
for elem in channels + root.findall("programme"):
    root.remove(elem)

# --- Sort channels alphabetically ---
def channel_key(c):
    name_elem = c.find("display-name")
    if name_elem is not None and name_elem.text:
        return name_elem.text.lower()
    return c.attrib.get("id", "").lower()

channels.sort(key=channel_key)

# --- Re-attach sorted channels ---
for c in channels:
    root.append(c)

# --- Sort programmes by channel then start ---
def sort_key(p):
    channel = p.attrib.get("channel", "").lower()
    start = p.attrib.get("start", "")
    return (channel, start)

programmes.sort(key=sort_key)

# --- Re-attach sorted programmes ---
for p in programmes:
    root.append(p)

# --- Pretty print XML with indentation ---
xml_str = ET.tostring(root, encoding="utf-8")
parsed = minidom.parseString(xml_str)
pretty_xml_as_str = parsed.toprettyxml(indent="  ", encoding="utf-8")

# Remove blank lines
pretty_xml_as_str = b"\n".join(
    line for line in pretty_xml_as_str.splitlines() if line.strip()
)

# --- Save cleaned XML ---
with open(output_file, "wb") as f:
    f.write(pretty_xml_as_str)

# --- Create gzipped version ---
with open(output_file, "rb") as f_in:
    with gzip.open(gzip_file, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

print(f"✅ Cleaned + sorted EPG saved to {output_file} and {gzip_file}")