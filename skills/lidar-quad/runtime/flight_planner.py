#!/usr/bin/env python3
"""
flight_planner.py — LiDAR flight plan calculator
No dependencies (stdlib only). Run directly:

    python3 flight_planner.py
    python3 flight_planner.py livox-mid360 50 8 200 150
    python3 flight_planner.py --json livox-mid360 50 8 200 150
"""

import math
import json
import sys
from dataclasses import dataclass

# ─── LiDAR Sensor Profiles ─────────────────────────────

SENSORS = {
    "livox-mid360": {
        "name": "Livox Mid-360",
        "fov_h": 360,
        "fov_v_min": -7,
        "fov_v_max": 52,
        "max_range": 70,
        "points_per_sec": 200_000,
        "weight_g": 265,
        "returns": 1,
    },
    "ouster-os0-32": {
        "name": "Ouster OS0-32",
        "fov_h": 360,
        "fov_v_min": -45,
        "fov_v_max": 45,
        "max_range": 35,
        "points_per_sec": 655_360,
        "weight_g": 447,
        "returns": 2,
    },
    "velodyne-vlp16": {
        "name": "Velodyne VLP-16",
        "fov_h": 360,
        "fov_v_min": -15,
        "fov_v_max": 15,
        "max_range": 100,
        "points_per_sec": 300_000,
        "weight_g": 830,
        "returns": 2,
    },
    "dji-l2": {
        "name": "DJI Zenmuse L2",
        "fov_h": 70,
        "fov_v_min": -70,
        "fov_v_max": 3,
        "max_range": 250,
        "points_per_sec": 240_000,
        "weight_g": 905,
        "returns": 5,
    },
    "hesai-xt32m2x": {
        "name": "Hesai XT32M2X",
        "fov_h": 360,
        "fov_v_min": -16,
        "fov_v_max": 15,
        "max_range": 120,
        "points_per_sec": 640_000,
        "weight_g": 600,
        "returns": 2,
    },
}


