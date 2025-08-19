import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
import shutil
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

input_file = "epg/senvora.xml"
output_file = "epg/senvora.xml"
gzip_file = "epg/senvora.xml.gz"

# Parse XML
tree = ET.parse(input_file)
root = tree.getroot()

# Convert <tv> date to IST if present
if "date" in root.attrib:
    date_str = root.attrib["date"][:14]
    try:
        dt_utc = datetime.strptime(date_str, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        dt_ist = dt_utc.astimezone(IST)
        root.set("date", dt_ist.strftime("%Y%m%d%H%M%S +0530"))
    except ValueError:
        pass

# Collect all programmes
programmes = []
for programme in root.findall("programme"):
    # Convert start/stop attributes to IST
    for attr in ("start", "stop"):
        if attr in programme.attrib:
            dt_str = programme.attrib[attr][:14]
            try:
                dt_utc = datetime.strptime(dt_str, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
                dt_ist = dt_utc.astimezone(IST)
                programme.set(attr, dt_ist.strftime("%Y%m%d%H%M%S +0530"))
            except ValueError:
                continue

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

    # Remove unwanted tags
    for child in list(programme):
        if child.tag not in ("title", "desc"):
            programme.remove(child)

    # Remove empty title/desc
    for tag in ("title", "desc"):
        element = programme.find(tag)
        if element is not None and (element.text is None or element.text.strip() == ""):
            programme.remove(element)

    programmes.append(programme)

# Remove old programmes
for p in root.findall("programme"):
    root.remove(p)

# Sort programmes by channel + start time
def sort_key(p):
    channel = p.attrib.get("channel", "").lower()
    start = p.attrib.get("start", "")
    return (channel, start)

programmes.sort(key=sort_key)

# Re-attach in sorted order
for p in programmes:
    root.append(p)

# Pretty print XML with indentation
xml_str = ET.tostring(root, encoding="utf-8")
parsed = minidom.parseString(xml_str)
pretty_xml_as_str = parsed.toprettyxml(indent="  ", encoding="utf-8")

# Remove blank lines
pretty_xml_as_str = b"\n".join(
    line for line in pretty_xml_as_str.splitlines() if line.strip()
)

# Save cleaned XML
with open(output_file, "wb") as f:
    f.write(pretty_xml_as_str)

# Save gzipped version
with open(output_file, "rb") as f_in:
    with gzip.open(gzip_file, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

print(f"Cleaned + sorted EPG saved to {output_file} and {gzip_file}")
