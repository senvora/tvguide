import os
import gzip
import xml.etree.ElementTree as ET
import requests
import io
from datetime import datetime, timedelta, timezone

# --- Timezone definitions ---
IST = timezone(timedelta(hours=5, minutes=30))

# --- Output folder ---
output_dir = "epg"
os.makedirs(output_dir, exist_ok=True)


def beautify_element(element, level=0):
    """Recursively add indentation for memory-efficient XML."""
    indent = "\n" + ("  " * level)
    if len(element):
        if not element.text or not element.text.strip():
            element.text = indent + "  "
        for child in element:
            beautify_element(child, level + 1)
        if not element.tail or not element.tail.strip():
            element.tail = indent
    else:
        if level and (not element.tail or not element.tail.strip()):
            element.tail = indent


def normalize_channels_and_programmes(root, provider):
    """
    Update channel IDs based on display-name (lowercase, no spaces + suffix).
    Keep only <display-name> for channels.
    Keep only <title> + <desc> for programmes.
    """
    suffix = ".my" if provider == "astro" else ".in"
    id_map = {}

    # Clean and rename channels
    for channel in root.findall("channel"):
        old_id = channel.attrib.get("id", "")
        display_name_elem = channel.find("display-name")

        if display_name_elem is not None:
            name = (display_name_elem.text or "").strip()
            if name:
                new_id = name.lower().replace(" ", "") + suffix
                id_map[old_id] = new_id
                channel.set("id", new_id)

        # Keep only <display-name>
        for child in list(channel):
            if child.tag != "display-name":
                channel.remove(child)

    # Update programmes
    for prog in root.findall("programme"):
        old_ref = prog.attrib.get("channel", "")
        if old_ref in id_map:
            prog.set("channel", id_map[old_ref])

        # Keep only <title> + <desc>
        for child in list(prog):
            if child.tag not in ("title", "desc"):
                prog.remove(child)

    return id_map


def convert_programme_times(root):
    """Convert all programme start/stop times into IST (+0530), skip if already +0530."""
    for prog in root.findall("programme"):
        for attr in ("start", "stop"):
            val = prog.attrib.get(attr)
            if not val:
                continue
            try:
                if val.endswith("+0530"):  # already IST
                    continue
                dt = datetime.strptime(val, "%Y%m%d%H%M%S %z")
                dt_ist = dt.astimezone(IST)
                prog.attrib[attr] = dt_ist.strftime("%Y%m%d%H%M%S %z")
            except Exception:
                # Leave invalid as-is
                pass


def sort_elements(root):
    """
    Sort <channel> alphabetically,
    Sort <programme> by channel + start time.
    """
    channels = sorted(root.findall("channel"), key=lambda c: c.attrib.get("id", ""))

    def prog_sort_key(p):
        return (p.attrib.get("channel", ""), p.attrib.get("start", ""))

    programmes = sorted(root.findall("programme"), key=prog_sort_key)

    # Clear and re-append in sorted order
    for child in list(root):
        root.remove(child)
    for ch in channels:
        root.append(ch)
    for pr in programmes:
        root.append(pr)


def process_and_save(input_url, output_file, provider):
    """
    Download XML or XML.GZ, normalize, convert times, sort, beautify,
    and save as both .xml and .xml.gz.
    """
    try:
        print(f"Downloading: {input_url}")
        response = requests.get(input_url, stream=True, timeout=60)
        response.raise_for_status()

        # Detect gzipped content
        content_stream = io.BytesIO(response.content)
        is_gzipped = response.content[:2] == b'\x1f\x8b'

        if is_gzipped:
            xml_stream = gzip.open(content_stream, "rt", encoding="utf-8")
        else:
            xml_stream = io.StringIO(response.text)

        # Parse full XML
        tree = ET.parse(xml_stream)
        root = tree.getroot()

        # Normalize
        normalize_channels_and_programmes(root, provider)

        # Convert times
        convert_programme_times(root)

        # Sort & Beautify
        sort_elements(root)
        beautify_element(root)

        # Save plain XML
        xml_path = os.path.join(output_dir, output_file.replace(".gz", ""))
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(ET.tostring(root, encoding="unicode"))

        # Save gzipped XML
        gz_path = os.path.join(output_dir, output_file)
        with gzip.open(gz_path, "wt", encoding="utf-8") as gz_out:
            gz_out.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            gz_out.write(ET.tostring(root, encoding="unicode"))

        print(f"✅ Saved: {xml_path}, {gz_path}")

    except Exception as e:
        print(f"❌ Error processing {input_url}: {e}")


if __name__ == "__main__":
    all_jobs = [
        # (url, filename, provider)
        ("https://www.tsepg.cf/jio.xml.gz", "jiotv.xml.gz", "jiotv"),
        ("https://github.com/azimabid00/epg/raw/refs/heads/main/astro_epg.xml", "astro.xml.gz", "astro"),
        ("https://epgshare01.online/epgshare01/epg_ripper_IN1.xml.gz", "jio.xml.gz", "jio"),
    ]

    for url, filename, provider in all_jobs:
        process_and_save(url, filename, provider)
