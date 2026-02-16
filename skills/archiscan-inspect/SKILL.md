---
name: archiscan-inspect
description: Building inspection and diagnostics from scan data — crack detection, moisture analysis, thermal imaging, facade pathology, structural assessment. Use when asked to inspect, diagnose, check condition, detect defects, or assess a building's health from photos, scans, or thermal images.
---

# ArchiScan Inspect — Building Diagnostics

Analyze scan data, photos, and thermal images to detect building pathologies and produce diagnostic assessments.

## Diagnostic Categories

| Category | Input | Detection Method |
|---|---|---|
| Fissures / cracks | Photos haute-résolution | OpenCV edge detection + classification |
| Humidité / moisture | Photos + thermal IR | Color analysis + thermal delta |
| Déformation / deformation | Point cloud | Plane fitting + deviation map |
| Façade pathology | Drone photos | Grid analysis + defect mapping |
| Thermal bridges | Thermal images (FLIR) | Temperature gradient analysis |
| Planéité / flatness | Point cloud | Surface deviation from ideal plane |

## Crack Detection (Photos)

```python
#!/usr/bin/env python3
"""Detect cracks in building facade/wall photos using OpenCV."""
import cv2
import numpy as np

def detect_cracks(image_path, output_path="cracks_detected.jpg"):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Enhance contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)

    # Edge detection (Canny)
    edges = cv2.Canny(blurred, 50, 150)

    # Morphological operations to connect crack fragments
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=1)
    edges = cv2.erode(edges, kernel, iterations=1)

    # Find contours (potential cracks)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    cracks = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        perimeter = cv2.arcLength(cnt, True)

        if perimeter == 0:
            continue

        # Crack = high perimeter-to-area ratio (thin and long)
        ratio = perimeter ** 2 / (area + 1)

        if ratio > 100 and perimeter > 50:
            # Classify severity by length
            x, y, w, h = cv2.boundingRect(cnt)
            length = max(w, h)

            severity = "légère" if length < 100 else "modérée" if length < 300 else "sévère"
            color = (0,255,0) if severity == "légère" else \
                    (0,165,255) if severity == "modérée" else (0,0,255)

            cv2.drawContours(img, [cnt], -1, color, 2)
            cv2.putText(img, severity, (x, y-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            cracks.append({
                'bbox': [int(x), int(y), int(w), int(h)],
                'length_px': int(length),
                'severity': severity
            })

    cv2.imwrite(output_path, img)
    print(f"Detected {len(cracks)} cracks: "
          f"{sum(1 for c in cracks if c['severity']=='légère')} légères, "
          f"{sum(1 for c in cracks if c['severity']=='modérée')} modérées, "
          f"{sum(1 for c in cracks if c['severity']=='sévère')} sévères")
    return cracks

# Usage
cracks = detect_cracks("facade_photo.jpg")
```

## Facade Deformation (Point Cloud)

```python
"""Detect facade deformation by comparing to ideal plane."""
import open3d as o3d
import numpy as np

def analyze_facade_flatness(pcd_path, max_deviation_cm=2.0):
    pcd = o3d.io.read_point_cloud(pcd_path)
    points = np.asarray(pcd.points)

    # Fit best plane (RANSAC)
    plane_model, inliers = pcd.segment_plane(
        distance_threshold=0.01, ransac_n=3, num_iterations=1000)
    a, b, c, d = plane_model

    # Compute distance of each point to ideal plane
    distances = np.abs(a*points[:,0] + b*points[:,1] + c*points[:,2] + d)
    distances_cm = distances * 100

    # Statistics
    stats = {
        'mean_deviation_cm': round(float(np.mean(distances_cm)), 2),
        'max_deviation_cm': round(float(np.max(distances_cm)), 2),
        'std_deviation_cm': round(float(np.std(distances_cm)), 2),
        'points_over_threshold': int(np.sum(distances_cm > max_deviation_cm)),
        'percent_over_threshold': round(
            float(np.sum(distances_cm > max_deviation_cm)) / len(points) * 100, 1),
    }

    # Colorize by deviation (green=ok, red=deformed)
    colors = np.zeros((len(points), 3))
    norm_dist = np.clip(distances_cm / (max_deviation_cm * 2), 0, 1)
    colors[:, 0] = norm_dist       # Red channel = deviation
    colors[:, 1] = 1 - norm_dist   # Green channel = OK
    pcd.colors = o3d.utility.Vector3dVector(colors)

    output = pcd_path.replace('.ply', '_deviation.ply')
    o3d.io.write_point_cloud(output, pcd)

    print(f"Facade flatness analysis:")
    print(f"  Mean deviation: {stats['mean_deviation_cm']:.2f} cm")
    print(f"  Max deviation:  {stats['max_deviation_cm']:.2f} cm")
    print(f"  Over {max_deviation_cm}cm:   {stats['percent_over_threshold']:.1f}%")
    print(f"  Deviation map saved: {output}")

    return stats

# Thresholds (DTU 26.1 / NF P 18-201):
# Enduit: < 5mm/m (very flat)
# Maçonnerie: < 10mm/m
# Béton brut: < 15mm/m
```

