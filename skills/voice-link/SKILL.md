---
name: voice-link
description: Voice command channel for OpenClaw field operations — STT (Whisper/Deepgram) + TTS (ElevenLabs/Piper) + intent mapping to existing services. Not a chatbot — a hands-free command interface for operators on site. Use when asked about voice commands, vocal control, hands-free operation, or audio feedback for robots/drones/fleet.
---

# Voice-Link — Canal Voix Terrain pour OpenClaw

## Pourquoi c'est PAS un gadget (dans ce contexte)

```
  Bureau (gadget)                    Terrain (nécessité)
  ─────────────────                  ──────────────────────
  Assis, écran, clavier              Debout, casque, gants
  "Alexa, mets du jazz"             "Stop le robot"
  Alternative au clic                Seul moyen d'interagir
  Confort                            Sécurité
  Latence acceptable: 3s             Latence max: 500ms
  Erreur: on recommence              Erreur: collision
```

Voice-Link est conçu pour le terrain :
- **Commandes courtes** (2-4 mots), pas de conversation
- **Vocabulaire fermé** (~30 commandes), pas d'IA générative
- **Feedback audio bref** ("OK", "Batterie 40%"), pas de phrases longues
- **Wake word local** (pas de cloud pour l'activation)
- **Fallback physique** toujours disponible (bouton stop)

## Architecture

```
  Opérateur terrain
       │
       │ voix
       ▼
  ┌──────────┐     ┌──────────────┐     ┌──────────────────┐
  │ Micro    │────▶│ Wake Word    │────▶│ STT Engine       │
  │ (casque) │     │ (local)      │     │ Whisper / Deepgram│
  └──────────┘     │ "openclaw"   │     │                  │
                   └──────────────┘     └────────┬─────────┘
                                                 │ texte
                                                 ▼
                                        ┌──────────────────┐
                                        │ Intent Parser    │
                                        │                  │
                                        │ "stop le robot"  │
                                        │ → intent: stop   │
                                        │ → target: robot  │
                                        └────────┬─────────┘
                                                 │ commande
                                        ┌────────▼─────────┐
                                        │ Command Router   │
                                        │                  │
                                        │ fleet/cmd POST   │
                                        │ {action: "stop"} │
                                        └────────┬─────────┘
                                                 │ résultat
                                        ┌────────▼─────────┐
                                        │ TTS Engine       │
                                        │ Piper (local)    │
                                        │ ou ElevenLabs    │
                                        └────────┬─────────┘
                                                 │ audio
                                                 ▼
                                           Casque opérateur
                                           "Robot arrêté"

  Latence cible bout en bout: < 800ms
  Wake word → STT → Intent → Commande → TTS → Retour audio
```

## Choix STT/TTS — pragmatique, pas gadget

### STT (Speech-to-Text)

| Option | Latence | Coût | Offline | Qualité bruit | Usage |
|--------|---------|------|---------|---------------|-------|
| **Whisper.cpp local** | ~200ms | Gratuit | Oui | Moyen | Default — tourne sur le gateway |
| **Deepgram Nova-2** | ~150ms | $0.0043/min | Non | Excellent | Si internet dispo |
| **Vosk** | ~100ms | Gratuit | Oui | Bon | Alternative légère |

**Recommandation** : Whisper.cpp en local (fonctionne offline sur chantier), fallback Deepgram si connecté.

### TTS (Text-to-Speech)

| Option | Latence | Coût | Offline | Naturalité | Usage |
|--------|---------|------|---------|------------|-------|
| **Piper** | ~50ms | Gratuit | Oui | Correct | Default — ultra rapide, local |
| **ElevenLabs** | ~300ms | $0.30/1K chars | Non | Excellent | Optionnel, si connecté |
| **Coqui XTTS** | ~150ms | Gratuit | Oui | Bon | Alternative locale |
| **espeak** | ~10ms | Gratuit | Oui | Robot | Fallback minimal |

**Recommandation** : Piper en local (voix FR correcte, 50ms). ElevenLabs n'apporte rien
pour des réponses de 3 mots sur un chantier bruyant. Garder en option si l'user le veut.

### Wake Word (détection locale)

| Option | CPU | Offline | Custom word |
|--------|-----|---------|-------------|
| **OpenWakeWord** | Minimal | Oui | Oui |
| **Porcupine** | Minimal | Oui | Oui (payant) |
| **Snowboy** | Minimal | Oui | Oui |

**Recommandation** : OpenWakeWord — open source, custom wake word "openclaw".

## Vocabulaire de commandes (fermé)

Le parser n'utilise PAS d'IA générative. C'est un matcher de patterns rapide.
~30 commandes couvrent 95% des besoins terrain.

```yaml
# runtime/intents.yml — Vocabulaire voix OpenClaw

intents:
  # ─── Contrôle direct ───────────────────────────────
  - id: stop
    patterns:
      - "stop"
      - "stop le robot"
      - "stop le drone"
      - "arrête"
      - "arrête tout"
      - "halt"
    target: auto          # Déduit du contexte ou du mot
    action: emergency_stop
    confirm: false        # Pas de confirmation — urgence
    response: "Arrêt d'urgence"

  - id: go
    patterns:
      - "go"
      - "avance"
      - "continue"
      - "reprends"
      - "c'est bon"
    action: resume
    response: "Reprise"

  - id: return_home
    patterns:
      - "rentre"
      - "retour base"
      - "reviens"
      - "retour"
      - "go home"
    action: return_home
    response: "Retour base"

  - id: land
    patterns:
      - "atterris"
      - "pose-toi"
      - "land"
      - "descends"
    target_type: drone
    action: land
    response: "Atterrissage"

  - id: takeoff
    patterns:
      - "décolle"
      - "takeoff"
      - "envole"
    target_type: drone
    action: takeoff
    confirm: true         # Confirmation requise pour sécurité
    response: "Décollage confirmé"

  # ─── Requêtes d'info ──────────────────────────────
  - id: battery
    patterns:
      - "batterie"
      - "niveau batterie"
      - "combien de batterie"
      - "battery"
      - "autonomie"
    action: query_battery
    response_template: "{entity} : batterie {battery} pourcent"

  - id: position
    patterns:
      - "position"
      - "où est"
      - "localise"
      - "où il est"
      - "where"
    action: query_position
    response_template: "{entity} : zone {zone}"

  - id: status
    patterns:
      - "status"
      - "état"
      - "ça va"
      - "comment ça va"
      - "rapport"
    action: query_status
    response_template: "{count} entités en ligne, {alerts} alertes"

  # ─── Missions ─────────────────────────────────────
  - id: start_mission
    patterns:
      - "lance la mission"
      - "démarre le scan"
      - "start mission"
      - "commence le relevé"
    action: start_mission
    confirm: true
    response: "Mission lancée"

  - id: abort_mission
    patterns:
      - "annule la mission"
      - "abort"
      - "stop mission"
      - "arrête la mission"
    action: abort_mission
    confirm: true
    response: "Mission annulée"

  # ─── Geofence ─────────────────────────────────────
  - id: extend_zone
    patterns:
      - "étends la zone"
      - "agrandis le périmètre"
      - "plus grand"
    action: extend_geofence
    confirm: true
    response: "Zone étendue"

  - id: lock_zone
    patterns:
      - "verrouille la zone"
      - "lock"
      - "bloque le périmètre"
    action: lock_geofence
    response: "Zone verrouillée"

  # ─── Micro-UI ─────────────────────────────────────
  - id: show_map
    patterns:
      - "montre la carte"
      - "affiche la carte"
      - "ouvre la carte"
      - "show map"
    action: spawn_panel
    panel: fleet-map
    response: "Carte affichée"

  - id: show_config
    patterns:
      - "ouvre la config"
      - "configuration"
      - "paramètres"
    action: spawn_panel
    panel: gateway-config
    response: "Config ouverte"

  # ─── Confirmation / Annulation ────────────────────
  - id: confirm_yes
    patterns:
      - "oui"
      - "confirme"
      - "yes"
      - "ok"
      - "affirmatif"
      - "go"
    action: confirm
    internal: true

  - id: confirm_no
    patterns:
      - "non"
      - "annule"
      - "no"
      - "cancel"
      - "négatif"
    action: cancel
    internal: true

  # ─── Système ──────────────────────────────────────
  - id: mute
    patterns:
      - "silence"
      - "tais-toi"
      - "mute"
      - "coupe le son"
    action: mute_tts
    response: null        # Pas de réponse vocale (il a dit silence)

  - id: unmute
    patterns:
      - "parle"
      - "unmute"
      - "remet le son"
      - "réactive"
    action: unmute_tts
    response: "Audio réactivé"
```

## Runtime — Voice-Link Engine

```javascript
// runtime/voice-link.js
// Minimal voice command engine — wake word + STT + intent matching + TTS

import { spawn } from 'child_process';
import { readFileSync } from 'fs';
import { join } from 'path';
import YAML from 'yaml';

// ─── Config ────────────────────────────────────────────
const CONFIG = {
    // STT
    stt_engine: process.env.STT_ENGINE || 'whisper',  // whisper | deepgram | vosk
    whisper_model: 'small',   // tiny | base | small | medium
    whisper_lang: 'fr',
    deepgram_key: process.env.DEEPGRAM_API_KEY || '',

    // TTS
    tts_engine: process.env.TTS_ENGINE || 'piper',    // piper | elevenlabs | espeak
    piper_model: 'fr_FR-siwis-medium',
    piper_bin: '/usr/local/bin/piper',
    elevenlabs_key: process.env.ELEVENLABS_API_KEY || '',
    elevenlabs_voice: 'onyx',

    // Wake word
    wake_word: 'openclaw',
    wake_engine: 'openwakeword',

    // Services
    fleet_api: 'http://localhost:8091',
    mui_api: 'http://localhost:4040',

    // Audio
    sample_rate: 16000,
    vad_threshold: 0.5,      // Voice Activity Detection
    max_listen_s: 5,         // Max recording after wake word
    silence_timeout_ms: 800, // Stop recording after silence

    // Safety
    confirm_dangerous: true,  // Require "oui" for dangerous commands
};

// ─── Load intents ──────────────────────────────────────
const intentsFile = readFileSync(join(import.meta.dirname, 'intents.yml'), 'utf-8');
const { intents } = YAML.parse(intentsFile);
console.log(`[VOICE] Loaded ${intents.length} intent patterns`);

// ─── Intent Matcher (no AI, just fast pattern matching) ─
class IntentMatcher {
    constructor(intents) {
        this.intents = intents;
        // Pre-compile: normalize patterns for fuzzy matching
        this.compiled = intents.map(intent => ({
            ...intent,
            normalized: intent.patterns.map(p => this.normalize(p)),
        }));
    }

    normalize(text) {
        return text
            .toLowerCase()
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '')  // Remove accents
            .replace(/[^a-z0-9 ]/g, '')
            .trim();
    }

    match(transcript) {
        const input = this.normalize(transcript);
        let bestMatch = null;
        let bestScore = 0;

        for (const intent of this.compiled) {
            for (const pattern of intent.normalized) {
                const score = this.similarity(input, pattern);
                if (score > bestScore && score > 0.6) {  // 60% minimum match
                    bestScore = score;
                    bestMatch = { intent, score };
                }
            }
        }

        if (bestMatch) {
            console.log(`[INTENT] "${transcript}" → ${bestMatch.intent.id} (${(bestMatch.score * 100).toFixed(0)}%)`);
            return bestMatch.intent;
        }

        console.log(`[INTENT] "${transcript}" → no match`);
        return null;
    }

    similarity(a, b) {
        // Exact match
        if (a === b) return 1.0;
        // Contains
        if (a.includes(b) || b.includes(a)) return 0.9;
        // Word overlap (Jaccard)
        const wordsA = new Set(a.split(' '));
        const wordsB = new Set(b.split(' '));
        const intersection = [...wordsA].filter(w => wordsB.has(w)).length;
        const union = new Set([...wordsA, ...wordsB]).size;
        return intersection / union;
    }

    // Extract target entity from transcript
    extractTarget(transcript) {
        const lower = transcript.toLowerCase();
        // Match entity names/types
        if (lower.includes('robot') || lower.includes('spot') || lower.includes('go2')) return { type: 'robot' };
        if (lower.includes('drone') || lower.includes('dji'))   return { type: 'drone' };
        // Match specific IDs
        const idMatch = lower.match(/gw[- ]?(\d+)/);
        if (idMatch) return { id: `gw-${idMatch[1].padStart(2, '0')}` };
        return null;  // All entities
    }
}

const matcher = new IntentMatcher(intents);

// ─── STT Engines ───────────────────────────────────────

// Whisper.cpp (local, offline)
async function sttWhisper(audioBuffer) {
    return new Promise((resolve, reject) => {
        const proc = spawn('whisper-cpp', [
            '--model', `models/ggml-${CONFIG.whisper_model}.bin`,
            '--language', CONFIG.whisper_lang,
            '--no-timestamps',
            '--output-txt',
            '-f', '-',  // stdin
        ]);

        let output = '';
        proc.stdout.on('data', d => output += d.toString());
        proc.stderr.on('data', () => {});  // Suppress progress
        proc.on('close', () => {
            const text = output.trim().replace(/^\[.*?\]\s*/gm, '');
            resolve(text);
        });
        proc.on('error', reject);
        proc.stdin.write(audioBuffer);
        proc.stdin.end();
    });
}

// Deepgram (cloud, low latency)
async function sttDeepgram(audioBuffer) {
    const res = await fetch('https://api.deepgram.com/v1/listen?language=fr&model=nova-2', {
        method: 'POST',
        headers: {
            'Authorization': `Token ${CONFIG.deepgram_key}`,
            'Content-Type': 'audio/wav',
        },
        body: audioBuffer,
    });
    const data = await res.json();
    return data.results?.channels?.[0]?.alternatives?.[0]?.transcript || '';
}

// Vosk (local, lightweight)
async function sttVosk(audioBuffer) {
    return new Promise((resolve, reject) => {
        const proc = spawn('vosk-transcriber', [
            '--model', 'models/vosk-model-small-fr',
            '--input', '-',
        ]);
        let output = '';
        proc.stdout.on('data', d => output += d.toString());
        proc.on('close', () => {
            try {
                const result = JSON.parse(output);
                resolve(result.text || '');
            } catch {
                resolve(output.trim());
            }
        });
        proc.on('error', reject);
        proc.stdin.write(audioBuffer);
        proc.stdin.end();
    });
}

async function transcribe(audioBuffer) {
    const start = Date.now();
    let text;

    switch (CONFIG.stt_engine) {
        case 'deepgram':
            text = await sttDeepgram(audioBuffer);
            break;
        case 'vosk':
            text = await sttVosk(audioBuffer);
            break;
        case 'whisper':
        default:
            text = await sttWhisper(audioBuffer);
            break;
    }

    console.log(`[STT] "${text}" (${Date.now() - start}ms, ${CONFIG.stt_engine})`);
    return text;
}

// ─── TTS Engines ───────────────────────────────────────

// Piper (local, fast, good quality)
async function ttsPiper(text) {
    return new Promise((resolve, reject) => {
        const proc = spawn(CONFIG.piper_bin, [
            '--model', CONFIG.piper_model,
            '--output-raw',
        ]);

        const chunks = [];
        proc.stdout.on('data', d => chunks.push(d));
        proc.on('close', () => resolve(Buffer.concat(chunks)));
        proc.on('error', reject);
        proc.stdin.write(text);
        proc.stdin.end();
    });
}

// ElevenLabs (cloud, premium voice)
async function ttsElevenLabs(text) {
    const res = await fetch(
        `https://api.elevenlabs.io/v1/text-to-speech/${CONFIG.elevenlabs_voice}`,
        {
            method: 'POST',
            headers: {
                'xi-api-key': CONFIG.elevenlabs_key,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text,
                model_id: 'eleven_multilingual_v2',
                voice_settings: {
                    stability: 0.7,
                    similarity_boost: 0.5,
                    speed: 1.2,  // Slightly faster for field use
                },
            }),
        }
    );
    return Buffer.from(await res.arrayBuffer());
}

