---
name: digital-twin
description: Create a digital twin (3D model) of a building, site, or object by orchestrating drone or ground robot scanning missions. Use when asked to scan, model, digitize, or create a twin of a physical space — houses, buildings, construction sites, rooms, facades. Combines flight/walk planning, photo and LiDAR capture, and 3D reconstruction into a single guided workflow.
---

# Digital Twin — Scan-to-Model Workflow

Orchestrate a complete scan-to-3D pipeline: plan the capture, execute the mission, process the data, deliver the model.

## Workflow Overview

```
1. ASSESS  → What to scan, what gear is available
2. PLAN    → Generate mission (flight path or walk path)
3. CAPTURE → Execute mission, collect photos + optional LiDAR
4. PROCESS → Reconstruct 3D model
5. DELIVER → Export in target format
```

## Step 1 — Assess

Ask the operator:

| Question | Why |
|---|---|
| What is the target? (house, room, facade, terrain) | Determines indoor vs outdoor strategy |
| What platform? (drone, quadruped, handheld, tripod) | Determines motion planning |
| What sensors? (camera only, camera + LiDAR) | Determines processing pipeline |
| Desired output? (point cloud, mesh, orthophoto, BIM) | Determines export format |
| Accuracy needed? (visual only, cm-level, survey-grade) | Determines GCP usage |

Select the matching strategy:

| Scenario | Strategy | Reference |
|---|---|---|
| Exterior building, drone available | Aerial grid + oblique passes | [references/aerial-scan.md](references/aerial-scan.md) |
| Interior rooms, ground robot or handheld | Room-by-room walk scan | [references/ground-scan.md](references/ground-scan.md) |
| Both interior + exterior | Combined: drone exterior then ground interior | Both references |

## Step 2 — Plan the Mission

### Aerial (drone)

Generate a lawn-mower grid using `scripts/plan_grid_mission.sh`:

```bash
scripts/plan_grid_mission.sh \
  --lat 48.8584 --lon 2.2945 \
  --width 60 --height 40 \
  --altitude 25 --overlap 75 \
  --speed 3 --output mission.plan
```

Add an oblique orbit for facades:

```bash
scripts/plan_orbit_mission.sh \
  --lat 48.8584 --lon 2.2945 \
  --radius 30 --altitude 20 \
  --gimbal-pitch -45 --points 24 \
  --output orbit.plan
```

### Ground (quadruped / handheld)

```bash
# Start ROS2 navigation with SLAM
ros2 launch nav2_bringup navigation_launch.py use_sim_time:=false

# Send waypoints around the building
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 5.0, y: 0.0}, orientation: {w: 1.0}}}}"
```

## Step 3 — Capture

### Photos (all platforms)

- Interval: 1 photo every 2 seconds (or every 2 meters)
- Overlap: minimum 75% frontal, 65% lateral
- Format: JPEG (or RAW if available)

### LiDAR (if available)

```bash
ros2 bag record -o building_scan \
  /velodyne_points /odom /tf /tf_static /imu/data /camera/image_raw
```

## Step 4 — Process

Choose pipeline based on available data:

### Photos only → OpenDroneMap

```bash
mkdir -p /data/twin/images
# Copy all captured photos to /data/twin/images/

docker run -ti --rm \
  -v /data/twin:/datasets/code \
  opendronemap/odm \
  --project-path /datasets code \
  --dsm --dtm \
  --mesh-octree-depth 12 \
  --pc-quality high \
  --use-3dmesh \
  --orthophoto-resolution 2
```

### Photos only → COLMAP (alternative)

```bash
colmap automatic_reconstructor \
  --workspace_path /data/twin \
  --image_path /data/twin/images
```

### LiDAR + Photos → Hybrid pipeline

```bash
# 1. Process LiDAR: replay bag through SLAM
ros2 bag play building_scan &
ros2 launch lio_sam run.launch.py

# 2. Clean point cloud
pdal translate slam_output.las cleaned.las \
  --filter outlier --filters.outlier.method=statistical \
  --filters.outlier.mean_k=12 --filters.outlier.multiplier=2.2

# 3. Colorize with photos via ODM
docker run -ti --rm \
  -v /data/twin:/datasets/code \
  opendronemap/odm \
  --project-path /datasets code \
  --use-3dmesh

# 4. Merge LiDAR + photogrammetry clouds
pdal merge cleaned.las odm_georeferencing/odm_georeferenced_model.laz \
  merged_twin.las
```

## Step 5 — Deliver

Export to the requested format:

```bash
# Point cloud (universal)
pdal translate merged_twin.las twin.ply
pdal translate merged_twin.las twin.laz   # compressed

# Textured mesh → glTF (for web/AR viewers)
# From ODM OBJ output:
pip install trimesh
python3 -c "
import trimesh
mesh = trimesh.load('odm_texturing/odm_textured_model_geo.obj')
mesh.export('twin.glb')
"

# Orthophoto → web tiles
gdal2tiles.py -z 10-22 odm_orthophoto/odm_orthophoto.tif tiles/

# DEM → contour lines
gdal_contour -i 0.5 -a elevation odm_dem/dsm.tif contours.shp
```

### Output Summary

| Format | File | Usage |
|---|---|---|
| Point cloud | `twin.laz` | CAD, GIS, BIM import |
| 3D mesh | `twin.glb` | Web viewer, AR, Unity |
| Orthophoto | `odm_orthophoto.tif` | 2D map overlay |
| DSM/DTM | `dsm.tif` / `dtm.tif` | Elevation analysis |
| Contours | `contours.shp` | Topographic plans |

## Quick Reference: Full Command Sequence

For the most common case (drone, photos only, house exterior):

```bash
# 1. Plan
scripts/plan_grid_mission.sh --lat LAT --lon LON --width 50 --height 50 --altitude 25 --overlap 75 --speed 3 --output mission.plan

# 2. Fly (via MAVSDK)
python3 scripts/fly_mission.py --plan mission.plan --connection udp://:14540

# 3. Process
mkdir -p /data/twin/images && cp ~/drone_photos/*.jpg /data/twin/images/
docker run -ti --rm -v /data/twin:/datasets/code opendronemap/odm --project-path /datasets code --dsm --use-3dmesh --pc-quality high

# 4. Export
pdal translate /data/twin/odm_georeferencing/odm_georeferenced_model.laz twin.ply
python3 -c "import trimesh; trimesh.load('/data/twin/odm_texturing/odm_textured_model_geo.obj').export('twin.glb')"
```
