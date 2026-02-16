---
name: archiscan-gateway
description: Field IoT/4G gateway using LilyGO T-SIM7600 (ESP32 + SIM7600 modem). Provides cellular connectivity, GPS tracking, sensor relay, and remote command for ArchiScan field robots and drones. Use when asked to set up field connectivity, GPS tracking, 4G modem, IoT gateway, or remote robot control via cellular network.
---

# ArchiScan Gateway — LilyGO T-SIM7600 Field IoT Hub

Turn the LilyGO T-SIM7600 (ESP32 + SIM7600E/G 4G modem) into a field gateway for ArchiScan operations: 4G connectivity, GPS tracking, sensor telemetry, remote command relay.

## Architecture

```
                         ┌─────────────────────────┐
                         │     Cloud / VPS          │
                         │                          │
                         │  MQTT Broker (Mosquitto)  │
                         │  OpenClaw API Server      │
                         │  ArchiScan Dashboard      │
                         └────────────┬──────────────┘
                                      │ Internet
                                      │
                              ┌───────┴───────┐
                              │   4G / LTE     │
                              └───────┬───────┘
                                      │
               ┌──────────────────────┴──────────────────────┐
               │         LilyGO T-SIM7600 (ESP32)            │
               │                                              │
               │  ┌──────────┐  ┌─────────┐  ┌────────────┐  │
               │  │ SIM7600  │  │  GPS     │  │ ESP32      │  │
               │  │ 4G Modem │  │ GNSS     │  │ WiFi + BLE │  │
               │  └──────────┘  └─────────┘  └────────────┘  │
               │                                              │
               │  GPIO / I2C / SPI / UART                     │
               └──┬──────────┬──────────┬──────────┬─────────┘
                  │          │          │          │
            ┌─────┴───┐ ┌───┴────┐ ┌───┴────┐ ┌──┴──────────┐
            │ Sensors  │ │ Relay  │ │ Camera │ │ USB to Pi/  │
            │ BME280   │ │ Robot  │ │ ESP32  │ │ Jetson      │
            │ INA219   │ │ Start  │ │ -CAM   │ │ (tethering) │
            │ MPU6050  │ │ /Stop  │ │        │ │             │
            └─────────┘ └────────┘ └────────┘ └─────────────┘
```

## Hardware Setup

### LilyGO T-SIM7600 Pinout

```
T-SIM7600E-H (common EU version):
┌─────────────────────────────────────┐
│  SIM7600 UART  → GPIO26 (TX), GPIO27 (RX)   │
│  SIM7600 Power → GPIO4 (PWRKEY)              │
│  GPS           → Built-in (via SIM7600 NMEA) │
│  SD Card       → GPIO13,15,2,14 (SPI)        │
│  LED           → GPIO12                       │
│  I2C           → GPIO21 (SDA), GPIO22 (SCL)  │
│  Battery       → JST connector (3.7V LiPo)   │
│  USB-C         → Programming + power          │
│  SIM slot      → Nano-SIM (bottom)            │
└─────────────────────────────────────┘
```

### Bill of Materials

| Component | Role | Price (~) |
|---|---|---|
| LilyGO T-SIM7600E-H | Main board (ESP32 + 4G + GPS) | ~35€ |
| Nano-SIM (4G data) | Cellular connectivity | ~5€/mois |
| 4G + GPS antenna (SMA) | Signal reception (2 antennas) | Included |
| LiPo 3.7V 2000mAh | Battery backup | ~8€ |
| BME280 (I2C) | Temperature / humidity / pressure | ~4€ |
| INA219 (I2C) | Battery/solar voltage+current monitor | ~3€ |
| IP65 enclosure | Weather protection | ~10€ |
| Solar panel 6V 2W (optional) | Field autonomy | ~12€ |

**Total: ~80€** for a complete autonomous field gateway.

## Firmware — PlatformIO Project

### platformio.ini