// espeak (fallback, robotic but instant)
async function ttsEspeak(text) {
    return new Promise((resolve, reject) => {
        const proc = spawn('espeak', ['-v', 'fr', '--stdout', text]);
        const chunks = [];
        proc.stdout.on('data', d => chunks.push(d));
        proc.on('close', () => resolve(Buffer.concat(chunks)));
        proc.on('error', reject);
    });
}

async function speak(text) {
    if (!text || voiceState.muted) return;

    const start = Date.now();
    let audio;

    switch (CONFIG.tts_engine) {
        case 'elevenlabs':
            audio = await ttsElevenLabs(text);
            break;
        case 'espeak':
            audio = await ttsEspeak(text);
            break;
        case 'piper':
        default:
            audio = await ttsPiper(text);
            break;
    }

    console.log(`[TTS] "${text}" (${Date.now() - start}ms, ${CONFIG.tts_engine})`);

    // Play audio through speaker
    const player = spawn('aplay', ['-r', '22050', '-f', 'S16_LE', '-']);
    player.stdin.write(audio);
    player.stdin.end();
}

// ─── Command Router ────────────────────────────────────

const voiceState = {
    muted: false,
    pendingConfirm: null,  // { intent, target, timestamp }
};

async function executeIntent(intent, transcript) {
    const target = matcher.extractTarget(transcript);

    // ── Confirmation flow ──
    if (intent.id === 'confirm_yes' && voiceState.pendingConfirm) {
        const pending = voiceState.pendingConfirm;
        voiceState.pendingConfirm = null;
        return executeAction(pending.intent, pending.target);
    }
    if (intent.id === 'confirm_no' && voiceState.pendingConfirm) {
        voiceState.pendingConfirm = null;
        await speak('Annulé');
        return;
    }

    // ── Requires confirmation? ──
    if (intent.confirm && CONFIG.confirm_dangerous) {
        voiceState.pendingConfirm = { intent, target, timestamp: Date.now() };
        await speak(`Confirmer : ${intent.response || intent.id} ?`);
        return;
    }

    // ── Direct execution ──
    return executeAction(intent, target);
}

