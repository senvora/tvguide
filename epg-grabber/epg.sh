#!/bin/bash
set -e

# Ensure the epg directory exists in the repository workspace
mkdir -p "$GITHUB_WORKSPACE/epg"

# Run the PHP grabber (inside epg-grabber folder)
php ./epg-grabber/tempest.php --epg config=./epg-grabber/tempest.config.xml inv

# Remove unnecessary XML with details
rm -f ./epg-grabber/tempest_config/epg/epg_with_details.xml

# Get today's and tomorrow's dates in IST (Indian Standard Time)
TODAY=$(TZ=Asia/Kolkata date -d '00:00' +%Y%m%d)
TOMORROW=$(TZ=Asia/Kolkata date -d '00:00 +1 day' +%Y%m%d)

echo "📅 IST Today: $TODAY"
echo "📅 IST Tomorrow: $TOMORROW"

# Filter programmes:
# Keep only if start OR stop falls on today/tomorrow (IST).
# Original @start/@stop values remain unchanged.
xmlstarlet ed -d "//programme[
  not(
    (substring(@start, 1, 8) >= '${TODAY}' and substring(@start, 1, 8) <= '${TOMORROW}')
    or
    (substring(@stop, 1, 8) >= '${TODAY}' and substring(@stop, 1, 8) <= '${TOMORROW}')
  )
]" ./epg-grabber/tempest_config/epg/epg.xml > ./epg-grabber/epg.xml

# Check if the filtered file exists and compress it
if [ -f ./epg-grabber/epg.xml ]; then
  gzip -c ./epg-grabber/epg.xml > "$GITHUB_WORKSPACE/epg/tempest.xml.gz"

  # Cleanup
  rm -f ./epg-grabber/tempest_config/epg/epg.xml
  rm -f ./epg-grabber/epg.xml

  echo "✅ Script execution completed. Final file: epg/tempest.xml.gz"
else
  echo "❌ Filtered EPG file not found. Script terminated."
  exit 1
fi