```ini
; platformio.ini — ArchiScan Gateway Firmware
[env:tsim7600]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
upload_speed = 921600

lib_deps =
    knolleary/PubSubClient@^2.8       ; MQTT
    bblanchon/ArduinoJson@^7.0        ; JSON
    mikalhart/TinyGPSPlus@^1.0        ; GPS parsing
    adafruit/Adafruit BME280 Library   ; Temp/Humidity
    adafruit/Adafruit INA219           ; Power monitor
    256dpi/MQTT@^2.5                   ; Alt MQTT lib

build_flags =
    -DCORE_DEBUG_LEVEL=3
    -DSIM7600_TX=26
    -DSIM7600_RX=27
    -DSIM7600_PWRKEY=4
    -DLED_PIN=12
    -DMQTT_MAX_PACKET_SIZE=1024
```

### Main Firmware

```cpp
// firmware/main.cpp — ArchiScan Gateway for T-SIM7600
#include <Arduino.h>
#include <HardwareSerial.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <TinyGPSPlus.h>
#include <Wire.h>
#include <Adafruit_BME280.h>
#include <Adafruit_INA219.h>

// ─── Configuration ─────────────────────────────────────
#define DEVICE_ID        "archiscan-gw-01"
#define MQTT_BROKER      "mqtt.your-server.com"
#define MQTT_PORT        1883
#define MQTT_USER        "archiscan"
#define MQTT_PASS        "changeme"
#define APN              "your_apn"        // e.g., "free" or "iot.1nce.net"

#define TOPIC_TELEMETRY  "archiscan/gw/" DEVICE_ID "/telemetry"
#define TOPIC_GPS        "archiscan/gw/" DEVICE_ID "/gps"
#define TOPIC_CMD        "archiscan/gw/" DEVICE_ID "/cmd"
#define TOPIC_STATUS     "archiscan/gw/" DEVICE_ID "/status"
#define TOPIC_ALERT      "archiscan/gw/" DEVICE_ID "/alert"

#define TELEMETRY_INTERVAL_MS  30000   // 30s
#define GPS_INTERVAL_MS        5000    // 5s

// ─── Hardware ──────────────────────────────────────────
HardwareSerial simSerial(1);  // UART1 for SIM7600
TinyGPSPlus gps;
Adafruit_BME280 bme;
Adafruit_INA219 ina219;

// ─── MQTT via SIM7600 TCP ──────────────────────────────
// Note: We use AT commands for TCP since SIM7600 handles the
// network stack. For simplicity, we bridge to WiFi AP mode
// and use PubSubClient over that. Alternative: direct AT+CMQTT.

// ─── State ─────────────────────────────────────────────
struct GatewayState {
    float lat = 0, lon = 0, alt = 0, speed = 0;
    float temperature = 0, humidity = 0, pressure = 0;
    float voltage = 0, current = 0;
    int satellites = 0;
    int signalStrength = 0;  // CSQ
    bool sim7600Ready = false;
    bool gpsFix = false;
    bool mqttConnected = false;
    unsigned long lastTelemetry = 0;
    unsigned long lastGPS = 0;
    unsigned long bootTime = 0;
} state;

// ─── AT Command Helper ─────────────────────────────────
String sendAT(const char* cmd, unsigned long timeout = 2000) {
    simSerial.println(cmd);
    String response = "";
    unsigned long start = millis();
    while (millis() - start < timeout) {
        while (simSerial.available()) {
            response += (char)simSerial.read();
        }
        if (response.indexOf("OK") >= 0 || response.indexOf("ERROR") >= 0) {
            break;
        }
    }
    Serial.printf("[AT] %s → %s\n", cmd, response.c_str());
    return response;
}

// ─── SIM7600 Init ──────────────────────────────────────
bool initSIM7600() {
    Serial.println("[SIM] Powering on SIM7600...");
    pinMode(SIM7600_PWRKEY, OUTPUT);
    digitalWrite(SIM7600_PWRKEY, HIGH);
    delay(500);
    digitalWrite(SIM7600_PWRKEY, LOW);
    delay(3000);

    simSerial.begin(115200, SERIAL_8N1, SIM7600_RX, SIM7600_TX);
    delay(1000);

    // Basic check
    for (int i = 0; i < 10; i++) {
        String r = sendAT("AT", 1000);
        if (r.indexOf("OK") >= 0) {
            state.sim7600Ready = true;
            break;
        }
        delay(1000);
    }

    if (!state.sim7600Ready) {
        Serial.println("[SIM] FAILED — SIM7600 not responding");
        return false;
    }

    // Disable echo
    sendAT("ATE0");

    // Check SIM
    sendAT("AT+CPIN?");

    // Set APN
    char apnCmd[64];
    snprintf(apnCmd, sizeof(apnCmd), "AT+CGDCONT=1,\"IP\",\"%s\"", APN);
    sendAT(apnCmd);

    // Activate data
    sendAT("AT+NETOPEN", 5000);
    delay(2000);

    // Check signal
    String csq = sendAT("AT+CSQ");
    // Parse signal strength (AT+CSQ returns +CSQ: XX,YY)
    int csqIdx = csq.indexOf("+CSQ:");
    if (csqIdx >= 0) {
        state.signalStrength = csq.substring(csqIdx + 6, csq.indexOf(",", csqIdx)).toInt();
    }

    // Enable GPS
    sendAT("AT+CGPS=1", 3000);

    Serial.printf("[SIM] Ready. Signal: %d/31\n", state.signalStrength);
    return true;
}

// ─── GPS Reading ───────────────────────────────────────
void readGPS() {
    // Request NMEA data from SIM7600 GPS
    simSerial.println("AT+CGPSINFO");
    delay(100);

    String nmea = "";
    unsigned long start = millis();
    while (millis() - start < 1000) {
        while (simSerial.available()) {
            char c = simSerial.read();
            nmea += c;
            gps.encode(c);
        }
    }

    if (gps.location.isValid()) {
        state.lat = gps.location.lat();
        state.lon = gps.location.lng();
        state.alt = gps.altitude.meters();
        state.speed = gps.speed.kmph();
        state.satellites = gps.satellites.value();
        state.gpsFix = true;
    }
}

// ─── Sensor Reading ────────────────────────────────────
void readSensors() {
    // BME280
    state.temperature = bme.readTemperature();
    state.humidity = bme.readHumidity();
    state.pressure = bme.readPressure() / 100.0;  // hPa

    // INA219 (battery monitor)
    state.voltage = ina219.getBusVoltage_V();
    state.current = ina219.getCurrent_mA();
}

// ─── MQTT via SIM7600 AT Commands ──────────────────────
bool mqttConnect() {
    // SIM7600 has built-in MQTT support via AT+CMQTT
    sendAT("AT+CMQTTSTART", 3000);
    delay(1000);

    char cmd[256];
    snprintf(cmd, sizeof(cmd),
        "AT+CMQTTACCQ=0,\"%s\"", DEVICE_ID);
    sendAT(cmd, 3000);

    snprintf(cmd, sizeof(cmd),
        "AT+CMQTTCONNECT=0,\"tcp://%s:%d\",60,1,\"%s\",\"%s\"",
        MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASS);
    String r = sendAT(cmd, 10000);

    if (r.indexOf("OK") >= 0) {
        state.mqttConnected = true;

        // Subscribe to command topic
        snprintf(cmd, sizeof(cmd),
            "AT+CMQTTSUB=0,%d,1", strlen(TOPIC_CMD));
        sendAT(cmd, 2000);
        delay(100);
        simSerial.print(TOPIC_CMD);
        delay(1000);

        Serial.println("[MQTT] Connected & subscribed");
        return true;
    }

    Serial.println("[MQTT] Connection failed");
    return false;
}

void mqttPublish(const char* topic, const char* payload) {
    char cmd[128];
    int payloadLen = strlen(payload);
    int topicLen = strlen(topic);

    // Set topic
    snprintf(cmd, sizeof(cmd), "AT+CMQTTTOPIC=0,%d", topicLen);
    sendAT(cmd, 1000);
    delay(100);
    simSerial.print(topic);
    delay(500);

    // Set payload and publish
    snprintf(cmd, sizeof(cmd), "AT+CMQTTPAYLOAD=0,%d", payloadLen);
    sendAT(cmd, 1000);
    delay(100);
    simSerial.print(payload);
    delay(500);

    sendAT("AT+CMQTTPUB=0,1,60", 3000);
}

// ─── Telemetry Publish ─────────────────────────────────
void publishTelemetry() {
    JsonDocument doc;
    doc["device"] = DEVICE_ID;
    doc["ts"] = millis() - state.bootTime;
    doc["temp"] = round(state.temperature * 10) / 10.0;
    doc["hum"] = round(state.humidity * 10) / 10.0;
    doc["pres"] = round(state.pressure * 10) / 10.0;
    doc["bat_v"] = round(state.voltage * 100) / 100.0;
    doc["bat_ma"] = round(state.current * 10) / 10.0;
    doc["csq"] = state.signalStrength;
    doc["uptime_s"] = (millis() - state.bootTime) / 1000;

    char payload[512];
    serializeJson(doc, payload, sizeof(payload));
    mqttPublish(TOPIC_TELEMETRY, payload);
    Serial.printf("[TEL] %s\n", payload);
}

void publishGPS() {
    if (!state.gpsFix) return;

    JsonDocument doc;
    doc["device"] = DEVICE_ID;
    doc["lat"] = state.lat;
    doc["lon"] = state.lon;
    doc["alt"] = state.alt;
    doc["speed"] = state.speed;
    doc["sats"] = state.satellites;

    char payload[256];
    serializeJson(doc, payload, sizeof(payload));
    mqttPublish(TOPIC_GPS, payload);
}

// ─── Command Handler ───────────────────────────────────
void handleCommand(const char* payload) {
    JsonDocument doc;
    if (deserializeJson(doc, payload)) {
        Serial.println("[CMD] Invalid JSON");
        return;
    }

    const char* action = doc["action"];
    Serial.printf("[CMD] Action: %s\n", action);

    if (strcmp(action, "ping") == 0) {
        mqttPublish(TOPIC_STATUS, "{\"status\":\"alive\"}");
    }
    else if (strcmp(action, "reboot") == 0) {
        mqttPublish(TOPIC_STATUS, "{\"status\":\"rebooting\"}");
        delay(1000);
        ESP.restart();
    }
    else if (strcmp(action, "locate") == 0) {
        // Force GPS publish
        readGPS();
        publishGPS();
    }
    else if (strcmp(action, "relay_on") == 0) {
        // Activate relay (start robot/scan)
        int pin = doc["pin"] | 25;
        pinMode(pin, OUTPUT);
        digitalWrite(pin, HIGH);
        mqttPublish(TOPIC_STATUS, "{\"relay\":\"on\"}");
    }
    else if (strcmp(action, "relay_off") == 0) {
        int pin = doc["pin"] | 25;
        pinMode(pin, OUTPUT);
        digitalWrite(pin, LOW);
        mqttPublish(TOPIC_STATUS, "{\"relay\":\"off\"}");
    }
    else if (strcmp(action, "sms") == 0) {
        // Send SMS alert
        const char* number = doc["number"];
        const char* message = doc["message"];
        if (number && message) {
            char cmd[64];
            snprintf(cmd, sizeof(cmd), "AT+CMGS=\"%s\"", number);
            sendAT(cmd, 2000);
            delay(100);
            simSerial.print(message);
            simSerial.write(0x1A);  // Ctrl+Z to send
            delay(5000);
        }
    }
    else if (strcmp(action, "set_interval") == 0) {
        // Dynamic telemetry interval
        // (would need a global var, simplified here)
        Serial.printf("[CMD] New interval: %dms\n", doc["ms"].as<int>());
    }
}

// ─── Check for incoming MQTT messages ──────────────────
void checkMQTTMessages() {
    // SIM7600 sends URC: +CMQTTRXSTART, +CMQTTRXPAYLOAD, +CMQTTRXEND
    while (simSerial.available()) {
        String line = simSerial.readStringUntil('\n');
        if (line.indexOf("+CMQTTRXPAYLOAD") >= 0) {
            // Next line is the payload
            delay(100);
            String payload = simSerial.readStringUntil('\n');
            payload.trim();
            handleCommand(payload.c_str());
        }
    }
}

// ─── Alerts ────────────────────────────────────────────
void checkAlerts() {
    // Low battery
    if (state.voltage > 0 && state.voltage < 3.3) {
        char msg[128];
        snprintf(msg, sizeof(msg),
            "{\"alert\":\"low_battery\",\"voltage\":%.2f}", state.voltage);
        mqttPublish(TOPIC_ALERT, msg);
    }

    // High temperature (device overheating)
    if (state.temperature > 55) {
        char msg[128];
        snprintf(msg, sizeof(msg),
            "{\"alert\":\"overtemp\",\"temp\":%.1f}", state.temperature);
        mqttPublish(TOPIC_ALERT, msg);
    }

    // Signal lost
    if (state.signalStrength < 5 && state.signalStrength > 0) {
        mqttPublish(TOPIC_ALERT, "{\"alert\":\"weak_signal\"}");
    }
}

// ─── Setup ─────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    Serial.println("\n=== ArchiScan Gateway ===");
    Serial.printf("Device: %s\n", DEVICE_ID);

    state.bootTime = millis();

    // LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH);

    // I2C sensors
    Wire.begin(21, 22);
    if (bme.begin(0x76)) {
        Serial.println("[I2C] BME280 OK");
    }
    if (ina219.begin()) {
        Serial.println("[I2C] INA219 OK");
    }

    // SIM7600
    if (initSIM7600()) {
        delay(2000);
        mqttConnect();
    }

    // Announce online
    mqttPublish(TOPIC_STATUS, "{\"status\":\"online\",\"fw\":\"1.0.0\"}");
    digitalWrite(LED_PIN, LOW);

    Serial.println("[BOOT] Gateway ready");
}

// ─── Loop ──────────────────────────────────────────────
void loop() {
    unsigned long now = millis();

    // GPS update
    if (now - state.lastGPS >= GPS_INTERVAL_MS) {
        readGPS();
        publishGPS();
        state.lastGPS = now;
    }

    // Telemetry update
    if (now - state.lastTelemetry >= TELEMETRY_INTERVAL_MS) {
        readSensors();
        publishTelemetry();
        checkAlerts();
        state.lastTelemetry = now;
    }

    // Check incoming commands
    checkMQTTMessages();

    // Heartbeat LED
    digitalWrite(LED_PIN, (now / 1000) % 2);

    // Reconnect MQTT if needed
    if (!state.mqttConnected && (now % 60000 < 100)) {
        mqttConnect();
    }

    delay(100);
}
```

