#!/usr/bin/env bash
# Generate a circular orbit mission for oblique facade capture.
#
# Usage:
#   plan_orbit_mission.sh --lat 48.8584 --lon 2.2945 \
#     --radius 30 --altitude 20 --gimbal-pitch -45 --points 24 \
#     --output orbit.plan

set -euo pipefail

LAT="" LON="" RADIUS=30 ALT=20 GIMBAL=-45 POINTS=24 OUTPUT="orbit.plan"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lat)          LAT="$2";     shift 2 ;;
    --lon)          LON="$2";     shift 2 ;;
    --radius)       RADIUS="$2";  shift 2 ;;
    --altitude)     ALT="$2";     shift 2 ;;
    --gimbal-pitch) GIMBAL="$2";  shift 2 ;;
    --points)       POINTS="$2";  shift 2 ;;
    --output)       OUTPUT="$2";  shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$LAT" || -z "$LON" ]]; then
  echo "Usage: $0 --lat LAT --lon LON [--radius M] [--altitude M] [--gimbal-pitch DEG] [--points N] [--output FILE]" >&2
  exit 1
fi

python3 -c "
import json, math

lat_center = $LAT
lon_center = $LON
radius_m   = $RADIUS
altitude   = $ALT
gimbal     = $GIMBAL
num_points = $POINTS

d_lat_per_m = 1.0 / 111320.0
d_lon_per_m = 1.0 / (111320.0 * math.cos(math.radians(lat_center)))

waypoints = []
for i in range(num_points):
    angle = 2 * math.pi * i / num_points
    dlat = radius_m * math.cos(angle) * d_lat_per_m
    dlon = radius_m * math.sin(angle) * d_lon_per_m
    # Yaw points toward center
    yaw = math.degrees(math.atan2(-math.sin(angle), -math.cos(angle)))
    yaw = (yaw + 360) % 360

    waypoints.append({
        'lat': round(lat_center + dlat, 8),
        'lon': round(lon_center + dlon, 8),
        'alt': altitude,
        'speed': 2,
        'gimbal_pitch': gimbal,
        'yaw': round(yaw, 1),
        'camera': 'photo'
    })

mission = {
    'version': 1,
    'type': 'orbit',
    'center': {'lat': lat_center, 'lon': lon_center},
    'params': {
        'radius_m': radius_m,
        'altitude_m': altitude,
        'gimbal_pitch_deg': gimbal,
        'num_points': num_points,
        'total_photos': num_points
    },
    'waypoints': waypoints
}

print(json.dumps(mission, indent=2))
" > "$OUTPUT"

echo "Orbit plan written to $OUTPUT ($POINTS waypoints, radius ${RADIUS}m)"
