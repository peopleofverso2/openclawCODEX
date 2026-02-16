---
name: micro-ui
description: Micro-interfaces éphémères lancées à la volée par l'IA ou l'utilisateur. Chaque service OpenClaw peut déclarer des panels légers (HTML fragments) qui s'affichent en contexte, sans app lourde. Use when asked about UI panels, micro-interfaces, contextual dashboards, or on-the-fly interfaces for OpenClaw services.
---

# Micro-UI — Interfaces Contextuelles à la Volée

## Philosophie

OpenClaw n'est pas un OS classique avec des "applications". C'est un OS conversationnel
où l'IA orchestre des services. Mais parfois, une interface visuelle est plus efficace
qu'un échange texte : une carte, un graphique, un formulaire de config, un retour vidéo.

**Micro-UI** résout ça : des fragments HTML légers, déclaratifs, qui apparaissent
quand un service en a besoin — et disparaissent quand c'est fini.

```
                    ┌─────────────────────────────────────────────┐
                    │              OpenClaw OS                     │
                    │                                             │
                    │   Conversation IA  ←→  Services/Skills      │
                    │         │                    │               │
                    │         │    "j'ai besoin    │               │
                    │         │     d'une carte"   │               │
                    │         ▼                    ▼               │
                    │   ┌──────────────────────────────┐          │
                    │   │     Micro-UI Launcher         │          │
                    │   │                              │          │
                    │   │  ┌────┐ ┌────┐ ┌────┐       │          │
                    │   │  │Map │ │Cfg │ │Mon │  ...   │          │
                    │   │  │ μ  │ │ μ  │ │ μ  │       │          │
                    │   │  └────┘ └────┘ └────┘       │          │
                    │   └──────────────────────────────┘          │
                    │                                             │
                    │   μ = micro-panel (HTML fragment, ~50 LOC)  │
                    │   Lifecycle: spawn → interact → dismiss     │
                    └─────────────────────────────────────────────┘

Pas d'app store. Pas d'installation. Pas de fenêtres.
Juste des bulles d'interaction qui apparaissent au bon moment.
```

## Concepts Clés

| Concept | Description |
|---------|-------------|
| **Panel** | Un fragment HTML autonome (~50-200 LOC) avec son propre état |
| **Manifest** | Déclaration YAML de ce que le panel fait, quand il s'affiche |
| **Launcher** | Runtime Node.js qui sert les panels et gère leur cycle de vie |
| **Trigger** | Ce qui provoque l'apparition d'un panel (IA, service, user) |
| **Slot** | Où le panel s'affiche (overlay, sidebar, fullscreen, toast) |
| **Bridge** | Canal WebSocket entre le panel et le service backend |

## Architecture du Launcher

```
┌─────────────────────────────────────────────────────────────────┐
│                     micro-ui-launcher (Node.js)                  │
│                                                                  │
│  ┌──────────┐   ┌───────────┐   ┌────────────┐   ┌──────────┐  │
│  │ Registry │   │ Lifecycle │   │  Bridge    │   │ Security │  │
│  │          │   │           │   │ (WebSocket)│   │          │  │
│  │ panels/  │   │ spawn()   │   │            │   │ sandbox  │  │
│  │ *.yml    │◄─►│ dismiss() │◄─►│ panel ↔    │   │ CSP      │  │
│  │          │   │ resize()  │   │ service    │   │ scope    │  │
│  └──────────┘   └───────────┘   └────────────┘   └──────────┘  │
│                                                                  │
│  HTTP :4040                                                      │
│  ├── GET  /panels              → liste des panels disponibles   │
│  ├── POST /panels/:id/spawn    → lance un panel                 │
│  ├── POST /panels/:id/dismiss  → ferme un panel                 │
│  ├── GET  /panels/:id/render   → HTML du panel                  │
│  ├── WS   /bridge/:id          → canal data service ↔ panel    │
│  └── GET  /shell               → host page (contient les slots) │
└─────────────────────────────────────────────────────────────────┘
```

## Panel Manifest Format

Chaque panel est décrit par un fichier YAML + un fichier HTML.

