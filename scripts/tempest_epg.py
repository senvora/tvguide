import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

input_file = "epg-grabber/tempest_config/epg/tataplay.xml"
gzip_file = "epg/tataplay.xml.gz"

# --- Parse XML ---
tree = ET.parse(input_file)
root = tree.getroot()

# --- Time range: today & tomorrow (IST) ---
now_ist = datetime.now(IST)
start_of_today = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
end_of_tomorrow = start_of_today + timedelta(days=2)

print("⏰ Current IST time:", now_ist.strftime("%Y-%m-%d %H:%M:%S %z"))
print("📅 Filtering range (IST):", start_of_today, "→", end_of_tomorrow)

# --- Collect programmes ---
programmes = []
for programme in root.findall("programme"):
    try:
        start_raw = programme.attrib.get("start", "")
        stop_raw = programme.attrib.get("stop", "")

        # Parse datetimes directly (they already include +0530)
        start_dt = datetime.strptime(start_raw[:14], "%Y%m%d%H%M%S").replace(tzinfo=IST)
        stop_dt = datetime.strptime(stop_raw[:14], "%Y%m%d%H%M%S").replace(tzinfo=IST)
    except Exception:
        continue

    # Keep only if programme falls in today/tomorrow range
    if stop_dt < start_of_today or start_dt >= end_of_tomorrow:
        continue

    # Normalize format
    programme.set("start", start_dt.strftime("%Y%m%d%H%M%S +0530"))
    programme.set("stop", stop_dt.strftime("%Y%m%d%H%M%S +0530"))

    # Keep only title & desc
    for child in list(programme):
        if child.tag not in ("title", "desc"):
            programme.remove(child)

    programmes.append(programme)

# --- Collect channels ---
channels = root.findall("channel")

# --- Remove old channels and programmes ---
for elem in channels + root.findall("programme"):
    root.remove(elem)

# --- Sort channels alphabetically ---
def channel_key(c):
    name_elem = c.find("display-name")
    if name_elem is not None and name_elem.text:
        return name_elem.text.lower()
    return c.attrib.get("id", "").lower()

channels.sort(key=channel_key)

for c in channels:
    root.append(c)

# --- Sort programmes by channel then start ---
def programme_key(p):
    return (p.attrib.get("channel", "").lower(), p.attrib.get("start", ""))

programmes.sort(key=programme_key)

for p in programmes:
    root.append(p)

# --- Pretty print XML ---
xml_str = ET.tostring(root, encoding="utf-8")
parsed = minidom.parseString(xml_str)
pretty_xml_as_str = parsed.toprettyxml(indent="  ", encoding="utf-8")

# Remove blank lines
pretty_xml_as_str = b"\n".join(
    line for line in pretty_xml_as_str.splitlines() if line.strip()
)

# --- Save only gzipped version ---
with gzip.open(gzip_file, "wb") as f_out:
    f_out.write(pretty_xml_as_str)

print(f"✅ Cleaned EPG (today+tomorrow IST only) saved to {gzip_file}")
