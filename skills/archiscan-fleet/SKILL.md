---
name: archiscan-fleet
description: Fleet management for ArchiScan field entities — geofencing, multi-robot orchestration, declarative mission planning, real-time dashboard. Use when asked to manage multiple robots, drones, or gateways simultaneously, set up geofences, coordinate missions, or monitor a fleet of field devices.
---

# ArchiScan Fleet — Multi-Entity Orchestration & Geofencing

Manage multiple ArchiScan entities (robots, drones, gateways) from a single declarative configuration. No per-device programming — define zones, rules, and missions once, the fleet obeys.

## Concept

```
                   ┌──────────────────────────────────────────┐
                   │          fleet.yml (déclaratif)           │
                   │                                          │
                   │  entities:  gw-01, gw-02, gw-03, gw-04  │
                   │  zones:     chantier-A, chantier-B       │
                   │  rules:     geofence, battery, schedule  │
                   │  missions:  scan-interieur, survey-toit  │
                   └──────────────────┬───────────────────────┘
                                      │
                              ┌───────┴───────┐
                              │  Fleet Engine  │
                              │  (Node.js)     │
                              │                │
                              │  • Rule eval   │
                              │  • Geofence    │
                              │  • Scheduler   │
                              │  • Dashboard   │
                              └───┬───┬───┬───┘
                                  │   │   │  MQTT
                        ┌─────────┘   │   └─────────┐
                        │             │             │
                   ┌────┴───┐   ┌────┴───┐   ┌────┴───┐
                   │ GW-01  │   │ GW-02  │   │ GW-03  │
                   │ Robot  │   │ Drone  │   │ Fixe   │
                   └────────┘   └────────┘   └────────┘

Principe: Tu écris du YAML → le Fleet Engine traduit en commandes MQTT.
Zéro code par entité.
```

## Fleet Configuration (fleet.yml)

