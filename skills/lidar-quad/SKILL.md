---
name: lidar-quad
description: LiDAR quadcopter end-to-end — hardware selection, payload integration, aerial LiDAR flight planning, real-time SLAM, sensor fusion (LiDAR+IMU+GNSS+Camera), point cloud pipeline, and field workflow for construction/architecture surveying. Unifies drone-mavlink + lidar-scan + photogrammetry into a single aerial LiDAR platform. Use when asked about drone LiDAR, aerial scanning, airborne point clouds, LiDAR drone missions, or choosing a LiDAR quad for BTP.
homepage: https://docs.px4.io/main/en/
metadata: {
  "openclaw": {
    "emoji": "📡",
    "requires": { "bins": ["ros2", "pdal", "python3"] },
    "depends_on": ["drone-mavlink", "lidar-scan", "photogrammetry", "archiscan-fleet"],
    "install": [
      {
        "id": "ros2-humble",
        "kind": "shell",
        "command": "sudo apt install ros-humble-desktop",
        "bins": ["ros2"],
        "label": "ROS 2 Humble"
      },
      {
        "id": "pdal",
        "kind": "shell",
        "command": "sudo apt install pdal libpdal-dev",
        "bins": ["pdal"],
        "label": "PDAL point cloud processing"
      }
    ]
  }
}
---

# LiDAR-Quad — Drone LiDAR pour le Relevé Terrain

## La vraie question : LiDAR aérien, pour quoi faire ?

Avant le hardware, la réflexion stratégique.

### LiDAR drone vs Photogrammétrie drone — choix honnête

```
                        Photogrammétrie seule       LiDAR + Camera
                        ─────────────────────       ──────────────
  Coût plateforme       2 000 – 5 000 €             15 000 – 80 000 €
  Coût traitement       Faible (ODM gratuit)        Moyen (logiciel propriétaire)
  Précision XY          2-5 cm (avec GCP)           2-3 cm (direct georef)
  Précision Z           5-10 cm                     2-5 cm
  Pénétration végétation Non                        Oui (multi-retour)
  Intérieur sombre      Non                         Oui
  Texture couleur       Excellente                  Nécessite caméra couplée
  Temps terrain         Court (photos rapides)      Court (scan rapide)
  Temps traitement      Long (heures)               Court (minutes à heures)
  Densité points        50-200 pts/m² (dense)       100-500 pts/m² (direct)
  Besoin GCP            Oui (pour cm-accuracy)      Non (IMU+GNSS intégré)
  Conditions météo      Soleil requis               Jour ou nuit, pluie légère OK
  Skill opérateur       Moyen                       Élevé (calibration, IMU)
```

### Quand le LiDAR aérien est JUSTIFIÉ (BTP / Architecture)

```
  ✅ JUSTIFIÉ                              ❌ OVERKILL
  ──────────────────────────────            ──────────────────────────────
  Terrain végétalisé (forêt, friche)        Façade bâtiment dégagée
  MNT sous canopée (sol réel)              Toiture simple
  Grande emprise (> 1 ha)                   Petit bâtiment (< 500 m²)
  Relevé topo avant terrassement            Plan de masse standard
  Suivi de chantier fréquent                Relevé unique
  Intérieur vaste + extérieur               Intérieur seul (→ terrestre)
  Nuit ou faible luminosité                 Belles conditions soleil
  Pas de GCP possible (accès limité)        GCP faciles à poser
  Livrable = MNT + courbes de niveau        Livrable = ortho + 3D visuel
  Client exige < 3cm en Z                   Tolérance 10cm OK
```

### L'équation économique réaliste

```
  ┌─────────────────────────────────────────────────────────────┐
  │  Investissement LiDAR drone (entrée de gamme)               │
  │                                                             │
  │  DJI Matrice 350 RTK + Zenmuse L2     ~  15 000 €          │
  │  Logiciel DJI Terra (licence)         ~   3 000 €/an       │
  │  Formation pilote + traitement        ~   2 000 €           │
  │  Assurance drone                      ~   1 500 €/an       │
  │  ─────────────────────────────────────────────────          │
  │  Total année 1                        ~  21 500 €           │
  │                                                             │
  │  Prix d'une prestation LiDAR externe  ~  2 000 – 5 000 €   │
  │                                                             │
  │  → Rentable à partir de 5-10 missions/an                   │
  │  → Si < 5 missions/an : sous-traiter                       │
  └─────────────────────────────────────────────────────────────┘
```

**Verdict terrain** : Pour un bureau d'étude BTP qui fait > 10 relevés/an
avec besoin de précision Z (terrassement, VRD, topographie), l'investissement
est justifié. Pour de l'architecture pure (façades, plans intérieurs),
la photogrammétrie + LiDAR terrestre couvre 90% des besoins.

---

## Plateformes LiDAR Drone — Du commercial au custom

### Tier 1 — Solutions intégrées (recommandé pour débuter)

```
  ┌──────────────────────────────────────────────────────────────┐
  │  DJI Matrice 350 RTK + Zenmuse L2                           │
  │  ════════════════════════════════                            │
  │  LiDAR:     Livox (semi-solid state), 5 retours             │
  │  Portée:    250m @ 80% réflectivité                         │
  │  Densité:   > 240 pts/m² (à 100m, 15 m/s)                  │
  │  Précision: 4cm horizontal, 3cm vertical (sans RTK)         │
  │             2cm H, 1.5cm V (avec RTK)                       │
  │  Camera:    RGB 4/3 CMOS, 20MP                              │
  │  IMU:       Intégré, calibré usine                          │
  │  GNSS:      L1/L2/L5 multi-constellation + RTK              │
  │  Poids:     905g (charge utile)                             │
  │  Autonomie: ~42 min (M350 avec L2)                          │
  │  Logiciel:  DJI Terra (traitement point cloud intégré)      │
  │  Prix:      ~ 15 000 € (L2) / déjà dispo si M350 existant  │
  │                                                             │
  │  ✅ Plug & play, calibré, logiciel inclus                   │
  │  ✅ RTK pour géoréférencement direct (pas de GCP)           │
  │  ❌ Écosystème fermé, pas de ROS natif                      │
  │  ❌ Pas de multi-retour classique (Livox = non-répétitif)   │
  └──────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────┐
  │  DJI Matrice 350 RTK + Zenmuse L1                           │
  │  ════════════════════════════════                            │
  │  LiDAR:     Livox, 3 retours                                │
  │  Portée:    190m                                            │
  │  Densité:   > 160 pts/m² (à 100m)                          │
  │  Camera:    RGB 20MP                                        │
  │  Prix:      ~ 10 000 € (plus ancien, souvent d'occasion)   │
  │                                                             │
  │  → Bon rapport qualité/prix en occasion                     │
  └──────────────────────────────────────────────────────────────┘
```