```yaml
# panels/fleet-map.panel.yml
id: fleet-map
name: "Carte de la flotte"
description: "Carte Leaflet temps réel avec positions, zones, tracks"
version: 1

# Quand afficher ce panel automatiquement
triggers:
  - event: service.fleet.entities_online    # Quand des entités sont en ligne
    min_entities: 1
  - event: user.ask                         # Quand l'user demande "montre la carte"
    keywords: [carte, map, position, où, localise]
  - event: rule.triggered                   # Quand une règle geofence se déclenche
    rules: [geofence-breach, forbidden-zone]

# Connexion aux services
bridge:
  service: archiscan-fleet       # Quel service backend
  endpoints:                     # Quelles données le panel peut demander
    - GET /fleet
    - GET /fleet/map
    - POST /fleet/cmd
  refresh_ms: 3000               # Polling auto

# Affichage
display:
  slot: overlay                  # overlay | sidebar | fullscreen | toast | pip
  size: { width: 600, height: 450 }
  resizable: true
  position: bottom-right         # Pour overlay/toast
  auto_dismiss: false            # Se ferme automatiquement ?
  dismiss_after_s: null          # Durée avant auto-dismiss

# Dépendances externes (CDN chargé à la volée)
deps:
  css:
    - "https://unpkg.com/leaflet@1.9/dist/leaflet.css"
  js:
    - "https://unpkg.com/leaflet@1.9/dist/leaflet.js"

# Sécurité
security:
  sandbox: true                  # iframe sandboxé
  allow_scripts: true
  allow_network: [localhost]     # Seules ces origines autorisées
  max_memory_mb: 50
```

## Launcher Runtime