## Server-Side — MQTT to OpenClaw Bridge

### Docker Compose (Mosquitto + Node.js Bridge)

```yaml
# docker-compose.gateway.yml
version: '3.8'
services:
  mosquitto:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - mosquitto_data:/mosquitto/data
    restart: unless-stopped

  gateway-bridge:
    build: ./gateway-bridge
    environment:
      - MQTT_BROKER=mosquitto
      - MQTT_PORT=1883
      - OPENCLAW_API=http://openclaw:3000
    depends_on:
      - mosquitto
    restart: unless-stopped

volumes:
  mosquitto_data:
```

### Mosquitto Config

```
# mosquitto/config/mosquitto.conf
listener 1883
allow_anonymous false
password_file /mosquitto/config/passwd

listener 9001
protocol websockets
```

### Node.js MQTT Bridge

```javascript
// gateway-bridge/index.js
// Bridges T-SIM7600 MQTT telemetry to OpenClaw and stores GPS tracks

import mqtt from 'mqtt';
import { writeFile, appendFile, mkdir } from 'fs/promises';

const MQTT_URL = `mqtt://${process.env.MQTT_BROKER || 'localhost'}:${process.env.MQTT_PORT || 1883}`;

const client = mqtt.connect(MQTT_URL, {
    username: process.env.MQTT_USER || 'archiscan',
    password: process.env.MQTT_PASS || 'changeme',
});