### Tier 2 — Modules LiDAR pour drone custom (intégration OpenClaw)

```
  ┌──────────────────────────────────────────────────────────────┐
  │  Livox Mid-360 + Custom Quad                                │
  │  ═══════════════════════════                                │
  │  LiDAR:     Livox Mid-360 (semi-solid state)               │
  │  FoV:       360° horizontal, -7° à +52° vertical           │
  │  Portée:    40m @ 10% / 70m @ 80%                          │
  │  Points:    200,000 pts/s                                   │
  │  Poids:     265g (capteur seul)                             │
  │  Prix:      ~ 1 200 €                                      │
  │  Interface: Ethernet 100BASE-TX                             │
  │                                                             │
  │  Companion: Raspberry Pi 5 / Jetson Orin Nano              │
  │  IMU:       VectorNav VN-100 ou Xsens MTi-3                │
  │  GNSS:      u-blox F9P (RTK capable)                       │
  │  Camera:    Sony α6000 ou RasPi HQ Camera                  │
  │                                                             │
  │  Drone:     Holybro X500 V2 / Custom 650mm                 │
  │  FC:        Pixhawk 6C (PX4)                               │
  │  Autonomie: ~15-20 min (selon batterie 6S)                  │
  │  Budget:    ~ 5 000 – 8 000 € total                        │
  │                                                             │
  │  ✅ Full ROS 2 / OpenClaw compatible                        │
  │  ✅ Données brutes accessibles                              │
  │  ✅ Budget maîtrisé                                         │
  │  ❌ Intégration IMU/GNSS manuelle                           │
  │  ❌ Calibration boresight à faire soi-même                  │
  │  ❌ Moins précis sans post-traitement PPK                   │
  └──────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────┐
  │  Ouster OS0-32 + Custom Hex                                 │
  │  ══════════════════════════                                 │
  │  LiDAR:     Ouster OS0-32 (digital spinning)               │
  │  FoV:       360° × 90° (ultra-wide)                        │
  │  Portée:    35m                                             │
  │  Points:    655,360 pts/s                                   │
  │  Poids:     447g                                            │
  │  Prix:      ~ 4 000 €                                      │
  │                                                             │
  │  → Excellente densité, bon pour intérieur + proche range   │
  │  → Plus lourd : nécessite hexacoptère ou gros quad          │
  └──────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────┐
  │  Velodyne VLP-16 (Puck) + Custom Hex                       │
  │  ══════════════════════════════════                         │
  │  LiDAR:     Velodyne Puck, 16 canaux                       │
  │  FoV:       360° × 30°                                     │
  │  Portée:    100m                                            │
  │  Points:    300,000 pts/s                                   │
  │  Poids:     830g                                            │
  │  Prix:      ~ 4 000 – 8 000 €                              │
  │                                                             │
  │  → Standard industriel, beaucoup de support SLAM            │
  │  → Lourd : hexacoptère obligatoire                          │
  └──────────────────────────────────────────────────────────────┘
```

### Tier 3 — Pro / Topographie (référence)

```
  Yellowscan Mapper+      ~ 50 000 €    (Velodyne + IMU + GNSS intégré)
  RIEGL miniVUX-3UAV      ~ 80 000 €    (meilleur multi-retour, 200m)
  Hesai XT32M2X            ~ 10 000 €    (nouveau, bon rapport qualité/prix)

  → Pour les géomètres qui facturent ces missions au quotidien.
  → Au-delà du scope OpenClaw (mais les données sortent en LAS/LAZ).
```

---

## Architecture système — Drone LiDAR OpenClaw

### Vue d'ensemble