```yaml
# fleet.yml — Configuration déclarative de la flotte ArchiScan

fleet:
  name: "Chantier Rivoli"
  mqtt_broker: "mqtt://mqtt.your-server.com:1883"
  mqtt_user: "archiscan"
  mqtt_pass: "changeme"
  api_port: 8091
  dashboard_port: 3030

# ─── Entités ────────────────────────────────────────────
entities:
  - id: gw-01
    name: "Robot Sol — Spot"
    type: robot
    capabilities: [move, scan_lidar, photo]
    home_zone: chantier-A
    battery_warn: 20      # % — alert below this
    battery_critical: 10  # % — force return home

  - id: gw-02
    name: "Drone — DJI Mini"
    type: drone
    capabilities: [fly, photo, video, thermal]
    home_zone: chantier-A
    max_altitude: 50      # m — geofence vertical
    battery_warn: 30
    battery_critical: 20

  - id: gw-03
    name: "Capteur Fixe — Toiture"
    type: station
    capabilities: [temperature, humidity, vibration]
    home_zone: chantier-A

  - id: gw-04
    name: "Robot Sol — Go2"
    type: robot
    capabilities: [move, scan_lidar, photo]
    home_zone: chantier-B
    battery_warn: 25
    battery_critical: 15

# ─── Zones (Geofences) ─────────────────────────────────
zones:
  - id: chantier-A
    name: "15 rue de Rivoli — Bâtiment principal"
    type: polygon
    coordinates:  # lon, lat (GeoJSON order)
      - [2.34210, 48.86050]
      - [2.34280, 48.86050]
      - [2.34280, 48.86010]
      - [2.34210, 48.86010]
    buffer_m: 10          # Tolérance GPS (10m autour)
    max_altitude: 30      # Plafond drone (m AGL)
    allowed_entities: [gw-01, gw-02, gw-03]
    restrictions:
      no_fly_hours: ["22:00-07:00"]  # Pas de drone la nuit
      max_speed_kmh: 5               # Vitesse max robot

  - id: chantier-B
    name: "8 rue Saint-Honoré — Annexe"
    type: polygon
    coordinates:
      - [2.34100, 48.86100]
      - [2.34180, 48.86100]
      - [2.34180, 48.86060]
      - [2.34100, 48.86060]
    buffer_m: 15
    allowed_entities: [gw-04]

  - id: zone-interdite
    name: "Voie publique — interdit"
    type: polygon
    coordinates:
      - [2.34150, 48.86055]
      - [2.34200, 48.86055]
      - [2.34200, 48.86045]
      - [2.34150, 48.86045]
    forbidden: true       # Aucune entité autorisée

  - id: home-base
    name: "Point de retour"
    type: circle
    center: [2.34245, 48.86030]
    radius_m: 3

# ─── Règles (évaluées en continu) ──────────────────────
rules:
  # Geofence: alerte + action si une entité sort de sa zone
  - id: geofence-breach
    trigger: entity_outside_zone
    description: "Entité hors de sa zone autorisée"
    actions:
      - alert: "⚠ {entity.name} hors zone {entity.home_zone}"
      - command:
          action: stop
          reason: "geofence_breach"
      - notify:
          channels: [mqtt, sms]
          sms_to: "+33612345678"

  # Geofence: zone interdite
  - id: forbidden-zone
    trigger: entity_in_zone
    zone: zone-interdite
    description: "Entité dans une zone interdite"
    actions:
      - alert: "🛑 {entity.name} dans zone interdite!"
      - command:
          action: return_home
          priority: emergency
      - notify:
          channels: [mqtt, sms]

  # Batterie faible → retour base
  - id: battery-low
    trigger: battery_below
    threshold_field: battery_warn  # Lit la valeur depuis l'entité
    description: "Batterie faible"
    actions:
      - alert: "🔋 {entity.name} batterie {battery}%"
      - command:
          action: return_home
          priority: normal

  # Batterie critique → arrêt immédiat
  - id: battery-critical
    trigger: battery_below
    threshold_field: battery_critical
    description: "Batterie critique"
    actions:
      - alert: "🔴 {entity.name} batterie CRITIQUE {battery}%"
      - command:
          action: emergency_stop
      - notify:
          channels: [mqtt, sms]

  # Vent fort → drone au sol
  - id: wind-safety
    trigger: wind_above
    threshold_kmh: 35
    applies_to: [drone]
    description: "Vent trop fort pour le drone"
    actions:
      - alert: "💨 Vent {wind_kmh} km/h — drone interdit"
      - command:
          target_type: drone
          action: land
          priority: emergency

  # Horaire → pas de drone la nuit
  - id: night-curfew
    trigger: schedule
    cron: "0 22 * * *"  # 22h00
    description: "Couvre-feu nocturne drones"
    actions:
      - command:
          target_type: drone
          action: return_home
      - alert: "🌙 Couvre-feu — drones rappelés"

  # Signal perdu → alerte après 60s
  - id: lost-contact
    trigger: no_heartbeat
    timeout_s: 60
    description: "Perte de contact"
    actions:
      - alert: "📡 {entity.name} — contact perdu depuis {timeout}s"
      - notify:
          channels: [mqtt, sms]

  # Vibration anormale (station fixe)
  - id: vibration-alert
    trigger: sensor_above
    sensor: vibration_g
    threshold: 0.5
    applies_to: [station]
    description: "Vibration anormale détectée"
    actions:
      - alert: "📳 Vibration {value}g sur {entity.name}"
      - notify:
          channels: [mqtt, sms]

# ─── Missions (séquences de tâches) ────────────────────
missions:
  - id: scan-interieur-complet
    name: "Scan intérieur complet"
    zone: chantier-A
    assign_to: gw-01  # ou "auto" pour assigner au premier robot dispo
    steps:
      - action: move_to
        waypoint: [2.34230, 48.86035]
        description: "Aller à l'entrée"
      - action: scan_lidar
        duration_s: 600
        description: "Scan LiDAR intérieur — 10 min"
      - action: photo
        count: 50
        interval_s: 5
        description: "Série photos intérieur"
      - action: return_home
        description: "Retour base"

  - id: survey-facades
    name: "Relevé façades drone"
    zone: chantier-A
    assign_to: gw-02
    preconditions:
      - wind_below_kmh: 30
      - battery_above: 60
      - time_between: ["08:00", "21:00"]
    steps:
      - action: takeoff
        altitude: 5
      - action: orbit
        center: [2.34245, 48.86030]
        radius: 12
        altitude: 8
        points: 24
        gimbal_pitch: -20
        description: "Orbite façade basse"
      - action: orbit
        center: [2.34245, 48.86030]
        radius: 15
        altitude: 15
        points: 24
        gimbal_pitch: -30
        description: "Orbite façade haute"
      - action: grid
        bounds: [[2.34220, 48.86020], [2.34270, 48.86040]]
        altitude: 20
        overlap: 80
        description: "Grille toiture"
      - action: land
        description: "Atterrissage"

  - id: monitoring-24h
    name: "Monitoring continu chantier"
    zone: chantier-A
    assign_to: gw-03
    repeat: forever
    interval_s: 30
    steps:
      - action: read_sensors
        sensors: [temperature, humidity, vibration]
      - action: publish_telemetry
```

## Fleet Engine (Node.js)

