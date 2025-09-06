#!/usr/bin/env python3
import os
import xml.etree.ElementTree as ET
import gzip
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import re

INPUT_FOLDER = "guide"
OUTPUT_FILE = "guide/epg.xml.gz"

# Use IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

GENERATOR_INFO_NAME = "EPG Generator (Senvora)"
GENERATOR_INFO_URL = "https://github.com/senvora/epg.git"

def indent(elem, level=0):
    """Pretty-print XML tree with indentation."""
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            indent(child, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if not elem.tail or not elem.tail.strip():
            elem.tail = i

def merge_epg(xml_files):
    """Merge all XMLs: channels first, then programmes, overwrite tv date and generator-info."""
    root = ET.Element("tv")

    # fresh attributes
    now = datetime.now(IST).strftime("%Y%m%d%H%M%S")
    root.set("date", now)
    root.set("generator-info-name", GENERATOR_INFO_NAME)
    root.set("generator-info-url", GENERATOR_INFO_URL)

    channels, programmes = [], []

    for file_path in xml_files:
        try:
            tree = ET.parse(file_path)
            subroot = tree.getroot()

            for elem in subroot:
                if elem.tag == "channel":
                    channels.append(elem)
                elif elem.tag == "programme":
                    programmes.append(elem)

        except Exception as e:
            print(f"Skipping {file_path}, error: {e}")

    for ch in channels:
        root.append(ch)
    for pr in programmes:
        root.append(pr)

    return ET.ElementTree(root)

def write_tree_with_newline(tree, output_file):
    """Write XML ensuring newline after <tv ...> and pretty-print children."""
    # Pretty-print children first
    indent(tree.getroot())

    # Get raw string
    xml_bytes = ET.tostring(tree.getroot(), encoding="utf-8")
    xml_str = xml_bytes.decode("utf-8")

    # Insert XML declaration
    xml_str = '<?xml version="1.0" encoding="utf-8"?>\n' + xml_str

    # Force newline right after the opening <tv ...> tag
    xml_str = re.sub(r'(<tv[^>]*>)', r'\1\n', xml_str, count=1)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(xml_str)

def main():
    # collect only *.xml.gz, but ignore the output file if it already exists
    gz_files = [
        p for p in Path(INPUT_FOLDER).glob("*.xml.gz")
        if p.name != Path(OUTPUT_FILE).name
    ]

    if not gz_files:
        print("⚠️ No XML.GZ files found in guide/, skipping merge.")
        return

    xml_files = []

    # decompress each .gz into a temp .xml
    for f in gz_files:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xml")
        with gzip.open(f, "rb") as gz_in, open(tmp.name, "wb") as out:
            shutil.copyfileobj(gz_in, out)
        xml_files.append(tmp.name)

    print(f"Merging {len(xml_files)} compressed EPG files...")

    tree = merge_epg(xml_files)

    # write merged XML with pretty-print and newline after <tv ...>
    temp_output = OUTPUT_FILE.replace(".gz", "")
    write_tree_with_newline(tree, temp_output)

    # compress into final .gz
    with open(temp_output, "rb") as src, gzip.open(OUTPUT_FILE, "wb") as dst:
        shutil.copyfileobj(src, dst)

    os.remove(temp_output)
    print(f"✅ Created merged {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
