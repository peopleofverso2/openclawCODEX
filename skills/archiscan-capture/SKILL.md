---
name: archiscan-capture
description: Plan and execute architectural survey captures — interior rooms, exterior facades, roofs. Use when asked to scan, survey, or capture a building, apartment, house, or construction site for architectural purposes. Guides sensor selection, capture protocols, and quality validation.
---

# ArchiScan Capture — Architectural Survey Protocol

Guide a complete building capture adapted to architectural needs: room-by-room interiors, facade details, roof coverage.

## Capture Strategy Selection

Ask the operator:

| Question | Options |
|---|---|
| Type de bâtiment ? | Appartement, Maison, Immeuble, Bâtiment industriel, Monument |
| Intérieur, extérieur, ou les deux ? | Intérieur seul, Extérieur seul, Complet |
| Équipement disponible ? | Smartphone, Caméra 360, LiDAR handheld, Drone, Robot quadrupède |
| Livrable attendu ? | Plans 2D, Maquette 3D, BIM/IFC, Diagnostic, Métré |
| Précision requise ? | Visuelle (~5cm), Architecturale (~2cm), Topographique (~5mm) |

Select protocol:

| Scenario | Protocol | Capture time (100m²) |
|---|---|---|
| Appartement, smartphone | Photo walk | ~20 min |
| Maison, caméra 360 | Panoramic stations | ~30 min |
| Intérieur, LiDAR handheld | Continuous walk | ~15 min |
| Extérieur, drone | Aerial grid + orbit | ~15 min |
| Complet, multi-capteur | Hybrid protocol | ~45 min |

## Protocol 1 — Photo Walk (smartphone/camera)

For interiors without LiDAR. Produces photogrammetry-ready dataset.

### Room Preparation

```
Before capture:
- Open all interior doors (maintain line of sight between rooms)
- Turn on all lights (consistent lighting)
- Remove moving objects (pets, curtains blowing, fans)
- Close exterior blinds if harsh sunlight
- Place scale references (A4 paper = 21x29.7cm) in each room
```

### Capture Pattern Per Room

```
Top view of room capture:

  ┌─────────────────────┐
  │  ↗   ↑   ↖         │
  │                     │
  │  →   ●   ←    4 corners + center  │
  │                     │
  │  ↘   ↓   ↙         │
  └────────D────────────┘
       start at door

At each position (5 per room):
  • 1 photo straight ahead
  • 1 photo left 45°
  • 1 photo right 45°
  • 1 photo ceiling (corners visible)
  • 1 photo floor (skirting boards visible)

Total: ~25 photos per room
```

### Transitions (critical)

```
Doorways: take 3 photos straddling the threshold
  • 1 from room A looking into room B
  • 1 standing IN the doorway
  • 1 from room B looking into room A

Corridors: every 1.5m, left-center-right

Stairs: every 3 steps, up and down views
```

### Naming Convention

```bash
# Auto-organize by room
mkdir -p scan/{salon,cuisine,chambre1,chambre2,sdb,wc,couloir,exterieur}
# Or use sequential naming with a shot log
```

## Protocol 2 — Panoramic Stations (caméra 360)

### Station Placement

```
Floor plan with station positions (○):

  ┌──────────┬──────────┐
  │          │          │
  │    ○     │    ○     │  Chambre 1, Chambre 2
  │          │          │
  ├────D─────┼────D─────┤
  │          │          │
  │    ○     │    ○     │  Salon, Cuisine
  │          │          │
  └──────────┴────D─────┘

Rules:
  • 1 station per room (center, 1.5m height)
  • Extra station for rooms > 20m²
  • Station in each doorway for corridor views
  • 30% overlap between adjacent station views
```

### Capture Settings

```
Resolution: maximum (8K+ if available)
HDR: ON (captures shadows and highlights)
Stabilization: tripod or monopod (mandatory)
Wait 3s after placement before trigger (vibration)
```

## Protocol 3 — LiDAR Handheld (Leica BLK2GO, iPad Pro, iPhone Pro)

### Walk Pattern

```bash
# Start at entrance, walk through every room
# Speed: 0.3-0.5 m/s (slow walk)
# Pause 2-3s at each doorway
# Close the loop: return to starting point

# If using ROS2 + handheld LiDAR:
ros2 launch slam_toolbox online_async_launch.py
ros2 bag record -o archiscan_interior /scan /odom /tf /tf_static /imu/data
```

### Walk Order (apartment example)

```
Entrance → Couloir → Salon → Cuisine → Couloir →
Chambre 1 → Couloir → Chambre 2 → Couloir → SDB →
Couloir → WC → Couloir → Entrance (close loop)
```

### Quality Checks During Capture

```
Monitor in real-time:
  • SLAM drift < 2cm (check loop closure)
  • Point density > 1000 pts/m²
  • No gaps in coverage (check dark corners)
  • Battery level (LiDAR + tablet)
```

## Protocol 4 — Drone Exterior

### Flight Plan

```bash
# Facade orbit (all 4 sides)
scripts/plan_orbit_mission.sh \
  --lat LAT --lon LON \
  --radius 15 --altitude 8 --gimbal-pitch -30 --points 32 \
  --output facade_low.plan

# Roof grid
scripts/plan_grid_mission.sh \
  --lat LAT --lon LON \
  --width 20 --height 20 --altitude 20 --overlap 80 \
  --output roof.plan

# Detail pass (manual or slow orbit at window level)
# Gimbal -15°, altitude = each floor level
```

### Facade-Specific Captures

```
Per facade:
  • 3 altitude levels: ground (2m), mid (6m), top (10m+)
  • Gimbal: -15° to -30° (not nadir)
  • Overlap: 80% horizontal
  • Include: windows, doors, ornaments, damage, joints
```

## Protocol 5 — Hybrid (Interior + Exterior)

### Execution Order

```
1. Exterior drone capture (while light is good)
   └── Facade orbits + roof grid

2. Place GCPs on facade (if survey-grade needed)
   └── Minimum 4 targets visible from both inside and outside

3. Interior capture (LiDAR or photo walk)
   └── Room by room, close the loop

4. Transition zones (windows/doors visible from both sides)
   └── Photos from inside showing window frames
   └── These enable interior-exterior alignment
```

## Post-Capture Validation

Run before leaving the site:

```bash
# Quick check: photo count per room
echo "Photos par dossier:"
for d in scan/*/; do echo "  $(basename $d): $(ls "$d"/*.jpg 2>/dev/null | wc -l) photos"; done

# Check for blurry images (if ImageMagick available)
for f in scan/**/*.jpg; do
  blur=$(identify -verbose "$f" | grep -i "deviation" | head -1 | awk '{print $2}')
  if (( $(echo "$blur < 10" | bc -l) )); then
    echo "FLOU: $f (variance=$blur)"
  fi
done

# LiDAR: check point count
pdal info scan.las --pointcount

# Minimum thresholds:
# Photos: 25/room interior, 50/facade
# LiDAR: 500 pts/m² interior, 100 pts/m² exterior
# 360: 1 pano/room + 1 pano/doorway
```

## Tips Architecture

- Photographier les **étiquettes** : compteur électrique, plaque adresse, nom sonnette (identification).
- Capturer les **détails constructifs** : type de menuiserie, matériaux murs, état toiture.
- Noter les **hauteurs sous plafond** avec un mètre laser (validation du scan).
- En copropriété, prévenir le syndic et les voisins (accès toiture, parties communes).
- Stocker les données brutes avant tout traitement — ne jamais supprimer les originaux.