```javascript
// scripts/fleet-engine.js
// Core fleet management engine — reads fleet.yml, enforces rules, dispatches commands

import mqtt from 'mqtt';
import { readFileSync } from 'fs';
import YAML from 'yaml';
import * as turf from '@turf/turf';

// ─── Load fleet config ─────────────────────────────────
const config = YAML.parse(readFileSync('fleet.yml', 'utf-8'));
console.log(`[FLEET] Loaded: ${config.fleet.name}`);
console.log(`[FLEET] ${config.entities.length} entities, ${config.zones.length} zones, ${config.rules.length} rules`);

// ─── MQTT Connection ───────────────────────────────────
const client = mqtt.connect(config.fleet.mqtt_broker, {
    username: config.fleet.mqtt_user,
    password: config.fleet.mqtt_pass,
});

client.on('connect', () => {
    console.log('[MQTT] Connected');
    client.subscribe('archiscan/gw/+/gps');
    client.subscribe('archiscan/gw/+/telemetry');
    client.subscribe('archiscan/gw/+/status');
    client.subscribe('archiscan/gw/+/alert');
});

// ─── Entity State ──────────────────────────────────────
class EntityState {
    constructor(entityConfig) {
        this.config = entityConfig;
        this.id = entityConfig.id;
        this.name = entityConfig.name;
        this.type = entityConfig.type;
        this.lat = null;
        this.lon = null;
        this.alt = null;
        this.speed = 0;
        this.battery = 100;
        this.temperature = null;
        this.humidity = null;
        this.signalStrength = 0;
        this.lastSeen = null;
        this.lastGPS = null;
        this.status = 'unknown';     // unknown, online, offline, mission, returning, stopped
        this.currentZone = null;      // which zone the entity is currently in
        this.insideHomeZone = false;
        this.insideForbidden = false;
        this.activeAlerts = new Set();
        this.missionId = null;
        this.missionStep = 0;
        this.gpsTrack = [];
    }

    updateGPS(data) {
        this.lat = data.lat;
        this.lon = data.lon;
        this.alt = data.alt || 0;
        this.speed = data.speed || 0;
        this.lastGPS = new Date();
        this.lastSeen = new Date();
        this.gpsTrack.push({ ts: Date.now(), lat: data.lat, lon: data.lon, alt: data.alt });
        // Keep last 10000 points
        if (this.gpsTrack.length > 10000) this.gpsTrack = this.gpsTrack.slice(-5000);
    }

    updateTelemetry(data) {
        if (data.bat_v !== undefined) {
            // Convert voltage to percentage (3.0V=0%, 4.2V=100%)
            this.battery = Math.round(Math.max(0, Math.min(100,
                (data.bat_v - 3.0) / 1.2 * 100)));
        }
        if (data.temp !== undefined) this.temperature = data.temp;
        if (data.hum !== undefined) this.humidity = data.hum;
        if (data.csq !== undefined) this.signalStrength = data.csq;
        this.lastSeen = new Date();
        this.status = 'online';
    }
}

const entities = new Map();
for (const ec of config.entities) {
    entities.set(ec.id, new EntityState(ec));
}

// ─── Geofence Engine (Turf.js) ─────────────────────────
function buildZonePolygon(zone) {
    if (zone.type === 'polygon') {
        // Close the polygon if needed
        const coords = [...zone.coordinates];
        if (coords[0][0] !== coords[coords.length-1][0] ||
            coords[0][1] !== coords[coords.length-1][1]) {
            coords.push(coords[0]);
        }
        let poly = turf.polygon([coords]);
        // Apply buffer
        if (zone.buffer_m) {
            poly = turf.buffer(poly, zone.buffer_m / 1000, { units: 'kilometers' });
        }
        return poly;
    } else if (zone.type === 'circle') {
        return turf.circle(zone.center, zone.radius_m / 1000, {
            units: 'kilometers', steps: 64
        });
    }
    return null;
}

// Pre-build zone polygons
const zonePolygons = new Map();
for (const zone of config.zones) {
    const poly = buildZonePolygon(zone);
    if (poly) zonePolygons.set(zone.id, { polygon: poly, config: zone });
}

function checkGeofence(entity) {
    if (entity.lat === null || entity.lon === null) return;

    const point = turf.point([entity.lon, entity.lat]);
    let insideAny = false;

    for (const [zoneId, zone] of zonePolygons) {
        const inside = turf.booleanPointInPolygon(point, zone.polygon);

        if (zone.config.forbidden && inside) {
            entity.insideForbidden = true;
            triggerRule('forbidden-zone', entity, { zone: zone.config });
        }

        if (zoneId === entity.config.home_zone && inside) {
            entity.insideHomeZone = true;
            insideAny = true;
        }

        // Check altitude ceiling
        if (inside && zone.config.max_altitude && entity.alt > zone.config.max_altitude) {
            triggerRule('geofence-breach', entity, {
                reason: `altitude ${entity.alt}m > max ${zone.config.max_altitude}m`
            });
        }

        // Check speed limit
        if (inside && zone.config.restrictions?.max_speed_kmh &&
            entity.speed > zone.config.restrictions.max_speed_kmh) {
            triggerRule('speed-limit', entity, {
                speed: entity.speed,
                limit: zone.config.restrictions.max_speed_kmh
            });
        }
    }

    // Outside home zone
    if (!insideAny && entity.config.home_zone) {
        entity.insideHomeZone = false;
        triggerRule('geofence-breach', entity, { zone: entity.config.home_zone });
    }
}

// ─── Rule Engine ───────────────────────────────────────
const ruleIndex = new Map();
for (const rule of config.rules) {
    ruleIndex.set(rule.id, rule);
}

// Cooldown to avoid alert spam (1 rule trigger per entity per 60s)
const ruleCooldowns = new Map();

function triggerRule(ruleId, entity, context = {}) {
    const rule = ruleIndex.get(ruleId);
    if (!rule) return;

    // Cooldown check
    const key = `${ruleId}:${entity.id}`;
    const now = Date.now();
    if (ruleCooldowns.has(key) && now - ruleCooldowns.get(key) < 60000) return;
    ruleCooldowns.set(key, now);

    console.log(`[RULE] ${ruleId} triggered for ${entity.name}`, context);

    for (const action of rule.actions) {
        if (action.alert) {
            const msg = interpolate(action.alert, entity, context);
            console.log(`[ALERT] ${msg}`);
            // Publish alert to MQTT
            client.publish(`archiscan/fleet/alerts`, JSON.stringify({
                rule: ruleId,
                entity: entity.id,
                message: msg,
                ts: new Date().toISOString(),
            }));
        }

        if (action.command) {
            sendCommand(
                action.command.target_type
                    ? getEntitiesByType(action.command.target_type)
                    : [entity.id],
                action.command
            );
        }

        if (action.notify) {
            for (const channel of action.notify.channels) {
                if (channel === 'sms' && action.notify.sms_to) {
                    sendSMSvia(entity.id, action.notify.sms_to,
                        interpolate(action.alert || rule.description, entity, context));
                }
            }
        }
    }
}

function interpolate(template, entity, context) {
    return template
        .replace(/\{entity\.name\}/g, entity.name)
        .replace(/\{entity\.id\}/g, entity.id)
        .replace(/\{entity\.home_zone\}/g, entity.config.home_zone || '?')
        .replace(/\{battery\}/g, entity.battery)
        .replace(/\{timeout\}/g, context.timeout || '?')
        .replace(/\{value\}/g, context.value || '?')
        .replace(/\{wind_kmh\}/g, context.wind_kmh || '?')
        .replace(/\{speed\}/g, context.speed || '?');
}

function getEntitiesByType(type) {
    return [...entities.values()]
        .filter(e => e.type === type)
        .map(e => e.id);
}

// ─── Battery Monitor ───────────────────────────────────
function checkBattery(entity) {
    const warn = entity.config.battery_warn || 20;
    const crit = entity.config.battery_critical || 10;

    if (entity.battery <= crit) {
        triggerRule('battery-critical', entity);
    } else if (entity.battery <= warn) {
        triggerRule('battery-low', entity);
    }
}

// ─── Heartbeat Monitor ────────────────────────────────
function checkHeartbeats() {
    const now = Date.now();
    for (const [id, entity] of entities) {
        if (entity.lastSeen && now - entity.lastSeen.getTime() > 60000) {
            if (entity.status !== 'offline') {
                entity.status = 'offline';
                triggerRule('lost-contact', entity, {
                    timeout: Math.round((now - entity.lastSeen.getTime()) / 1000)
                });
            }
        }
    }
}

// ─── Command Dispatch ──────────────────────────────────
function sendCommand(entityIds, command) {
    for (const id of entityIds) {
        const topic = `archiscan/gw/${id}/cmd`;
        const payload = JSON.stringify({
            action: command.action,
            priority: command.priority || 'normal',
            reason: command.reason || '',
            source: 'fleet-engine',
        });
        client.publish(topic, payload);
        console.log(`[CMD] → ${id}: ${command.action} (${command.priority || 'normal'})`);
    }
}

function sendSMSvia(gatewayId, number, message) {
    const topic = `archiscan/gw/${gatewayId}/cmd`;
    client.publish(topic, JSON.stringify({
        action: 'sms',
        number,
        message: message.substring(0, 160),
    }));
}

// ─── MQTT Message Handler ──────────────────────────────
client.on('message', (topic, message) => {
    const parts = topic.split('/');
    const deviceId = parts[2];
    const channel = parts[3];

    const entity = entities.get(deviceId);
    if (!entity) {
        // Unknown device — auto-register?
        console.log(`[FLEET] Unknown device: ${deviceId}`);
        return;
    }

    const payload = JSON.parse(message.toString());

    switch (channel) {
        case 'gps':
            entity.updateGPS(payload);
            checkGeofence(entity);
            break;
        case 'telemetry':
            entity.updateTelemetry(payload);
            checkBattery(entity);
            break;
        case 'status':
            entity.status = payload.status || 'online';
            entity.lastSeen = new Date();
            break;
        case 'alert':
            console.log(`[DEV-ALERT] ${deviceId}: ${JSON.stringify(payload)}`);
            break;
    }
});

// ─── Periodic Checks ───────────────────────────────────
setInterval(checkHeartbeats, 10000);  // Every 10s

// ─── Mission Engine ────────────────────────────────────
class MissionRunner {
    constructor(missionConfig) {
        this.config = missionConfig;
        this.id = missionConfig.id;
        this.entityId = missionConfig.assign_to;
        this.steps = missionConfig.steps;
        this.currentStep = 0;
        this.status = 'pending';  // pending, running, paused, completed, failed
        this.startTime = null;
    }

    checkPreconditions() {
        if (!this.config.preconditions) return true;

        const entity = entities.get(this.entityId);
        if (!entity) return false;

        for (const pre of this.config.preconditions) {
            if (pre.battery_above && entity.battery < pre.battery_above) {
                console.log(`[MISSION] ${this.id}: battery too low (${entity.battery}% < ${pre.battery_above}%)`);
                return false;
            }
            if (pre.wind_below_kmh) {
                // Would need weather data — skip for now
            }
            if (pre.time_between) {
                const now = new Date();
                const hours = now.getHours();
                const [start, end] = pre.time_between.map(t => parseInt(t.split(':')[0]));
                if (hours < start || hours >= end) {
                    console.log(`[MISSION] ${this.id}: outside allowed hours`);
                    return false;
                }
            }
        }
        return true;
    }

    start() {
        if (!this.checkPreconditions()) {
            this.status = 'blocked';
            return false;
        }

        this.status = 'running';
        this.startTime = Date.now();
        const entity = entities.get(this.entityId);
        if (entity) entity.missionId = this.id;

        console.log(`[MISSION] Starting: ${this.config.name} on ${this.entityId}`);
        this.executeNextStep();
        return true;
    }

    executeNextStep() {
        if (this.currentStep >= this.steps.length) {
            this.complete();
            return;
        }

        const step = this.steps[this.currentStep];
        console.log(`[MISSION] ${this.id} step ${this.currentStep + 1}/${this.steps.length}: ${step.description || step.action}`);

        // Send command to entity
        sendCommand([this.entityId], {
            action: step.action,
            ...step,
            mission_id: this.id,
            step: this.currentStep,
        });

        this.currentStep++;
        // The entity confirms step completion via status message
        // For now, we advance on timer (simplified)
        const delay = step.duration_s ? step.duration_s * 1000 : 10000;
        setTimeout(() => this.executeNextStep(), delay);
    }

    complete() {
        this.status = 'completed';
        const entity = entities.get(this.entityId);
        if (entity) entity.missionId = null;

        console.log(`[MISSION] Completed: ${this.config.name} (${Math.round((Date.now() - this.startTime) / 1000)}s)`);

        client.publish('archiscan/fleet/missions', JSON.stringify({
            mission: this.id,
            entity: this.entityId,
            status: 'completed',
            duration_s: Math.round((Date.now() - this.startTime) / 1000),
        }));

        // Repeat if configured
        if (this.config.repeat === 'forever') {
            this.currentStep = 0;
            setTimeout(() => this.start(), (this.config.interval_s || 60) * 1000);
        }
    }

    pause() { this.status = 'paused'; }
    abort() {
        this.status = 'failed';
        sendCommand([this.entityId], { action: 'stop', reason: 'mission_aborted' });
    }
}

const activeMissions = new Map();

function startMission(missionId) {
    const missionConfig = config.missions.find(m => m.id === missionId);
    if (!missionConfig) {
        console.log(`[MISSION] Unknown mission: ${missionId}`);
        return null;
    }
    const runner = new MissionRunner(missionConfig);
    activeMissions.set(missionId, runner);
    runner.start();
    return runner;
}

// ─── Fleet Dashboard API ───────────────────────────────
import { createServer } from 'http';

const server = createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

    // ── GET /fleet — full fleet state ──
    if (url.pathname === '/fleet' && req.method === 'GET') {
        const state = {
            name: config.fleet.name,
            entities: [...entities.values()].map(e => ({
                id: e.id,
                name: e.name,
                type: e.type,
                status: e.status,
                lat: e.lat, lon: e.lon, alt: e.alt,
                speed: e.speed,
                battery: e.battery,
                temperature: e.temperature,
                humidity: e.humidity,
                signal: e.signalStrength,
                lastSeen: e.lastSeen,
                insideHomeZone: e.insideHomeZone,
                insideForbidden: e.insideForbidden,
                missionId: e.missionId,
                trackPoints: e.gpsTrack.length,
            })),
            zones: config.zones.map(z => ({
                id: z.id, name: z.name, type: z.type,
                forbidden: z.forbidden || false,
                coordinates: z.coordinates || z.center,
                radius_m: z.radius_m,
            })),
            activeMissions: [...activeMissions.entries()].map(([id, m]) => ({
                id, entity: m.entityId, status: m.status,
                step: m.currentStep, totalSteps: m.steps.length,
            })),
        };
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(state, null, 2));
        return;
    }

    // ── GET /fleet/map — GeoJSON for map rendering ──
    if (url.pathname === '/fleet/map' && req.method === 'GET') {
        const features = [];

        // Zone polygons
        for (const zone of config.zones) {
            const poly = zonePolygons.get(zone.id);
            if (poly) {
                features.push({
                    ...poly.polygon,
                    properties: {
                        id: zone.id, name: zone.name,
                        type: 'zone',
                        forbidden: zone.forbidden || false,
                        style: zone.forbidden
                            ? { fill: '#ff000030', stroke: '#ff0000' }
                            : { fill: '#00ff0015', stroke: '#00aa00' },
                    }
                });
            }
        }

        // Entity positions
        for (const [id, e] of entities) {
            if (e.lat !== null) {
                features.push(turf.point([e.lon, e.lat], {
                    id: e.id, name: e.name, type: e.type,
                    status: e.status, battery: e.battery,
                    featureType: 'entity',
                    icon: e.type === 'drone' ? 'drone' : e.type === 'robot' ? 'robot' : 'sensor',
                }));
            }

            // GPS track
            if (e.gpsTrack.length > 1) {
                features.push(turf.lineString(
                    e.gpsTrack.map(p => [p.lon, p.lat]),
                    { id: `${e.id}-track`, entity: e.id, featureType: 'track' }
                ));
            }
        }

        const geojson = turf.featureCollection(features);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(geojson));
        return;
    }

    // ── POST /fleet/cmd — send command to entity(ies) ──
    if (url.pathname === '/fleet/cmd' && req.method === 'POST') {
        let body = '';
        req.on('data', c => body += c);
        req.on('end', () => {
            const { targets, action, ...params } = JSON.parse(body);
            // targets: array of entity IDs, or "all", or type name
            let ids = [];
            if (targets === 'all') {
                ids = [...entities.keys()];
            } else if (['robot', 'drone', 'station'].includes(targets)) {
                ids = getEntitiesByType(targets);
            } else if (Array.isArray(targets)) {
                ids = targets;
            } else {
                ids = [targets];
            }
            sendCommand(ids, { action, ...params });
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ sent: true, targets: ids }));
        });
        return;
    }

    // ── POST /fleet/mission/start ──
    if (url.pathname === '/fleet/mission/start' && req.method === 'POST') {
        let body = '';
        req.on('data', c => body += c);
        req.on('end', () => {
            const { mission_id } = JSON.parse(body);
            const runner = startMission(mission_id);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                started: runner?.status === 'running',
                status: runner?.status || 'not_found',
            }));
        });
        return;
    }

    // ── POST /fleet/mission/abort ──
    if (url.pathname === '/fleet/mission/abort' && req.method === 'POST') {
        let body = '';
        req.on('data', c => body += c);
        req.on('end', () => {
            const { mission_id } = JSON.parse(body);
            const runner = activeMissions.get(mission_id);
            if (runner) runner.abort();
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ aborted: !!runner }));
        });
        return;
    }

    // ── POST /fleet/geofence — add/update a geofence zone live ──
    if (url.pathname === '/fleet/geofence' && req.method === 'POST') {
        let body = '';
        req.on('data', c => body += c);
        req.on('end', () => {
            const zone = JSON.parse(body);
            // Add or replace
            const existing = config.zones.findIndex(z => z.id === zone.id);
            if (existing >= 0) {
                config.zones[existing] = zone;
            } else {
                config.zones.push(zone);
            }
            // Rebuild polygon
            const poly = buildZonePolygon(zone);
            if (poly) zonePolygons.set(zone.id, { polygon: poly, config: zone });

            console.log(`[GEOFENCE] Zone ${zone.id} ${existing >= 0 ? 'updated' : 'added'}`);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ ok: true, zone: zone.id }));
        });
        return;
    }

    res.writeHead(404);
    res.end('Not found');
});

server.listen(config.fleet.api_port || 8091, () => {
    console.log(`[HTTP] Fleet API on :${config.fleet.api_port || 8091}`);
});

// ─── Dashboard (minimal HTML served) ───────────────────
const dashServer = createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(DASHBOARD_HTML);
});

dashServer.listen(config.fleet.dashboard_port || 3030, () => {
    console.log(`[DASH] Dashboard on :${config.fleet.dashboard_port || 3030}`);
});
```

