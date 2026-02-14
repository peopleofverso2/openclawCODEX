---
name: photogrammetry
description: 3D reconstruction from photos using OpenDroneMap, COLMAP, or Meshroom.
homepage: https://opendronemap.org
metadata:
  {
    "openclaw":
      {
        "emoji": "🗺️",
        "requires": { "bins": ["docker"] },
        "install":
          [
            {
              "id": "docker-odm",
              "kind": "shell",
              "command": "docker pull opendronemap/odm",
              "bins": ["docker"],
              "label": "Pull OpenDroneMap Docker image",
            },
            {
              "id": "pip-colmap",
              "kind": "shell",
              "command": "sudo apt install -y colmap",
              "bins": ["colmap"],
              "label": "Install COLMAP (apt)",
            },
          ],
      },
  }
---

# Photogrammetry — 3D Reconstruction from Photos

Reconstruct 3D models, orthophotos, and digital elevation models from overlapping photographs.

## OpenDroneMap (ODM) — Recommended for Aerial Mapping

### Quick Start

```bash
# Organize photos in a folder
mkdir -p /data/project/images
# Copy drone photos into /data/project/images/

# Run ODM via Docker
docker run -ti --rm \
  -v /data/project:/datasets/code \
  opendronemap/odm \
  --project-path /datasets \
  code
```

### Output Structure

```
/data/project/
├── images/                  # Input photos
├── odm_orthophoto/         # Georeferenced orthophoto (GeoTIFF)
├── odm_dem/                # Digital Elevation Model
├── odm_texturing/          # Textured 3D mesh (OBJ)
├── odm_georeferencing/     # Georeferenced point cloud (LAS)
├── odm_report/             # Processing report (PDF)
└── opensfm/                # SfM intermediate results
```

### Common Options

```bash
docker run -ti --rm \
  -v /data/project:/datasets/code \
  opendronemap/odm \
  --project-path /datasets \
  code \
  --dsm                       # Generate Digital Surface Model \
  --dtm                       # Generate Digital Terrain Model \
  --orthophoto-resolution 2   # cm/pixel \
  --mesh-octree-depth 12      # Mesh detail level \
  --pc-quality high           # Point cloud density (ultra|high|medium|low) \
  --feature-quality high      # Feature extraction detail \
  --fast-orthophoto           # Skip 3D, only produce orthophoto \
  --gps-accuracy 5            # GPS accuracy in meters \
  --max-concurrency 8         # Parallel threads \
  --use-3dmesh                # Full 3D mesh instead of 2.5D
```

### With Ground Control Points (GCPs)

```bash
# Create gcp_list.txt in project root:
# EPSG:4326
# lon lat alt pixelX pixelY imageName
# -122.085 37.422 10.5 1250 800 DJI_0001.JPG

docker run -ti --rm \
  -v /data/project:/datasets/code \
  opendronemap/odm \
  --project-path /datasets \
  code \
  --gcp /datasets/code/gcp_list.txt
```

## COLMAP — Research-Grade SfM + MVS

### Automatic Reconstruction

```bash
# Full pipeline (feature extraction → matching → sparse → dense)
colmap automatic_reconstructor \
  --workspace_path /data/colmap_project \
  --image_path /data/colmap_project/images

# Outputs:
# sparse/  — camera poses + sparse point cloud
# dense/   — dense point cloud + mesh
```

### Step-by-Step Pipeline