```
                    ┌─────────────────────────────────────────────┐
                    │           Drone Quadricopter                │
                    │                                             │
                    │  ┌─────────┐  ┌──────────┐  ┌──────────┐  │
                    │  │ Pixhawk │  │ Livox    │  │ Camera   │  │
                    │  │ FC      │  │ Mid-360  │  │ RGB      │  │
                    │  │ (PX4)   │  │          │  │          │  │
                    │  └────┬────┘  └────┬─────┘  └────┬─────┘  │
                    │       │            │              │         │
                    │       │ MAVLink    │ Ethernet     │ USB    │
                    │       │            │              │         │
                    │  ┌────▼────────────▼──────────────▼─────┐  │
                    │  │         Companion Computer           │  │
                    │  │       (Jetson Orin Nano / RPi5)      │  │
                    │  │                                      │  │
                    │  │  ┌─────────┐ ┌──────┐ ┌──────────┐  │  │
                    │  │  │ ROS 2   │ │ SLAM │ │ Bag      │  │  │
                    │  │  │ Drivers │ │(opt) │ │ Recorder │  │  │
                    │  │  └─────────┘ └──────┘ └──────────┘  │  │
                    │  │                                      │  │
                    │  │  ┌──────────┐ ┌─────────────────┐   │  │
                    │  │  │ IMU      │ │ GNSS (u-blox    │   │  │
                    │  │  │ VN-100   │ │ F9P + antenne)  │   │  │
                    │  │  └──────────┘ └─────────────────┘   │  │
                    │  │                                      │  │
                    │  │  ┌──────────────────────────────┐   │  │
                    │  │  │ OpenClaw Gateway Agent       │   │  │
                    │  │  │ (telemetry → MQTT → 4G)      │   │  │
                    │  │  └──────────────────────────────┘   │  │
                    │  └──────────────────────────────────────┘  │
                    └─────────────────────────────────────────────┘
                                        │
                          WiFi / 4G     │    Données en vol :
                                        │    - Telemetry (position, batterie)
                                        │    - Status mission
                                        │    - Alertes (geofence, batterie)
                                        │
                                        │    Données post-vol :
                                        │    - ROS2 bags (LiDAR + IMU + GNSS)
                                        │    - Photos horodatées
                                        │    - Logs de vol
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │           Station Sol / Cloud               │
                    │                                             │
                    │  ┌──────────┐  ┌───────────┐  ┌─────────┐ │
                    │  │ Fleet    │  │ Post-     │  │ Livra-  │ │
                    │  │ Engine   │  │ Processing│  │ bles    │ │
                    │  │ (live)   │  │ Pipeline  │  │         │ │
                    │  └──────────┘  └───────────┘  └─────────┘ │
                    │                                             │
                    │  Monitoring     SLAM + Geo    LAS/LAZ      │
                    │  Geofence       Nettoyage     DEM/DTM      │
                    │  Alertes        Classification Ortho       │
                    │  Commandes      Fusion RGB    Mesh 3D      │
                    │                 Export        IFC/DXF      │
                    └─────────────────────────────────────────────┘
```

### Communication en vol

```yaml
# Temps réel (pendant le vol) — via archiscan-fleet
# Faible bande passante, juste le monitoring

Topics MQTT:
  archiscan/gw/{drone-id}/gps:         # Position 5 Hz
    { lat, lon, alt, speed, heading, sats, hdop }

  archiscan/gw/{drone-id}/telemetry:   # Santé 1 Hz
    { bat_v, bat_pct, signal, temp, storage_pct, lidar_status }

  archiscan/gw/{drone-id}/status:      # État mission
    { state: "scanning", mission_step: 12, total_steps: 48, eta_min: 8 }

  archiscan/gw/{drone-id}/cmd:         # Commandes
    { action: "return_home" | "pause" | "resume" | "abort" | "land" }

# Les données LiDAR NE SONT PAS streamées en vol.
# Trop de bande passante (200k pts/s × 12 bytes = 2.4 MB/s).
# Tout est enregistré en rosbag sur le SSD embarqué.
```

---

## Plan de vol LiDAR — Différent d'un plan photo

### Les paramètres qui changent

```
  ┌─────────────────────────────────────────────────────────────┐
  │  Photogrammétrie            vs.     LiDAR aérien            │
  │  ───────────────                    ──────────────          │
  │  Altitude: 30-80m                   Altitude: 40-120m       │
  │  Vitesse: 3-8 m/s                  Vitesse: 5-15 m/s       │
  │  Overlap: 75% front, 65% lat       Overlap: 30-50% lat     │
  │  Nadir camera obligatoire           Camera optionnelle      │
  │  Soleil important                   Jour/nuit OK            │
  │  Vent: < 25 km/h                   Vent: < 35 km/h         │
  │  Résolution sol: 2-3 cm/px         Densité: 100+ pts/m²    │
  │  Trigger: par distance/temps        Acquisition: continue   │
  │  Plan en grille serrée              Lignes plus espacées    │
  └─────────────────────────────────────────────────────────────┘

  Le LiDAR scanne en continu → pas besoin de trigger photo.
  L'espacement des lignes dépend du FoV et de l'altitude.
```

### Calcul de l'espacement inter-lignes

