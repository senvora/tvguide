import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
import shutil
import os
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

# Files
input_file = "epg/dishtv.xml"             # fresh grab (raw)
backup_file = "epg/dishtv_backup.xml.gz"  # merged backup (full from today onward)
final_file = "epg/dishtv.xml.gz"          # trimmed 2-day

# --- Helpers ---
def to_ist_label(dt_str):
    """Relabel datetime string as +0530 (IST) without shifting actual time"""
    try:
        dt = datetime.strptime(dt_str[:14], "%Y%m%d%H%M%S")
        return dt.strftime("%Y%m%d%H%M%S +0530")
    except ValueError:
        return dt_str

def parse_xml(path, gz=False):
    if not os.path.exists(path):
        return None
    if gz:
        with gzip.open(path, "rb") as f:
            return ET.ElementTree(ET.fromstring(f.read()))
    else:
        return ET.parse(path)

def write_gzip_xml(tree, path):
    xml_str = ET.tostring(tree.getroot(), encoding="utf-8")
    parsed = minidom.parseString(xml_str)
    pretty = parsed.toprettyxml(indent="  ", encoding="utf-8")
    pretty = b"\n".join(line for line in pretty.splitlines() if line.strip())
    with gzip.open(path, "wb") as f:
        f.write(pretty)

# --- Step 1: Clean today’s input ---
tree = ET.parse(input_file)
root = tree.getroot()

if "date" in root.attrib:
    root.set("date", to_ist_label(root.attrib["date"]))

programmes_today = []
for programme in root.findall("programme"):
    # Relabel start/stop
    for attr in ("start", "stop"):
        if attr in programme.attrib:
            programme.set(attr, to_ist_label(programme.attrib[attr]))

    # Keep only English title
    titles = programme.findall("title")
    if len(titles) > 1:
        for t in titles:
            if t.attrib.get("lang") != "en":
                programme.remove(t)

    # Keep only English desc
    descs = programme.findall("desc")
    if len(descs) > 1:
        for d in descs:
            if d.attrib.get("lang") != "en":
                programme.remove(d)

    # Remove other tags
    for child in list(programme):
        if child.tag not in ("title", "desc"):
            programme.remove(child)

    # Remove empty title/desc
    for tag in ("title", "desc"):
        element = programme.find(tag)
        if element is not None and (element.text is None or element.text.strip() == ""):
            programme.remove(element)

    programmes_today.append(programme)

channels_today = root.findall("channel")

# --- Step 2: Load yesterday’s backup (if exists) ---
yesterday_tree = parse_xml(backup_file, gz=True)
yesterday_root = yesterday_tree.getroot() if yesterday_tree else None

# --- Step 3: Merge channels + programmes ---
channels_final = {c.attrib["id"]: c for c in channels_today}
programmes_final = {}
for p in programmes_today:
    ch = p.attrib.get("channel")
    if ch not in programmes_final:
        programmes_final[ch] = []
    programmes_final[ch].append(p)

if yesterday_root is not None:
    for c in yesterday_root.findall("channel"):
        cid = c.attrib["id"]
        if cid not in channels_final:
            channels_final[cid] = c

    today_date = datetime.now(IST).date()
    for p in yesterday_root.findall("programme"):
        cid = p.attrib.get("channel")
        if cid not in programmes_final:
            programmes_final[cid] = []
        # keep only from today onwards
        start_str = p.attrib.get("start", "")[:14]
        try:
            start_dt = datetime.strptime(start_str, "%Y%m%d%H%M%S")
            if start_dt.date() >= today_date:
                programmes_final[cid].append(p)
        except:
            continue

# --- Step 4: Build merged backup tree ---
backup_root = ET.Element("tv")

# Channels sorted alphabetically
def channel_key(c):
    name_elem = c.find("display-name")
    if name_elem is not None and name_elem.text:
        return name_elem.text.lower()
    return c.attrib.get("id", "").lower()

for c in sorted(channels_final.values(), key=channel_key):
    backup_root.append(c)

# Programmes sorted by channel, then start
for cid in sorted(programmes_final.keys()):
    for p in sorted(programmes_final[cid], key=lambda x: x.attrib.get("start", "")):
        backup_root.append(p)

backup_tree = ET.ElementTree(backup_root)

# --- Step 5: Save merged backup ---
write_gzip_xml(backup_tree, backup_file)
print(f"✅ Updated backup: {backup_file}")

# --- Step 6: Build 2-day trimmed file ---
today = datetime.now(IST).date()
tomorrow = today + timedelta(days=1)

final_root = ET.Element("tv")
for c in backup_root.findall("channel"):
    final_root.append(c)

for p in backup_root.findall("programme"):
    start_str = p.attrib.get("start", "")[:14]
    try:
        start_dt = datetime.strptime(start_str, "%Y%m%d%H%M%S")
        if today <= start_dt.date() <= tomorrow:
            final_root.append(p)
    except:
        continue

final_tree = ET.ElementTree(final_root)
write_gzip_xml(final_tree, final_file)
print(f"✅ Trimmed final (2 days): {final_file}")