async function executeAction(intent, target) {
    try {
        switch (intent.action) {
            // ── Direct commands to fleet ──
            case 'emergency_stop':
            case 'stop':
            case 'resume':
            case 'return_home':
            case 'land':
            case 'takeoff': {
                const targets = target?.id || target?.type || intent.target_type || 'all';
                await fetch(`${CONFIG.fleet_api}/fleet/cmd`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ targets, action: intent.action }),
                });
                await speak(intent.response);
                break;
            }

            // ── Queries ──
            case 'query_battery': {
                const fleet = await (await fetch(`${CONFIG.fleet_api}/fleet`)).json();
                const entities = target?.id
                    ? fleet.entities.filter(e => e.id === target.id)
                    : target?.type
                    ? fleet.entities.filter(e => e.type === target.type)
                    : fleet.entities;

                for (const e of entities.slice(0, 3)) {  // Max 3 to keep it short
                    await speak(`${e.name} : batterie ${e.battery} pourcent`);
                }
                break;
            }

            case 'query_position': {
                const fleet = await (await fetch(`${CONFIG.fleet_api}/fleet`)).json();
                const entities = target?.id
                    ? fleet.entities.filter(e => e.id === target.id)
                    : fleet.entities.filter(e => e.lat !== null);

                for (const e of entities.slice(0, 3)) {
                    const zoneStatus = e.insideHomeZone ? 'dans la zone' : 'hors zone';
                    await speak(`${e.name} : ${zoneStatus}`);
                }
                break;
            }

            case 'query_status': {
                const fleet = await (await fetch(`${CONFIG.fleet_api}/fleet`)).json();
                const online = fleet.entities.filter(e => e.status === 'online').length;
                const total = fleet.entities.length;
                const missions = fleet.activeMissions?.length || 0;
                await speak(`${online} sur ${total} en ligne. ${missions} missions actives.`);
                break;
            }

            // ── Missions ──
            case 'start_mission': {
                // Start the first available mission (or a specific one)
                await fetch(`${CONFIG.fleet_api}/fleet/mission/start`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mission_id: target?.missionId || 'scan-interieur-complet' }),
                });
                await speak(intent.response);
                break;
            }

            case 'abort_mission': {
                await fetch(`${CONFIG.fleet_api}/fleet/mission/abort`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mission_id: 'scan-interieur-complet' }),
                });
                await speak(intent.response);
                break;
            }

            // ── Micro-UI ──
            case 'spawn_panel': {
                await fetch(`${CONFIG.mui_api}/panels/${intent.panel}/spawn`, {
                    method: 'POST',
                });
                await speak(intent.response);
                break;
            }

            // ── System ──
            case 'mute_tts':
                voiceState.muted = true;
                break;
            case 'unmute_tts':
                voiceState.muted = false;
                await speak(intent.response);
                break;

            default:
                await speak(intent.response || 'Commande reçue');
        }
    } catch (err) {
        console.error(`[CMD] Error:`, err.message);
        await speak('Erreur de commande');
    }
}