```python
# runtime/flight_planner.py
# Plan de vol LiDAR — calcul des paramètres optimaux

import math
import json
from dataclasses import dataclass, field, asdict
from typing import Optional

# ─── LiDAR Sensor Profiles ─────────────────────────────

SENSORS = {
    "livox-mid360": {
        "name": "Livox Mid-360",
        "fov_h": 360,         # degrés
        "fov_v_min": -7,      # degrés
        "fov_v_max": 52,      # degrés
        "max_range": 70,      # mètres (80% réflectivité)
        "points_per_sec": 200_000,
        "weight_g": 265,
        "returns": 1,         # Livox = single return (non-repetitive)
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
        "fov_h": 70,          # Livox pattern, effective FoV
        "fov_v_min": -70,     # Repetitive scan
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
    # Input
    sensor: str
    altitude_m: float           # AGL (Above Ground Level)
    speed_ms: float             # m/s
    area_length_m: float        # longueur zone
    area_width_m: float         # largeur zone
    overlap_pct: float = 30.0   # recouvrement latéral (%)

    # Computed
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

        # Swath width = 2 × altitude × tan(half_FoV)
        # For aerial LiDAR, we care about the across-track FoV
        if s["fov_h"] == 360:
            # Spinning/rotating LiDAR: across-track = vertical FoV projected
            half_fov = math.radians(max(abs(s["fov_v_min"]), abs(s["fov_v_max"])))
        else:
            # Fixed FoV (like DJI L2): across-track = horizontal FoV
            half_fov = math.radians(s["fov_h"] / 2)

        self.swath_width_m = 2 * self.altitude_m * math.tan(half_fov)
        # Cap to sensor max range × 2 (diameter)
        max_swath = s["max_range"] * 2
        self.swath_width_m = min(self.swath_width_m, max_swath)

        # Line spacing with overlap
        self.line_spacing_m = self.swath_width_m * (1 - self.overlap_pct / 100)

        # Number of flight lines
        self.num_lines = max(1, math.ceil(self.area_width_m / self.line_spacing_m) + 1)

        # Flight distance (lines + turns)
        turn_distance = self.line_spacing_m * 2  # Rough estimate for U-turns
        self.flight_distance_m = (
            self.num_lines * self.area_length_m +
            (self.num_lines - 1) * turn_distance
        )

        # Flight time
        self.flight_time_min = (self.flight_distance_m / self.speed_ms) / 60

        # Point density on ground
        # Points per meter of flight = pts/s ÷ speed
        pts_per_m = s["points_per_sec"] / self.speed_ms
        # Points per m² = pts_per_m ÷ swath_width
        self.point_density_m2 = pts_per_m / self.swath_width_m
        # With overlap, effective density is higher
        effective_overlap_factor = 1 + (self.overlap_pct / 100)
        self.point_density_m2 *= effective_overlap_factor

        # Data size estimate (16 bytes per point: XYZ float32 + intensity + return + timestamp)
        total_pts = s["points_per_sec"] * (self.flight_time_min * 60)
        self.data_size_gb = (total_pts * 16) / (1024 ** 3)

        # Coverage
        self.coverage_m2 = self.area_length_m * self.area_width_m

        return self

    def summary(self) -> str:
        s = SENSORS[self.sensor]
        return f"""
╔══════════════════════════════════════════════════╗
║  Plan de Vol LiDAR — {s['name']:<27s} ║
╠══════════════════════════════════════════════════╣
║  Zone:         {self.area_length_m:.0f} × {self.area_width_m:.0f} m ({self.coverage_m2:.0f} m²)
║  Altitude:     {self.altitude_m:.0f} m AGL
║  Vitesse:      {self.speed_ms:.1f} m/s ({self.speed_ms * 3.6:.1f} km/h)
║  Recouvrement: {self.overlap_pct:.0f}%
╠──────────────────────────────────────────────────╣
║  Fauchée:      {self.swath_width_m:.1f} m
║  Espacement:   {self.line_spacing_m:.1f} m
║  Lignes:       {self.num_lines}
║  Distance:     {self.flight_distance_m:.0f} m
║  Temps vol:    {self.flight_time_min:.1f} min
╠──────────────────────────────────────────────────╣
║  Densité:      {self.point_density_m2:.0f} pts/m²
║  Données:      {self.data_size_gb:.1f} GB (brut)
║  Retours:      {s['returns']}
╚══════════════════════════════════════════════════╝"""

    def to_mavlink_mission(self) -> list:
        """Generate MAVLink waypoints for a lawn-mower pattern."""
        waypoints = []
        # Start position (first line, beginning)
        start_x = 0
        start_y = 0

        for i in range(self.num_lines):
            y = start_y + i * self.line_spacing_m

            if i % 2 == 0:
                # Left to right
                wp_start = {"lat_offset": start_x, "lon_offset": y, "alt": self.altitude_m}
                wp_end = {"lat_offset": self.area_length_m, "lon_offset": y, "alt": self.altitude_m}
            else:
                # Right to left
                wp_start = {"lat_offset": self.area_length_m, "lon_offset": y, "alt": self.altitude_m}
                wp_end = {"lat_offset": start_x, "lon_offset": y, "alt": self.altitude_m}

            waypoints.append({
                "seq": len(waypoints),
                "type": "scan_line_start",
                "speed": self.speed_ms,
                **wp_start,
            })
            waypoints.append({
                "seq": len(waypoints),
                "type": "scan_line_end",
                "speed": self.speed_ms,
                **wp_end,
            })

        return waypoints


def plan_lidar_flight(
    sensor: str = "livox-mid360",
    altitude: float = 50,
    speed: float = 8,
    length: float = 200,
    width: float = 150,
    overlap: float = 30,
) -> FlightPlan:
    """Plan a LiDAR drone flight and return computed parameters."""
    plan = FlightPlan(
        sensor=sensor,
        altitude_m=altitude,
        speed_ms=speed,
        area_length_m=length,
        area_width_m=width,
        overlap_pct=overlap,
    ).compute()
    return plan


# ─── CLI ────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("=== Comparaison capteurs pour une zone 200×150m ===\n")

    for sensor_id in SENSORS:
        plan = plan_lidar_flight(
            sensor=sensor_id,
            altitude=50,
            speed=8,
            length=200,
            width=150,
            overlap=30,
        )
        print(plan.summary())
        print()

    # Example with custom params
    if len(sys.argv) > 1:
        sensor = sys.argv[1] if len(sys.argv) > 1 else "livox-mid360"
        alt = float(sys.argv[2]) if len(sys.argv) > 2 else 50
        spd = float(sys.argv[3]) if len(sys.argv) > 3 else 8
        l = float(sys.argv[4]) if len(sys.argv) > 4 else 200
        w = float(sys.argv[5]) if len(sys.argv) > 5 else 150

        plan = plan_lidar_flight(sensor, alt, spd, l, w)
        print(plan.summary())
        print(f"\nWaypoints MAVLink: {len(plan.to_mavlink_mission())} points")
        print(json.dumps(plan.to_mavlink_mission()[:4], indent=2))
```

### Exemples de plans de vol selon le cas BTP

```bash
# ── Relevé topographique grand terrain (terrassement) ──
python3 runtime/flight_planner.py livox-mid360 60 10 500 300 30
# → Altitude 60m, vitesse 10 m/s, zone 500×300m, overlap 30%
# → ~15 lignes, ~12 min de vol, ~120 pts/m²

# ── Relevé précis petit bâtiment ──
python3 runtime/flight_planner.py livox-mid360 30 5 100 80 40
# → Altitude 30m, vitesse 5 m/s, zone 100×80m, overlap 40%
# → ~8 lignes, ~4 min de vol, ~250 pts/m²

# ── Scan façades (orbite, pas grid) ──
# Pour les façades → utiliser un plan orbital, pas un grid
# Voir section "Mission types" ci-dessous.
```