@dataclass
class FlightPlan:
    """LiDAR flight plan parameters and computed values."""
    sensor: str
    altitude_m: float
    speed_ms: float
    area_length_m: float
    area_width_m: float
    overlap_pct: float = 30.0

    swath_width_m: float = 0.0
    line_spacing_m: float = 0.0
    num_lines: int = 0
    flight_distance_m: float = 0.0
    flight_time_min: float = 0.0
    point_density_m2: float = 0.0
    data_size_gb: float = 0.0
    coverage_m2: float = 0.0

    def compute(self):
        s = SENSORS[self.sensor]

        if s["fov_h"] == 360:
            half_fov = math.radians(max(abs(s["fov_v_min"]), abs(s["fov_v_max"])))
        else:
            half_fov = math.radians(s["fov_h"] / 2)

        self.swath_width_m = 2 * self.altitude_m * math.tan(half_fov)
        max_swath = s["max_range"] * 2
        self.swath_width_m = min(self.swath_width_m, max_swath)

        self.line_spacing_m = self.swath_width_m * (1 - self.overlap_pct / 100)
        self.num_lines = max(1, math.ceil(self.area_width_m / self.line_spacing_m) + 1)

        turn_distance = self.line_spacing_m * 2
        self.flight_distance_m = (
            self.num_lines * self.area_length_m
            + (self.num_lines - 1) * turn_distance
        )

        self.flight_time_min = (self.flight_distance_m / self.speed_ms) / 60

        pts_per_m = s["points_per_sec"] / self.speed_ms
        self.point_density_m2 = pts_per_m / self.swath_width_m
        effective_overlap_factor = 1 + (self.overlap_pct / 100)
        self.point_density_m2 *= effective_overlap_factor

        total_pts = s["points_per_sec"] * (self.flight_time_min * 60)
        self.data_size_gb = (total_pts * 16) / (1024**3)

        self.coverage_m2 = self.area_length_m * self.area_width_m
        return self

    def summary(self) -> str:
        s = SENSORS[self.sensor]
        return (
            f"\n"
            f"  Plan de Vol LiDAR — {s['name']}\n"
            f"  {'=' * 40}\n"
            f"  Zone:         {self.area_length_m:.0f} x {self.area_width_m:.0f} m ({self.coverage_m2:.0f} m2)\n"
            f"  Altitude:     {self.altitude_m:.0f} m AGL\n"
            f"  Vitesse:      {self.speed_ms:.1f} m/s ({self.speed_ms * 3.6:.1f} km/h)\n"
            f"  Recouvrement: {self.overlap_pct:.0f}%\n"
            f"  ----------------------------------------\n"
            f"  Fauchee:      {self.swath_width_m:.1f} m\n"
            f"  Espacement:   {self.line_spacing_m:.1f} m\n"
            f"  Lignes:       {self.num_lines}\n"
            f"  Distance:     {self.flight_distance_m:.0f} m\n"
            f"  Temps vol:    {self.flight_time_min:.1f} min\n"
            f"  ----------------------------------------\n"
            f"  Densite:      {self.point_density_m2:.0f} pts/m2\n"
            f"  Donnees:      {self.data_size_gb:.1f} GB (brut)\n"
            f"  Retours:      {s['returns']}\n"
        )

    def to_dict(self) -> dict:
        s = SENSORS[self.sensor]
        return {
            "sensor": self.sensor,
            "sensor_name": s["name"],
            "altitude_m": self.altitude_m,
            "speed_ms": self.speed_ms,
            "area_m2": self.coverage_m2,
            "swath_width_m": round(self.swath_width_m, 1),
            "line_spacing_m": round(self.line_spacing_m, 1),
            "num_lines": self.num_lines,
            "flight_distance_m": round(self.flight_distance_m, 0),
            "flight_time_min": round(self.flight_time_min, 1),
            "point_density_m2": round(self.point_density_m2, 0),
            "data_size_gb": round(self.data_size_gb, 1),
        }

    def to_mavlink_mission(self) -> list:
        """Generate MAVLink waypoints for a lawn-mower pattern."""
        waypoints = []
        for i in range(self.num_lines):
            y = i * self.line_spacing_m
            if i % 2 == 0:
                wp_start = {"lat_offset": 0, "lon_offset": y, "alt": self.altitude_m}
                wp_end = {"lat_offset": self.area_length_m, "lon_offset": y, "alt": self.altitude_m}
            else:
                wp_start = {"lat_offset": self.area_length_m, "lon_offset": y, "alt": self.altitude_m}
                wp_end = {"lat_offset": 0, "lon_offset": y, "alt": self.altitude_m}

            waypoints.append({"seq": len(waypoints), "type": "scan_line_start", "speed": self.speed_ms, **wp_start})
            waypoints.append({"seq": len(waypoints), "type": "scan_line_end", "speed": self.speed_ms, **wp_end})

        return waypoints


def plan_lidar_flight(sensor="livox-mid360", altitude=50, speed=8, length=200, width=150, overlap=30):
    return FlightPlan(
        sensor=sensor, altitude_m=altitude, speed_ms=speed,
        area_length_m=length, area_width_m=width, overlap_pct=overlap,
    ).compute()


if __name__ == "__main__":
    use_json = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--json"]

    if args:
        sensor = args[0] if len(args) > 0 else "livox-mid360"
        alt = float(args[1]) if len(args) > 1 else 50
        spd = float(args[2]) if len(args) > 2 else 8
        l = float(args[3]) if len(args) > 3 else 200
        w = float(args[4]) if len(args) > 4 else 150

        plan = plan_lidar_flight(sensor, alt, spd, l, w)
        if use_json:
            print(json.dumps(plan.to_dict(), indent=2))
        else:
            print(plan.summary())
            wps = plan.to_mavlink_mission()
            print(f"  Waypoints MAVLink: {len(wps)} points")
    else:
        print("=== Comparaison capteurs — zone 200x150m, 50m AGL, 8 m/s ===")
        for sensor_id in SENSORS:
            plan = plan_lidar_flight(sensor=sensor_id)
            if use_json:
                print(json.dumps(plan.to_dict()))
            else:
                print(plan.summary())