## Dashboard HTML (Leaflet Map)

```html
<!-- scripts/dashboard.html — Served by fleet engine on :3030 -->
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>ArchiScan Fleet</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9/dist/leaflet.js"></script>
<style>
  body { margin: 0; font-family: system-ui; background: #0a0a1a; color: #eee; }
  #map { height: 70vh; }
  #panel { padding: 16px; display: flex; gap: 16px; flex-wrap: wrap; }
  .card { background: #1a1a2e; border-radius: 8px; padding: 12px 16px; min-width: 200px; }
  .card h3 { margin: 0 0 8px; font-size: 14px; color: #888; }
  .card .value { font-size: 22px; font-weight: bold; }
  .online { color: #4ade80; }
  .offline { color: #f87171; }
  .warning { color: #fbbf24; }
  .entity-row { display: flex; align-items: center; gap: 10px; padding: 6px 0;
                border-bottom: 1px solid #333; }
  .dot { width: 10px; height: 10px; border-radius: 50%; }
  .dot.online { background: #4ade80; }
  .dot.offline { background: #f87171; }
  .dot.mission { background: #60a5fa; animation: pulse 1s infinite; }
  @keyframes pulse { 50% { opacity: 0.5; } }
  #entities { padding: 0 16px 16px; }
  button { background: #3b82f6; color: white; border: none; padding: 6px 14px;
           border-radius: 4px; cursor: pointer; font-size: 13px; }
  button:hover { background: #2563eb; }
  button.danger { background: #ef4444; }
  button.danger:hover { background: #dc2626; }
</style>
</head>
<body>

<div id="map"></div>

<div id="panel">
  <div class="card">
    <h3>Entités</h3>
    <div class="value" id="total-entities">—</div>
  </div>
  <div class="card">
    <h3>En ligne</h3>
    <div class="value online" id="online-count">—</div>
  </div>
  <div class="card">
    <h3>Alertes</h3>
    <div class="value warning" id="alert-count">0</div>
  </div>
  <div class="card">
    <h3>Missions actives</h3>
    <div class="value" id="mission-count">0</div>
  </div>
</div>

<div id="entities"></div>

<script>
const API = 'http://localhost:8091';

// Map
const map = L.map('map').setView([48.8605, 2.3425], 18);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 22,
    attribution: 'OSM'
}).addTo(map);

const entityMarkers = {};
const zoneLayers = {};
const trackLayers = {};

const icons = {
    robot: L.divIcon({ html: '🤖', className: '', iconSize: [28, 28] }),
    drone: L.divIcon({ html: '🛸', className: '', iconSize: [28, 28] }),
    station: L.divIcon({ html: '📡', className: '', iconSize: [28, 28] }),
};

async function refresh() {
    try {
        // Fleet state
        const fleet = await (await fetch(`${API}/fleet`)).json();

        document.getElementById('total-entities').textContent = fleet.entities.length;
        document.getElementById('online-count').textContent =
            fleet.entities.filter(e => e.status === 'online').length;
        document.getElementById('mission-count').textContent = fleet.activeMissions.length;

        // Entity list
        const el = document.getElementById('entities');
        el.innerHTML = fleet.entities.map(e => `
            <div class="entity-row">
                <div class="dot ${e.status}"></div>
                <strong>${e.name}</strong>
                <span style="color:#888">${e.type}</span>
                <span>🔋 ${e.battery}%</span>
                <span>${e.lat ? e.lat.toFixed(5) + ', ' + e.lon.toFixed(5) : 'No GPS'}</span>
                <span style="color:${e.insideHomeZone ? '#4ade80' : '#f87171'}">
                    ${e.insideHomeZone ? '✓ In zone' : '✗ Out of zone'}
                </span>
                ${e.missionId ? `<span style="color:#60a5fa">Mission: ${e.missionId}</span>` : ''}
                <button onclick="sendCmd('${e.id}','ping')">Ping</button>
                <button onclick="sendCmd('${e.id}','locate')">Locate</button>
                <button class="danger" onclick="sendCmd('${e.id}','emergency_stop')">STOP</button>
            </div>
        `).join('');

        // Map: GeoJSON overlay
        const geojson = await (await fetch(`${API}/fleet/map`)).json();

        // Clear old
        Object.values(zoneLayers).forEach(l => map.removeLayer(l));
        Object.values(trackLayers).forEach(l => map.removeLayer(l));

        for (const feature of geojson.features) {
            const props = feature.properties;

            if (props.featureType === 'entity' || props.type === 'robot' || props.type === 'drone' || props.type === 'station') {
                if (feature.geometry.type === 'Point') {
                    const [lon, lat] = feature.geometry.coordinates;
                    const icon = icons[props.type] || icons.station;
                    if (entityMarkers[props.id]) {
                        entityMarkers[props.id].setLatLng([lat, lon]);
                    } else {
                        entityMarkers[props.id] = L.marker([lat, lon], { icon })
                            .bindPopup(`<b>${props.name}</b><br>${props.type} — 🔋${props.battery}%`)
                            .addTo(map);
                    }
                }
            } else if (props.type === 'zone') {
                const style = props.style || {};
                const layer = L.geoJSON(feature, {
                    style: {
                        fillColor: style.fill || '#00ff0020',
                        color: style.stroke || '#00aa00',
                        weight: 2,
                        fillOpacity: 0.3,
                    }
                }).bindPopup(`<b>${props.name}</b>${props.forbidden ? '<br>⛔ INTERDIT' : ''}`);
                layer.addTo(map);
                zoneLayers[props.id] = layer;
            } else if (props.featureType === 'track') {
                const layer = L.geoJSON(feature, {
                    style: { color: '#60a5fa', weight: 2, opacity: 0.6 }
                });
                layer.addTo(map);
                trackLayers[props.entity] = layer;
            }
        }
    } catch (err) {
        console.error('Refresh error:', err);
    }
}

async function sendCmd(entityId, action) {
    await fetch(`${API}/fleet/cmd`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ targets: entityId, action }),
    });
}

// Refresh every 3s
refresh();
setInterval(refresh, 3000);
</script>
</body>
</html>
```