---

## Missions types — au-delà du grid

### 1. Grid classique (topographie, terrain)

```
    ──────────────────▶
    ◀──────────────────
    ──────────────────▶
    ◀──────────────────
    ──────────────────▶

  Espacement régulier, altitude constante.
  Usage: MNT, courbes de niveau, cubature.
```

### 2. Double grid croisé (bâtiment + terrain)

```
    ──────────────────▶       │ │ │ │ │
    ◀──────────────────       │ │ │ │ │
    ──────────────────▶       ▼ ▼ ▼ ▼ ▼
    ◀──────────────────       ▲ ▲ ▲ ▲ ▲
    ──────────────────▶       │ │ │ │ │

    Pass 1 (Est-Ouest)   +   Pass 2 (Nord-Sud)

  Double densité, meilleur coverage des façades verticales.
  Usage: Bâtiment complexe, toitures multi-pans.
```

### 3. Orbite (façade, monument, structure)

```
              ┌─────────┐
          ╱   │Bâtiment │   ╲
        ╱     │         │     ╲
      ◀       │         │       ▲
        ╲     │         │     ╱
          ╲   │         │   ╱
              └─────────┘

  Cercle autour du sujet à distance/altitude constante.
  LiDAR + Camera pour texture.
  Usage: Façade complète, monument, pylône, silo.
```

### 4. Corridor (route, voie ferrée, pipeline)

```
    ════════════════════════════════════════▶

  Ligne unique ou double avec overlap.
  Haute vitesse (10-15 m/s).
  Usage: Route, voie ferrée, berge, réseau.
```

### 5. Terrain + intérieur combiné (digital twin complet)

```
    Phase 1: Drone LiDAR — extérieur + toiture
    ──────────────────▶
    ◀──────────────────
    ──────────────────▶

    Phase 2: Robot terrestre — intérieur
    ┌──────────────┐
    │ ┌──┐  ┌──┐   │
    │ │  │  │  │   │    ← quadruped-ctrl + lidar-scan
    │ └──┘  └──┘   │
    │    ┌──────┐  │
    │    │      │  │
    │    └──────┘  │
    └──────────────┘

    Phase 3: Fusion — cloud2bim
    Nuage extérieur + nuage intérieur → ICP registration → Modèle complet
```

---

## Pipeline de traitement post-vol

### Étapes

```
  1. TRANSFERT          SSD drone → Workstation
  │                     (rosbag ou fichiers .lvx2 / .las bruts)
  │
  2. TRAJECTOGRAPHIE    IMU + GNSS → trajectoire précise
  │                     (POSPac, Inertial Explorer, ou custom PPK)
  │
  3. GÉORÉFÉRENCEMENT   Appliquer trajectoire au nuage brut
  │                     (direct georeferencing)
  │
  4. NETTOYAGE          Supprimer bruit, outliers, points parasites
  │                     (PDAL filters)
  │
  5. CLASSIFICATION     Sol / Végétation / Bâtiment / Autre
  │                     (PDAL SMRF + manual cleanup)
  │
  6. PRODUITS DÉRIVÉS   MNT, MNS, Ortho, Mesh, Plans
  │                     (PDAL, Open3D, cloud2bim)
  │
  7. LIVRAISON          LAS/LAZ + DEM GeoTIFF + DXF + IFC
                        (archiscan-report)
```

### Scripts de traitement (PDAL + Open3D)

```bash
# ── Étape 1 : Conversion rosbag → LAS ──────────────────

# Si données Livox (.lvx2)
# Utiliser livox_ros_driver2 pour convertir en rosbag,
# puis ros2_to_las.py pour extraire les points

# Si données DJI Terra : export direct en LAS/LAZ

# ── Étape 2 : Nettoyage PDAL ───────────────────────────

# Pipeline PDAL pour nettoyage aérien standard
cat > pipeline_clean.json << 'PIPELINE'
{
  "pipeline": [
    {
      "type": "readers.las",
      "filename": "raw_scan.las"
    },
    {
      "type": "filters.elm",
      "comment": "Extended Local Minimum — supprime les points aberrants bas"
    },
    {
      "type": "filters.outlier",
      "method": "statistical",
      "mean_k": 12,
      "multiplier": 2.2,
      "comment": "Supprime les outliers statistiques"
    },
    {
      "type": "filters.range",
      "limits": "Z[-50:500]",
      "comment": "Filtre altitude aberrante"
    },
    {
      "type": "filters.returns",
      "groups": "first,last,only",
      "comment": "Garde premier et dernier retour"
    },
    {
      "type": "writers.las",
      "filename": "cleaned.las",
      "compression": "laszip",
      "a_srs": "EPSG:2154",
      "comment": "Export en Lambert-93 (France)"
    }
  ]
}
PIPELINE

pdal pipeline pipeline_clean.json

# ── Étape 3 : Classification sol ───────────────────────

cat > pipeline_classify.json << 'PIPELINE'
{
  "pipeline": [
    "cleaned.las",
    {
      "type": "filters.assign",
      "assignment": "Classification[:]=0"
    },
    {
      "type": "filters.smrf",
      "scalar": 1.2,
      "slope": 0.2,
      "threshold": 0.45,
      "window": 16,
      "comment": "Simple Morphological Filter — classifie le sol (class 2)"
    },
    {
      "type": "filters.range",
      "limits": "Classification[2:2]",
      "tag": "ground_only"
    },
    {
      "type": "writers.las",
      "filename": "ground.las",
      "compression": "laszip"
    }
  ]
}
PIPELINE

pdal pipeline pipeline_classify.json

# ── Étape 4 : MNT (Modèle Numérique de Terrain) ──────

cat > pipeline_dem.json << 'PIPELINE'
{
  "pipeline": [
    "ground.las",
    {
      "type": "writers.gdal",
      "filename": "mnt.tif",
      "resolution": 0.25,
      "output_type": "idw",
      "gdaldriver": "GTiff",
      "gdalopts": "COMPRESS=DEFLATE",
      "comment": "MNT GeoTIFF résolution 25cm"
    }
  ]
}
PIPELINE

pdal pipeline pipeline_dem.json

# ── Étape 5 : MNS (Modèle Numérique de Surface) ──────

cat > pipeline_dsm.json << 'PIPELINE'
{
  "pipeline": [
    "cleaned.las",
    {
      "type": "writers.gdal",
      "filename": "mns.tif",
      "resolution": 0.25,
      "output_type": "max",
      "gdaldriver": "GTiff",
      "gdalopts": "COMPRESS=DEFLATE",
      "comment": "MNS = point le plus haut par cellule"
    }
  ]
}
PIPELINE

pdal pipeline pipeline_dsm.json

# ── Bonus : Courbes de niveau depuis le MNT ───────────

gdal_contour -a elevation -i 0.5 mnt.tif courbes_50cm.shp
gdal_contour -a elevation -i 1.0 mnt.tif courbes_1m.shp
# → Import dans QGIS ou export DXF
ogr2ogr -f DXF courbes_1m.dxf courbes_1m.shp
```