// State per device
const devices = new Map();

client.on('connect', () => {
    console.log('[MQTT] Connected to broker');
    // Subscribe to all ArchiScan gateway topics
    client.subscribe('archiscan/gw/+/telemetry');
    client.subscribe('archiscan/gw/+/gps');
    client.subscribe('archiscan/gw/+/status');
    client.subscribe('archiscan/gw/+/alert');
});

client.on('message', async (topic, message) => {
    const parts = topic.split('/');
    const deviceId = parts[2];
    const channel = parts[3];
    const payload = JSON.parse(message.toString());

    console.log(`[${deviceId}/${channel}]`, JSON.stringify(payload));

    // Update device state
    if (!devices.has(deviceId)) {
        devices.set(deviceId, { firstSeen: new Date(), gpsTrack: [] });
    }
    const dev = devices.get(deviceId);
    dev.lastSeen = new Date();
    dev[channel] = payload;

    switch (channel) {
        case 'gps':
            // Append to GPS track
            dev.gpsTrack.push({
                ts: new Date().toISOString(),
                lat: payload.lat,
                lon: payload.lon,
                alt: payload.alt,
                speed: payload.speed,
            });

            // Save GeoJSON track
            await saveGeoJSON(deviceId, dev.gpsTrack);
            break;

        case 'alert':
            console.warn(`[ALERT] ${deviceId}: ${payload.alert}`);
            // Could forward to Slack, email, etc.
            break;

        case 'telemetry':
            // Log to CSV
            const logDir = `./logs/${deviceId}`;
            await mkdir(logDir, { recursive: true });
            const line = `${new Date().toISOString()},${payload.temp},${payload.hum},${payload.bat_v},${payload.bat_ma},${payload.csq}\n`;
            await appendFile(`${logDir}/telemetry.csv`, line);
            break;
    }
});

