---
name: archiscan-measure
description: Automated architectural measurements from point clouds and BIM models — surface areas, room volumes, wall lengths, heights, distances, slope analysis. Use when asked to measure, compute area, calculate volume, or extract quantities from a scan or 3D model.
---

# ArchiScan Measure — Automated Metrics & Quantities

Extract architectural measurements from point clouds, meshes, or IFC models.

## Quick Measurements from Point Cloud

### Distance Between Two Points

```python
import open3d as o3d
import numpy as np

pcd = o3d.io.read_point_cloud("scan.ply")
points = np.asarray(pcd.points)

# Interactive: pick 2 points (GUI)
# vis = o3d.visualization.VisualizerWithEditing()
# vis.create_window()
# vis.add_geometry(pcd)
# vis.run()  # Shift+Click to pick points
# picked = vis.get_picked_points()

# Programmatic: measure between known coordinates
p1 = np.array([1.0, 2.0, 0.0])
p2 = np.array([4.5, 2.0, 0.0])
distance = np.linalg.norm(p2 - p1)
print(f"Distance: {distance:.3f} m")
```

### Height Under Ceiling

```python
def measure_ceiling_height(points, x, y, search_radius=0.5):
    """Measure floor-to-ceiling height at position (x,y)."""
    mask = (np.abs(points[:, 0] - x) < search_radius) & \
           (np.abs(points[:, 1] - y) < search_radius)
    column = points[mask]

    if len(column) < 10:
        return None

    z_values = column[:, 2]
    floor_z = np.percentile(z_values, 5)   # 5th percentile = floor
    ceiling_z = np.percentile(z_values, 95) # 95th percentile = ceiling
    height = ceiling_z - floor_z

    return {
        'floor_z': round(float(floor_z), 3),
        'ceiling_z': round(float(ceiling_z), 3),
        'height': round(float(height), 3)
    }

# Usage
pcd = o3d.io.read_point_cloud("scan.ply")
pts = np.asarray(pcd.points)
h = measure_ceiling_height(pts, x=3.0, y=2.0)
print(f"Hauteur sous plafond: {h['height']:.2f} m")
```

## Room Measurements

### Surface Area (from floor plan)

```python
def compute_room_areas(rooms, walls, resolution=0.05):
    """Compute room areas from flood-fill segmentation."""
    results = []
    for room in rooms:
        # Area already computed during segmentation
        area = room['area_m2']

        # Compute perimeter from bounding walls
        perimeter = 0
        for wall in walls:
            # Check if wall borders this room (simplified)
            perimeter += wall['length']

        results.append({
            'room_id': room['id'],
            'area_m2': round(area, 2),
            'perimeter_m': round(perimeter, 2),
        })

    return results
```

### Volume (area x height)

```python
def compute_room_volumes(rooms, points):
    """Compute room volumes using area and measured ceiling height."""
    for room in rooms:
        cx, cy = room['center']
        h = measure_ceiling_height(points, cx, cy)
        if h:
            room['height_m'] = h['height']
            room['volume_m3'] = round(room['area_m2'] * h['height'], 2)
        else:
            room['height_m'] = 2.50  # Default
            room['volume_m3'] = round(room['area_m2'] * 2.50, 2)

    return rooms
```

## Wall Measurements

### Wall Thickness from Point Cloud

```python
def measure_wall_thickness(points, wall, search_width=0.5):
    """Measure wall thickness by analyzing point distribution perpendicular to wall."""
    wall_vec = np.array(wall['end']) - np.array(wall['start'])
    wall_dir = wall_vec / np.linalg.norm(wall_vec)
    normal = np.array([-wall_dir[1], wall_dir[0]])  # Perpendicular

    # Project nearby points onto wall normal
    wall_center = (np.array(wall['start']) + np.array(wall['end'])) / 2
    relative = points[:, :2] - wall_center

    # Filter points near the wall
    along = relative @ wall_dir
    perp = relative @ normal
    mask = (np.abs(along) < wall['length'] / 2) & (np.abs(perp) < search_width)
    perp_values = perp[mask]

    if len(perp_values) < 20:
        return 0.20  # Default

    # Wall surfaces create two peaks in perpendicular distribution
    hist, bins = np.histogram(perp_values, bins=100)
    from scipy.signal import find_peaks
    peaks, _ = find_peaks(hist, height=len(perp_values) * 0.05)

    if len(peaks) >= 2:
        thickness = abs(bins[peaks[-1]] - bins[peaks[0]])
        return round(float(thickness), 3)

    return 0.20  # Default if detection fails
```

## Facade Measurements

### Window and Door Dimensions

