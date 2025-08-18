import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
import shutil
from datetime import datetime, timedelta

input_file = "epg/dishtv.xml"
output_file = "epg/dishtv.xml"
gzip_file = "epg/dishtv.xml.gz"

# Helper: shift time 5:30 back
def shift_back_530(dt_str):
    try:
        dt = datetime.strptime(dt_str[:14], "%Y%m%d%H%M%S")
        shifted = dt - timedelta(hours=5, minutes=30)
        return shifted.strftime("%Y%m%d%H%M%S +0530")
    except ValueError:
        return dt_str

# Parse XML
tree = ET.parse(input_file)
root = tree.getroot()

# Convert <tv> date
if "date" in root.attrib:
    root.set("date", shift_back_530(root.attrib["date"]))

# Loop through all programme elements
for programme in root.findall("programme"):
    # Shift start/stop attributes 5:30 behind
    for attr in ("start", "stop"):
        if attr in programme.attrib:
            programme.set(attr, shift_back_530(programme.attrib[attr]))

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
