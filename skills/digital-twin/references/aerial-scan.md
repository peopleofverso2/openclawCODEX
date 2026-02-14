# Aerial Scan Strategy (Drone)

## Flight Plan Design

### Grid Pattern (nadir — top-down)

Primary capture for roof, terrain, and orthophoto generation.

| Parameter | Small house | Large building | Terrain/site |
|---|---|---|---|
| Altitude | 20-25 m | 30-40 m | 40-80 m |
| Speed | 2-3 m/s | 3-5 m/s | 5-8 m/s |
| Frontal overlap | 80% | 75% | 75% |
| Lateral overlap | 70% | 65% | 60% |
| Line spacing | ~5 m | ~8 m | ~15 m |
| Photo interval | 2 s | 2 s | 2-3 s |
| Gimbal pitch | -90° (nadir) | -90° | -90° |

### Oblique Orbit (facades)

Secondary capture to reconstruct vertical surfaces (walls, windows, details).

- Fly a circular orbit around the building
- Gimbal pitch: -45° to -60°
- Radius: 1.5x building footprint diagonal
- Altitude: ~2/3 of building height above ground
- Points: 24-36 positions around the orbit (one photo every 10-15°)
- Repeat at 2 altitudes for tall buildings

### Combined Mission Order

1. **Grid pass** at planned altitude (nadir photos)
2. **Oblique orbit** — low altitude, -45° gimbal
3. **Oblique orbit** — mid altitude, -60° gimbal (tall buildings only)
4. **Detail pass** — manual or slow flyby for areas of interest

## Camera Settings

| Setting | Recommendation |
|---|---|
| Mode | Shutter priority or manual |
| Shutter speed | 1/800 or faster (avoid motion blur) |
| ISO | Auto (cap at 800) |
| Format | JPEG fine (RAW if storage permits) |
| White balance | Auto or Daylight |
| Focus | Infinity or auto with lock |

## Weather Conditions

| Condition | Impact |
|---|---|
| Overcast sky | Best — diffuse light, no harsh shadows |
| Light wind (<15 km/h) | OK |
| Strong wind (>25 km/h) | Abort — blur risk + GPS drift |
| Rain | Abort |
| Low sun (golden hour) | Avoid — long shadows confuse matching |
| Midday harsh sun | Acceptable but overcast is better |

## GCP Placement (for survey-grade accuracy)

Ground Control Points improve absolute accuracy from meters to centimeters.

- Place 5-10 GCPs around the site
- Distribute evenly, including corners and center
- Use high-contrast targets (checkerboard pattern, 30x30 cm minimum)
- Survey each GCP with RTK GPS or total station
- Format for ODM `gcp_list.txt`:

```
EPSG:4326
lon lat alt pixelX pixelY imageName
2.2945 48.8584 35.2 1250 800 DJI_0001.JPG
2.2950 48.8588 35.1 900 1100 DJI_0015.JPG
```

## Preflight Checklist

1. Battery charged > 90%
2. SD card formatted and empty
3. Propellers secure
4. GPS lock confirmed (> 10 satellites)
5. Geofence set (max radius, max altitude)
6. RTL altitude set above obstacles
7. Wind check
8. Airspace authorization (if required)
9. Observers in position (VLOS compliance)