## CLI Commands — Fleet Operations

```bash
# ── Fleet status ──
curl -s http://localhost:8091/fleet | jq '.entities[] | {id, name, status, battery, insideHomeZone}'

# ── Ping all entities ──
curl -X POST http://localhost:8091/fleet/cmd \
  -H 'Content-Type: application/json' \
  -d '{"targets":"all","action":"ping"}'

# ── Locate all robots ──
curl -X POST http://localhost:8091/fleet/cmd \
  -d '{"targets":"robot","action":"locate"}'

# ── Emergency stop entire fleet ──
curl -X POST http://localhost:8091/fleet/cmd \
  -d '{"targets":"all","action":"emergency_stop"}'

# ── Start a mission ──
curl -X POST http://localhost:8091/fleet/mission/start \
  -d '{"mission_id":"scan-interieur-complet"}'

# ── Abort a mission ──
curl -X POST http://localhost:8091/fleet/mission/abort \
  -d '{"mission_id":"scan-interieur-complet"}'

# ── Add geofence zone on the fly ──
curl -X POST http://localhost:8091/fleet/geofence \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "zone-temporaire",
    "name": "Exclusion travaux",
    "type": "circle",
    "center": [2.3430, 48.8603],
    "radius_m": 5,
    "forbidden": true
  }'

# ── Get GeoJSON map (zones + tracks + positions) ──
curl -s http://localhost:8091/fleet/map | jq '.features | length'

# ── Open dashboard ──
open http://localhost:3030
```

## Tips

- **Geofencing precision**: Le GPS du SIM7600 a ~3m de précision. Le `buffer_m` dans les zones compense cette imprécision.
- **Turf.js** gère la géométrie sphérique — les polygones et distances sont corrects même sur de grandes zones.
- **Rules are declarative**: Ajouter une nouvelle règle = une entrée YAML. Pas de code à modifier.
- **Live geofence**: L'endpoint `POST /fleet/geofence` permet de créer/modifier des zones en temps réel, sans redémarrer.
- **Multi-site**: Définir plusieurs zones `home_zone` pour dispatcher les entités sur différents chantiers.
- **Scalability**: MQTT gère facilement 100+ entités avec des messages toutes les 5s.
- **Offline resilience**: Si le Fleet Engine redémarre, les gateways continuent à publier — l'état se reconstitue en quelques secondes.
