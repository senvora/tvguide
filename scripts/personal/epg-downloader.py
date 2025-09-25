import os
import gzip
import xml.etree.ElementTree as ET
import requests
import io
from datetime import datetime, timedelta, timezone
import re
from xml.dom import minidom

# --- Timezone ---
IST = timezone(timedelta(hours=5, minutes=30))

# --- Output folder ---
output_dir = "guide"
os.makedirs(output_dir, exist_ok=True)

# --- Helpers ---
def parse_time(ts: str):
    """Parse EPG timestamps and return datetime with timezone."""
    if len(ts) >= 14:
        return datetime.strptime(ts[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    raise ValueError(f"Invalid timestamp: {ts}")

def convert_and_filter_programmes(root):
    """Convert times to IST and filter programmes to today + tomorrow."""
    now = datetime.now(IST)
    start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_day = start_day + timedelta(days=2)

    keep_progs = []
    for prog in root.findall("programme"):
        try:
            start = parse_time(prog.attrib["start"]).astimezone(IST)
            stop = parse_time(prog.attrib["stop"]).astimezone(IST)

            # Convert attrs to IST +0530
            prog.attrib["start"] = start.strftime("%Y%m%d%H%M%S %z")
            prog.attrib["stop"] = stop.strftime("%Y%m%d%H%M%S %z")

            # Remove catchup attributes
            if "catchup-id" in prog.attrib:
                del prog.attrib["catchup-id"]

            # Keep if any overlap with [today, tomorrow]
            if stop > start_day and start < end_day:
                for tag in ("title", "sub-title", "desc"):
                    elements = prog.findall(tag)
                    en_elements = [e for e in elements if e.attrib.get("lang") == "en" and e.text and e.text.strip()]
                    if en_elements:
                        for e in elements:
                            if e not in en_elements:
                                prog.remove(e)
                    else:
                        for e in elements:
                            if not e.text or not e.text.strip():
                                prog.remove(e)

                for child in list(prog):
                    if child.tag not in ("title", "sub-title", "desc"):
                        prog.remove(child)

                if prog.findall("title") or prog.findall("sub-title") or prog.findall("desc"):
                    keep_progs.append(prog)
        except Exception as e:
            print("⚠️ Time parse failed:", prog.attrib.get("start"), e)
            continue

    for prog in list(root.findall("programme")):
        root.remove(prog)
    for prog in keep_progs:
        root.append(prog)

    root.set("date", now.strftime("%Y%m%d%H%M%S %z"))
    root.set("generator-info-name", "EPG Generator (Senvora)")
    root.set("generator-info-url", "https://github.com/senvora/epg.git")

def strip_jio_prefix_and_sort(root):
    """Strip 'jio-' prefix, remove <url>/<icon>, and sort channels + programmes."""
    id_map = {}
    for ch in root.findall("channel"):
        old_id = ch.attrib.get("id", "")
        new_id = old_id[4:] if old_id.startswith("jio-") else old_id
        ch.set("id", new_id)
        id_map[old_id] = new_id

        for url in ch.findall("url"):
            ch.remove(url)
        for icon in ch.findall("icon"):
            ch.remove(icon)

    for prog in root.findall("programme"):
        old_ref = prog.attrib.get("channel", "")
        if old_ref in id_map:
            prog.set("channel", id_map[old_ref])

    def channel_key(c):
        cid = c.attrib.get("id", "")
        try:
            return int(re.findall(r'\d+', cid)[0])
        except:
            return float("inf")

    channels_sorted = sorted(root.findall("channel"), key=channel_key)
    channel_order = {c.attrib["id"]: i for i, c in enumerate(channels_sorted)}

    programmes_sorted = sorted(
        root.findall("programme"),
        key=lambda p: (channel_order.get(p.attrib.get("channel", ""), 9999), p.attrib.get("start", ""))
    )

    for elem in list(root):
        root.remove(elem)
    for c in channels_sorted:
        root.append(c)
    for p in programmes_sorted:
        root.append(p)

def process_and_save(input_url, output_file):
    """Download XML/XML.GZ, clean up, filter, sort, and save gzipped pretty XML."""
    try:
        print(f"Downloading: {input_url}")
        response = requests.get(input_url, stream=True, timeout=60)
        response.raise_for_status()

        content_stream = io.BytesIO(response.content)
        is_gzipped = response.content[:2] == b"\x1f\x8b"

        if is_gzipped:
            xml_stream = gzip.open(content_stream, "rt", encoding="utf-8")
        else:
            xml_stream = io.StringIO(response.text)

        tree = ET.parse(xml_stream)
        root = tree.getroot()

        convert_and_filter_programmes(root)
        strip_jio_prefix_and_sort(root)

        xml_str = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(xml_str)
        pretty_xml_as_str = parsed.toprettyxml(indent="  ", encoding="utf-8")
        pretty_xml_as_str = b"\n".join(line for line in pretty_xml_as_str.splitlines() if line.strip())

        # --- Save deterministic gzip using GzipFile ---
        gz_path = os.path.join(output_dir, output_file)
        with open(gz_path, "wb") as gz_out_raw:
            with gzip.GzipFile(fileobj=gz_out_raw, mode="wb", mtime=0) as gz_out:
                gz_out.write(pretty_xml_as_str)

        print(f"✅ Saved deterministically: {gz_path}")

    except Exception as e:
        print(f"❌ Error processing {input_url}: {e}")

if __name__ == "__main__":
    input_url = os.environ.get("JIO_EPG_URL")
    if not input_url:
        raise ValueError("❌ Environment variable JIO_EPG_URL is not set")

    all_jobs = [
        (input_url, "jiotv.xml.gz"),
    ]

    for url, filename in all_jobs:
        process_and_save(url, filename)
