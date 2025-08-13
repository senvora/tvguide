import xml.etree.ElementTree as ET
from xml.dom import minidom
import gzip
import shutil

input_file = "epg.xml"
output_file = "epg.xml"
gzip_file = "epg.xml.gz"

# Parse XML
tree = ET.parse(input_file)
root = tree.getroot()

# Loop through all programme elements
for programme in root.findall('programme'):
    for child in list(programme):
        if child.tag not in ("title", "desc"):
            programme.remove(child)

    # Remove empty title/desc
    for tag in ("title", "desc"):
        element = programme.find(tag)
        if element is not None and (element.text is None or element.text.strip() == ""):
            programme.remove(element)

# Pretty print XML (with line breaks and indentation)
xml_str = ET.tostring(root, encoding="utf-8")
parsed = minidom.parseString(xml_str)
pretty_xml_as_str = parsed.toprettyxml(indent="  ", encoding="utf-8")

# Save readable XML
with open(output_file, "wb") as f:
    f.write(pretty_xml_as_str)

# Create gzipped version
with open(output_file, "rb") as f_in:
    with gzip.open(gzip_file, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

print(f"Cleaned EPG saved to {output_file} and {gzip_file}")
