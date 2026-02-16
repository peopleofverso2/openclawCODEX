#!/usr/bin/env python3
"""Unit tests for flight_planner.py — no external deps."""

import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from flight_planner import FlightPlan, SENSORS, plan_lidar_flight


def test_all_sensors_compute():
    """Every sensor should produce valid flight plans."""
    for sensor_id in SENSORS:
        plan = plan_lidar_flight(sensor=sensor_id, altitude=50, speed=8, length=200, width=150)
        assert plan.swath_width_m > 0, f"{sensor_id}: swath must be > 0"
        assert plan.line_spacing_m > 0, f"{sensor_id}: spacing must be > 0"
        assert plan.num_lines >= 1, f"{sensor_id}: must have >= 1 line"
        assert plan.flight_time_min > 0, f"{sensor_id}: flight time must be > 0"
        assert plan.point_density_m2 > 0, f"{sensor_id}: density must be > 0"
        assert plan.data_size_gb > 0, f"{sensor_id}: data size must be > 0"
        assert plan.coverage_m2 == 200 * 150, f"{sensor_id}: coverage should match area"
        print(f"  PASS  {sensor_id}: {plan.num_lines} lines, {plan.flight_time_min:.1f} min, {plan.point_density_m2:.0f} pts/m2")


def test_altitude_affects_swath():
    """Higher altitude → wider swath → fewer lines."""
    plan_low = plan_lidar_flight(sensor="livox-mid360", altitude=30, speed=8, length=200, width=150)
    plan_high = plan_lidar_flight(sensor="livox-mid360", altitude=80, speed=8, length=200, width=150)

    assert plan_high.swath_width_m > plan_low.swath_width_m, "Higher alt should give wider swath"
    assert plan_high.num_lines <= plan_low.num_lines, "Higher alt should need fewer lines"
    assert plan_high.point_density_m2 < plan_low.point_density_m2, "Higher alt = lower density"
    print(f"  PASS  altitude: 30m → {plan_low.swath_width_m:.0f}m swath, 80m → {plan_high.swath_width_m:.0f}m swath")


def test_speed_affects_density():
    """Slower speed → more points per m²."""
    plan_slow = plan_lidar_flight(sensor="livox-mid360", altitude=50, speed=4, length=200, width=150)
    plan_fast = plan_lidar_flight(sensor="livox-mid360", altitude=50, speed=12, length=200, width=150)

    assert plan_slow.point_density_m2 > plan_fast.point_density_m2, "Slower = denser"
    assert plan_slow.flight_time_min > plan_fast.flight_time_min, "Slower = longer"
    print(f"  PASS  speed: 4 m/s → {plan_slow.point_density_m2:.0f} pts/m2, 12 m/s → {plan_fast.point_density_m2:.0f} pts/m2")


def test_overlap_affects_lines():
    """More overlap → more lines → longer flight."""
    plan_low = plan_lidar_flight(sensor="livox-mid360", altitude=50, speed=8, length=200, width=150, overlap=20)
    plan_high = plan_lidar_flight(sensor="livox-mid360", altitude=50, speed=8, length=200, width=150, overlap=50)

    assert plan_high.num_lines >= plan_low.num_lines, "More overlap = more lines"
    assert plan_high.flight_time_min >= plan_low.flight_time_min, "More overlap = longer"
    print(f"  PASS  overlap: 20% → {plan_low.num_lines} lines, 50% → {plan_high.num_lines} lines")


def test_swath_capped_by_range():
    """Swath width should not exceed sensor max range × 2."""
    # Ouster OS0-32: max_range = 35m → max swath = 70m
    # At 100m altitude with 90° FoV, geometric swath would be huge
    plan = plan_lidar_flight(sensor="ouster-os0-32", altitude=100, speed=8, length=200, width=150)
    max_swath = SENSORS["ouster-os0-32"]["max_range"] * 2

    assert plan.swath_width_m <= max_swath, f"Swath {plan.swath_width_m:.0f}m exceeds max {max_swath}m"
    print(f"  PASS  range cap: OS0-32 at 100m → swath capped at {plan.swath_width_m:.0f}m (max {max_swath}m)")


def test_mavlink_waypoints():
    """Waypoints should form a lawn-mower pattern."""
    plan = plan_lidar_flight(sensor="livox-mid360", altitude=50, speed=8, length=200, width=150)
    wps = plan.to_mavlink_mission()

    assert len(wps) == plan.num_lines * 2, f"Expected {plan.num_lines * 2} waypoints, got {len(wps)}"
    # Check alternating direction
    assert wps[0]["lat_offset"] == 0, "First line should start at 0"
    assert wps[1]["lat_offset"] == 200, "First line should end at length"
    if len(wps) > 2:
        assert wps[2]["lat_offset"] == 200, "Second line should start at length (reverse)"
        assert wps[3]["lat_offset"] == 0, "Second line should end at 0 (reverse)"
    print(f"  PASS  waypoints: {len(wps)} points, lawn-mower pattern OK")


def test_json_output():
    """to_dict() should produce valid JSON-serializable dict."""
    plan = plan_lidar_flight()
    d = plan.to_dict()

    required_keys = ["sensor", "altitude_m", "speed_ms", "swath_width_m",
                     "num_lines", "flight_time_min", "point_density_m2"]
    for key in required_keys:
        assert key in d, f"Missing key: {key}"
        assert isinstance(d[key], (int, float, str)), f"Bad type for {key}: {type(d[key])}"

    import json
    json.dumps(d)  # Should not raise
    print(f"  PASS  JSON output: {len(d)} fields, serializable")


def test_small_area():
    """Even a tiny area should produce at least 1 line."""
    plan = plan_lidar_flight(sensor="livox-mid360", altitude=50, speed=8, length=20, width=10)
    assert plan.num_lines >= 1
    assert plan.flight_time_min > 0
    print(f"  PASS  small area: 20x10m → {plan.num_lines} line(s), {plan.flight_time_min:.1f} min")


def main():
    tests = [
        ("All sensors compute", test_all_sensors_compute),
        ("Altitude affects swath", test_altitude_affects_swath),
        ("Speed affects density", test_speed_affects_density),
        ("Overlap affects lines", test_overlap_affects_lines),
        ("Swath capped by range", test_swath_capped_by_range),
        ("MAVLink waypoints", test_mavlink_waypoints),
        ("JSON output", test_json_output),
        ("Small area", test_small_area),
    ]

    print(f"Running {len(tests)} flight planner tests...\n")
    passed = 0
    failed = 0

    for name, fn in tests:
        try:
            fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"  {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'=' * 50}")
    return failed == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