## Thermal Analysis (FLIR images)

```python
"""Analyze thermal images for heat loss and thermal bridges."""
import cv2
import numpy as np

def analyze_thermal_image(thermal_path, output_path="thermal_analysis.jpg",
                           cold_threshold=15.0, hot_threshold=25.0):
    """
    Analyze a thermal image (radiometric JPEG from FLIR).
    Detects cold spots (heat loss) and thermal bridges.
    """
    img = cv2.imread(thermal_path)
    # Convert to grayscale (thermal images map temp to intensity)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Normalize to temperature range (approximate)
    # Real radiometric data needs FLIR SDK — this is visual approximation
    temp_min, temp_max = cold_threshold - 5, hot_threshold + 5
    temp_map = gray.astype(float) / 255 * (temp_max - temp_min) + temp_min

    # Detect cold zones (potential thermal bridges / heat loss)
    cold_mask = temp_map < cold_threshold
    hot_mask = temp_map > hot_threshold

    # Find cold zone contours
    cold_binary = (cold_mask * 255).astype(np.uint8)
    contours, _ = cv2.findContours(cold_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    zones = []
    result = img.copy()
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 500:  # Ignore tiny spots
            x, y, w, h = cv2.boundingRect(cnt)
            avg_temp = np.mean(temp_map[y:y+h, x:x+w])

            cv2.rectangle(result, (x, y), (x+w, y+h), (255, 0, 0), 2)
            cv2.putText(result, f"{avg_temp:.1f}C", (x, y-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

            zones.append({
                'type': 'cold_spot',
                'bbox': [int(x), int(y), int(w), int(h)],
                'avg_temp': round(float(avg_temp), 1),
                'area_px': int(area),
                'diagnosis': classify_thermal_defect(avg_temp, area)
            })

    cv2.imwrite(output_path, result)
    return zones

def classify_thermal_defect(temp, area):
    """Classify thermal anomaly."""
    if temp < 10:
        return "Pont thermique sévère — déperdition importante"
    elif temp < 14:
        return "Pont thermique — isolation insuffisante"
    elif temp < 17:
        return "Zone froide — vérifier isolation"
    else:
        return "Anomalie légère"
```

## Moisture Detection (Visual)

```python
def detect_moisture_stains(image_path, output_path="moisture_detected.jpg"):
    """Detect moisture/water stains via color anomaly detection."""
    img = cv2.imread(image_path)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Moisture stains are typically darker with yellow-brown tones
    # HSV ranges for common stain colors
    stain_ranges = [
        # Yellow-brown stains
        ((10, 30, 50), (30, 200, 180)),
        # Dark gray-green (mold)
        ((35, 20, 20), (85, 150, 100)),
    ]

    combined_mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lower, upper in stain_ranges:
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        combined_mask = cv2.bitwise_or(combined_mask, mask)

    # Clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    stains = []
    result = img.copy()
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 1000:
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(result, (x, y), (x+w, y+h), (0, 0, 255), 2)
            cv2.putText(result, "Humidite", (x, y-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            stains.append({
                'bbox': [int(x), int(y), int(w), int(h)],
                'area_px': int(area),
                'type': 'moisture_stain'
            })

    cv2.imwrite(output_path, result)
    print(f"Detected {len(stains)} moisture zones")
    return stains
```

## Floor Levelness

