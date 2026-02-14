---
name: drone-mavlink
description: Pilot drones via MAVLink/MAVSDK — takeoff, waypoints, missions, camera triggers.
homepage: https://mavsdk.mavlink.io/main/en/
metadata:
  {
    "openclaw":
      {
        "emoji": "🛸",
        "requires": { "bins": ["python3"] },
        "install":
          [
            {
              "id": "pip-mavsdk",
              "kind": "shell",
              "command": "pip install mavsdk aioconsole",
              "bins": ["python3"],
              "label": "Install MAVSDK Python (pip)",
            },
            {
              "id": "apt-mavproxy",
              "kind": "shell",
              "command": "pip install MAVProxy",
              "bins": ["mavproxy.py"],
              "label": "Install MAVProxy (pip)",
            },
          ],
      },
  }
---

# Drone Piloting — MAVLink / MAVSDK

Control ArduPilot or PX4-based drones via MAVSDK (Python). Supports real hardware and SITL simulation.

## Connection

```bash
# SITL simulation (ArduPilot)
sim_vehicle.py -v ArduCopter --console --map

# SITL simulation (PX4)
make px4_sitl gazebo-classic

# MAVSDK connects via UDP by default
# Hardware: serial:///dev/ttyUSB0:57600
# SITL: udp://:14540
```

## Basic Flight (Python + MAVSDK)

```python
#!/usr/bin/env python3
"""Basic takeoff, hover, and land with MAVSDK."""
import asyncio
from mavsdk import System

async def run():
    drone = System()
    await drone.connect(system_address="udp://:14540")

    # Wait for connection
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Connected to drone")
            break

    # Wait for GPS fix
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("GPS fix acquired")
            break

    # Arm and takeoff
    await drone.action.arm()
    await drone.action.takeoff()
    await asyncio.sleep(10)

    # Land
    await drone.action.land()

asyncio.run(run())
```

## Telemetry

```python
async def print_telemetry(drone):
    # Position
    async for pos in drone.telemetry.position():
        print(f"Lat: {pos.latitude_deg}, Lon: {pos.longitude_deg}, Alt: {pos.relative_altitude_m}m")
        break

    # Battery
    async for batt in drone.telemetry.battery():
        print(f"Battery: {batt.remaining_percent * 100:.0f}%")
        break

    # Attitude (Euler angles)
    async for att in drone.telemetry.attitude_euler():
        print(f"Roll: {att.roll_deg:.1f}, Pitch: {att.pitch_deg:.1f}, Yaw: {att.yaw_deg:.1f}")
        break

    # GPS info
    async for gps in drone.telemetry.gps_info():
        print(f"Satellites: {gps.num_satellites}, Fix: {gps.fix_type}")
        break
```

## Waypoint Missions

```python
from mavsdk.mission import MissionItem, MissionPlan

async def run_mission(drone):
    mission_items = [
        MissionItem(lat, lon, alt, speed_m_s, is_fly_through,
                    gimbal_pitch_deg, gimbal_yaw_deg,
                    camera_action, loiter_time_s,
                    camera_photo_interval_s, acceptance_radius_m,
                    yaw_deg, camera_photo_distance_m)
    ]

    # Example: fly a rectangle for scanning
    mission_items = [
        MissionItem(47.3978, 8.5456, 25, 5, True, -90, 0,
                    MissionItem.CameraAction.START_PHOTO_INTERVAL, 0, 2, 1, 0, 0),
        MissionItem(47.3980, 8.5456, 25, 5, True, -90, 0,
                    MissionItem.CameraAction.NONE, 0, 2, 1, 0, 0),
        MissionItem(47.3980, 8.5460, 25, 5, True, -90, 0,
                    MissionItem.CameraAction.NONE, 0, 2, 1, 0, 0),
        MissionItem(47.3978, 8.5460, 25, 5, True, -90, 0,
                    MissionItem.CameraAction.STOP_PHOTO_INTERVAL, 0, 2, 1, 0, 0),
    ]

    mission_plan = MissionPlan(mission_items)
    await drone.mission.upload_mission(mission_plan)
    await drone.action.arm()
    await drone.mission.start_mission()
```

## Manual Control

```python
# Move to specific GPS position
await drone.action.goto_location(lat_deg, lon_deg, abs_alt_m, yaw_deg)

# Set flight speed
await drone.action.set_maximum_speed(10.0)  # m/s

# Return to launch
await drone.action.return_to_launch()

# Emergency kill (motors off immediately — use only in emergency)
await drone.action.kill()
```

## Camera & Gimbal

```python
# Point gimbal down for mapping
await drone.gimbal.set_pitch_and_yaw(-90, 0)

# Take a single photo
await drone.camera.take_photo()

# Start video recording
await drone.camera.start_video()
await asyncio.sleep(30)
await drone.camera.stop_video()

# Start interval photos (every 2 seconds)
await drone.camera.start_photo_interval(2.0)
```

## MAVProxy (CLI alternative)

```bash
# Connect to SITL
mavproxy.py --master=udp:127.0.0.1:14550

# Inside MAVProxy console:
# mode GUIDED
# arm throttle
# takeoff 10
# wp load mission.txt
# mode AUTO
# mode RTL
```

## Grid Scan Pattern (for LiDAR / Photogrammetry)

```python
def generate_grid_waypoints(lat_start, lon_start, width_m, height_m,
                             altitude_m, spacing_m, speed_m_s):
    """Generate a lawn-mower scan pattern for aerial mapping."""
    import math
    items = []
    rows = int(height_m / spacing_m)
    # ~1 degree lat ≈ 111320m, 1 degree lon ≈ 111320m * cos(lat)
    d_lat = spacing_m / 111320
    d_lon = width_m / (111320 * math.cos(math.radians(lat_start)))

    for i in range(rows):
        lat = lat_start + i * d_lat
        if i % 2 == 0:
            lon_a, lon_b = lon_start, lon_start + d_lon
        else:
            lon_a, lon_b = lon_start + d_lon, lon_start

        items.append(MissionItem(lat, lon_a, altitude_m, speed_m_s, True,
                                  -90, 0, MissionItem.CameraAction.NONE, 0, 2, 1, 0, 0))
        items.append(MissionItem(lat, lon_b, altitude_m, speed_m_s, True,
                                  -90, 0, MissionItem.CameraAction.NONE, 0, 2, 1, 0, 0))
    return items
```

## Safety

- **ALWAYS test in SITL simulation first** before running on real hardware.
- Check `drone.telemetry.health()` before arming — wait for GPS fix.
- Set geofence limits: `await drone.param.set_param_float("GF_MAX_HOR_DIST", 100)`.
- Monitor battery — set RTL (Return To Launch) at 30%.
- Comply with local drone regulations (altitude limits, no-fly zones, VLOS).
- Keep `await drone.action.return_to_launch()` or `kill()` ready.
