import os
import gzip
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString
import requests
from datetime import datetime, timedelta, timezone
import io

# Define paths
output_dir = os.path.join('public', 'epg')
os.makedirs(output_dir, exist_ok=True)

output_file_gz = os.path.join(output_dir, 'epgshare.xml.gz')  # Save in the 'epg/' directory
tvg_ids_file = os.path.join(os.path.dirname(__file__), 'epgshare-tvg-ids.txt')

def download_file(url, save_path):
    """Download a file from a URL and save it to a specified path."""
    try:
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            raise Exception(f"Failed to download file from {url}. HTTP Status Code: {response.status_code}")
        
        with open(save_path, "wb") as file:
            file.write(response.content)
        print(f"File downloaded successfully from {url} to '{save_path}'")
    except Exception as e:
        print(f"An error occurred while downloading the file: {e}")


def organize_and_save_xml_gz(input_url, output_gz_file):
    """Download, organize, and save an XML file compressed in .gz format."""
    try:
        response = requests.get(input_url, stream=True)
        if response.status_code != 200:
            raise Exception(f"Failed to download file. HTTP Status Code: {response.status_code}")

        with gzip.open(io.BytesIO(response.content), "rt", encoding="utf-8") as gz_file:
            uncompressed_data = gz_file.read()

        root = ET.fromstring(uncompressed_data)

        for programme in root.findall(".//programme"):
            channel = programme.attrib.get("channel")
            start = programme.attrib.get("start")
            stop = programme.attrib.get("stop")

            if channel is not None:
                programme.attrib = {"start": start, "stop": stop, "channel": channel}

        rough_string = ET.tostring(root, encoding="utf-8", method="xml")
        pretty_xml = parseString(rough_string).toprettyxml(indent="  ")

        cleaned_xml = "\n".join([line for line in pretty_xml.splitlines() if line.strip()])

        with gzip.open(output_gz_file, "wt", encoding="utf-8") as gz_file:
            gz_file.write(cleaned_xml)

        print(f"Organized XML has been saved to '{output_gz_file}' successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")


def fetch_and_extract_xml(url):
    """Fetch and extract XML from a URL."""
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch {url}")
            return None

        if url.endswith('.gz'):
            decompressed_data = gzip.decompress(response.content)
            return ET.fromstring(decompressed_data)
        else:
            return ET.fromstring(response.content)
    except Exception as e:
        print(f"Failed to parse XML from {url}: {e}")
        return None


def convert_to_utc(time_str, original_offset):
    # Extract the original time with the timezone
    original_time = datetime.strptime(time_str[:-6], '%Y%m%d%H%M%S').replace(tzinfo=timezone(
        timedelta(hours=int(original_offset[:3]), minutes=int(original_offset[0] + original_offset[3:]))))
    
    # Convert to UTC
    utc_time = original_time.astimezone(tz=timezone.utc)
    return utc_time.strftime('%Y%m%d%H%M%S')  # Return time in UTC without offset


def filter_and_build_epg(urls):
    """Filter EPG data based on valid tvg-ids and convert times to UTC."""
    with open(tvg_ids_file, 'r', encoding='utf-8') as file:
        valid_tvg_ids = set(line.strip() for line in file)

    root = ET.Element('tv')

    for url in urls:
        epg_data = fetch_and_extract_xml(url)
        if epg_data is None:
            continue

        for channel in epg_data.findall('channel'):
            tvg_id = channel.get('id')
            if tvg_id in valid_tvg_ids:
                root.append(channel)

        for programme in epg_data.findall('programme'):
            tvg_id = programme.get('channel')
            if tvg_id in valid_tvg_ids:
                start_time = programme.get('start')
                stop_time = programme.get('stop')
                original_offset_start = start_time[-5:]
                original_offset_stop = stop_time[-5:]

                programme.set('start', convert_to_utc(start_time, original_offset_start) + ' +0000')
                programme.set('stop', convert_to_utc(stop_time, original_offset_stop) + ' +0000')

                root.append(programme)

    # Saving the EPG file in gzip format
    with gzip.open(output_file_gz, 'wb') as f:
        tree = ET.ElementTree(root)
        tree.write(f, encoding='utf-8', xml_declaration=True)
    print(f"Compressed EPG with UTC times saved to {output_file_gz}")


# URLs to fetch EPG data
urls = [
    'https://epgshare01.online/epgshare01/epg_ripper_NZ1.xml.gz',
]

if __name__ == "__main__":
    # Example file handling
    organize_url = "http://tsepg.cf/jio.xml.gz"
    output_gz_path = os.path.join(output_dir, "jiotv.xml.gz")
    organize_and_save_xml_gz(organize_url, output_gz_path)
    
    # Filter and build the EPG
    filter_and_build_epg(urls)
