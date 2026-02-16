#!/usr/bin/env bash
# Generate a lawn-mower grid mission file for aerial photogrammetry.
# Output: a JSON mission plan compatible with MAVSDK or QGroundControl.
#
# Usage:
#   plan_grid_mission.sh --lat 48.8584 --lon 2.2945 \
#     --width 60 --height 40 --altitude 25 --overlap 75 --speed 3 \
#     --output mission.plan

set -euo pipefail

# Defaults
LAT="" LON="" WIDTH="" HEIGHT=""
ALT=25 OVERLAP=75 SPEED=3 OUTPUT="mission.plan"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lat)      LAT="$2";     shift 2 ;;
    --lon)      LON="$2";     shift 2 ;;
    --width)    WIDTH="$2";   shift 2 ;;
    --height)   HEIGHT="$2";  shift 2 ;;
    --altitude) ALT="$2";     shift 2 ;;
    --overlap)  OVERLAP="$2"; shift 2 ;;
    --speed)    SPEED="$2";   shift 2 ;;
    --output)   OUTPUT="$2";  shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$LAT" || -z "$LON" || -z "$WIDTH" || -z "$HEIGHT" ]]; then
  echo "Usage: $0 --lat LAT --lon LON --width METERS --height METERS [--altitude M] [--overlap %] [--speed M/S] [--output FILE]" >&2
  exit 1
fi

python3 -c "
import json, math, sys

lat_start = $LAT
lon_start = $LON
width_m   = $WIDTH
height_m  = $HEIGHT
altitude  = $ALT
overlap   = $OVERLAP / 100.0
speed     = $SPEED

# Compute line spacing from overlap (assume ~80° FOV camera at given altitude)
fov_rad = math.radians(80)
ground_width = 2 * altitude * math.tan(fov_rad / 2)
spacing = ground_width * (1 - overlap)
rows = max(1, int(math.ceil(height_m / spacing)))

# Degree conversions
d_lat_per_m = 1.0 / 111320.0
d_lon_per_m = 1.0 / (111320.0 * math.cos(math.radians(lat_start)))

waypoints = []
for i in range(rows):
    lat = lat_start + i * spacing * d_lat_per_m
    if i % 2 == 0:
        lon_a = lon_start
        lon_b = lon_start + width_m * d_lon_per_m
    else:
        lon_a = lon_start + width_m * d_lon_per_m
        lon_b = lon_start

    waypoints.append({
        'lat': round(lat, 8),
        'lon': round(lon_a, 8),
        'alt': altitude,
        'speed': speed,
        'gimbal_pitch': -90,
        'camera': 'interval' if i == 0 else 'none'
    })
    waypoints.append({
        'lat': round(lat, 8),
        'lon': round(lon_b, 8),
        'alt': altitude,
        'speed': speed,
        'gimbal_pitch': -90,
        'camera': 'stop_interval' if i == rows - 1 else 'none'
    })

mission = {
    'version': 1,
    'type': 'grid',
    'origin': {'lat': lat_start, 'lon': lon_start},
    'params': {
        'width_m': width_m,
        'height_m': height_m,
        'altitude_m': altitude,
        'overlap_pct': overlap * 100,
        'speed_m_s': speed,
        'line_spacing_m': round(spacing, 2),
        'num_lines': rows,
        'total_waypoints': len(waypoints),
        'estimated_photos': int(sum(
            math.ceil(width_m / (ground_width * (1 - overlap))) for _ in range(rows)
        ))
    },
    'waypoints': waypoints
}

print(json.dumps(mission, indent=2))
" > "$OUTPUT"

echo "Mission plan written to $OUTPUT"
python3 -c "
import json
m = json.load(open('$OUTPUT'))
p = m['params']
print(f\"Grid: {p['num_lines']} lines, {p['total_waypoints']} waypoints\")
print(f\"Spacing: {p['line_spacing_m']}m, Est. photos: ~{p['estimated_photos']}\")
"
