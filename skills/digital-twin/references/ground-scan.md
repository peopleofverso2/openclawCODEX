# Ground Scan Strategy (Quadruped / Handheld)

## When to Use Ground Scanning

- Interior rooms and corridors
- Building facades from street level
- Areas where drone flight is prohibited or impractical
- Under-canopy environments
- Combined with aerial scan for complete coverage

## Platform Options

| Platform | Best for | Sensor mount |
|---|---|---|
| Quadruped robot (Unitree Go2) | Rough terrain, autonomous patrol | Top-mounted LiDAR + camera |
| Handheld scanner (iPhone LiDAR, Matterport) | Quick interior scans | Handheld |
| Backpack LiDAR (Leica BLK2GO) | Large interiors, corridors | Backpack-mounted |
| Tripod LiDAR (Leica RTC360) | High-precision static scans | Tripod per station |

## Scanning Strategy

### Interior Rooms

1. **Station-based** (highest quality):
   - Place scanner at center of each room
   - Ensure 30% overlap between adjacent stations
   - Minimum 3 stations per room for redundancy

2. **Continuous walk** (fastest):
   - Walk slowly through all rooms (0.3-0.5 m/s)
   - Pause 2-3 seconds at doorways
   - Return to start point to close the loop (reduces drift)

### Exterior Facades (ground level)

- Walk parallel to the facade at 3-5 m distance
- Walk speed: 0.3-0.5 m/s
- If using photos: capture every 1-2 meters, 80% overlap
- If using LiDAR: continuous recording
- Complete a full loop around the building

### Multi-Floor Buildings

- Scan each floor independently
- Include stairwells in both floor scans (overlap zone)
- Process floors separately, then align using stairwell overlap

## Photo Capture for Photogrammetry (no LiDAR)

### Camera Setup

- Resolution: highest available
- Mode: auto or aperture priority (f/5.6-f/8)
- Flash: OFF (use ambient or supplemental lighting)
- Format: JPEG fine

### Capture Pattern

```
Room capture pattern (top view):

    +---------+
    |  3   4  |
    |         |
    |  2   5  |
    |         |
    |  1   6  |
    +----D----+
         ↑ start/end at door

At each position: shoot 3 directions
(left, center, right) + up + down for ceiling/floor
```

- Minimum 30 photos per small room
- 60+ photos for large rooms
- Always include corners and transitions (doors, windows)
- Shoot from multiple heights if possible

## LiDAR + ROS 2 Setup

### Launch Drivers

```bash
# Velodyne VLP-16 on robot
ros2 launch velodyne_driver velodyne_driver_node-VLP16-launch.py

# Start SLAM
ros2 launch slam_toolbox online_async_launch.py \
  slam_params_file:=mapper_params_online_async.yaml

# Record everything
ros2 bag record -o interior_scan \
  /velodyne_points /odom /tf /tf_static /imu/data /camera/image_raw
```

### Quadruped Autonomous Scan

```bash
# Define waypoints for room coverage
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 0.0, y: 0.0}, orientation: {w: 1.0}}}}"

# Navigate to next waypoint
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 3.0, y: 0.0}, orientation: {w: 1.0}}}}"

# Rotate 360° at each waypoint for full coverage
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{angular: {z: 0.3}}" --times 20 --rate 1
```

## Post-Processing

### From ROS2 Bag → Point Cloud

```bash
# Replay through SLAM for aligned cloud
ros2 bag play interior_scan
ros2 launch lio_sam run.launch.py
# SLAM node outputs aligned point cloud
```

### From Photos → 3D Model

```bash
# Using COLMAP (better for indoor)
colmap automatic_reconstructor \
  --workspace_path /data/interior \
  --image_path /data/interior/images \
  --dense 1
```

### Registration (align multiple scans)

```python
import open3d as o3d
import numpy as np

floor1 = o3d.io.read_point_cloud("floor1.ply")
floor2 = o3d.io.read_point_cloud("floor2.ply")

# ICP alignment using stairwell overlap
reg = o3d.pipelines.registration.registration_icp(
    floor2, floor1, 0.05, np.eye(4),
    o3d.pipelines.registration.TransformationEstimationPointToPlane())

floor2.transform(reg.transformation)
merged = floor1 + floor2
o3d.io.write_point_cloud("building_complete.ply", merged)
```

## Tips

- Close loops: return to start position to reduce SLAM drift.
- Avoid featureless areas (white walls) — add temporary markers.
- For rooms with glass or mirrors, expect gaps — LiDAR passes through glass.
- Ensure consistent lighting — avoid mixing natural and artificial light.
- Process in sections, then merge — better than one giant scan.
