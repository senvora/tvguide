import os
import gzip
import xml.etree.ElementTree as ET
import requests
import io

# Output folder
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


def process_and_save(input_url, output_gz_file):
    """
    Stream XML or XML.GZ from URL, normalize programme attributes, 
    beautify, and save as gzipped XML.
    """
    try:
        print(f"Downloading: {input_url}")
        response = requests.get(input_url, stream=True, timeout=60)
        response.raise_for_status()

        # Detect gzipped content by magic bytes
        content_stream = io.BytesIO(response.content)
        is_gzipped = response.content[:2] == b'\x1f\x8b'

        if is_gzipped:
            xml_stream = gzip.open(content_stream, "rt", encoding="utf-8")
        else:
            xml_stream = io.StringIO(response.text)

        with gzip.open(output_gz_file, "wt", encoding="utf-8") as gz_out:
            gz_out.write('<?xml version="1.0" encoding="UTF-8"?>\n<tv>')

            for event, elem in ET.iterparse(xml_stream, events=("end",)):
                if elem.tag == "programme":
                    # Normalize attributes order: start-stop-channel
                    attrs = elem.attrib
                    ordered_attrs = {k: attrs[k] for k in ("start", "stop", "channel") if k in attrs}
                    for k, v in attrs.items():
                        if k not in ordered_attrs:
                            ordered_attrs[k] = v
                    elem.attrib.clear()
                    elem.attrib.update(ordered_attrs)

                    beautify_element(elem, level=1)
                    gz_out.write(ET.tostring(elem, encoding="unicode"))
                    elem.clear()

                elif elem.tag == "channel":
                    beautify_element(elem, level=1)
                    gz_out.write(ET.tostring(elem, encoding="unicode"))
                    elem.clear()

            gz_out.write("\n</tv>")

        print(f"Saved gzipped beautified XML: {output_gz_file}")

    except Exception as e:
        print(f"Error processing {input_url}: {e}")


if __name__ == "__main__":
    all_jobs = [
        ("https://gitlab.com/anbuchelva/epg/-/raw/main/epg.xml.gz?ref_type=heads&inline=false", "jiotv.xml.gz"),
        ("https://github.com/azimabid00/epg/raw/refs/heads/main/astro_epg.xml", "astro.xml.gz")
    ]

    for url, filename in all_jobs:
        output_path = os.path.join(output_dir, filename)
        process_and_save(url, output_path)
