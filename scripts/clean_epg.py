import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta, time, timezone
import gzip
import shutil

# Timezone offsets
IST = timezone(timedelta(hours=5, minutes=30))  # IST +05:30
UTC = timezone.utc

input_file = "epg.xml"
output_file = "epg.xml"
gzip_file = "epg.xml.gz"

# Get current IST date range
now_ist = datetime.now(IST)
today_ist = datetime.combine(now_ist.date(), time.min, tzinfo=IST)  # 00:00 IST today
tomorrow_ist = today_ist + timedelta(days=2)  # up to tomorrow midnight IST

# Convert to UTC for filtering
start_utc = today_ist.astimezone(UTC)
end_utc = tomorrow_ist.astimezone(UTC)

# Parse XML
tree = ET.parse(input_file)
root = tree.getroot()

# Force <tv> date to today's 00:00 IST
root.set("date", today_ist.strftime("%Y%m%d%H%M%S +0530"))

# Loop through all programme elements
for programme in list(root.findall('programme')):
    start_str = programme.attrib.get("start", "")[:14]
    stop_str = programme.attrib.get("stop", "")[:14]

    try:
        start_dt_utc = datetime.strptime(start_str, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        stop_dt_utc = datetime.strptime(stop_str, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    except ValueError:
        root.remove(programme)
        continue

    # Filter by IST date range (converted to UTC)
    if stop_dt_utc <= start_utc or start_dt_utc >= end_utc:
        root.remove(programme)
        continue

    # Convert start/stop to IST in XML
    start_dt_ist = start_dt_utc.astimezone(IST)
    stop_dt_ist = stop_dt_utc.astimezone(IST)
    programme.set("start", start_dt_ist.strftime("%Y%m%d%H%M%S +0530"))
    programme.set("stop", stop_dt_ist.strftime("%Y%m%d%H%M%S +0530"))

    # Keep only English titles if multiple exist
    titles = programme.findall('title')
    if len(titles) > 1:
        for t in titles:
            if t.attrib.get('lang') != 'en':
                programme.remove(t)

    # Keep only English descriptions if multiple exist
    descs = programme.findall('desc')
    if len(descs) > 1:
        for d in descs:
            if d.attrib.get('lang') != 'en':
                programme.remove(d)

    # Remove unwanted tags
    for child in list(programme):
        if child.tag not in ("title", "desc"):
            programme.remove(child)

    # Remove empty title/desc
    for tag in ("title", "desc"):
        element = programme.find(tag)
        if element is not None and (element.text is None or element.text.strip() == ""):
            programme.remove(element)

# Pretty print XML with indentation
xml_str = ET.tostring(root, encoding="utf-8")
parsed = minidom.parseString(xml_str)
pretty_xml_as_str = parsed.toprettyxml(indent="  ", encoding="utf-8")

# Remove all blank lines
pretty_xml_as_str = b"\n".join(
    line for line in pretty_xml_as_str.splitlines() if line.strip()
)

# Save cleaned XML
with open(output_file, "wb") as f:
    f.write(pretty_xml_as_str)

# Create gzipped version
with open(output_file, "rb") as f_in:
    with gzip.open(gzip_file, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

print(f"Cleaned EPG saved to {output_file} and {gzip_file}")