async function saveGeoJSON(deviceId, track) {
    const geojson = {
        type: 'FeatureCollection',
        features: [
            {
                type: 'Feature',
                geometry: {
                    type: 'LineString',
                    coordinates: track.map(p => [p.lon, p.lat, p.alt]),
                },
                properties: {
                    device: deviceId,
                    startTime: track[0]?.ts,
                    endTime: track[track.length - 1]?.ts,
                    points: track.length,
                },
            },
            // Current position as point
            {
                type: 'Feature',
                geometry: {
                    type: 'Point',
                    coordinates: [
                        track[track.length - 1]?.lon,
                        track[track.length - 1]?.lat,
                    ],
                },
                properties: {
                    device: deviceId,
                    label: 'Current Position',
                    ts: track[track.length - 1]?.ts,
                },
            },
        ],
    };

    const dir = `./tracks/${deviceId}`;
    await mkdir(dir, { recursive: true });
    await writeFile(`${dir}/track.geojson`, JSON.stringify(geojson, null, 2));
}

// ─── Send commands to devices ──────────────────────────
export function sendCommand(deviceId, action, params = {}) {
    const topic = `archiscan/gw/${deviceId}/cmd`;
    const payload = JSON.stringify({ action, ...params });
    client.publish(topic, payload);
    console.log(`[CMD] → ${deviceId}: ${payload}`);
}