```javascript
// runtime/launcher.js
// Micro-UI Launcher — serves panels, manages lifecycle, bridges to services

import { createServer } from 'http';
import { WebSocketServer } from 'ws';
import { readFileSync, readdirSync, existsSync } from 'fs';
import { join } from 'path';
import YAML from 'yaml';

const PANELS_DIR = join(import.meta.dirname, '..', 'panels');
const PORT = 4040;
const WS_PORT = 4041;

// ─── Panel Registry ────────────────────────────────────
class PanelRegistry {
    constructor() {
        this.panels = new Map();        // id → manifest
        this.active = new Map();        // instanceId → { panel, state, ws, spawnedAt }
        this.instanceCounter = 0;
    }

    loadAll() {
        const files = readdirSync(PANELS_DIR).filter(f => f.endsWith('.panel.yml'));
        for (const file of files) {
            const manifest = YAML.parse(readFileSync(join(PANELS_DIR, file), 'utf-8'));
            const htmlFile = join(PANELS_DIR, file.replace('.panel.yml', '.html'));
            manifest._htmlPath = existsSync(htmlFile) ? htmlFile : null;
            this.panels.set(manifest.id, manifest);
            console.log(`[REG] Panel loaded: ${manifest.id} — ${manifest.name}`);
        }
        console.log(`[REG] ${this.panels.size} panels registered`);
    }

    spawn(panelId, params = {}) {
        const manifest = this.panels.get(panelId);
        if (!manifest) return null;

        const instanceId = `${panelId}-${++this.instanceCounter}`;
        const instance = {
            instanceId,
            panelId,
            manifest,
            params,
            state: 'spawned',       // spawned → visible → dismissed
            spawnedAt: Date.now(),
            ws: null,
        };

        this.active.set(instanceId, instance);
        console.log(`[SPAWN] ${instanceId} (${manifest.name})`);
        return instance;
    }

    dismiss(instanceId) {
        const instance = this.active.get(instanceId);
        if (!instance) return false;
        instance.state = 'dismissed';
        if (instance.ws) instance.ws.close();
        this.active.delete(instanceId);
        console.log(`[DISMISS] ${instanceId}`);
        return true;
    }

    dismissAll() {
        for (const [id] of this.active) this.dismiss(id);
    }

    getActive() {
        return [...this.active.values()].map(i => ({
            instanceId: i.instanceId,
            panelId: i.panelId,
            name: i.manifest.name,
            state: i.state,
            slot: i.manifest.display?.slot || 'overlay',
            age_s: Math.round((Date.now() - i.spawnedAt) / 1000),
        }));
    }
}

const registry = new PanelRegistry();
registry.loadAll();

// ─── Render Panel HTML ─────────────────────────────────
function renderPanel(manifest, instanceId, params) {
    // Load the panel's HTML
    let panelHTML = '';
    if (manifest._htmlPath) {
        panelHTML = readFileSync(manifest._htmlPath, 'utf-8');
    }

    // Inject deps
    const cssLinks = (manifest.deps?.css || [])
        .map(url => `<link rel="stylesheet" href="${url}">`)
        .join('\n');
    const jsScripts = (manifest.deps?.js || [])
        .map(url => `<script src="${url}"><\/script>`)
        .join('\n');

    // Wrap in host page with bridge
    return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${manifest.name}</title>
${cssLinks}
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: system-ui, -apple-system, sans-serif;
    background: #0f0f1a;
    color: #e0e0e0;
    overflow: hidden;
  }
  .mui-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background: #1a1a2e;
    border-bottom: 1px solid #333;
    cursor: move;
    user-select: none;
  }
  .mui-header h1 {
    font-size: 13px;
    font-weight: 600;
    color: #aaa;
  }
  .mui-header .controls {
    display: flex;
    gap: 6px;
  }
  .mui-header .controls button {
    width: 12px; height: 12px;
    border-radius: 50%;
    border: none;
    cursor: pointer;
  }
  .mui-close { background: #ff5f57; }
  .mui-minimize { background: #ffbd2e; }
  .mui-expand { background: #28c840; }
  .mui-body { padding: 12px; height: calc(100vh - 40px); overflow: auto; }
  .mui-toast {
    position: fixed;
    bottom: 12px;
    right: 12px;
    background: #2a2a4a;
    padding: 10px 16px;
    border-radius: 8px;
    font-size: 13px;
    opacity: 0;
    transition: opacity 0.3s;
    z-index: 1000;
  }
  .mui-toast.show { opacity: 1; }
</style>
</head>
<body>

<div class="mui-header" id="mui-drag-handle">
  <h1>${manifest.name}</h1>
  <div class="controls">
    <button class="mui-minimize" onclick="MUI.minimize()" title="Réduire"></button>
    <button class="mui-expand" onclick="MUI.expand()" title="Agrandir"></button>
    <button class="mui-close" onclick="MUI.dismiss()" title="Fermer"></button>
  </div>
</div>

<div class="mui-body" id="mui-content">
  ${panelHTML}
</div>

<div class="mui-toast" id="mui-toast"></div>

${jsScripts}
<script>
// ─── Micro-UI Bridge ───────────────────────────────────
const MUI = {
    instanceId: '${instanceId}',
    panelId: '${manifest.id}',
    params: ${JSON.stringify(params)},
    ws: null,
    listeners: {},

    // Connect to service via WebSocket bridge
    connect() {
        const wsUrl = 'ws://localhost:${WS_PORT}/bridge/${instanceId}';
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('[MUI] Bridge connected');
            this.emit('connected');
        };

        this.ws.onmessage = (evt) => {
            const msg = JSON.parse(evt.data);
            this.emit(msg.type, msg.data);
        };

        this.ws.onclose = () => {
            console.log('[MUI] Bridge disconnected');
            // Auto-reconnect after 2s
            setTimeout(() => this.connect(), 2000);
        };
    },

    // Send data to service
    send(type, data = {}) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type, data }));
        }
    },

    // Fetch from service API
    async fetch(endpoint) {
        const servicePort = ${manifest.bridge?.service === 'archiscan-fleet' ? 8091 : 4040};
        const res = await fetch('http://localhost:' + servicePort + endpoint);
        return res.json();
    },

    // Post to service API
    async post(endpoint, body) {
        const servicePort = ${manifest.bridge?.service === 'archiscan-fleet' ? 8091 : 4040};
        const res = await fetch('http://localhost:' + servicePort + endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        return res.json();
    },

    // Event system
    on(event, fn) {
        if (!this.listeners[event]) this.listeners[event] = [];
        this.listeners[event].push(fn);
    },
    emit(event, data) {
        (this.listeners[event] || []).forEach(fn => fn(data));
    },

    // Lifecycle
    dismiss() {
        fetch('/panels/${instanceId}/dismiss', { method: 'POST' });
        window.parent?.postMessage({ type: 'mui-dismiss', instanceId: '${instanceId}' }, '*');
    },
    minimize() {
        window.parent?.postMessage({ type: 'mui-minimize', instanceId: '${instanceId}' }, '*');
    },
    expand() {
        window.parent?.postMessage({ type: 'mui-expand', instanceId: '${instanceId}' }, '*');
    },

    // Toast notification inside the panel
    toast(message, duration = 3000) {
        const el = document.getElementById('mui-toast');
        el.textContent = message;
        el.classList.add('show');
        setTimeout(() => el.classList.remove('show'), duration);
    },

    // Auto-refresh helper
    poll(endpoint, callback, intervalMs) {
        const run = async () => {
            try {
                const data = await this.fetch(endpoint);
                callback(data);
            } catch (e) { console.warn('[MUI] Poll error:', e); }
        };
        run();
        return setInterval(run, intervalMs || ${manifest.bridge?.refresh_ms || 5000});
    },
};

// Auto-connect bridge
MUI.connect();
</script>
</body>
</html>`;
}

// ─── Trigger Engine ────────────────────────────────────
// Evaluates whether a panel should auto-spawn based on events

class TriggerEngine {
    constructor(registry) {
        this.registry = registry;
        this.suppressed = new Set();  // Panels the user dismissed (don't re-spawn)
    }