// ─── Audio Pipeline (main loop) ────────────────────────
// Simplified — in production, use a proper audio stream with VAD

async function voiceLoop() {
    console.log('[VOICE] Voice-Link active');
    console.log(`[VOICE] Wake word: "${CONFIG.wake_word}"`);
    console.log(`[VOICE] STT: ${CONFIG.stt_engine} | TTS: ${CONFIG.tts_engine}`);
    console.log('[VOICE] Say "openclaw" followed by a command...');

    await speak('Voice Link activé');

    // In production, this would be a continuous audio stream
    // with wake word detection → record → transcribe → act
    //
    // Simplified event-driven version:
    // The wake word detector emits events when triggered,
    // then we record for max_listen_s or until silence.

    // For now, expose an HTTP endpoint for testing
    const { createServer } = await import('http');

    const server = createServer(async (req, res) => {
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Methods', 'POST');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
        if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

        const url = new URL(req.url, 'http://localhost');

        // ── POST /voice/text — text input (for testing without mic) ──
        if (url.pathname === '/voice/text' && req.method === 'POST') {
            let body = '';
            req.on('data', c => body += c);
            req.on('end', async () => {
                const { text } = JSON.parse(body);
                console.log(`[VOICE] Text input: "${text}"`);

                const intent = matcher.match(text);
                if (intent) {
                    await executeIntent(intent, text);
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({
                        intent: intent.id,
                        action: intent.action,
                        response: intent.response,
                    }));
                } else {
                    await speak('Commande non reconnue');
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ intent: null, error: 'no_match' }));
                }
            });
            return;
        }

        // ── POST /voice/audio — raw audio input ──
        if (url.pathname === '/voice/audio' && req.method === 'POST') {
            const chunks = [];
            req.on('data', c => chunks.push(c));
            req.on('end', async () => {
                const audioBuffer = Buffer.concat(chunks);
                const text = await transcribe(audioBuffer);

                const intent = matcher.match(text);
                if (intent) {
                    await executeIntent(intent, text);
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({
                        transcript: text,
                        intent: intent.id,
                        action: intent.action,
                    }));
                } else {
                    await speak('Commande non reconnue');
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ transcript: text, intent: null }));
                }
            });
            return;
        }

        // ── GET /voice/status ──
        if (url.pathname === '/voice/status') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                active: true,
                stt: CONFIG.stt_engine,
                tts: CONFIG.tts_engine,
                muted: voiceState.muted,
                pending_confirm: voiceState.pendingConfirm?.intent?.id || null,
                wake_word: CONFIG.wake_word,
            }));
            return;
        }

        // ── GET /voice/intents — list all available commands ──
        if (url.pathname === '/voice/intents') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(intents.filter(i => !i.internal).map(i => ({
                id: i.id,
                patterns: i.patterns,
                confirm: i.confirm || false,
                response: i.response,
            })), null, 2));
            return;
        }

        res.writeHead(404);
        res.end('Not found');
    });

    server.listen(4050, () => {
        console.log(`[VOICE] HTTP test interface on :4050`);
        console.log(`[VOICE]   POST /voice/text  {"text":"stop le robot"}`);
        console.log(`[VOICE]   POST /voice/audio  (raw WAV)`);
        console.log(`[VOICE]   GET  /voice/status`);
        console.log(`[VOICE]   GET  /voice/intents`);
    });
}