```python
def analyze_floor_level(points, room_bounds, grid_resolution=0.2):
    """Check floor levelness by measuring Z at grid points."""
    x_min, y_min = room_bounds[0]
    x_max, y_max = room_bounds[1]

    grid_x = np.arange(x_min, x_max, grid_resolution)
    grid_y = np.arange(y_min, y_max, grid_resolution)

    z_map = np.full((len(grid_y), len(grid_x)), np.nan)

    for iy, y in enumerate(grid_y):
        for ix, x in enumerate(grid_x):
            mask = (np.abs(points[:,0] - x) < grid_resolution/2) & \
                   (np.abs(points[:,1] - y) < grid_resolution/2)
            if mask.sum() > 5:
                z_map[iy, ix] = np.percentile(points[mask, 2], 5)

    valid = z_map[~np.isnan(z_map)]
    z_ref = np.median(valid)
    deviations = z_map - z_ref

    return {
        'max_high_cm': round(float(np.nanmax(deviations)) * 100, 2),
        'max_low_cm': round(float(np.nanmin(deviations)) * 100, 2),
        'range_cm': round(float(np.nanmax(deviations) - np.nanmin(deviations)) * 100, 2),
        'std_cm': round(float(np.nanstd(valid - z_ref)) * 100, 2),
        # NF P 18-201: tolérance 7mm sous règle de 2m
        'within_norm': bool(np.nanmax(np.abs(deviations)) * 100 < 0.7)
    }
```

## Diagnostic Summary Generator

```python
def generate_diagnostic_summary(cracks, thermal_zones, moisture, flatness, floor_level):
    """Compile all inspections into a structured diagnostic."""
    issues = []

    # Cracks
    severe_cracks = [c for c in cracks if c['severity'] == 'sévère']
    if severe_cracks:
        issues.append({
            'category': 'Structure',
            'severity': 'ALERTE',
            'finding': f"{len(severe_cracks)} fissure(s) sévère(s) détectée(s)",
            'recommendation': "Expertise structurelle recommandée sous 30 jours"
        })

    # Thermal
    bridges = [z for z in thermal_zones if 'sévère' in z.get('diagnosis', '')]
    if bridges:
        issues.append({
            'category': 'Isolation',
            'severity': 'IMPORTANT',
            'finding': f"{len(bridges)} pont(s) thermique(s) sévère(s)",
            'recommendation': "Audit énergétique recommandé, isolation à renforcer"
        })

    # Moisture
    if moisture:
        issues.append({
            'category': 'Humidité',
            'severity': 'IMPORTANT' if len(moisture) > 3 else 'MINEUR',
            'finding': f"{len(moisture)} zone(s) d'humidité détectée(s)",
            'recommendation': "Recherche de fuite, vérification ventilation (VMC)"
        })

    # Flatness
    if flatness and flatness['percent_over_threshold'] > 10:
        issues.append({
            'category': 'Déformation',
            'severity': 'IMPORTANT',
            'finding': f"Déformation facade: max {flatness['max_deviation_cm']}cm",
            'recommendation': "Vérification structurelle, possible tassement"
        })

    # Floor
    if floor_level and not floor_level['within_norm']:
        issues.append({
            'category': 'Planéité sol',
            'severity': 'MINEUR',
            'finding': f"Dénivellation sol: {floor_level['range_cm']:.1f}cm",
            'recommendation': "Ragréage nécessaire avant pose de revêtement"
        })

    return {
        'total_issues': len(issues),
        'critical': sum(1 for i in issues if i['severity'] == 'ALERTE'),
        'important': sum(1 for i in issues if i['severity'] == 'IMPORTANT'),
        'minor': sum(1 for i in issues if i['severity'] == 'MINEUR'),
        'issues': issues
    }
```

## Tips

- Fissures < 0.2mm = cosmétique. 0.2-2mm = à surveiller. > 2mm = structurel.
- Photos thermiques : capturer tôt le matin (delta max intérieur/extérieur).
- Humidité : confirmer avec un hygromètre (l'analyse photo est indicative).
- Toujours croiser les résultats avec une inspection visuelle humaine.
- Ce skill produit des **pré-diagnostics** — pour un diagnostic officiel, faire appel à un expert certifié.