    evaluate(event) {
        for (const [panelId, manifest] of this.registry.panels) {
            // Don't re-spawn dismissed panels
            if (this.suppressed.has(panelId)) continue;
            // Don't spawn duplicates
            if ([...this.registry.active.values()].some(i => i.panelId === panelId)) continue;

            for (const trigger of (manifest.triggers || [])) {
                if (this.matchTrigger(trigger, event)) {
                    console.log(`[TRIGGER] Auto-spawning ${panelId} on event: ${event.type}`);
                    this.registry.spawn(panelId, event.data || {});
                    break;
                }
            }
        }
    }

    matchTrigger(trigger, event) {
        if (trigger.event !== event.type) return false;

        // Keyword matching for user.ask
        if (trigger.keywords && event.text) {
            const lower = event.text.toLowerCase();
            return trigger.keywords.some(k => lower.includes(k));
        }

        // Rule matching
        if (trigger.rules && event.ruleId) {
            return trigger.rules.includes(event.ruleId);
        }

        // Min entities
        if (trigger.min_entities && event.entityCount !== undefined) {
            return event.entityCount >= trigger.min_entities;
        }

        return true;
    }

    suppress(panelId) {
        this.suppressed.add(panelId);
    }

    unsuppress(panelId) {
        this.suppressed.delete(panelId);
    }
}

const triggers = new TriggerEngine(registry);

// ─── HTTP Server ───────────────────────────────────────
const server = createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

    // ── GET /panels — list all available panels ──
    if (url.pathname === '/panels' && req.method === 'GET') {
        const list = [...registry.panels.values()].map(p => ({
            id: p.id,
            name: p.name,
            description: p.description,
            slot: p.display?.slot,
            triggers: (p.triggers || []).map(t => t.event),
            service: p.bridge?.service,
        }));
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(list, null, 2));
        return;
    }

    // ── GET /panels/active — list active panel instances ──
    if (url.pathname === '/panels/active' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(registry.getActive(), null, 2));
        return;
    }

    // ── POST /panels/:id/spawn — spawn a panel ──
    const spawnMatch = url.pathname.match(/^\/panels\/([^/]+)\/spawn$/);
    if (spawnMatch && req.method === 'POST') {
        let body = '';
        req.on('data', c => body += c);
        req.on('end', () => {
            const params = body ? JSON.parse(body) : {};
            const instance = registry.spawn(spawnMatch[1], params);
            if (!instance) {
                res.writeHead(404, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Panel not found' }));
                return;
            }
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                instanceId: instance.instanceId,
                url: `http://localhost:${PORT}/panels/${instance.instanceId}/render`,
                slot: instance.manifest.display?.slot,
                size: instance.manifest.display?.size,
            }));
        });
        return;
    }

    // ── POST /panels/:instanceId/dismiss — dismiss a panel ──
    const dismissMatch = url.pathname.match(/^\/panels\/([^/]+)\/dismiss$/);
    if (dismissMatch && req.method === 'POST') {
        const ok = registry.dismiss(dismissMatch[1]);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ dismissed: ok }));
        return;
    }

    // ── POST /panels/dismiss-all ──
    if (url.pathname === '/panels/dismiss-all' && req.method === 'POST') {
        registry.dismissAll();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true }));
        return;
    }

    // ── GET /panels/:instanceId/render — HTML du panel ──
    const renderMatch = url.pathname.match(/^\/panels\/([^/]+)\/render$/);
    if (renderMatch && req.method === 'GET') {
        const instance = registry.active.get(renderMatch[1]);
        if (!instance) {
            res.writeHead(404);
            res.end('Panel instance not found');
            return;
        }
        const html = renderPanel(instance.manifest, instance.instanceId, instance.params);
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(html);
        return;
    }

    // ── POST /trigger — send an event to the trigger engine ──
    if (url.pathname === '/trigger' && req.method === 'POST') {
        let body = '';
        req.on('data', c => body += c);
        req.on('end', () => {
            const event = JSON.parse(body);
            triggers.evaluate(event);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ ok: true, active: registry.getActive() }));
        });
        return;
    }

    // ── GET /shell — the host page that contains panel slots ──
    if (url.pathname === '/shell') {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(SHELL_HTML);
        return;
    }

    res.writeHead(404);
    res.end('Not found');
});

server.listen(PORT, () => {
    console.log(`[MUI] Micro-UI Launcher on :${PORT}`);
    console.log(`[MUI] Shell: http://localhost:${PORT}/shell`);
});

// ─── WebSocket Bridge ──────────────────────────────────
const wss = new WebSocketServer({ port: WS_PORT });