### Fusion multi-sources (drone + terrestre)

```python
# runtime/fusion.py
# Fusion nuage drone (extérieur) + nuage robot (intérieur)

import open3d as o3d
import numpy as np

def load_and_clean(path, voxel_size=0.05):
    """Load point cloud, downsample, remove outliers."""
    pcd = o3d.io.read_point_cloud(path)
    print(f"  Loaded {path}: {len(pcd.points)} points")

    # Downsample
    pcd = pcd.voxel_down_sample(voxel_size)

    # Remove outliers
    pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
    print(f"  After cleaning: {len(pcd.points)} points")

    return pcd


def register_clouds(source, target, voxel_size=0.1):
    """
    Register two point clouds using Global + ICP refinement.
    source: interior scan (robot)
    target: exterior scan (drone)
    """
    # Compute normals
    source.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.3, max_nn=30))
    target.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.3, max_nn=30))

    # FPFH features for global registration
    source_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        source, o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 5, max_nn=100)
    )
    target_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        target, o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 5, max_nn=100)
    )

    # Global registration (RANSAC)
    result_global = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        source, target, source_fpfh, target_fpfh,
        mutual_filter=True,
        max_correspondence_distance=voxel_size * 2,
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(),
        ransac_n=3,
        checkers=[
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(voxel_size * 2),
        ],
        criteria=o3d.pipelines.registration.RANSACConvergenceCriteria(100000, 0.999),
    )

    print(f"  Global registration fitness: {result_global.fitness:.3f}")

    # ICP refinement
    result_icp = o3d.pipelines.registration.registration_icp(
        source, target,
        max_correspondence_distance=voxel_size * 0.5,
        init=result_global.transformation,
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPlane(),
    )

    print(f"  ICP refinement fitness: {result_icp.fitness:.3f}")
    print(f"  RMSE: {result_icp.inlier_rmse:.4f} m")

    return result_icp.transformation


def fuse_drone_and_robot(
    drone_cloud_path: str,
    robot_cloud_path: str,
    output_path: str = "fused_complete.ply",
    voxel_size: float = 0.05,
):
    """
    Complete fusion pipeline:
    1. Load and clean both clouds
    2. Register (align) robot scan to drone scan
    3. Merge into single cloud
    4. Final cleanup
    """
    print("=== Fusion drone + robot ===")

    print("\n[1/4] Loading clouds...")
    drone_pcd = load_and_clean(drone_cloud_path, voxel_size)
    robot_pcd = load_and_clean(robot_cloud_path, voxel_size)

    print("\n[2/4] Registering robot → drone...")
    transform = register_clouds(robot_pcd, drone_pcd, voxel_size)

    print("\n[3/4] Applying transform and merging...")
    robot_pcd.transform(transform)

    # Merge
    merged = drone_pcd + robot_pcd

    print("\n[4/4] Final cleanup...")
    merged = merged.voxel_down_sample(voxel_size)
    merged, _ = merged.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)

    # Save
    o3d.io.write_point_cloud(output_path, merged)
    print(f"\n✓ Fused cloud saved: {output_path}")
    print(f"  Total points: {len(merged.points)}")

    return merged


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        fuse_drone_and_robot(sys.argv[1], sys.argv[2],
                             sys.argv[3] if len(sys.argv) > 3 else "fused.ply")
    else:
        print("Usage: python3 fusion.py <drone_cloud.ply> <robot_cloud.ply> [output.ply]")
```

---

## Intégration OpenClaw — Fleet Entity

### Déclarer le drone LiDAR dans fleet.yml

