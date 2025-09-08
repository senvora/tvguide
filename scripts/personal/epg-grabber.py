import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
from datetime import datetime, timedelta
import os
import re

# --- Paths ---
folder = "guide/"
xml_file = os.path.join(folder, "guide.xml")
gz_file = os.path.join(folder, "guide.xml.gz")

# --- Time setup ---
now = datetime.now()
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
three_days_end = today_start + timedelta(days=3) - timedelta(seconds=1)
offset = " +0530"

print("🕒 Current runtime:", now.strftime("%Y-%m-%d %H:%M:%S") + offset)

# --- Helpers ---
def alphanum_sort_key(cid):
    m = re.match(r'([a-zA-Z]+)?(\d+)?', cid)
    prefix, number = (m.group(1) or '', int(m.group(2)) if m.group(2) else float('inf')) if m else (cid, float('inf'))
    return (prefix.lower(), number)

def pretty_xml(root):
    xml_str = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(xml_str)
    return b"\n".join(line for line in parsed.toprettyxml(indent="  ", encoding="utf-8").splitlines() if line.strip())

def clean_xml(path):
    """Read raw XML, strip problematic characters, return new path."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        data = f.read()

    # Fix bare ampersands
    data = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;)', '&amp;', data)

    # Remove ASCII control chars (except \t \n \r)
    data = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', data)

    cleaned_path = path + ".cleaned"
    with open(cleaned_path, "w", encoding="utf-8") as f:
        f.write(data)

    return cleaned_path

def clean_programmes(root):
    cleaned = []
    for p in root.findall("programme"):
        try:
            start_dt = datetime.strptime(p.attrib["start"][:14], "%Y%m%d%H%M%S")
            stop_dt = datetime.strptime(p.attrib["stop"][:14], "%Y%m%d%H%M%S")
        except (KeyError, ValueError):
            continue
        if stop_dt < today_start or start_dt > three_days_end:
            continue
        p.set("start", start_dt.strftime("%Y%m%d%H%M%S") + offset)
        p.set("stop", stop_dt.strftime("%Y%m%d%H%M%S") + offset)

        # Keep only title + desc
        for tag in ("title", "desc"):
            elems = p.findall(tag)
            if elems:
                eng = [e for e in elems if e.attrib.get("lang")=="en"] or [elems[0]]
                for e in elems:
                    if e not in eng:
                        p.remove(e)
                for e in eng:
                    if not e.text or not e.text.strip():
                        p.remove(e)

        # Remove other children
        for child in list(p):
            if child.tag not in ("title","desc"):
                p.remove(child)
        if p.find("title") or p.find("desc"):
            cleaned.append(p)
    return cleaned

# --- Main processing ---
def process_xml(path):
    print(f"Processing: {path}")
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        print(f"⚠️ Parse error in {path}, attempting clean...")
        cleaned_path = clean_xml(path)
        tree = ET.parse(cleaned_path)

    root = tree.getroot()

    channels = root.findall("channel")
    for c in channels:
        for url in c.findall("url"):
            c.remove(url)

    programmes = clean_programmes(root)

    # Clear existing
    for e in channels + root.findall("programme"):
        root.remove(e)

    channels.sort(key=lambda c: alphanum_sort_key(c.attrib.get("id","")))
    for c in channels: 
        root.append(c)

    order = {c.attrib["id"]: i for i,c in enumerate(channels)}
    programmes.sort(key=lambda p: (order.get(p.attrib.get("channel",""),9999), p.attrib.get("start","")))
    for p in programmes: 
        root.append(p)

    root.attrib.clear()
    root.set("date", now.strftime("%Y%m%d%H%M%S") + offset)
    root.set("generator-info-name","EPG Generator (Senvora)")
    root.set("generator-info-url","https://github.com/senvora/epg.git")

    with gzip.open(gz_file,"wb") as f:
        f.write(pretty_xml(root))
    print(f"✅ Saved: {gz_file}")

# --- Execute ---
if os.path.exists(xml_file):
    process_xml(xml_file)
else:
    print(f"❌ File not found: {xml_file}")