wss.on('connection', (ws, req) => {
    const instanceId = req.url.replace('/bridge/', '');
    const instance = registry.active.get(instanceId);

    if (!instance) {
        ws.close(4004, 'Instance not found');
        return;
    }

    instance.ws = ws;
    console.log(`[BRIDGE] ${instanceId} connected`);

    ws.on('message', (data) => {
        const msg = JSON.parse(data.toString());
        // Forward to service or handle internally
        console.log(`[BRIDGE] ${instanceId} →`, msg);
    });

    ws.on('close', () => {
        console.log(`[BRIDGE] ${instanceId} disconnected`);
        if (instance.ws === ws) instance.ws = null;
    });
});

console.log(`[BRIDGE] WebSocket bridge on :${WS_PORT}`);

// ─── Shell HTML ────────────────────────────────────────
const SHELL_HTML = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>OpenClaw — Micro-UI Shell</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: system-ui, -apple-system, sans-serif;
    background: #08080f;
    color: #d0d0d0;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* ── Top bar ── */
  .topbar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 16px;
    background: #111122;
    border-bottom: 1px solid #252540;
  }
  .topbar .logo { font-size: 15px; font-weight: 700; color: #7c5cfc; }
  .topbar .sep { width: 1px; height: 18px; background: #333; }
  .topbar .active-count {
    font-size: 12px;
    background: #2a2a4a;
    padding: 2px 10px;
    border-radius: 10px;
  }
  .topbar button {
    margin-left: auto;
    background: #333;
    color: #ccc;
    border: none;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
  }

  /* ── Panel Slots ── */
  .workspace { flex: 1; position: relative; overflow: hidden; }

  /* Overlay panels (floating) */
  .panel-frame {
    position: absolute;
    border: 1px solid #333;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    background: #0f0f1a;
    transition: opacity 0.2s, transform 0.2s;
    animation: panelIn 0.25s ease-out;
  }
  @keyframes panelIn {
    from { opacity: 0; transform: scale(0.95) translateY(10px); }
    to   { opacity: 1; transform: scale(1) translateY(0); }
  }
  .panel-frame iframe {
    width: 100%;
    height: 100%;
    border: none;
  }

  /* Toast slot (bottom-right, small) */
  .toast-slot {
    position: fixed;
    bottom: 16px;
    right: 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    z-index: 100;
  }

  /* Sidebar slot */
  .sidebar-slot {
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    width: 360px;
    border-left: 1px solid #333;
    display: none;
  }
  .sidebar-slot.visible { display: block; }

  /* Panel catalog (bottom drawer) */
  .catalog {
    position: fixed;
    bottom: 0; left: 0; right: 0;
    background: #151528;
    border-top: 1px solid #333;
    padding: 16px;
    transform: translateY(100%);
    transition: transform 0.3s;
    z-index: 200;
  }
  .catalog.open { transform: translateY(0); }
  .catalog h2 { font-size: 14px; color: #888; margin-bottom: 12px; }
  .catalog-grid {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
  .catalog-card {
    background: #1e1e36;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 12px 16px;
    min-width: 180px;
    cursor: pointer;
    transition: border-color 0.2s;
  }
  .catalog-card:hover { border-color: #7c5cfc; }
  .catalog-card h3 { font-size: 14px; margin-bottom: 4px; }
  .catalog-card p { font-size: 11px; color: #888; }
  .catalog-card .tag {
    display: inline-block;
    font-size: 10px;
    background: #2a2a4a;
    padding: 1px 8px;
    border-radius: 8px;
    margin-top: 6px;
  }
</style>
</head>
<body>

<div class="topbar">
  <span class="logo">OpenClaw</span>
  <span class="sep"></span>
  <span class="active-count" id="active-count">0 panels</span>
  <button onclick="toggleCatalog()">+ Panel</button>
  <button onclick="dismissAll()">Tout fermer</button>
</div>

<div class="workspace" id="workspace">
  <div class="toast-slot" id="toast-slot"></div>
  <div class="sidebar-slot" id="sidebar-slot"></div>
</div>

<div class="catalog" id="catalog">
  <h2>Panels disponibles</h2>
  <div class="catalog-grid" id="catalog-grid"></div>
</div>

<script>
const API = 'http://localhost:${PORT}';
let catalogOpen = false;
let panelOffset = 20; // stagger panels

// ── Load catalog ──
async function loadCatalog() {
    const panels = await (await fetch(API + '/panels')).json();
    const grid = document.getElementById('catalog-grid');
    grid.innerHTML = panels.map(p => \`
        <div class="catalog-card" onclick="spawnPanel('\${p.id}')">
            <h3>\${p.name}</h3>
            <p>\${p.description}</p>
            <span class="tag">\${p.slot || 'overlay'}</span>
            \${p.service ? '<span class="tag">' + p.service + '</span>' : ''}
        </div>
    \`).join('');
}

function toggleCatalog() {
    catalogOpen = !catalogOpen;
    document.getElementById('catalog').classList.toggle('open', catalogOpen);
}

// ── Spawn panel ──
async function spawnPanel(panelId, params = {}) {
    catalogOpen = false;
    document.getElementById('catalog').classList.remove('open');

    const res = await (await fetch(API + '/panels/' + panelId + '/spawn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
    })).json();

    if (!res.instanceId) return;

    const slot = res.slot || 'overlay';
    const size = res.size || { width: 500, height: 380 };

    if (slot === 'overlay' || slot === 'pip') {
        createOverlayPanel(res.instanceId, res.url, size);
    } else if (slot === 'sidebar') {
        createSidebarPanel(res.instanceId, res.url);
    } else if (slot === 'fullscreen') {
        createFullscreenPanel(res.instanceId, res.url);
    } else if (slot === 'toast') {
        createToastPanel(res.instanceId, res.url);
    }

    refreshActive();
}

function createOverlayPanel(instanceId, url, size) {
    const ws = document.getElementById('workspace');
    const frame = document.createElement('div');
    frame.className = 'panel-frame';
    frame.id = 'panel-' + instanceId;
    frame.style.width = size.width + 'px';
    frame.style.height = size.height + 'px';
    frame.style.left = (panelOffset) + 'px';
    frame.style.top = (panelOffset) + 'px';
    panelOffset = (panelOffset + 30) % 200;

    frame.innerHTML = '<iframe src="' + url + '"></iframe>';
    ws.appendChild(frame);

    // Drag support
    makeDraggable(frame);
}

function createSidebarPanel(instanceId, url) {
    const slot = document.getElementById('sidebar-slot');
    slot.innerHTML = '<iframe src="' + url + '" style="width:100%;height:100%;border:none"></iframe>';
    slot.classList.add('visible');
}

function createFullscreenPanel(instanceId, url) {
    const ws = document.getElementById('workspace');
    const frame = document.createElement('div');
    frame.className = 'panel-frame';
    frame.id = 'panel-' + instanceId;
    frame.style.cssText = 'left:0;top:0;right:0;bottom:0;width:100%;height:100%;border-radius:0;z-index:50';
    frame.innerHTML = '<iframe src="' + url + '"></iframe>';
    ws.appendChild(frame);
}

function createToastPanel(instanceId, url) {
    const slot = document.getElementById('toast-slot');
    const frame = document.createElement('div');
    frame.className = 'panel-frame';
    frame.id = 'panel-' + instanceId;
    frame.style.cssText = 'position:relative;width:320px;height:180px';
    frame.innerHTML = '<iframe src="' + url + '"></iframe>';
    slot.appendChild(frame);
}

function makeDraggable(el) {
    let isDragging = false, startX, startY, origX, origY;

    el.addEventListener('mousedown', (e) => {
        if (e.target.tagName === 'IFRAME') return;
        isDragging = true;
        startX = e.clientX; startY = e.clientY;
        origX = el.offsetLeft; origY = el.offsetTop;
        el.style.zIndex = 10;
    });
    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        el.style.left = (origX + e.clientX - startX) + 'px';
        el.style.top = (origY + e.clientY - startY) + 'px';
    });
    document.addEventListener('mouseup', () => { isDragging = false; });
}

// ── Listen for panel messages ──
window.addEventListener('message', (e) => {
    if (e.data.type === 'mui-dismiss') {
        const el = document.getElementById('panel-' + e.data.instanceId);
        if (el) el.remove();
        refreshActive();
    }
    if (e.data.type === 'mui-minimize') {
        const el = document.getElementById('panel-' + e.data.instanceId);
        if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
    }
    if (e.data.type === 'mui-expand') {
        const el = document.getElementById('panel-' + e.data.instanceId);
        if (el) {
            if (el.style.width === '100%') {
                el.style.cssText = 'width:500px;height:380px;left:20px;top:20px';
            } else {
                el.style.cssText = 'left:0;top:0;width:100%;height:100%;border-radius:0;z-index:50';
            }
        }
    }
});

async function dismissAll() {
    await fetch(API + '/panels/dismiss-all', { method: 'POST' });
    document.querySelectorAll('.panel-frame').forEach(el => el.remove());
    refreshActive();
}

async function refreshActive() {
    const active = await (await fetch(API + '/panels/active')).json();
    document.getElementById('active-count').textContent = active.length + ' panel' + (active.length !== 1 ? 's' : '');
}

// Init
loadCatalog();
setInterval(refreshActive, 5000);
</script>
</body>
</html>`;
```

## Exemple : Panel Fleet-Map

```html
<!-- panels/fleet-map.html — La partie contenu du micro-panel carte -->
<div id="map" style="width:100%;height:100%;border-radius:4px"></div>

<script>
const map = L.map('map').setView([48.8605, 2.3425], 18);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 22
}).addTo(map);

const markers = {};
const zoneLayers = {};

const icons = {
    robot: L.divIcon({ html: '🤖', className: '', iconSize: [24, 24] }),
    drone: L.divIcon({ html: '🛸', className: '', iconSize: [24, 24] }),
    station: L.divIcon({ html: '📡', className: '', iconSize: [24, 24] }),
};

MUI.poll('/fleet/map', (geojson) => {
    for (const feature of geojson.features) {
        const p = feature.properties;

        if (feature.geometry.type === 'Point' && (p.featureType === 'entity' || p.icon)) {
            const [lon, lat] = feature.geometry.coordinates;
            if (markers[p.id]) {
                markers[p.id].setLatLng([lat, lon]);
            } else {
                markers[p.id] = L.marker([lat, lon], { icon: icons[p.type] || icons.station })
                    .bindPopup(`<b>${p.name}</b><br>${p.type} — 🔋${p.battery}%`)
                    .addTo(map);
            }
        }

        if (p.type === 'zone' && !zoneLayers[p.id]) {
            const style = p.style || {};
            zoneLayers[p.id] = L.geoJSON(feature, {
                style: {
                    fillColor: style.fill || '#00ff0020',
                    color: style.stroke || '#00aa00',
                    weight: 2,
                    fillOpacity: 0.3,
                }
            }).bindPopup(`<b>${p.name}</b>`).addTo(map);
        }
    }
}, 3000);
</script>
```

## Exemple : Panel Config (formulaire)

```yaml
# panels/gateway-config.panel.yml
id: gateway-config
name: "Config Gateway"
description: "Formulaire de configuration rapide d'un gateway ArchiScan"
version: 1

triggers:
  - event: user.ask
    keywords: [config, configurer, paramètre, réglage, gateway]
  - event: service.gateway.new_device

bridge:
  service: archiscan-gateway
  endpoints:
    - GET /status
    - POST /config

display:
  slot: sidebar
  size: { width: 360, height: 500 }
  auto_dismiss: false
```

```html
<!-- panels/gateway-config.html -->
<style>
  .form-group { margin-bottom: 14px; }
  label { display: block; font-size: 12px; color: #888; margin-bottom: 4px; }
  input, select {
    width: 100%;
    padding: 8px 10px;
    background: #1a1a2e;
    border: 1px solid #333;
    border-radius: 4px;
    color: #eee;
    font-size: 13px;
  }
  input:focus, select:focus { border-color: #7c5cfc; outline: none; }
  .btn {
    width: 100%;
    padding: 10px;
    background: #7c5cfc;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
    margin-top: 8px;
  }
  .btn:hover { background: #6b4de6; }
  .btn.secondary { background: #333; }
  .status-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    background: #1a1a2e;
    border-radius: 6px;
    margin-bottom: 16px;
    font-size: 13px;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; }
  .dot.ok { background: #4ade80; }
  .dot.err { background: #f87171; }
</style>

<div class="status-bar">
  <div class="dot" id="status-dot"></div>
  <span id="status-text">Connexion...</span>
</div>

<div class="form-group">
  <label>Device ID</label>
  <input id="device-id" placeholder="gw-01" />
</div>

<div class="form-group">
  <label>APN</label>
  <input id="apn" value="iot.orange.fr" />
</div>

<div class="form-group">
  <label>MQTT Broker</label>
  <input id="mqtt-broker" placeholder="mqtt://your-server.com:1883" />
</div>

<div class="form-group">
  <label>GPS Interval (s)</label>
  <input id="gps-interval" type="number" value="10" min="1" max="3600" />
</div>

<div class="form-group">
  <label>Telemetry Interval (s)</label>
  <input id="telem-interval" type="number" value="30" min="5" max="3600" />
</div>

<div class="form-group">
  <label>Mode</label>
  <select id="mode">
    <option value="active">Active (GPS + Télémétrie)</option>
    <option value="passive">Passive (Télémétrie seule)</option>
    <option value="sleep">Sleep (réveil périodique)</option>
  </select>
</div>

<button class="btn" onclick="saveConfig()">Appliquer la config</button>
<button class="btn secondary" onclick="MUI.dismiss()">Fermer</button>

<script>
// Auto-load current config
MUI.on('connected', async () => {
    try {
        const status = await MUI.fetch('/status');
        document.getElementById('status-dot').className = 'dot ok';
        document.getElementById('status-text').textContent = 'Connecté — ' + (status.device_id || 'N/A');
        if (status.device_id) document.getElementById('device-id').value = status.device_id;
    } catch {
        document.getElementById('status-dot').className = 'dot err';
        document.getElementById('status-text').textContent = 'Hors ligne';
    }
});

async function saveConfig() {
    const config = {
        device_id: document.getElementById('device-id').value,
        apn: document.getElementById('apn').value,
        mqtt_broker: document.getElementById('mqtt-broker').value,
        gps_interval_s: parseInt(document.getElementById('gps-interval').value),
        telemetry_interval_s: parseInt(document.getElementById('telem-interval').value),
        mode: document.getElementById('mode').value,
    };
    try {
        await MUI.post('/config', config);
        MUI.toast('Config appliquée !');
    } catch (e) {
        MUI.toast('Erreur: ' + e.message);
    }
}
</script>
```

## Exemple : Panel Alert Toast

```yaml
# panels/alert-toast.panel.yml
id: alert-toast
name: "Alerte"
description: "Notification toast pour les alertes fleet/gateway"
version: 1

triggers:
  - event: rule.triggered
    rules: [geofence-breach, forbidden-zone, battery-critical, lost-contact]

bridge:
  service: archiscan-fleet
  endpoints:
    - GET /fleet

display:
  slot: toast
  size: { width: 320, height: 120 }
  auto_dismiss: true
  dismiss_after_s: 15
  position: bottom-right
```

```html
<!-- panels/alert-toast.html -->
<style>
  .alert-body {
    display: flex;
    align-items: center;
    gap: 10px;
    height: 100%;
  }
  .alert-icon { font-size: 28px; }
  .alert-text h3 { font-size: 14px; margin-bottom: 2px; }
  .alert-text p { font-size: 11px; color: #aaa; }
  .dismiss-btn {
    position: absolute;
    top: 6px; right: 8px;
    background: none;
    border: none;
    color: #666;
    cursor: pointer;
    font-size: 14px;
  }
</style>

<button class="dismiss-btn" onclick="MUI.dismiss()">×</button>
<div class="alert-body">
  <div class="alert-icon" id="icon">⚠</div>
  <div class="alert-text">
    <h3 id="title">Alerte</h3>
    <p id="detail">...</p>
  </div>
</div>

<script>
const params = MUI.params;
document.getElementById('title').textContent = params.title || 'Alerte fleet';
document.getElementById('detail').textContent = params.message || '';

const iconMap = {
    'geofence-breach': '📍',
    'forbidden-zone': '⛔',
    'battery-critical': '🔴',
    'lost-contact': '📡',
};
document.getElementById('icon').textContent = iconMap[params.rule] || '⚠';

// Auto-dismiss
if (MUI.params.auto_dismiss !== false) {
    setTimeout(() => MUI.dismiss(), 15000);
}
</script>
```

## Comment l'IA lance un panel

Depuis n'importe quel service OpenClaw, l'IA peut lancer un panel via l'API ou via un événement :

```bash
# Lancer un panel explicitement
curl -X POST http://localhost:4040/panels/fleet-map/spawn

# Lancer un panel avec des paramètres
curl -X POST http://localhost:4040/panels/alert-toast/spawn \
  -H 'Content-Type: application/json' \
  -d '{"title":"Geofence breach","message":"GW-01 hors zone chantier-A","rule":"geofence-breach"}'

# Envoyer un événement (le trigger engine décide quel panel s'ouvre)
curl -X POST http://localhost:4040/trigger \
  -d '{"type":"user.ask","text":"montre-moi la carte de la flotte"}'

# Envoyer un événement de règle (auto-spawn le toast d'alerte)
curl -X POST http://localhost:4040/trigger \
  -d '{"type":"rule.triggered","ruleId":"geofence-breach","data":{"title":"Breach","message":"GW-01 out"}}'

# Voir les panels actifs
curl -s http://localhost:4040/panels/active | jq

# Fermer tous les panels
curl -X POST http://localhost:4040/panels/dismiss-all

# Ouvrir le shell complet
open http://localhost:4040/shell
```

## Créer un nouveau micro-panel

1. Créer `panels/mon-panel.panel.yml` (manifest)
2. Créer `panels/mon-panel.html` (contenu)
3. Redémarrer le launcher (ou hot-reload à venir)

Le panel a accès à l'objet `MUI` avec :
- `MUI.fetch(endpoint)` — requête GET au service
- `MUI.post(endpoint, body)` — requête POST
- `MUI.poll(endpoint, callback, intervalMs)` — polling auto
- `MUI.send(type, data)` — envoyer via WebSocket
- `MUI.on(event, fn)` — écouter les messages du service
- `MUI.toast(message)` — notification interne
- `MUI.dismiss()` — se fermer
- `MUI.params` — paramètres passés au spawn

~50 lignes de HTML suffisent pour un panel fonctionnel.