```yaml
# Dans archiscan-fleet/fleet.yml — section entities

entities:
  - id: gw-04
    name: "LiDAR-Quad-01"
    type: drone
    capabilities:
      - lidar       # Livox Mid-360
      - camera      # Sony α6000
      - rtk         # u-blox F9P
      - slam        # FAST-LIO2 embarqué
    hardware:
      frame: "Holybro X500 V2"
      fc: "Pixhawk 6C"
      firmware: "PX4 1.14"
      lidar: "Livox Mid-360"
      imu: "VectorNav VN-100"
      gnss: "u-blox F9P"
      companion: "Jetson Orin Nano 8GB"
      battery: "6S 5000mAh"
      auw_g: 3200            # All-Up Weight
      max_flight_min: 18
    home_zone: zone-chantier-a
    battery_thresholds:
      low: 30                 # Alerte + retour base
      critical: 15            # Atterrissage immédiat
    gateway:
      type: companion         # Agent OpenClaw sur Jetson
      connection: wifi        # WiFi 5GHz vers station sol
      fallback: 4g            # 4G si WiFi perdu
      mqtt_prefix: "archiscan/gw/gw-04"

# Zone de vol
zones:
  - id: zone-chantier-a
    name: "Chantier Résidence Eole"
    type: polygon
    coordinates:              # GeoJSON [lon, lat]
      - [2.3510, 48.8565]
      - [2.3530, 48.8565]
      - [2.3530, 48.8580]
      - [2.3510, 48.8580]
    ceiling_m: 120            # Plafond altitude
    buffer_m: 15              # Marge GPS
    forbidden_hours: []       # Pas de restriction horaire

# Mission LiDAR scan
missions:
  - id: scan-terrain-eole
    name: "Relevé topo pré-terrassement"
    entity: gw-04
    type: lidar_grid
    preconditions:
      - battery > 80
      - wind_kmh < 30
      - gps_fix == "rtk_fixed"
    params:
      altitude_m: 50
      speed_ms: 8
      overlap_pct: 30
      sensor: livox-mid360
      record_camera: true      # Photos synchronisées
      record_imu: true         # Données IMU brutes
    steps:
      - action: arm
      - action: takeoff
        alt: 50
      - action: start_lidar_recording
      - action: execute_grid     # Calculé par flight_planner.py
      - action: stop_lidar_recording
      - action: return_home
      - action: land
    on_complete:
      - publish: archiscan/fleet/missions
        payload: { mission: "scan-terrain-eole", status: "complete" }
      - voice: "Scan terminé. Données prêtes pour transfert."
```

### Voice-Link integration

```yaml
# Commandes vocales spécifiques au LiDAR drone
# À ajouter dans voice-link/runtime/intents.yml

  - id: start_scan
    patterns:
      - "lance le scan"
      - "démarre le scan lidar"
      - "scan le terrain"
      - "commence le relevé"
    target_type: drone
    action: start_mission
    mission_type: lidar_grid
    confirm: true
    response: "Scan LiDAR lancé"

  - id: lidar_status
    patterns:
      - "état du lidar"
      - "lidar status"
      - "le lidar tourne"
    action: query_lidar_status
    response_template: "LiDAR {status}, {points_per_sec} points par seconde"

  - id: storage_check
    patterns:
      - "stockage"
      - "espace disque"
      - "combien de place"
    action: query_storage
    response_template: "{free_gb} giga libres, {recording_min} minutes d'enregistrement"
```

---

## Checklist terrain — Jour du vol

### Pré-vol (T-30 min)

```
  MATÉRIEL
  □ Drone assemblé, hélices serrées
  □ Batterie chargée > 95%
  □ Batterie de rechange
  □ LiDAR fixé, connecteur Ethernet branché
  □ Camera fixée, carte SD vide
  □ Antenne GNSS correctement orientée (ciel dégagé)
  □ Companion (Jetson) démarré, LED verte
  □ SSD embarqué : espace libre > 50 GB

  LOGICIEL
  □ ROS 2 drivers lancés (LiDAR + IMU + GNSS)
  □ Fleet agent connecté (MQTT → station sol)
  □ Plan de vol chargé (waypoints vérifiés sur carte)
  □ Geofence activé dans fleet engine
  □ RTK base station opérationnelle (si applicable)
  □ Correction NTRIP active (vérifier fix RTK)

  RÉGLEMENTAIRE
  □ Déclaration de vol enregistrée (AlphaTango / DGAC)
  □ Zone de vol vérifiée (pas de zone P/R/D)
  □ NOTAM consultés
  □ Assurance à jour
  □ Brevet pilote (catégorie Spécifique si > 25kg ou zone urbaine)
  □ Briefing sécurité avec équipe terrain
```

### Vol (T-0)

```
  1. □ Vérifier vent < 30 km/h (anémomètre)
  2. □ Dégager la zone de décollage (5m radius)
  3. □ Démarrer l'enregistrement LiDAR (rosbag record)
  4. □ Arm + Takeoff (vocal: "openclaw, décolle")
  5. □ Vérifier altitude + GPS fix sur dashboard
  6. □ Lancer la mission (vocal: "openclaw, lance le scan")
  7. □ Monitorer : batterie, storage, geofence, SLAM
  8. □ À batterie 30% : retour auto (ou vocal: "openclaw, rentre")
  9. □ Landing + Disarm
  10. □ Arrêter l'enregistrement LiDAR
  11. □ Vérifier que les données sont sur le SSD
```

### Post-vol (T+15 min)

```
  1. □ Transférer les données : SSD → Workstation (USB 3.0)
  2. □ Vérifier intégrité des fichiers (ros2 bag info)
  3. □ Quick preview du nuage (pdal info + CloudCompare)
  4. □ Lancer le pipeline de traitement (nettoyage → classification → MNT)
  5. □ Si 2e vol nécessaire : changer batterie, répéter
  6. □ Ranger le matériel
  7. □ Envoyer le rapport de vol (archiscan-report)
```

---

## Calibration boresight — le point critique

C'est ce qui fait la différence entre 10cm et 2cm de précision.
Le boresight = l'angle entre l'axe du LiDAR et l'axe de l'IMU.

### Pourquoi c'est important

```
  Si le boresight est mal calibré de 0.1° :

  À 50m d'altitude → erreur = 50 × tan(0.1°) = 8.7 cm
  À 100m d'altitude → erreur = 17.5 cm

  0.1° ça semble rien. Mais c'est la différence entre
  un relevé exploitable et un relevé à refaire.
```

### Procédure de calibration

