import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
import shutil
import os
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

# Files
input_file = "epg/tataplay.xml"  # fresh grab (raw)
backup_file = "epg/tataplay_backup.xml.gz"  # merged full backup
final_file = "epg/tataplay.xml.gz"  # 2-day trimmed

# --- Helpers ---
def to_ist(dt_str):
    """Convert UTC string to IST formatted +0530 string"""
    try:
        dt_utc = datetime.strptime(dt_str[:14], "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        dt_ist = dt_utc.astimezone(IST)
        return dt_ist.strftime("%Y%m%d%H%M%S +0530")
    except Exception:
        return dt_str

def parse_xml(path, gz=False):
    """Parse XML (supporting gzip)"""
    if not os.path.exists(path):
        return None
    if gz:
        with gzip.open(path, "rb") as f:
            return ET.ElementTree(ET.fromstring(f.read()))
    else:
        return ET.parse(path)

def write_gzip_xml(tree, path):
    """Pretty-print and gzip an XML tree"""
    xml_str = ET.tostring(tree.getroot(), encoding="utf-8")
    parsed = minidom.parseString(xml_str)
    pretty = parsed.toprettyxml(indent="  ", encoding="utf-8")
    pretty = b"\n".join(line for line in pretty.splitlines() if line.strip())

    with gzip.open(path, "wb") as f:
        f.write(pretty)

# --- Load today's grab ---
today_tree = parse_xml(input_file)
if today_tree is None:
    raise FileNotFoundError(f"Missing input file: {input_file}")
today_root = today_tree.getroot()

# --- Load yesterday’s backup (if exists) ---
yesterday_tree = parse_xml(backup_file, gz=True)
yesterday_root = yesterday_tree.getroot() if yesterday_tree else None

# --- Build merged backup ---
channels_today = {c.attrib["id"]: c for c in today_root.findall("channel")}
programmes_today = {}
for p in today_root.findall("programme"):
    ch = p.attrib.get("channel")
    if ch not in programmes_today:
        programmes_today[ch] = []
    programmes_today[ch].append(p)

channels_final = dict(channels_today)  # start with today's
programmes_final = {k: list(v) for k, v in programmes_today.items()}

if yesterday_root is not None:
    for c in yesterday_root.findall("channel"):
        cid = c.attrib["id"]
        if cid not in channels_final:
            channels_final[cid] = c

    for p in yesterday_root.findall("programme"):
        cid = p.attrib.get("channel")
        if cid not in programmes_final:
            programmes_final[cid] = []
        # keep only programmes from today onwards
        start_str = p.attrib.get("start", "")[:14]
        try:
            start_dt = datetime.strptime(start_str, "%Y%m%d%H%M%S").replace(tzinfo=UTC).astimezone(IST)
            if start_dt.date() >= datetime.now(IST).date():
                programmes_final[cid].append(p)
        except:
            continue

# --- Create merged backup tree ---
backup_root = ET.Element("tv")
for c in sorted(channels_final.values(), key=lambda x: x.find("display-name").text.lower() if x.find("display-name") is not None else x.attrib.get("id", "")):
    backup_root.append(c)

for cid in sorted(programmes_final.keys()):
    for p in sorted(programmes_final[cid], key=lambda x: x.attrib.get("start", "")):
        # Convert start/stop to IST
        for attr in ("start", "stop"):
            if attr in p.attrib:
                p.set(attr, to_ist(p.attrib[attr]))
        backup_root.append(p)

backup_tree = ET.ElementTree(backup_root)

# --- Save merged backup ---
write_gzip_xml(backup_tree, backup_file)
print(f"✅ Updated backup: {backup_file}")

# --- Build trimmed final (today + tomorrow only) ---
today = datetime.now(IST).date()
tomorrow = today + timedelta(days=1)

final_root = ET.Element("tv")
for c in backup_root.findall("channel"):
    final_root.append(c)

for p in backup_root.findall("programme"):
    start_str = p.attrib.get("start", "")[:14]
    try:
        start_dt = datetime.strptime(start_str, "%Y%m%d%H%M%S").replace(tzinfo=IST)
        if today <= start_dt.date() <= tomorrow:
            final_root.append(p)
    except:
        continue

final_tree = ET.ElementTree(final_root)
write_gzip_xml(final_tree, final_file)
print(f"✅ Trimmed final (2 days): {final_file}")
