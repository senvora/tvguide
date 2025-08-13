import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
import shutil
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

input_file = "epg.xml"
output_file = "epg.xml"
gzip_file = "epg.xml.gz"

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

# Loop through all programme elements
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

    # Keep only English titles if multiple exist
    titles = programme.findall("title")
    if len(titles) > 1:
        for t in titles:
            if t.attrib.get("lang") != "en":
                programme.remove(t)

    # Keep only English descriptions if multiple exist
    descs = programme.findall("desc")
    if len(descs) > 1:
        for d in descs:
            if d.attrib.get("lang") != "en":
                programme.remove(d)

    # Remove any other unwanted tags
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

# Remove ALL blank lines
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
