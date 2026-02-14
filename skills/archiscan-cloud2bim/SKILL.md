---
name: archiscan-cloud2bim
description: Convert point clouds and photogrammetry outputs into BIM models (IFC), floor plans (DXF/SVG), and 3D meshes. Use when asked to create plans, BIM, IFC, floor plans, sections, or elevations from scan data. Handles wall detection, room segmentation, and architectural element extraction.
---

# ArchiScan Cloud2BIM — Point Cloud to BIM Conversion

Transform raw scan data (point clouds, meshes) into architectural deliverables: IFC models, 2D floor plans, sections, elevations.

## Pipeline Overview

```
Point Cloud (LAS/PLY)
    │
    ├── 1. Clean & align
    ├── 2. Slice horizontal planes (floors)
    ├── 3. Detect walls (Hough / RANSAC)
    ├── 4. Segment rooms
    ├── 5. Detect openings (doors/windows)
    ├── 6. Generate 2D plans (DXF/SVG)
    └── 7. Export BIM (IFC)
```

## Step 1 — Clean & Prepare Point Cloud

```python
#!/usr/bin/env python3
"""Clean and prepare point cloud for architectural processing."""
import open3d as o3d
import numpy as np

# Load
pcd = o3d.io.read_point_cloud("scan.ply")
print(f"Raw points: {len(pcd.points)}")

# Downsample (1cm voxel for architecture)
pcd = pcd.voxel_down_sample(voxel_size=0.01)

# Remove outliers
pcd, idx = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)

# Estimate normals
pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(
    radius=0.1, max_nn=30))

print(f"Clean points: {len(pcd.points)}")
o3d.io.write_point_cloud("scan_clean.ply", pcd)
```

## Step 2 — Extract Floor Slices

```python
"""Slice point cloud at floor levels to get horizontal cross-sections."""
import numpy as np
import open3d as o3d

pcd = o3d.io.read_point_cloud("scan_clean.ply")
points = np.asarray(pcd.points)

# Detect floor levels from Z-histogram
z_values = points[:, 2]
hist, bin_edges = np.histogram(z_values, bins=500)

# Peaks in histogram = floor/ceiling levels
from scipy.signal import find_peaks
peaks, _ = find_peaks(hist, height=len(points)*0.001, distance=50)
floor_levels = bin_edges[peaks]
print(f"Detected levels: {floor_levels}")

# Extract wall slice at 1.2m above each floor (counter height = captures walls)
def extract_slice(points, z_center, thickness=0.10):
    mask = np.abs(points[:, 2] - z_center) < thickness / 2
    return points[mask][:, :2]  # Return X,Y only

for i, floor_z in enumerate(floor_levels):
    slice_z = floor_z + 1.2  # 1.2m above floor
    wall_slice = extract_slice(points, slice_z, thickness=0.05)
    np.save(f"floor_{i}_slice.npy", wall_slice)
    print(f"Floor {i}: z={floor_z:.2f}m, slice at {slice_z:.2f}m, {len(wall_slice)} points")
```

## Step 3 — Wall Detection (RANSAC + Hough)

```python
"""Detect wall lines from horizontal point cloud slice."""
import numpy as np
from sklearn.linear_model import RANSACRegressor

def detect_walls_ransac(points_2d, min_wall_length=0.5, iterations=50):
    """Iteratively detect walls using RANSAC line fitting."""
    walls = []
    remaining = points_2d.copy()

    for _ in range(iterations):
        if len(remaining) < 20:
            break

        # Fit line with RANSAC
        X = remaining[:, 0].reshape(-1, 1)
        y = remaining[:, 1]
        ransac = RANSACRegressor(residual_threshold=0.05, min_samples=2)

        try:
            ransac.fit(X, y)
        except ValueError:
            break

        inlier_mask = ransac.inlier_mask_
        inliers = remaining[inlier_mask]

        if len(inliers) < 10:
            remaining = remaining[~inlier_mask]
            continue

        # Compute wall segment (min/max along principal axis)
        wall_start = inliers.min(axis=0)
        wall_end = inliers.max(axis=0)
        wall_length = np.linalg.norm(wall_end - wall_start)

        if wall_length >= min_wall_length:
            walls.append({
                'start': wall_start.tolist(),
                'end': wall_end.tolist(),
                'length': float(wall_length),
                'thickness': 0.20,  # Default 20cm, refine later
                'points': len(inliers)
            })

        remaining = remaining[~inlier_mask]

    return walls

# Usage
slice_points = np.load("floor_0_slice.npy")
walls = detect_walls_ransac(slice_points)
print(f"Detected {len(walls)} walls")
for i, w in enumerate(walls):
    print(f"  Wall {i}: {w['length']:.2f}m, {w['points']} points")
```

