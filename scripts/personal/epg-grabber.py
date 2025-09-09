import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
from datetime import datetime, timedelta
import os
import glob
import re

# --- Input/Output folder ---
folder = "guide/"

# --- Local time ---
now = datetime.now()
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
tomorrow_end = today_start + timedelta(days=2) - timedelta(seconds=1)
offset_str = " +0530"

print("🕒 Current runtime:", now.strftime("%Y-%m-%d %H:%M:%S") + offset_str)

# --- Helper: parse & filter programmes ---
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
        # Skip if outside today + tomorrow
        if stop_dt < today_start or start_dt > tomorrow_end:
            continue
        # Update start/stop
        programme.set("start", start_dt.strftime("%Y%m%d%H%M%S") + offset_str)
        programme.set("stop", stop_dt.strftime("%Y%m%d%H%M%S") + offset_str)

        # Keep only title + desc
        for tag in ("title", "desc"):
            elements = programme.findall(tag)
            if elements:
                eng = [e for e in elements if e.attrib.get("lang") == "en"]
                if eng:
                    for e in elements:
                        if e not in eng:
                            programme.remove(e)
                else:
                    # keep first language
                    first = elements[0]
                    for e in elements[1:]:
                        programme.remove(e)
            # Remove empty tags
            element = programme.find(tag)
            if element is not None and (element.text is None or element.text.strip() == ""):
                programme.remove(element)

        # Remove other child tags
        for child in list(programme):
            if child.tag not in ("title", "desc"):
                programme.remove(child)

        if programme.find("title") is None and programme.find("desc") is None:
            continue
        programmes.append(programme)
    return programmes

# --- Helper: alphanumeric channel sort ---
def alphanum_sort_key(cid):
    m = re.match(r'([a-zA-Z]+)?(\d+)?', cid)
    if m:
        prefix = m.group(1) or ''
        number = int(m.group(2)) if m.group(2) else float('inf')
        return (prefix.lower(), number)
    return (cid.lower(), float('inf'))

# --- Pretty print ---
def pretty_xml(root):
    xml_str = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(xml_str)
    pretty_xml_as_str = parsed.toprettyxml(indent="  ", encoding="utf-8")
    return b"\n".join(line for line in pretty_xml_as_str.splitlines() if line.strip())

# --- Process single XML ---
def process_xml(file_path):
    print(f"Processing: {file_path}")
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Collect channels
    channels = root.findall("channel")
    for c in channels:
        for url in c.findall("url"):
            c.remove(url)

    # Clean programmes
    programmes = clean_programmes(root)

    # Remove all existing channels and programmes
    for elem in channels + root.findall("programme"):
        root.remove(elem)

    # Sort channels
    channels.sort(key=lambda c: alphanum_sort_key(c.attrib.get("id", "")))
    for c in channels:
        root.append(c)

    # Map channel ID to order
    channel_order = {c.attrib["id"]: i for i, c in enumerate(channels)}

    # Sort programmes
    programmes.sort(key=lambda p: (
        channel_order.get(p.attrib.get("channel", ""), 9999),
        p.attrib.get("start", "")
    ))
    for p in programmes:
        root.append(p)

    # Update header
    root.attrib.clear()
    root.set("date", now.strftime("%Y%m%d%H%M%S") + offset_str)
    root.set("generator-info-name", "EPG Generator (Senvora)")
    root.set("generator-info-url", "https://github.com/senvora/epg.git")

    # Save gzipped XML in same folder
    gz_path = file_path + ".gz"
    with gzip.open(gz_path, "wb") as f_out:
        f_out.write(pretty_xml(root))
    print(f"✅ Saved: {gz_path}")

# --- Process all XMLs in folder ---
for xml_file in glob.glob(os.path.join(folder, "*.xml")):
    process_xml(xml_file)
