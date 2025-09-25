import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
from datetime import datetime, timedelta
import os
import re

TMP_FOLDER = "tmp_xml"  # Node grabs temporary folder
OUTPUT_FILE = "guide/guide.xml.gz"  # Merged output

DAYS_TO_KEEP = 3
now = datetime.now()
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
end_time = today_start + timedelta(days=DAYS_TO_KEEP) - timedelta(seconds=1)
offset_str = " +0530"

print("🕒 Current runtime:", now.strftime("%Y-%m-%d %H:%M:%S") + offset_str)
print(f"📺 Keeping programmes from {today_start} to {end_time}")

def clean_programmes(root):
    programmes = []
    for programme in root.findall("programme"):
        start_str = programme.attrib.get("start")
        stop_str = programme.attrib.get("stop")
        if not start_str or not stop_str:
            continue
        try:
            start_dt = datetime.strptime(start_str[:14], "%Y%m%d%H%M%S")
            stop_dt = datetime.strptime(stop_str[:14], "%Y%m%d%H%M%S")
        except ValueError:
            continue
        if stop_dt < today_start or start_dt > end_time:
            continue
        programme.set("start", start_dt.strftime("%Y%m%d%H%M%S") + offset_str)
        programme.set("stop", stop_dt.strftime("%Y%m%d%H%M%S") + offset_str)

        for tag in ("title", "sub-title", "desc"):
            elements = programme.findall(tag)
            if elements:
                eng = [e for e in elements if e.attrib.get("lang") == "en"]
                if eng:
                    for e in elements:
                        if e not in eng:
                            programme.remove(e)
                else:
                    first = elements[0]
                    for e in elements[1:]:
                        programme.remove(e)
            element = programme.find(tag)
            if element is not None and (element.text is None or element.text.strip() == ""):
                programme.remove(element)

        for child in list(programme):
            if child.tag not in ("title", "sub-title", "desc"):
                programme.remove(child)

        if (
            programme.find("title") is None
            and programme.find("sub-title") is None
            and programme.find("desc") is None
        ):
            continue

        programmes.append(programme)
    return programmes

def alphanum_sort_key(cid):
    m = re.match(r'([a-zA-Z]+)?(\d+)?', cid)
    if m:
        prefix = m.group(1) or ''
        number = int(m.group(2)) if m.group(2) else float('inf')
        return (prefix.lower(), number)
    return (cid.lower(), float('inf'))

def pretty_xml(root):
    xml_str = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(xml_str)
    pretty_xml_as_str = parsed.toprettyxml(indent="  ", encoding="utf-8")
    return b"\n".join(line for line in pretty_xml_as_str.splitlines() if line.strip())

# --- Merge all Node XMLs in the order of sites.txt ---
merged_root = ET.Element("tv")
merged_root.attrib["date"] = now.strftime("%Y%m%d%H%M%S") + offset_str
merged_root.attrib["generator-info-name"] = "EPG Generator (Senvora)"
merged_root.attrib["generator-info-url"] = "https://github.com/senvora/epg.git"

all_programmes = []

# Read sites.txt to preserve merge order
sites_file = "scripts/personal/sites.txt"
with open(sites_file, "r") as f:
    provider_paths = [line.strip() for line in f if line.strip() and not line.startswith("#")]

provider_files = []
for provider_path in provider_paths:
    xml_file = os.path.join(TMP_FOLDER, os.path.basename(provider_path))
    if os.path.exists(xml_file):
        provider_files.append(xml_file)
    else:
        print(f"⚠️ Skipping missing XML: {xml_file}")

for xml_file in provider_files:
    print(f"Processing: {xml_file}")
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Channels: keep only required tags
    channels = root.findall("channel")
    for c in channels:
        for url in c.findall("url"):
            c.remove(url)
    channels.sort(key=lambda c: alphanum_sort_key(c.attrib.get("id", "")))

    # Append channels to merged_root
    for c in channels:
        merged_root.append(c)

    # Channel order for sorting programmes
    channel_order = {c.attrib["id"]: i for i, c in enumerate(channels)}

    cleaned_programmes = clean_programmes(root)
    cleaned_programmes.sort(key=lambda p: (
        channel_order.get(p.attrib.get("channel", ""), 9999),
        p.attrib.get("start", "")
    ))

    all_programmes.extend(cleaned_programmes)

# Append all programmes to merged_root
for p in all_programmes:
    merged_root.append(p)

# --- Save gzipped XML deterministically ---
os.makedirs("guide", exist_ok=True)

# Use GzipFile with mtime=0 to ensure deterministic output
with open(OUTPUT_FILE, "wb") as f_out_raw:
    with gzip.GzipFile(fileobj=f_out_raw, mode="wb", mtime=0) as f_out:
        f_out.write(pretty_xml(merged_root))

print(f"✅ Merged and saved deterministically: {OUTPUT_FILE}")