voiceLoop();
```

## Intégration avec les autres skills

Voice-Link se branche sur les services existants — il n'invente rien :

```
  Voice-Link
       │
       ├── POST fleet_api/fleet/cmd     → archiscan-fleet (stop, go, land...)
       ├── GET  fleet_api/fleet         → archiscan-fleet (batterie, position)
       ├── POST fleet_api/fleet/mission → archiscan-fleet (start/abort mission)
       ├── POST mui_api/panels/spawn    → micro-ui (ouvre la carte, config...)
       └── POST mui_api/trigger         → micro-ui (événements)

  Il ne fait QUE router des commandes vocales vers les API existantes.
  Aucune logique métier dans Voice-Link.
```

## Installation terrain

```bash
# ── 1. STT — Whisper.cpp (recommandé, offline) ──
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp && make
bash models/download-ggml-model.sh small   # 466 MB
# Tester:
echo "test" | ./main -m models/ggml-small.bin -l fr -f -

# ── 2. TTS — Piper (recommandé, offline) ──
pip install piper-tts
# Ou binaire pré-compilé:
# https://github.com/rhasspy/piper/releases
piper --model fr_FR-siwis-medium --output-raw < "test" | aplay -r 22050 -f S16_LE

# ── 3. Wake word — OpenWakeWord ──
pip install openwakeword
# Custom model training pour "openclaw" :
# https://github.com/dscripka/openWakeWord