### Snap to Orthogonal Grid

```python
def snap_walls_to_grid(walls, angle_tolerance_deg=5):
    """Snap wall angles to 0°/90° for clean architectural plans."""
    snapped = []
    for wall in walls:
        dx = wall['end'][0] - wall['start'][0]
        dy = wall['end'][1] - wall['start'][1]
        angle = np.degrees(np.arctan2(dy, dx)) % 180

        # Snap to nearest 90°
        if angle % 90 < angle_tolerance_deg or angle % 90 > (90 - angle_tolerance_deg):
            snapped_angle = round(angle / 90) * 90
            length = wall['length']
            rad = np.radians(snapped_angle)
            center = [(wall['start'][0]+wall['end'][0])/2,
                       (wall['start'][1]+wall['end'][1])/2]
            wall['start'] = [center[0] - length/2*np.cos(rad),
                             center[1] - length/2*np.sin(rad)]
            wall['end'] = [center[0] + length/2*np.cos(rad),
                           center[1] + length/2*np.sin(rad)]

        snapped.append(wall)
    return snapped
```

## Step 4 — Room Segmentation

```python
"""Segment enclosed spaces into rooms from detected walls."""
import numpy as np
from scipy.ndimage import label

def segment_rooms(walls, bounds, resolution=0.05):
    """Create occupancy grid and flood-fill to find rooms."""
    x_min, y_min = bounds[0]
    x_max, y_max = bounds[1]
    w = int((x_max - x_min) / resolution) + 1
    h = int((y_max - y_min) / resolution) + 1
    grid = np.ones((h, w), dtype=np.uint8)  # 1 = free space

    # Draw walls on grid (0 = wall)
    for wall in walls:
        sx = int((wall['start'][0] - x_min) / resolution)
        sy = int((wall['start'][1] - y_min) / resolution)
        ex = int((wall['end'][0] - x_min) / resolution)
        ey = int((wall['end'][1] - y_min) / resolution)

        # Bresenham line + thickness
        from skimage.draw import line
        rr, cc = line(sy, sx, ey, ex)
        thickness_px = max(1, int(wall['thickness'] / resolution))
        for dr in range(-thickness_px, thickness_px + 1):
            for dc in range(-thickness_px, thickness_px + 1):
                rr_t = np.clip(rr + dr, 0, h-1)
                cc_t = np.clip(cc + dc, 0, w-1)
                grid[rr_t, cc_t] = 0

    # Flood fill to find rooms
    labeled, num_rooms = label(grid)
    print(f"Detected {num_rooms} enclosed spaces")

    rooms = []
    for room_id in range(1, num_rooms + 1):
        mask = labeled == room_id
        area_m2 = mask.sum() * resolution * resolution
        if area_m2 > 1.0:  # Ignore tiny spaces (< 1m²)
            ys, xs = np.where(mask)
            rooms.append({
                'id': room_id,
                'area_m2': round(area_m2, 2),
                'center': [
                    float(xs.mean() * resolution + x_min),
                    float(ys.mean() * resolution + y_min)
                ],
                'bbox': [
                    float(xs.min() * resolution + x_min),
                    float(ys.min() * resolution + y_min),
                    float(xs.max() * resolution + x_min),
                    float(ys.max() * resolution + y_min),
                ]
            })
            print(f"  Room {room_id}: {area_m2:.1f} m²")

    return rooms, labeled, grid
```

## Step 5 — Detect Openings (Doors / Windows)

```python
"""Detect doors and windows as gaps in wall segments."""

def detect_openings(walls, slice_low, slice_high):
    """
    Compare wall slice at 0.5m (below windows) vs 1.5m (above doors).
    Gaps that appear only at door height = doors.
    Gaps that appear only at window height = windows.
    """
    # Points present at low level but absent at high level = door
    # Points absent at both levels = window (if wall exists above)

    openings = []
    for wall in walls:
        # Project points onto wall axis
        wall_vec = np.array(wall['end']) - np.array(wall['start'])
        wall_len = np.linalg.norm(wall_vec)
        wall_dir = wall_vec / wall_len

        # Find gaps along wall in each slice
        gaps_low = find_gaps_along_wall(slice_low, wall, threshold=0.15)
        gaps_high = find_gaps_along_wall(slice_high, wall, threshold=0.15)

        for gap in gaps_high:
            if gap['width'] > 0.6 and gap['width'] < 1.2:
                openings.append({
                    'type': 'door',
                    'wall': wall,
                    'position': gap['center'],
                    'width': gap['width'],
                    'height': 2.10  # Standard door height
                })
            elif gap['width'] > 0.4:
                openings.append({
                    'type': 'window',
                    'wall': wall,
                    'position': gap['center'],
                    'width': gap['width'],
                    'height': 1.20  # Estimated
                })

    return openings
```

