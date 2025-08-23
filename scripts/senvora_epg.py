import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
import shutil
import os
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

input_file = "epg/senvora.xml"
backup_file = "epg/senvora_backup.xml.gz"
final_file = "epg/senvora.xml.gz"

# --- Helper: convert UTC string to IST ---
def to_ist(dt_str):
    try:
        dt_utc = datetime.strptime(dt_str[:14], "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        dt_ist = dt_utc.astimezone(IST)
        return dt_ist.strftime("%Y%m%d%H%M%S +0530")
    except ValueError:
        return dt_str

# --- Parse grabbed file ---
tree_today = ET.parse(input_file)
root_today = tree_today.getroot()

# Fix <tv> date
if "date" in root_today.attrib:
    root_today.set("date", to_ist(root_today.attrib["date"]))

# Collect channels + programmes (cleaned)
def clean_programmes(root):
    progs = []
    for p in root.findall("programme"):
        # Convert start/stop to IST
        for attr in ("start", "stop"):
            if attr in p.attrib:
                p.set(attr, to_ist(p.attrib[attr]))

        # Keep only English title/desc
        for t in list(p.findall("title")):
            if t.attrib.get("lang") != "en":
                p.remove(t)
        for d in list(p.findall("desc")):
            if d.attrib.get("lang") != "en":
                p.remove(d)

        # Remove unwanted tags
        for child in list(p):
            if child.tag not in ("title", "desc"):
                p.remove(child)

        # Drop empty title/desc
        for tag in ("title", "desc"):
            el = p.find(tag)
            if el is not None and (el.text is None or el.text.strip() == ""):
                p.remove(el)

        progs.append(p)
    return progs

channels_today = root_today.findall("channel")
progs_today = clean_programmes(root_today)

# --- Load yesterday's backup (if exists) ---
channels_prev, progs_prev = [], []
if os.path.exists(backup_file):
    with gzip.open(backup_file, "rb") as f:
        tree_prev = ET.parse(f)
        root_prev = tree_prev.getroot()
        channels_prev = root_prev.findall("channel")
        progs_prev = clean_programmes(root_prev)

# --- Merge: keep today's channels/programmes, fill missing from yesterday ---
channels_map = {c.attrib.get("id"): c for c in channels_today}
progs_map = {}

for p in progs_today:
    cid = p.attrib.get("channel")
    progs_map.setdefault(cid, []).append(p)

# Fill missing channels/programmes from yesterday
for c in channels_prev:
    cid = c.attrib.get("id")
    if cid not in channels_map:
        channels_today.append(c)
for p in progs_prev:
    cid = p.attrib.get("channel")
    if cid not in progs_map:
        progs_today.append(p)

# --- Rebuild <tv> root ---
root_new = ET.Element("tv")
for k, v in root_today.attrib.items():
    root_new.set(k, v)

# Sort channels alphabetically
channels_today.sort(key=lambda c: (c.find("display-name").text or c.attrib.get("id", "")).lower())
for c in channels_today:
    root_new.append(c)

# Sort programmes by channel + start
progs_today.sort(key=lambda p: (p.attrib.get("channel", "").lower(), p.attrib.get("start", "")))
for p in progs_today:
    root_new.append(p)

# --- Save backup (full, today+future) ---
xml_str = ET.tostring(root_new, encoding="utf-8")
parsed = minidom.parseString(xml_str)
pretty_xml = parsed.toprettyxml(indent="  ", encoding="utf-8")
pretty_xml = b"\n".join(line for line in pretty_xml.splitlines() if line.strip())

with gzip.open(backup_file, "wb") as f:
    f.write(pretty_xml)

# --- Save trimmed file (today + tomorrow only) ---
now_ist = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
tomorrow_ist = now_ist + timedelta(days=2)

root_trim = ET.Element("tv")
for k, v in root_new.attrib.items():
    root_trim.set(k, v)

for c in channels_today:
    root_trim.append(c)

for p in progs_today:
    try:
        start = datetime.strptime(p.attrib["start"][:14], "%Y%m%d%H%M%S").replace(tzinfo=IST)
        if now_ist <= start < tomorrow_ist:
            root_trim.append(p)
    except Exception:
        pass

xml_str = ET.tostring(root_trim, encoding="utf-8")
parsed = minidom.parseString(xml_str)
pretty_xml = parsed.toprettyxml(indent="  ", encoding="utf-8")
pretty_xml = b"\n".join(line for line in pretty_xml.splitlines() if line.strip())

with gzip.open(final_file, "wb") as f:
    f.write(pretty_xml)

print(f"✅ Backup saved: {backup_file}")
print(f"✅ Final 2-day EPG saved: {final_file}")