# ── 4. Lancer Voice-Link ──
STT_ENGINE=whisper TTS_ENGINE=piper node runtime/voice-link.js

# ── 5. Tester sans micro (mode texte) ──
curl -X POST http://localhost:4050/voice/text \
  -H 'Content-Type: application/json' \
  -d '{"text":"batterie du robot"}'

curl -X POST http://localhost:4050/voice/text \
  -d '{"text":"stop le drone"}'

curl -X POST http://localhost:4050/voice/text \
  -d '{"text":"montre la carte"}'

# ── 6. Tester avec audio ──
# Enregistrer 3 secondes de voix:
arecord -d 3 -r 16000 -f S16_LE cmd.wav
# Envoyer au voice-link:
curl -X POST http://localhost:4050/voice/audio \
  --data-binary @cmd.wav

# ── 7. Voir les commandes disponibles ──
curl -s http://localhost:4050/voice/intents | jq '.[].patterns[0]'
```

## Quand utiliser ElevenLabs vs Piper

| Situation | Choix | Pourquoi |
|-----------|-------|----------|
| Chantier, casque, bruit | **Piper** | 50ms latence, offline, suffisant |
| Démo client, showroom | **ElevenLabs** | Voix naturelle impressionne |
| Internet instable | **Piper** | Pas de dépendance réseau |
| Réponses longues (rapport) | **ElevenLabs** | Qualité sur phrases complexes |
| Commandes courtes (3 mots) | **Piper** | Aucune différence perceptible |
| Budget serré | **Piper** | Gratuit, open source |

En résumé : **Piper par défaut, ElevenLabs en option**. Sur le terrain, la latence
et la fiabilité offline importent plus que la naturalité de la voix.