## Step 6 — Generate 2D Floor Plans (DXF)

```python
#!/usr/bin/env python3
"""Generate architectural floor plan in DXF format."""
import ezdxf

def generate_floor_plan_dxf(walls, rooms, openings, output="plan.dxf"):
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    # Setup layers
    doc.layers.add("WALLS", color=7)       # White
    doc.layers.add("DOORS", color=3)       # Green
    doc.layers.add("WINDOWS", color=5)     # Blue
    doc.layers.add("ROOMS", color=1)       # Red
    doc.layers.add("DIMENSIONS", color=2)  # Yellow
    doc.layers.add("TEXT", color=6)         # Magenta

    # Draw walls (thick lines)
    for wall in walls:
        msp.add_line(
            wall['start'], wall['end'],
            dxfattribs={'layer': 'WALLS', 'lineweight': 50}
        )

    # Draw openings
    for opening in openings:
        if opening['type'] == 'door':
            # Door arc symbol
            pos = opening['position']
            w = opening['width']
            msp.add_arc(
                center=pos, radius=w,
                start_angle=0, end_angle=90,
                dxfattribs={'layer': 'DOORS'}
            )
        elif opening['type'] == 'window':
            # Window = thin parallel lines
            pos = opening['position']
            w = opening['width']
            msp.add_line(
                [pos[0]-w/2, pos[1]-0.05],
                [pos[0]+w/2, pos[1]-0.05],
                dxfattribs={'layer': 'WINDOWS'}
            )
            msp.add_line(
                [pos[0]-w/2, pos[1]+0.05],
                [pos[0]+w/2, pos[1]+0.05],
                dxfattribs={'layer': 'WINDOWS'}
            )

    # Room labels with area
    for room in rooms:
        msp.add_mtext(
            f"Pièce {room['id']}\n{room['area_m2']} m²",
            dxfattribs={
                'layer': 'TEXT',
                'char_height': 0.15,
                'insert': room['center']
            }
        )

    # Dimensions (wall lengths)
    for wall in walls:
        length = wall['length']
        mid = [(wall['start'][0]+wall['end'][0])/2,
               (wall['start'][1]+wall['end'][1])/2]
        msp.add_mtext(
            f"{length:.2f}",
            dxfattribs={
                'layer': 'DIMENSIONS',
                'char_height': 0.10,
                'insert': [mid[0], mid[1] + 0.15]
            }
        )

    doc.saveas(output)
    print(f"Floor plan saved: {output}")

# Install: pip install ezdxf
```

### SVG Alternative

```python
def generate_floor_plan_svg(walls, rooms, openings, output="plan.svg",
                             scale=50):  # 1:50
    """Generate SVG floor plan for web viewing."""
    # Compute bounds
    all_x = [w['start'][0] for w in walls] + [w['end'][0] for w in walls]
    all_y = [w['start'][1] for w in walls] + [w['end'][1] for w in walls]
    x_min, x_max = min(all_x) - 1, max(all_x) + 1
    y_min, y_max = min(all_y) - 1, max(all_y) + 1

    w_px = int((x_max - x_min) * scale)
    h_px = int((y_max - y_min) * scale)

    def tx(x): return int((x - x_min) * scale)
    def ty(y): return int((y_max - y) * scale)  # Flip Y

    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w_px}" height="{h_px}">']
    lines.append('<rect width="100%" height="100%" fill="white"/>')

    # Walls
    for wall in walls:
        t = max(2, int(wall['thickness'] * scale))
        lines.append(
            f'<line x1="{tx(wall["start"][0])}" y1="{ty(wall["start"][1])}" '
            f'x2="{tx(wall["end"][0])}" y2="{ty(wall["end"][1])}" '
            f'stroke="black" stroke-width="{t}"/>'
        )

    # Room labels
    for room in rooms:
        cx, cy = tx(room['center'][0]), ty(room['center'][1])
        lines.append(f'<text x="{cx}" y="{cy}" text-anchor="middle" '
                     f'font-size="12" fill="#666">{room["area_m2"]} m²</text>')

    lines.append('</svg>')
    with open(output, 'w') as f:
        f.write('\n'.join(lines))
    print(f"SVG plan saved: {output}")
```