```bash
PROJ=/data/colmap_project
DB=$PROJ/database.db

# 1. Feature extraction
colmap feature_extractor \
  --database_path $DB \
  --image_path $PROJ/images \
  --ImageReader.camera_model OPENCV \
  --SiftExtraction.use_gpu 1

# 2. Feature matching
colmap exhaustive_matcher \
  --database_path $DB \
  --SiftMatching.use_gpu 1

# For large datasets, use sequential or vocab-tree matcher:
# colmap sequential_matcher --database_path $DB
# colmap vocab_tree_matcher --database_path $DB --VocabTreeMatching.vocab_tree_path vocab.bin

# 3. Sparse reconstruction (Structure from Motion)
mkdir -p $PROJ/sparse
colmap mapper \
  --database_path $DB \
  --image_path $PROJ/images \
  --output_path $PROJ/sparse

# 4. Dense reconstruction
mkdir -p $PROJ/dense
colmap image_undistorter \
  --image_path $PROJ/images \
  --input_path $PROJ/sparse/0 \
  --output_path $PROJ/dense

colmap patch_match_stereo \
  --workspace_path $PROJ/dense

colmap stereo_fusion \
  --workspace_path $PROJ/dense \
  --output_path $PROJ/dense/fused.ply

# 5. Meshing (Poisson)
colmap poisson_mesher \
  --input_path $PROJ/dense/fused.ply \
  --output_path $PROJ/dense/mesh.ply
```

### Export Point Cloud

```bash
# Export sparse model to various formats
colmap model_converter \
  --input_path $PROJ/sparse/0 \
  --output_path $PROJ/sparse/0/points.ply \
  --output_type PLY
```

## Meshroom (AliceVision) — GUI + CLI

```bash
# Install via AppImage
wget https://github.com/alicevision/Meshroom/releases/latest/download/Meshroom-linux.tar.gz
tar xzf Meshroom-linux.tar.gz

# CLI pipeline
./Meshroom/meshroom_batch \
  --input /data/photos/ \
  --output /data/meshroom_output/
```

## Photo Capture Best Practices

### For Drone Mapping

- **Overlap**: 75% frontal, 65% lateral minimum
- **Altitude**: consistent, 30-80m depending on desired resolution
- **Pattern**: lawn-mower grid (see `drone-mavlink` skill for grid generation)
- **Camera**: nadir (pointing straight down), gimbal at -90°
- **Oblique pass**: optional second pass at 45° for better 3D facades
- **Lighting**: overcast is ideal, avoid harsh shadows

### For Ground-Level / Indoor

- **Overlap**: 80%+ between consecutive photos
- **Coverage**: walk around the object/room in circles at multiple heights
- **Avoid**: reflective surfaces, transparent objects, moving elements
- **Scale**: include a ruler or known-size object for accurate scale
- **Texture**: add targets on featureless surfaces (white walls)

## Post-Processing

### Convert Outputs

```bash
# Orthophoto to tiled web format (for web GIS)
gdal2tiles.py -z 10-22 odm_orthophoto/odm_orthophoto.tif tiles/

# DEM to contour lines (shapefile)
gdal_contour -i 1 -a elevation odm_dem/dsm.tif contours.shp

# Point cloud format conversion
pdal translate georeferenced.las output.ply
pdal translate georeferenced.las output.laz  # compressed
```

### Accuracy Assessment

```bash
# Compare with reference points
# Use PDAL to compute distances
pdal translate recon.las \
  --filter stats \
  --filters.stats.dimensions="X,Y,Z"

# Use CloudCompare for visual comparison
CloudCompare -o reference.ply -o reconstructed.ply -C2C_DIST
```

## Combined Workflow: Drone → 3D Model

1. **Plan mission** with `drone-mavlink` skill (grid pattern, 75% overlap)
2. **Fly and capture** — interval photos at 2s, gimbal at -90°
3. **Download photos** from drone/SD card
4. **Run ODM** — `docker run ... opendronemap/odm`
5. **Refine** — use GCPs if centimeter accuracy needed
6. **Optional**: merge with LiDAR data for hybrid point cloud
7. **Export** — orthophoto (GeoTIFF), 3D mesh (OBJ), point cloud (LAS)

## Tips

- More photos with overlap > fewer high-res photos with gaps.
- Use RAW format if possible for better feature detection.
- For large datasets (>500 photos), split into sub-areas and merge.
- COLMAP is more flexible; ODM is more turnkey for drone mapping.
- GPU (CUDA) dramatically speeds up COLMAP and Meshroom.
