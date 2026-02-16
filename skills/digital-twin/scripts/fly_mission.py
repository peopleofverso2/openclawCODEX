#!/usr/bin/env python3
"""
Execute a mission plan file (from plan_grid_mission.sh or plan_orbit_mission.sh)
on a real or simulated drone via MAVSDK.

Usage:
    python3 fly_mission.py --plan mission.plan [--connection udp://:14540] [--dry-run]
"""

import argparse
import asyncio
import json
import sys


async def run(plan_path: str, connection: str, dry_run: bool):
    with open(plan_path) as f:
        plan = json.load(f)

    waypoints = plan["waypoints"]
    params = plan["params"]
    print(f"Mission: {plan['type']}, {len(waypoints)} waypoints")
    print(f"Params: {json.dumps(params, indent=2)}")

    if dry_run:
        print("\n[DRY RUN] Waypoints:")
        for i, wp in enumerate(waypoints):
            print(f"  {i+1}. lat={wp['lat']}, lon={wp['lon']}, alt={wp['alt']}m")
        print("\n[DRY RUN] No drone connection made.")
        return

    try:
        from mavsdk import System
        from mavsdk.mission import MissionItem, MissionPlan
    except ImportError:
        print("ERROR: mavsdk not installed. Run: pip install mavsdk", file=sys.stderr)
        sys.exit(1)

    drone = System()
    await drone.connect(system_address=connection)

    print("Waiting for drone connection...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Connected.")
            break

    print("Waiting for GPS fix...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("GPS fix OK.")
            break

    # Build mission items
    camera_action_map = {
        "interval": MissionItem.CameraAction.START_PHOTO_INTERVAL,
        "stop_interval": MissionItem.CameraAction.STOP_PHOTO_INTERVAL,
        "photo": MissionItem.CameraAction.TAKE_PHOTO,
        "none": MissionItem.CameraAction.NONE,
    }

    mission_items = []
    for wp in waypoints:
        cam = camera_action_map.get(wp.get("camera", "none"),
                                     MissionItem.CameraAction.NONE)
        item = MissionItem(
            wp["lat"],
            wp["lon"],
            wp["alt"],
            wp.get("speed", 3),
            True,  # fly-through
            wp.get("gimbal_pitch", -90),
            wp.get("yaw", 0),
            cam,
            0,   # loiter_time
            2,   # photo_interval_s
            1,   # acceptance_radius
            wp.get("yaw", 0),
            0,   # camera_photo_distance
        )
        mission_items.append(item)

    mission_plan = MissionPlan(mission_items)

    print("Uploading mission...")
    await drone.mission.upload_mission(mission_plan)

    print("Arming...")
    await drone.action.arm()

    print("Starting mission...")
    await drone.mission.start_mission()

    # Monitor progress
    async for progress in drone.mission.mission_progress():
        print(f"  Waypoint {progress.current}/{progress.total}")
        if progress.current == progress.total:
            print("Mission complete.")
            break

    print("Returning to launch...")
    await drone.action.return_to_launch()


def main():
    parser = argparse.ArgumentParser(description="Fly a mission plan via MAVSDK")
    parser.add_argument("--plan", required=True, help="Path to mission .plan JSON file")
    parser.add_argument("--connection", default="udp://:14540",
                        help="MAVSDK connection string (default: udp://:14540)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print waypoints without connecting to drone")
    args = parser.parse_args()
    asyncio.run(run(args.plan, args.connection, args.dry_run))


if __name__ == "__main__":
    main()