## Step 7 — Export BIM (IFC)

```python
#!/usr/bin/env python3
"""Export detected architecture to IFC (BIM) format."""
import ifcopenshell
import ifcopenshell.api as api

def export_to_ifc(walls, rooms, openings, floor_height=2.80, output="model.ifc"):
    model = api.run("project.create_file")

    # Project
    project = api.run("root.create_entity", model, ifc_class="IfcProject", name="ArchiScan")
    api.run("unit.assign_unit", model)

    # Context
    ctx = api.run("context.add_context", model, context_type="Model")
    body = api.run("context.add_context", model, context_type="Model",
                   context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)

    # Site > Building > Storey
    site = api.run("root.create_entity", model, ifc_class="IfcSite", name="Site")
    building = api.run("root.create_entity", model, ifc_class="IfcBuilding", name="Bâtiment")
    storey = api.run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="RDC")

    api.run("aggregate.assign_object", model, relating_object=project, products=[site])
    api.run("aggregate.assign_object", model, relating_object=site, products=[building])
    api.run("aggregate.assign_object", model, relating_object=building, products=[storey])

    # Create walls
    for i, wall_data in enumerate(walls):
        wall = api.run("root.create_entity", model, ifc_class="IfcWall",
                       name=f"Mur_{i+1}")
        # Wall placement and geometry
        api.run("geometry.edit_object_placement", model, product=wall)
        api.run("spatial.assign_container", model, relating_structure=storey, products=[wall])

    # Create spaces (rooms)
    for room in rooms:
        space = api.run("root.create_entity", model, ifc_class="IfcSpace",
                        name=f"Pièce_{room['id']}")
        api.run("spatial.assign_container", model, relating_structure=storey, products=[space])
        # Set area property
        pset = api.run("pset.add_pset", model, product=space, name="ArchiScan_Metrics")
        api.run("pset.edit_pset", model, pset=pset, properties={
            "Area": room['area_m2'],
            "ScanSource": "ArchiScan"
        })

    # Create openings
    for j, opening in enumerate(openings):
        if opening['type'] == 'door':
            door = api.run("root.create_entity", model, ifc_class="IfcDoor",
                           name=f"Porte_{j+1}")
            api.run("spatial.assign_container", model, relating_structure=storey, products=[door])
        elif opening['type'] == 'window':
            window = api.run("root.create_entity", model, ifc_class="IfcWindow",
                             name=f"Fenêtre_{j+1}")
            api.run("spatial.assign_container", model, relating_structure=storey, products=[window])

    model.write(output)
    print(f"IFC model saved: {output}")
    print(f"  Walls: {len(walls)}, Rooms: {len(rooms)}, Openings: {len(openings)}")

# Install: pip install ifcopenshell
```

## Quick Reference — Full Pipeline

```bash
# 1. Clean point cloud
python3 -c "
import open3d as o3d
pcd = o3d.io.read_point_cloud('scan.ply')
pcd = pcd.voxel_down_sample(0.01)
pcd, _ = pcd.remove_statistical_outlier(20, 2.0)
o3d.io.write_point_cloud('clean.ply', pcd)
"

# 2. Run full pipeline script
python3 scripts/cloud2bim_pipeline.py \
  --input clean.ply \
  --output-dxf plan.dxf \
  --output-svg plan.svg \
  --output-ifc model.ifc \
  --floor-height 2.80

# 3. View results
# DXF: open in LibreCAD, AutoCAD, or FreeCAD
# SVG: open in browser
# IFC: open in FreeCAD BIM, BIMvision, or xBIM Xplorer
```

## Alternative: FreeCAD BIM Workbench

For manual refinement after automated detection:

```bash
# Install FreeCAD with BIM workbench
sudo apt install freecad
# Or: flatpak install flathub org.freecadweb.FreeCAD

# Import point cloud in FreeCAD:
# 1. File → Import → select .ply or .pcd
# 2. Switch to BIM Workbench
# 3. Use "BIM Wall" tool to trace over point cloud
# 4. File → Export → .ifc
```

## Tips

- Wall detection works best on **clean horizontal slices** — invest time in step 2.
- Snap walls to orthogonal grid for clean plans (most buildings are rectilinear).
- For curved walls or heritage buildings, increase RANSAC iterations and lower snap tolerance.
- IFC export via IfcOpenShell is the standard — compatible with Revit, ArchiCAD, FreeCAD.
- Always validate measurements against a known reference (door width = 83cm standard).
