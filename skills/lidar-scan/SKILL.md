---
name: lidar-scan
description: Acquire LiDAR point clouds, run SLAM, and process 3D scan data.
homepage: https://pdal.io
metadata:
  {
    "openclaw":
      {
        "emoji": "📡",
        "requires": { "bins": ["pdal"] },
        "install":
          [
            {
              "id": "apt-pdal",
              "kind": "shell",
              "command": "sudo apt install -y pdal",
              "bins": ["pdal"],
              "label": "Install PDAL (apt)",
            },
            {
              "id": "pip-open3d",
              "kind": "shell",
              "command": "pip install open3d laspy numpy",
              "bins": ["python3"],
              "label": "Install Open3D + laspy (pip)",
            },
            {
              "id": "apt-slam",
              "kind": "shell",
              "command": "sudo apt install -y ros-jazzy-slam-toolbox ros-jazzy-pointcloud-to-laserscan",
              "bins": ["ros2"],
              "label": "Install SLAM Toolbox (apt, requires ROS 2)",
            },
          ],
      },
  }
---

# LiDAR Scanning & Point Cloud Processing

Acquire, process, and visualize LiDAR point cloud data using PDAL, Open3D, and ROS 2.

## LiDAR Acquisition via ROS 2

### Launch LiDAR Driver

```bash
# Velodyne VLP-16
ros2 launch velodyne_driver velodyne_driver_node-VLP16-launch.py

# Ouster OS1
ros2 launch ouster_ros driver.launch.py params_file:=ouster_config.yaml

# Livox Mid-360
ros2 launch livox_ros2_driver livox_lidar_launch.py

# RPLidar (2D, budget option)
ros2 launch rplidar_ros rplidar_a2m12_launch.py
```

### Visualize Live Point Cloud

```bash
# Check the topic is publishing
ros2 topic list | grep -i point
ros2 topic hz /velodyne_points

# View in RViz2
rviz2 &
# Add PointCloud2 display, set topic to /velodyne_points
```

### Record a Scan Session

```bash
# Record LiDAR + odometry + TF for offline SLAM
ros2 bag record -o site_scan \
  /velodyne_points /odom /tf /tf_static /imu/data

# Check bag contents
ros2 bag info site_scan
```

## SLAM (Simultaneous Localization & Mapping)

### 2D SLAM — slam_toolbox

```bash
ros2 launch slam_toolbox online_async_launch.py \
  slam_params_file:=mapper_params_online_async.yaml \
  use_sim_time:=false
```

### 3D SLAM — LIO-SAM or FAST-LIO

```bash
# LIO-SAM (LiDAR-Inertial SLAM)
ros2 launch lio_sam run.launch.py

# FAST-LIO2
ros2 launch fast_lio mapping.launch.py
```

### Save Map

```bash
# Save 2D occupancy grid
ros2 run nav2_map_server map_saver_cli -f ~/maps/site_map

# Export 3D point cloud map (from SLAM node)
ros2 service call /save_map std_srvs/srv/Trigger
```

## PDAL — Point Cloud Processing CLI

### Inspect

```bash
# File metadata
pdal info scan.las

# Summary statistics
pdal info scan.las --summary

# Point count
pdal info scan.las --pointcount
```

### Convert Formats

```bash
# LAS → PLY
pdal translate scan.las scan.ply

# LAS → compressed LAZ
pdal translate scan.las scan.laz

# LAS → GeoTIFF (height raster)
pdal translate scan.las heightmap.tif \
  --writers.gdal.resolution=0.5 \
  --writers.gdal.output_type=mean
```

### Filter & Crop

```bash
# Remove noise (statistical outlier removal)
pdal translate input.las cleaned.las \
  --filter outlier --filters.outlier.method=statistical \
  --filters.outlier.mean_k=12 --filters.outlier.multiplier=2.2

# Crop to bounding box
pdal translate input.las cropped.las \
  --filter crop \
  --filters.crop.bounds="([xmin,xmax],[ymin,ymax])"

# Ground classification (SMRF algorithm)
pdal translate input.las ground.las \
  --filter smrf
```

### Merge Multiple Scans

```bash
pdal merge scan1.las scan2.las scan3.las merged.las
```

## Open3D — Python Point Cloud Processing

```python
#!/usr/bin/env python3
"""Process and visualize point clouds with Open3D."""
import open3d as o3d
import numpy as np

# Load point cloud
pcd = o3d.io.read_point_cloud("scan.ply")
print(f"Points: {len(pcd.points)}")

# Downsample (voxel grid)
pcd_down = pcd.voxel_down_sample(voxel_size=0.05)

# Remove outliers
pcd_clean, idx = pcd_down.remove_statistical_outlier(
    nb_neighbors=20, std_ratio=2.0)

# Estimate normals
pcd_clean.estimate_normals(
    search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))

# Surface reconstruction (Poisson)
mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
    pcd_clean, depth=9)
o3d.io.write_triangle_mesh("mesh.ply", mesh)

# Visualize
o3d.visualization.draw_geometries([pcd_clean])
```

### Registration (Align Multiple Scans)

```python
# ICP (Iterative Closest Point) alignment
threshold = 0.05
reg = o3d.pipelines.registration.registration_icp(
    source_pcd, target_pcd, threshold,
    np.eye(4),
    o3d.pipelines.registration.TransformationEstimationPointToPlane())

print(f"Fitness: {reg.fitness:.3f}, RMSE: {reg.inlier_rmse:.4f}")
source_pcd.transform(reg.transformation)
```

## CloudCompare (GUI / CLI)

```bash
# Install
sudo snap install cloudcompare

# CLI: compute distance between two clouds
CloudCompare -o cloud1.ply -o cloud2.ply -C2C_DIST

# CLI: subsample
CloudCompare -o input.ply -SS SPATIAL 0.05 -SAVE_CLOUDS

# CLI: export to different format
CloudCompare -o input.las -SAVE_CLOUDS FILE "output.ply"
```

## Typical Workflow: Scan a Building

1. **Mount LiDAR** on quadruped/drone (or handheld).
2. **Record** via `ros2 bag record` while traversing.
3. **Run SLAM** offline: replay bag → get aligned point cloud.
4. **Clean** with PDAL: denoise, crop, classify ground.
5. **Mesh** with Open3D: Poisson reconstruction.
6. **Export** as PLY/LAS/LAZ for CAD or GIS use.

## Tips

- Use LAZ (compressed LAS) for large datasets — saves 60-80% storage.
- Voxel downsample before heavy processing to reduce computation.
- For outdoor scans, classify ground points first (`pdal smrf`) to separate terrain from objects.
- Combine with photogrammetry for colorized point clouds.