```
  1. Choisir un site de calibration :
     - Terrain plat avec des bâtiments à arêtes franches
     - Des lignes droites visibles (murs, bordures, toiture)
     - Pas de végétation

  2. Voler 4 lignes croisées :
     ──────────▶  (ligne 1, Est)
     ◀──────────  (ligne 2, Ouest — même couloir, sens inverse)
     │            (ligne 3, Nord)
     ▼            (ligne 4, Sud — même couloir, sens inverse)

  3. Comparer les nuages des 4 passes :
     - Les arêtes de bâtiment doivent se superposer
     - Décalage visible = erreur boresight

  4. Ajuster les angles (roll, pitch, heading) :
     - Logiciel dédié (LiDAR360, POSPac)
     - Ou itératif : ajuster → revoler → vérifier

  5. Sauvegarder les valeurs de calibration :
     - Ne changent PAS tant qu'on ne démonte pas le LiDAR
     - Refaire si choc mécanique sur le payload
```

```python
# runtime/boresight_check.py
# Vérification rapide de l'alignement boresight
# Compare deux passes opposées sur le même couloir

import open3d as o3d
import numpy as np

def check_boresight(pass_forward: str, pass_reverse: str, threshold_m: float = 0.05):
    """
    Quick boresight check by comparing forward/reverse passes.
    Returns the mean offset between the two clouds.
    If offset > threshold, boresight needs recalibration.
    """
    pcd_fwd = o3d.io.read_point_cloud(pass_forward)
    pcd_rev = o3d.io.read_point_cloud(pass_reverse)

    # Downsample for speed
    pcd_fwd = pcd_fwd.voxel_down_sample(0.1)
    pcd_rev = pcd_rev.voxel_down_sample(0.1)

    # Compute distance from each point in fwd to nearest point in rev
    dists = pcd_fwd.compute_point_cloud_distance(pcd_rev)
    dists = np.asarray(dists)

    mean_offset = np.mean(dists)
    median_offset = np.median(dists)
    p95_offset = np.percentile(dists, 95)

    print(f"Boresight check:")
    print(f"  Mean offset:   {mean_offset:.4f} m ({mean_offset*100:.1f} cm)")
    print(f"  Median offset: {median_offset:.4f} m ({median_offset*100:.1f} cm)")
    print(f"  95th pctile:   {p95_offset:.4f} m ({p95_offset*100:.1f} cm)")

    if mean_offset > threshold_m:
        print(f"  ⚠ BORESIGHT RECALIBRATION NEEDED (>{threshold_m*100:.0f}cm)")
        return False
    else:
        print(f"  ✓ Boresight OK (<{threshold_m*100:.0f}cm)")
        return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        check_boresight(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python3 boresight_check.py <pass_forward.ply> <pass_reverse.ply>")
```

---

## Sécurité — règles non négociables

### Règles automatiques (fleet engine)

```yaml
# Ces règles sont TOUJOURS actives dans archiscan-fleet

rules:
  # Retour auto si batterie faible
  - trigger: battery_below
    threshold: 30
    entity_type: drone
    actions:
      - command: return_home
      - alert: sms
      - voice: "Batterie faible, retour base"

  # Atterrissage immédiat si batterie critique
  - trigger: battery_below
    threshold: 15
    entity_type: drone
    actions:
      - command: land
      - alert: sms
      - voice: "Batterie critique, atterrissage immédiat"

  # Retour si vent trop fort
  - trigger: wind_above
    threshold_kmh: 35
    entity_type: drone
    actions:
      - command: return_home
      - voice: "Vent fort, retour base"

  # Retour si sortie de zone
  - trigger: geofence_breach
    actions:
      - command: return_home
      - alert: sms
      - voice: "Hors zone, retour base"

  # Atterrissage si altitude dépassée
  - trigger: altitude_above
    threshold_m: 120    # Réglementaire France catégorie Ouverte
    actions:
      - command: descend
        target_alt: 100
      - voice: "Altitude max dépassée"

  # Arrêt si perte de signal GNSS
  - trigger: gps_fix_lost
    timeout_s: 10
    actions:
      - command: hover     # Maintien position sur inertiel
      - alert: dashboard
      - voice: "Perte GPS, hover en attente"

  # Perte de contact companion
  - trigger: heartbeat_lost
    timeout_s: 30
    actions:
      - command: return_home   # Failsafe PX4
      - alert: sms
```

### Ce que le LiDAR ne change PAS à la sécurité

```
  Le LiDAR est un capteur passif. Il ne modifie pas :
  - Les règles de vol (altitude, distance, zones)
  - La gestion batterie (même drone)
  - Le failsafe (même FC PX4/ArduPilot)
  - La réglementation (même catégorie de vol)
  - Le besoin de pilote qualifié (même responsabilité)

  Ce qu'il ajoute :
  - Poids supplémentaire → autonomie réduite (attention !)
  - Consommation électrique du capteur (~15W)
  - SSD qui doit ne PAS être plein (vérifier avant vol)
  - IMU qui doit être chaud (warm-up 5-10 min avant vol)
```

---

## Résumé — quand utiliser quel skill

```
  Besoin                         Skill(s) à utiliser
  ──────────────────────────     ────────────────────────────────
  Piloter un drone (MAVLink)     drone-mavlink
  Scanner LiDAR (terrestre)      lidar-scan
  Photos → 3D                    photogrammetry
  Nuage → Plans/BIM             archiscan-cloud2bim
  Orchestrer une flotte          archiscan-fleet
  Workflow complet scan→model    digital-twin

  Drone + LiDAR embarqué         lidar-quad (CE SKILL)
  ├── Quel hardware choisir ?    → Section "Plateformes"
  ├── Planifier un vol LiDAR ?   → flight_planner.py
  ├── Traiter les données ?      → Section "Pipeline post-vol"
  ├── Fusionner drone+robot ?    → fusion.py
  ├── Calibrer le boresight ?    → boresight_check.py
  └── Sécurité & réglementation  → Section "Sécurité"
```

lidar-quad est le **chaînon manquant** qui unifie drone-mavlink (le vol),
lidar-scan (le capteur) et photogrammetry (la caméra) en une seule
plateforme aérienne cohérente pour le BTP.