// ─── HTTP API for OpenClaw integration ─────────────────
import { createServer } from 'http';

const server = createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');

    // GET /devices — list all known devices
    if (url.pathname === '/devices' && req.method === 'GET') {
        const list = [];
        for (const [id, dev] of devices) {
            list.push({
                id,
                lastSeen: dev.lastSeen,
                gps: dev.gps,
                telemetry: dev.telemetry,
                status: dev.status,
                trackPoints: dev.gpsTrack.length,
            });
        }
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(list, null, 2));
        return;
    }

    // POST /cmd/:deviceId — send command
    if (url.pathname.startsWith('/cmd/') && req.method === 'POST') {
        const deviceId = url.pathname.split('/')[2];
        let body = '';
        req.on('data', c => body += c);
        req.on('end', () => {
            const { action, ...params } = JSON.parse(body);
            sendCommand(deviceId, action, params);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ sent: true }));
        });
        return;
    }

    // GET /track/:deviceId — get GeoJSON track
    if (url.pathname.startsWith('/track/') && req.method === 'GET') {
        const deviceId = url.pathname.split('/')[2];
        const dev = devices.get(deviceId);
        if (dev) {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(dev.gpsTrack));
        } else {
            res.writeHead(404);
            res.end('Device not found');
        }
        return;
    }

    res.writeHead(404);
    res.end('Not found');
});

server.listen(8090, () => {
    console.log('[HTTP] Gateway API on :8090');
});
```

## USB Tethering — Pi/Jetson Internet via T-SIM7600

The T-SIM7600 can share its 4G connection with a Raspberry Pi or Jetson via USB:

```bash
# On the Pi/Jetson, plug the T-SIM7600 via USB-C
# The SIM7600 appears as a network interface (RNDIS)