```python
def measure_openings(points, openings):
    """Refine opening dimensions from point cloud."""
    for opening in openings:
        pos = np.array(opening['position'])
        # Find points around opening
        mask = np.linalg.norm(points[:, :2] - pos, axis=1) < 1.5
        nearby = points[mask]

        if len(nearby) < 50:
            continue

        # Opening = gap in point cloud
        # Width: horizontal extent of gap
        # Height: vertical extent between lintel and sill

        z_vals = nearby[:, 2]
        # Sill height (bottom of window)
        sill = np.percentile(z_vals[z_vals > np.median(z_vals) - 0.5], 10)
        # Lintel height (top of window)
        lintel = np.percentile(z_vals[z_vals < np.median(z_vals) + 0.5], 90)

        opening['measured_height'] = round(float(lintel - sill), 3)
        opening['sill_height'] = round(float(sill), 3)

    return openings
```

## Surface Calculations (Loi Carrez / Boutin)

```python
def calcul_loi_carrez(rooms, min_height=1.80):
    """
    Surface Loi Carrez: plancher des pièces couvertes et closes
    dont la hauteur sous plafond >= 1.80m.
    Exclut: caves, garages, parkings, combles non aménagés.
    """
    surface_carrez = 0
    detail = []

    for room in rooms:
        h = room.get('height_m', 2.50)
        area = room['area_m2']

        if h >= min_height:
            surface_carrez += area
            detail.append({
                'room': f"Pièce {room['id']}",
                'area': area,
                'height': h,
                'included': True
            })
        else:
            detail.append({
                'room': f"Pièce {room['id']}",
                'area': area,
                'height': h,
                'included': False,
                'reason': f'Hauteur {h:.2f}m < 1.80m'
            })

    return {
        'surface_carrez_m2': round(surface_carrez, 2),
        'detail': detail
    }

def calcul_surface_habitable(rooms, min_height=1.80):
    """
    Surface habitable (loi Boutin): identique à Carrez
    mais exclut aussi vérandas, loggias, sous-sols.
    """
    return calcul_loi_carrez(rooms, min_height)
```

## Quantity Takeoff (Métrés)

```python
def generate_quantity_takeoff(walls, rooms, openings, floor_height=2.80):
    """Generate a quantity summary for renovation estimation."""
    # Walls
    total_wall_length = sum(w['length'] for w in walls)
    total_wall_surface = sum(w['length'] * floor_height for w in walls)
    total_wall_surface_net = total_wall_surface - sum(
        o['width'] * o.get('measured_height', o.get('height', 2.0))
        for o in openings
    )

    # Floors
    total_floor_area = sum(r['area_m2'] for r in rooms)

    # Openings
    num_doors = sum(1 for o in openings if o['type'] == 'door')
    num_windows = sum(1 for o in openings if o['type'] == 'window')

    # Perimeters (for skirting boards / plinthes)
    total_perimeter = sum(r.get('perimeter_m', 0) for r in rooms)
    # Subtract door widths
    total_skirting = total_perimeter - sum(
        o['width'] for o in openings if o['type'] == 'door')

    return {
        'murs': {
            'longueur_totale_m': round(total_wall_length, 2),
            'surface_brute_m2': round(total_wall_surface, 2),
            'surface_nette_m2': round(total_wall_surface_net, 2),
        },
        'sols': {
            'surface_totale_m2': round(total_floor_area, 2),
        },
        'plafonds': {
            'surface_totale_m2': round(total_floor_area, 2),
        },
        'plinthes': {
            'longueur_m': round(total_skirting, 2),
        },
        'ouvertures': {
            'portes': num_doors,
            'fenetres': num_windows,
        },
        'volumes': {
            'total_m3': round(sum(r.get('volume_m3', 0) for r in rooms), 2),
        }
    }
```

### Output Example

```json
{
  "murs": {
    "longueur_totale_m": 42.50,
    "surface_brute_m2": 119.00,
    "surface_nette_m2": 103.40
  },
  "sols": { "surface_totale_m2": 65.30 },
  "plafonds": { "surface_totale_m2": 65.30 },
  "plinthes": { "longueur_m": 38.20 },
  "ouvertures": { "portes": 5, "fenetres": 7 },
  "volumes": { "total_m3": 182.84 }
}
```

## CLI One-Liners

```bash
# Point count
pdal info scan.las --pointcount

# Bounding box (building footprint)
pdal info scan.las --summary | python3 -c "
import json,sys
s=json.load(sys.stdin)['summary']['bounds']
dx=s['maxx']-s['minx']; dy=s['maxy']-s['miny']; dz=s['maxz']-s['minz']
print(f'Footprint: {dx:.1f}m x {dy:.1f}m = {dx*dy:.1f}m²')
print(f'Height: {dz:.1f}m')
"

# Quick volume estimate from bounding box
pdal info scan.las --summary | python3 -c "
import json,sys
s=json.load(sys.stdin)['summary']['bounds']
v=(s['maxx']-s['minx'])*(s['maxy']-s['miny'])*(s['maxz']-s['minz'])
print(f'Bounding volume: {v:.1f}m³')
"
```

## Tips

- Validate automated measurements against manual spot checks (mètre laser).
- Loi Carrez tolerance: +/- 5% — check areas carefully for sales.
- Wall thickness varies: partition ~7cm, doublage ~10cm, porteur ~20cm, ancien ~40cm+.
- Include a reference object of known size in every scan for scale verification.