# Check interface
ip link show | grep -i usb
# Usually: usb0 or enx...

# Enable DHCP on USB interface
sudo dhclient usb0

# Verify connectivity
ping -c 3 8.8.8.8

# Make permanent (add to /etc/network/interfaces)
# auto usb0
# iface usb0 inet dhcp
```

### AT Command to Enable RNDIS Mode

```bash
# From ESP32 firmware or via serial terminal:
# AT+CUSBPIDSWITCH=9011,1,1
# (Enables RNDIS mode — the SIM7600 acts as a USB modem)
```

## Field Deployment Scenarios

### Scenario 1 — Robot Survey Gateway

```
Robot (Pi + LiDAR)  ←── USB ───→  T-SIM7600  ←── 4G ───→  Cloud
                                     │
                                  GPS track
                                  Telemetry
                                  Remote start/stop
```

- Robot gets internet via USB tethering
- T-SIM7600 sends GPS position every 5s
- OpenClaw can remotely trigger scan start/stop via MQTT relay command
- Battery and temperature monitored — alerts if issues

### Scenario 2 — Static Site Monitor

```
T-SIM7600 (in IP65 box, solar powered)
    │
    ├── BME280: Temperature / humidity (chantier monitoring)
    ├── MPU6050: Vibration detection (structural alert)
    ├── Camera: Periodic site photos (ESP32-CAM via UART)
    └── GPS: Fixed position (geofence alert if stolen)
```

- Deployed on construction site for weeks/months
- Solar + LiPo for autonomous power
- Sends telemetry every 30s, photo every hour
- Alerts on vibration, temperature, battery, movement

### Scenario 3 — Drone Companion

```
Drone (DJI/PX4)  ←── WiFi ───→  T-SIM7600  ←── 4G ───→  Operator
                                     │
                                  GPS relay
                                  Telemetry bridge
                                  Emergency SMS
```

- T-SIM7600 mounted on drone or operator's vest
- Bridges drone WiFi telemetry to cloud via 4G
- Sends SMS alert if drone loses connection
- GPS track of operator position

## CLI Control Commands

```bash
# List connected gateways
curl http://localhost:8090/devices | jq

# Ping a device
curl -X POST http://localhost:8090/cmd/archiscan-gw-01 \
  -H 'Content-Type: application/json' \
  -d '{"action":"ping"}'

# Get GPS position
curl -X POST http://localhost:8090/cmd/archiscan-gw-01 \
  -d '{"action":"locate"}'

# Start robot relay
curl -X POST http://localhost:8090/cmd/archiscan-gw-01 \
  -d '{"action":"relay_on","pin":25}'

# Send SMS
curl -X POST http://localhost:8090/cmd/archiscan-gw-01 \
  -d '{"action":"sms","number":"+33612345678","message":"Scan terminé — 150 photos capturées"}'

# Get GPS track (GeoJSON)
curl http://localhost:8090/track/archiscan-gw-01 | jq

# Reboot device
curl -X POST http://localhost:8090/cmd/archiscan-gw-01 \
  -d '{"action":"reboot"}'
```

## Flashing the Firmware

```bash
# Install PlatformIO
pip install platformio

# Build and upload
cd firmware/
pio run -t upload

# Monitor serial output
pio device monitor -b 115200
```

## Tips

- **SIM card**: Use a IoT SIM (1NCE, Things Mobile) for low-cost M2M data (~0.5€/mois for telemetry).
- **Antennas**: Always connect both 4G and GPS external antennas — built-in antenna has poor reception.
- **Power**: LiPo 3.7V 2000mAh gives ~8h autonomy. Add 6V solar panel for multi-day deployment.
- **MQTT QoS**: Use QoS 1 for telemetry (at least once), QoS 0 for GPS (loss acceptable).
- **Deep sleep**: For static monitoring, use ESP32 deep sleep between readings to extend battery to weeks.
- **Security**: Use TLS on MQTT (AT+CMQTTCONNECT with ssl://), and certificate pinning if possible.
- **Fallback**: If MQTT fails, buffer messages on SD card and send when connection resumes.
