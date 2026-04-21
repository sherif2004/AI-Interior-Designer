# 🏠 AI Interior Designer

### Stateful Embodied LLM for Real-Time Home Design, AR Visualization & Autonomous Layout Intelligence

![Phase](https://img.shields.io/badge/Phase-1--4_Complete_|_5--6_Planned-7c3aed?style=flat-square)
![Stack](https://img.shields.io/badge/Stack-FastAPI_%7C_LangGraph_%7C_Three.js_%7C_WebXR-0ea5e9?style=flat-square)
![LLM](https://img.shields.io/badge/LLM-OpenRouter-f5c842?style=flat-square)
![AR](https://img.shields.io/badge/AR-WebXR_%7C_ARKit_%7C_ARCore-22d3a5?style=flat-square)
![2D](https://img.shields.io/badge/2D-Planner_5D_Parity-f59e0b?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-10b981?style=flat-square)

---

## 🧠 Overview

AI Interior Designer is a **stateful, interactive embodied AI system** that lets you design full room layouts using natural language — and visualize them with **budget estimates**, **clearance validation**, **AI-generated photoreal renders**, **floor plan import**, **real product suggestions**, and **live AR camera interaction**.

Instead of generating a full layout at once, the system:

- Maintains a **persistent room and project state**
- Interprets **incremental user commands** ("Move the sofa left", "Add a window")
- Executes **structured, deterministic actions** validated by a spatial engine
- Updates a live **3D visualization** with real-time WebSocket streaming
- Supports full **save/load/version** project workflows
- Places furniture **live on your real camera feed** via WebXR, ARKit, or ARCore
- Provides a **professional 2D drag-and-drop floor plan editor** on par with Planner 5D
- Offers **life-size 1:1 product AR** with a product-first shopping flow like IKEA Place
- Acts as an **embodied AI agent** operating inside a physical spatial environment

This transforms the LLM from a passive generator into an **active goal-driven designer** — a practical tool for real home planning that surpasses both IKEA Place and Planner 5D.

---

## ✅ Phases 1–4: What's Already Built (v4.0)

### 🏗️ Phase 1 — Strong MVP ✅

| Feature | Description |
|---------|-------------|
| 🔁 Interactive session | Natural language CRUD on furniture in real time |
| 🧠 Stateful environment | Persistent room state, object IDs, full history |
| 🎨 Room styling | 7 theme presets, 5 wall materials, 5 floor types |
| 📐 Structural editing | Doors & windows on any wall with position control |
| 🪑 Furniture catalog | 17 furniture types across 5 room categories |
| 📂 Project persistence | Save/load designs as local JSON |
| 🖥️ 3D visualization | Three.js PBR rendering with orbit controls |
| 🗺️ 2D top-down view | Canvas-based floor plan toggle |

### 🏠 Phase 2 — Practical Home Planner ✅

| Feature | Description |
|---------|-------------|
| 💰 Budget estimation | Itemized cost ranges by furniture, grouped by category |
| ⚠️ Clearance checks | Validates 60cm walkways between all objects, red/yellow halos in 3D |
| 📊 Accessibility score | 0–100% walkability score updated after every action |
| 📏 Measurement tool | Click any 2 objects to draw a 3D measurement line with meter label |
| 🌅 Day/Night cycle | Sun arc slider (0–24h) controlling position, warmth, and intensity |
| 🔀 Version comparison | Save named snapshots, compare any two with a split-screen 2D diff canvas |
| 📦 Realistic dimensions | Industry-standard sizes with `price_low/high`, `weight_kg`, `min_clearance` |

### ✨ Phase 3 — See It Like Real Life ✅

| Feature | Description |
|---------|-------------|
| 🎨 AI photoreal render | Builds scene prompt → Stability AI / Replicate SDXL / mock Unsplash |
| 📐 Blueprint import | Upload PNG/JPG floor plan → LLM vision extracts dimensions, doors, windows |
| 🛍️ Product catalog | IKEA-style product cards (photo, price, dimensions, buy link) |
| 📱 AR preview (stub) | WebXR immersive-AR session — walk your room at 1:1 scale on mobile |

---

## 📷 Phase 4A — Live Camera & AR Placement ✅

> The camera becomes the canvas. Place real furniture in your real room — live — and have it appear in the 3D simulation simultaneously.

### Two Modes, One State

Both modes write to the same `RoomState`. Everything placed via camera is immediately visible in the 3D scene, scored by the constraint engine, and persisted to the backend.

```
Camera Input (WebXR | getUserMedia)
     ↓
Floor/Surface Detection
     ↓
Ghost Preview (semi-transparent mesh at cursor/reticle)
     ↓
Confirmed Placement
     ↓
AR Sync Coordinator (ar_sync.js)
     ↓
    ┌────────────────┬────────────────┐
    ↓                ↓                ↓
Three.js scene    RoomState       WebSocket
(live mesh)       (ADD action)    (backend sync)
```

### 📷 Mode 1 — Desktop Camera Background

| Feature | Description |
|---------|-------------|
| 📹 Live camera feed | `getUserMedia` → `THREE.VideoTexture` → scene background |
| 🖱️ Click-to-place | Raycast from 2D click → invisible floor plane → 3D world coords |
| 👻 Ghost preview | Semi-transparent furniture mesh follows cursor before placement |
| 🟢 Collision coloring | Ghost turns green (valid) or red (collision detected) |
| 🎛️ Camera toggle | One-click switch between normal 3D view and camera background mode |
| 📸 Frame scan | Capture still from live feed → LLM vision extracts room dimensions |

### 📱 Mode 2 — WebXR AR (Mobile)

| Feature | Description |
|---------|-------------|
| 🎯 Hit-test surface detection | WebXR hit-test API detects real floor and wall planes |
| 💍 Reticle indicator | Ring mesh positioned on detected surface, shows where furniture will land |
| 👆 Tap to place | Tap screen to confirm placement at reticle position |
| 🔄 Multi-object session | Reticle stays active after each placement for the next piece |
| 🏠 Room exit sync | All AR-placed furniture commits to RoomState when session ends |
| ⬇️ Graceful fallback | WebXR unsupported → camera background mode → normal 3D mode |

### New Files (Phase 4A)

```
frontend/js/
├── camera_background.js     ← getUserMedia → VideoTexture, captureFrame()
├── floor_raycaster.js       ← 2D click → 3D floor coord via invisible plane
├── ar_placement_overlay.js  ← ghost mesh + furniture picker sidebar
└── ar_sync.js               ← ARSyncCoordinator: world coords → RoomState actions
```

### New API Endpoints (Phase 4A)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/scan/frame` | Base64 camera frame → detected dims + furniture |

### Coordinate System

- Three.js scene: **1 unit = 1 meter**. Room origin at `(0, 0, 0)` center of floor.
- RoomState uses the same meter-based coordinates — no conversion needed.
- Walls at `±roomWidth/2` and `±roomDepth/2`.

---

## 🤖 Phase 4B — Intelligent AR & Autonomous Design ✅

> The system evolves from placing furniture to understanding your goals and optimizing your space autonomously.

### 🎯 Goal-Based Planning

Support for high-level user intents:
```
"Make this room cozy"
"Optimize this layout for a family of 4"
"I need a home office that fits in this corner"
```

1. LLM generates a **multi-step action plan**
2. Action Executor runs steps sequentially
3. Constraint + Scoring Engine evaluates each step
4. Evaluator loops back with refinements until score threshold is met

### 📊 Layout Intelligence & Scoring (5 dimensions)

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Walkability | 25% | Clear 60cm+ pathways throughout |
| Functional Zoning | 25% | Zones identified and respected |
| Visual Balance | 20% | Symmetry, focal points, alignment |
| Object Relationships | 20% | Sofa ↔ TV, bed ↔ walls, desk ↔ window |
| Natural Light | 10% | Furniture not blocking windows |

Outputs: **overall score (0–100)** + per-dimension breakdown with actionable improvement notes.

### 🔁 Self-Correcting Layout Engine

Auto-detects and fixes:
- Clearance violations and furniture collisions
- Poor ergonomic relationships (desk against wall, bed under window)
- Blocked circulation paths and emergency exit routes

### 🧩 Functional Zoning

Auto-identifies and enforces: Living / relaxation, Work / focus, Sleep / rest, Circulation paths.

### 🔮 What-If Simulation

Preview layout changes before committing — shows clearance impact, score delta, and potential conflicts.

### 🧠 Preference-Aware Adaptation

Learns from user behavior across sessions — preferred styles, budget tendencies, layout patterns — to personalize future suggestions.

### New Files (Phase 4B)

```
backend/
├── engine/
│   ├── layout_scorer.py         ← 5-dimension scoring system
│   └── zoning.py                ← functional zone detection + enforcement
├── planner/
│   ├── goal_planner.py          ← multi-step goal reasoning
│   ├── evaluator.py             ← feedback loop + refinement
│   ├── what_if_engine.py        ← simulate without committing to state
│   └── preference_store.py      ← per-user behavior learning

frontend/js/
└── scoring_panel.js             ← live score breakdown UI
```

### New API Endpoints (Phase 4B)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/goal` | Set a high-level design goal |
| `GET` | `/score` | Get 5-dimension layout score |
| `POST` | `/simulate` | What-if simulation without state commit |
| `POST` | `/autofix` | Trigger self-correcting layout engine |
| `GET` | `/zones` | Get detected functional zones |
| `POST` | `/preference` | Record user preference signal |
| `GET` | `/preference/profile` | Get learned preference profile |

---

## 🗺️ Phase 4C — Professional 2D Floor Plan Editor ✅

> Inspired by **Planner 5D** — drag-and-drop 2D floor plan drafting for both amateurs and professionals, with a massive materials library, room templates, and full bidirectional sync to the 3D scene and AI engine.

### The Core Concept

Planner 5D's defining strength is making professional-grade 2D drafting accessible to anyone. Phase 4C replicates this and adds AI intelligence: the 2D canvas is **always in sync** with the 3D scene, and every change is scored by the layout engine in real time.

```
2D Canvas Edit  ←──────────────────→  3D Scene + RoomState
      ↓                                       ↓
  Drag wall                               3D mesh updates
  Drop furniture   ←── instant sync ──→  AI re-scores layout
  Resize room                             Clearance re-checked
```

### 🖊️ 2D Canvas & Wall Drawing

| Feature | Description |
|---------|-------------|
| 🖱️ Drag-and-drop editor | Click-to-draw walls, drag endpoints to resize |
| 📐 Snap-to-grid | Configurable grid: 5cm / 10cm / 25cm increments |
| 📏 Auto-dimension labels | Live measurement annotations on every wall segment |
| 🔵 Smart snap | Snap furniture to walls, corners, grid intersections, and other pieces |
| ↩️ Undo / redo stack | Full history — Ctrl+Z / Ctrl+Y across all 2D operations |
| 🧱 Wall thickness control | Set wall thickness per wall: 10 / 15 / 20 / 30cm |
| 🔄 2D ↔ 3D sync | Every 2D change immediately reflects in the 3D scene and vice versa |
| 📐 Scale indicator | Switchable: 1:50, 1:100, 1:200 scale overlay |
| 🔖 Room labels | Annotate zones ("Living Room", "Walk-in Closet") on canvas |
| 📏 Alignment guides | Drag horizontal/vertical guide lines to position |

### 🪑 Drag-and-Drop Furniture Placement (2D)

| Feature | Description |
|---------|-------------|
| 📦 Catalog sidebar | Browse all categories, drag furniture directly onto the 2D canvas |
| 🔄 Rotation handle | Drag a rotation arc on any piece to rotate freely |
| 📐 Resize handle | Drag corners to scale furniture within realistic bounds |
| 🏷️ Hover labels | Name + dimensions shown on hover |
| 🟦 Clearance halo | 60cm walkway zone visualized around each piece in 2D |
| 🔁 Mirror mode | Flip furniture horizontally or vertically |
| 📌 Lock position | Pin a piece so it cannot be accidentally moved |

### 🎨 Materials & Textures Library

The key Planner 5D differentiator — a vastly expanded visual library:

| Category | Examples |
|----------|---------|
| 🪵 Wood floors | Oak, walnut, pine, herringbone parquet, dark mahogany, whitewashed |
| 🪨 Stone & tile | Marble, travertine, slate, hexagonal mosaic, subway tile, terrazzo |
| 🎨 Wall finishes | Matte paint (200+ colors), exposed brick, concrete, shiplap, wainscoting |
| 🧱 Structural materials | Plaster, drywall, glass partition, frosted glass, mirrored wall |
| 🛋️ Fabric textures | Linen, velvet, boucle, leather, microfiber — applied to furniture |
| 🌿 Decorative | Wallpaper patterns, wood paneling, stone cladding, decorative tiles |

Each material includes: `texture_url`, `scale`, `roughness`, `metalness` for PBR rendering in Three.js.

### 🏠 Room Templates Library

Ready-made starting layouts for common room types:

| Template | Description |
|----------|-------------|
| Studio apartment | 25–35m² open-plan with zoning suggestions |
| 1-bedroom apartment | Bedroom + living room + hallway |
| Living room — small | Up to 20m², TV wall + sofa zone |
| Living room — large | 30m²+, entertainment zone + reading nook |
| Master bedroom | King bed + wardrobe + dressing area |
| Home office | Desk zone + meeting area + storage |
| Open-plan kitchen-dining | Island + dining table + traffic flow |
| Kids' room | Bed + study area + play zone + storage |

Templates load as a `RoomState` starting point — the AI then refines based on user preferences.

### 📤 2D Export

| Format | Description |
|--------|-------------|
| 🖼️ PNG / JPEG | High-res 2D floor plan image (150 / 300 dpi) |
| 📄 PDF | Annotated floor plan with dimensions and legend |
| 🗂️ SVG | Scalable vector — perfect for presentations |
| 📐 DXF | CAD-compatible for architects (shared with Phase 5.5) |

### New Files (Phase 4C)

```
frontend/js/
├── floorplan_canvas.js       ← 2D canvas engine (Fabric.js or Konva.js)
├── wall_tool.js              ← click-to-draw wall segments
├── snap_engine.js            ← grid snap + smart alignment
├── dimension_overlay.js      ← auto measurement annotations
├── material_library.js       ← texture swatcher + material panel UI
├── room_templates.js         ← template loader + preview panel
└── floorplan_export.js       ← PNG / PDF / SVG / DXF export

backend/
├── floorplan/
│   ├── canvas_sync.py        ← 2D canvas state ↔ RoomState conversion
│   ├── wall_builder.py       ← wall geometry from 2D polyline → 3D mesh
│   └── floorplan_export.py   ← server-side PDF / SVG rendering

data/
├── materials/
│   ├── floors/               ← floor texture images
│   ├── walls/                ← wall finish textures
│   └── fabrics/              ← furniture material textures
└── templates/
    └── *.json                ← room template RoomState files
```

### New API Endpoints (Phase 4C)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/materials` | Full materials + textures library |
| `GET` | `/materials/{category}` | Materials by category (floors, walls, fabrics) |
| `POST` | `/floorplan/sync` | 2D canvas state → RoomState update |
| `GET` | `/floorplan/export?format=pdf` | Export 2D floor plan as PDF / PNG / SVG |
| `GET` | `/templates` | List all room templates |
| `GET` | `/templates/{id}` | Load a room template as RoomState |
| `POST` | `/floorplan/walls` | Draw walls from polyline → generate 3D room |

---

## 📱 Phase 4D — Life-Size Product AR: IKEA Place Parity ✅

> Inspired by **IKEA Place** (2017) — the ARKit app that lets users visualize furniture at true 1:1 scale in their real rooms before buying. Phase 4D replicates every IKEA Place capability and adds AI intelligence that IKEA Place never had.

### The Core Concept

IKEA Place's breakthrough was a **product-first workflow**: start from a product in the catalog, open AR, see it life-size in your room. Phase 4D adds this workflow while keeping it fully connected to the main design tool — every AR placement carries back into the 3D scene and is scored by the AI engine.

```
IKEA Place parity (Phase 4D):
Browse catalog → Tap product → Open AR → Life-size in your room → Save to design

AI Designer room-first (Phase 4A):
Design room in 3D → Switch to AR → See full room layout in your real space
```

Both flows share the same `RoomState` and sync bidirectionally.

### 🔭 True Life-Size 1:1 AR Visualization

| Feature | Description |
|---------|-------------|
| 📏 True 1:1 scale | Furniture rendered at exact real-world dimensions |
| 🏔️ Surface detection | ARKit / ARCore floor + wall plane detection |
| 🌑 Occlusion rendering | Furniture realistically goes *behind* real objects |
| 💡 Lighting estimation | ARKit / ARCore ambient light probe — furniture matches your room's actual light |
| 🌤️ Shadow casting | Furniture casts real shadows matching the detected light direction |
| 👁️ People occlusion | People walking in front of AR furniture are not covered by it (ARKit) |

### 🛍️ Product-First AR Shopping Workflow

| Feature | Description |
|---------|-------------|
| 📦 Catalog → AR in one tap | Browse IKEA catalog, tap any product → instantly opens AR session |
| 🏷️ AR product label | Floating overlay shows product name, series, price, and dimensions |
| 🔄 Swap in AR | Replace current product with an alternative without leaving AR |
| 🎨 Color variants in AR | Switch between all available color/finish options live in AR |
| 📐 Fit check | AR highlights green if furniture fits the space, red if it doesn't |
| ↔️ Distance indicator | Live distance from placed furniture to each wall |
| 🛒 Add to cart from AR | Direct purchase link triggered from within the AR session |

### 📸 AR Capture & Sharing

| Feature | Description |
|---------|-------------|
| 📷 AR screenshot | Capture the AR scene — shareable photo with furniture in your real room |
| 🎬 AR video recording | Record a 10–30s clip walking around AR-placed furniture |
| ↔️ Before/After toggle | Instantly remove all AR furniture to compare empty vs. furnished room |
| 🔗 Share AR result | Export AR photo/video to social media or messaging |
| 💾 Save to design | Save AR placement → import into the 3D room design |

### 📡 Native AR SDK Support (Beyond WebXR)

| SDK | Platform | Exclusive Features |
|-----|----------|--------------------|
| **ARKit** | iOS 11+ | People occlusion, LiDAR depth mesh (iPhone 12 Pro+), scene reconstruction |
| **ARCore** | Android 7+ | Environmental HDR lighting, Depth API, instant placement |
| **WebXR** | All browsers | Cross-platform fallback, no app install required |

Implementation path: Web version uses WebXR with graceful feature degradation. React Native app (Phase 6) uses ARKit / ARCore natively for full feature access.

### 📏 AR Room Measurement

| Feature | Description |
|---------|-------------|
| 📐 Wall-to-wall distance | Point camera at two walls → AR shows exact gap in meters |
| 🔲 Room dimension scan | Walk the perimeter → AR builds a floor plan from LiDAR / depth camera |
| 📋 Auto-import to design | Measured dimensions → auto-populate `SET_ROOM_DIMENSIONS` action |
| 🪟 Opening detection | LiDAR-assisted detection of windows and doors → placed on floor plan automatically |

### 🔗 AR ↔ 3D Design Bridge

The key feature that neither IKEA Place nor Planner 5D has:

```
AR Session                           3D Room Design
     │                                      │
Place sofa in AR  ── AR_PLACE ──→   Sofa added to RoomState
Tap "Save to design"                AI scores the new layout
                  ←── score + suggestions ──
Open full 3D view                   See full furnished room
```

### 📲 QR Code Cross-Device Handoff

| Feature | Description |
|---------|-------------|
| 📱 Desktop → mobile QR | Design on desktop, scan QR → open same room state in AR on phone |
| 🔄 Mobile → desktop sync | AR placements sync back to desktop 3D view via WebSocket |
| 🔗 Share AR session | Generate a link — another person opens it and sees the same AR room state |

### New Files (Phase 4D)

```
frontend/js/
├── ar_product_browser.js     ← product-first catalog → AR launch flow
├── ar_life_size.js           ← 1:1 scale AR session manager
├── ar_label_overlay.js       ← floating product info overlay in AR
├── ar_capture.js             ← screenshot + video recording from AR session
├── ar_before_after.js        ← toggle all AR furniture on/off
├── ar_room_measure.js        ← wall distance measurement in AR
└── ar_qr_handoff.js          ← QR code generation + cross-device sync

backend/
├── ar/
│   ├── session_manager.py    ← AR session state + QR token management
│   ├── room_measure.py       ← LiDAR/depth scan → RoomState dimensions
│   └── ar_capture_store.py   ← save AR screenshots/videos + metadata
```

### New API Endpoints (Phase 4D)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ar/session` | Create AR session, returns session token |
| `GET` | `/ar/session/{token}` | Load AR session state |
| `POST` | `/ar/session/{token}/place` | Place product in AR session → RoomState |
| `POST` | `/ar/session/{token}/capture` | Save AR screenshot / video |
| `GET` | `/ar/session/{token}/qr` | Generate QR code for cross-device handoff |
| `POST` | `/ar/session/{token}/save-to-design` | Import AR session into 3D room design |
| `POST` | `/ar/measure` | LiDAR scan result → room dimensions |
| `GET` | `/ar/product/{item_id}/preview` | AR-ready product metadata (scale, anchor, variants) |

---

## 🌟 Phase 5 — Beyond IKEA Place & Planner 5D: True Intelligence *(Planned)*

### 📸 Phase 5.1 — Real Room Scan & State Import

The single biggest differentiator over both IKEA Place and Planner 5D: **photograph your existing room and have the AI build a complete `RoomState` from it**.

| Feature | Description |
|---------|-------------|
| 🏠 Room photo → state | Upload photo → LLM vision extracts furniture, walls, dimensions, layout |
| 🪑 Furniture recognition | Identify existing pieces with type + approximate size |
| 📐 Dimension estimation | Estimate room size from perspective cues in the photo |
| 🎨 Style fingerprinting | Detect aesthetic (mid-century, minimalist, industrial) → match future suggestions |
| 📹 Live frame scan | Capture still from live camera → continuous room update (Phase 4A integration) |
| 🔄 Incremental merge | "I got a new rug" — merge new item into existing scanned state |

**New API endpoints:**
```
POST /import/photo              ← upload room photo → extract full RoomState
GET  /import/photo/preview      ← preview extracted state before applying
POST /style/detect              ← detect aesthetic from photo or current state
POST /scan/frame                ← live camera frame → partial state update
```

**New backend files:**
```
backend/vision/
├── room_scanner.py             ← LLM vision → structured RoomState
├── furniture_recognizer.py     ← object detection + type classification
├── style_extractor.py          ← aesthetic fingerprinting
└── live_scanner.py             ← base64 camera frame → partial updates
```

### 🛍️ Phase 5.2 — Multi-Retailer Commerce Intelligence

| Feature | Description |
|---------|-------------|
| 🌐 Multi-retailer search | IKEA + Wayfair + Amazon + West Elm simultaneously |
| 💬 Semantic search | "Find me something like this sofa but under $300" |
| ✅ Live availability | In-stock checker + nearest store locator |
| 🔄 Smart substitution | If piece doesn't fit spatially, auto-suggest next-best size |
| 👯 Style-consistent alternatives | "Same vibe, half the price" intelligent matching |
| 🎁 Bundle deals | "This sofa + rug + lamp combo saves $140" |
| 🌱 Sustainability score | Recycled materials, longevity rating, certifications |
| 💳 Financing calculator | Monthly payment breakdown for total cart value |
| 📊 Splurge vs. Save mode | Premium and budget versions of the same layout |

**New API endpoints:**
```
GET  /products/search?q=sofa&budget=800&style=minimalist&retailers=ikea,wayfair
GET  /products/substitute/{furniture_id}
GET  /products/bundle
GET  /products/availability
GET  /budget/financing?months=12
GET  /products/sustainability/{product_id}
```

**New backend files:**
```
backend/catalog/
├── multi_retailer.py
├── substitution_engine.py
└── sustainability_scorer.py
```

### 🎤 Phase 5.3 — Multimodal & Voice Input

| Feature | Description |
|---------|-------------|
| 🎙️ Voice commands | Web Speech API — full NL commands by voice |
| ✏️ Sketch floor plan | Draw rough floor plan on mobile → AI interprets dimensions |
| 📌 Inspiration import | Upload Pinterest/Houzz photo → AI reverse-engineers the style |
| 🖼️ Style transfer | "Make it look like this" photo → applied to current room state |

**New API endpoints:**
```
POST /voice/command
POST /import/inspiration
POST /import/sketch
```

### 🎬 Phase 5.4 — Advanced Visualization

| Feature | Description |
|---------|-------------|
| 🚶 First-person walkthrough | WASD/touch navigation at eye level through the room |
| 🎥 Cinematic render export | Camera path animation → exported MP4 walkthrough video |
| 🎨 Live material swapper | Oak → walnut, fabric → leather without re-adding furniture |
| ☀️ Shadow & glare simulation | Real shadow casting per time of day via sun position |
| 🔭 True AR occlusion | Furniture goes *behind* real objects (plane detection + occlusion) |
| 💡 AR lighting estimation | Match ambient light to your real room's actual conditions |
| 📦 Multi-object AR | Place multiple pieces in a single WebXR session simultaneously |

**New API endpoints:**
```
POST /render/video
GET  /render/shadow?time=14.5
POST /furniture/{id}/material
```

### 🤝 Phase 5.5 — Collaboration & Professional Export

| Feature | Description |
|---------|-------------|
| 🔗 Shareable link | Role-based access: view-only vs. edit |
| 👥 Real-time multiplayer | Architect + client in same session via WebSocket rooms |
| 💬 3D comment pins | Drop a sticky note on any furniture piece in the 3D scene |
| 📄 Contractor-ready PDF | Dimensions, product links, quantities, material list |
| 📐 DXF / SketchUp export | CAD-compatible for professional use |
| 🧱 Material takeoff sheet | Sq. footage of flooring, paint needed per wall, quantities |
| 🔧 Assembly difficulty score | Per-item complexity + estimated assembly time |
| 📦 One-click procurement list | Shopping list with links, SKUs, quantities |

**New API endpoints:**
```
POST /share
GET  /share/{token}
WS   /ws/collab/{room_id}
POST /export/pdf
POST /export/dxf
GET  /export/materials
POST /comments
GET  /comments
```

### 🏡 Phase 5.6 — Multi-Room & Whole-Home Planning

| Feature | Description |
|---------|-------------|
| 🏘️ Multi-room projects | Bedroom + living room + office in one project |
| 🏢 Multi-floor support | Define floors, connect rooms with stairs/hallways |
| 🔄 Room-to-room flow | Analyze traffic flow between connected rooms |
| 💰 Whole-home budget | Aggregate budget + shopping list across all rooms |
| 📐 Shared wall detection | Rooms sharing walls sync structural changes automatically |

**State schema additions:**
```python
class HomeState(TypedDict):
    floors: List[FloorState]
    rooms: Dict[str, RoomState]
    connections: List[RoomConnection]
    shared_walls: List[SharedWall]
    global_budget: BudgetSummary
    global_style: StyleProfile
```

**New API endpoints:**
```
POST /home/rooms
POST /home/connect
GET  /home/flow
GET  /home/budget
```

---

## 🔭 Phase 6 — Platform & Ecosystem *(Long-Term Vision)*

### 👤 User Accounts & Cloud Sync

| Feature | Description |
|---------|-------------|
| 🔐 Authentication | Email/OAuth login, user profiles |
| ☁️ Cloud project storage | Projects synced to cloud, accessible across devices |
| 📱 Mobile-native app | React Native / Expo for iOS + Android (unlocks full ARKit + ARCore) |
| 🔔 Push notifications | "Your saved product is now on sale" alerts |

### 🌐 Community & Social

| Feature | Description |
|---------|-------------|
| 🏛️ Design gallery | Public showcase of community room designs |
| ❤️ Like + fork designs | Save and remix other users' layouts |
| 🏆 Design challenges | Weekly prompts ("Design a 20m² studio") |
| ✨ Featured templates | Curated starter layouts by style and room type |

### 📊 Analytics & Smart Suggestions

| Feature | Description |
|---------|-------------|
| 📈 Combination analytics | Which furniture combinations are most popular |
| 🔍 Trend detection | "Japandi is trending this month" |
| 🎯 Personalized feed | Suggest layouts based on user history |
| 📣 Retailer partnerships | Revenue through affiliate product links |

### 🏗️ Professional / B2B Tier

| Feature | Description |
|---------|-------------|
| 🏢 Architect workspace | Multi-client project management dashboard |
| 📋 Client portal | Clients view and comment without editing |
| 💼 White-label SDK | Embed the designer in other platforms |
| 🔌 Headless API | Third-party integration access |
| 📑 BIM export | IFC format for building information modeling |

---

## 🏗️ Full System Architecture (v4.0 Target)

```
User Input (Text | Voice | Photo | Sketch | AR Touch | Camera Frame | 2D Canvas)
     ↓
Multimodal Input Router
     ↓
LLM Planner (Intent → Action JSON)                    ← OpenRouter API
     ↓
Goal Planner (multi-step if needed)
     ↓
What-If Engine (simulate before committing)
     ↓
Action Dispatcher (30+ action types)
     ↓
State Manager (RoomState / HomeState)
     ↓
Spatial Reasoning Engine
     ↓
Constraint Solver (collision, boundary, walkability)
     ↓
Clearance Checker + Accessibility Score
     ↓
Layout Scorer (5-dimension scoring)
     ↓
Functional Zoning Engine
     ↓
Evaluator (feedback loop — refine until threshold met)
     ↓
WebSocket Broadcast → Frontend
     ↓
┌──────────────┬──────────────┬──────────────┬──────────────┐
↓              ↓              ↓              ↓              ↓
Three.js 3D    2D Canvas      AR Camera      Life-Size AR   Product AR
Renderer       (Fabric.js)    View           (ARKit/Core)   (Phase 4D)
     ↓
All Panels (Budget | Clearance | Score | Materials | Products | Camera | AR | Collab | Export)
```

---

## ⚙️ Complete Action System (v4.0)

### Core Actions (14 — Live)

| Action | Description |
|--------|-------------|
| `ADD` | Place new furniture |
| `MOVE` | Reposition an object |
| `ROTATE` | Change orientation |
| `DELETE` | Remove an object |
| `SET_WALL_STYLE` | Change wall color / material |
| `SET_FLOOR_STYLE` | Change floor material |
| `SET_ROOM_STYLE` | Apply a full theme preset |
| `GENERATE_LAYOUT` | Auto-generate a full room |
| `SET_ROOM_DIMENSIONS` | Resize room & set ceiling height |
| `ADD_WINDOW` | Add a window to any wall |
| `ADD_DOOR` | Add a door to any wall |
| `SAVE_PROJECT` | Save design to disk |
| `LOAD_PROJECT` | Restore a saved design |
| `NEW_PROJECT` | Start a blank room |

### New Actions (Phases 4–5)

| Action | Phase | Description |
|--------|-------|-------------|
| `AR_PLACE` | 4A | Place furniture via camera/AR tap |
| `AR_MOVE` | 4A | Reposition furniture via AR drag |
| `SET_GOAL` | 4B | Trigger goal-based multi-step planning |
| `SIMULATE` | 4B | What-if preview without committing |
| `AUTO_FIX` | 4B | Trigger self-correcting layout engine |
| `DRAW_WALL` | 4C | Draw a wall segment on the 2D canvas |
| `SET_MATERIAL` | 4C | Apply a texture/material to floor or wall surface |
| `LOAD_TEMPLATE` | 4C | Load a room template as the starting RoomState |
| `AR_LIFE_SIZE` | 4D | Open a life-size 1:1 AR product preview |
| `AR_MEASURE` | 4D | Trigger AR room measurement session |
| `AR_SAVE_TO_DESIGN` | 4D | Import AR session placements into 3D room |
| `SWAP_MATERIAL` | 5.4 | Change material/finish on placed furniture |
| `ADD_COMMENT` | 5.5 | Pin a 3D comment to a furniture item |
| `SET_ZONE` | 4B | Manually define a functional zone |
| `IMPORT_PHOTO` | 5.1 | Trigger room scan from photo |
| `SCAN_FRAME` | 4A | Trigger room scan from live camera frame |
| `ADD_ROOM` | 5.6 | Add a new room to the project |
| `CONNECT_ROOMS` | 5.6 | Link two rooms via a door |

---

## 🪑 Furniture Catalog (v4.0 — Expanded)

### Current: 17 types across 5 categories

| Category | Items |
|----------|-------|
| 🛏️ Bedroom | `bed`, `single_bed`, `nightstand`, `wardrobe`, `dresser` |
| 🛋️ Living Room | `sofa`, `armchair`, `coffee_table`, `tv_stand`, `rug` |
| 🍽️ Dining | `dining_table`, `chair` |
| 🧑‍💻 Workspace | `desk`, `office_chair`, `bookshelf` |
| 🏠 Accents | `lamp`, `plant` |

### Phase 5 Additions (Target: 50+ types)

| Category | New Items |
|----------|-----------|
| 🛏️ Bedroom | `king_bed`, `bunk_bed`, `vanity`, `ottoman`, `mirror` |
| 🛋️ Living Room | `sectional_sofa`, `loveseat`, `console_table`, `side_table`, `fireplace`, `curtain`, `wall_art` |
| 🍽️ Dining | `bar_stool`, `sideboard`, `buffet_table`, `bar_cart`, `wine_rack` |
| 🧑‍💻 Workspace | `standing_desk`, `filing_cabinet`, `whiteboard`, `monitor_stand`, `desk_lamp` |
| 🚿 Bathroom | `bathtub`, `shower`, `sink`, `toilet`, `towel_rack`, `vanity_unit` |
| 🍳 Kitchen | `kitchen_island`, `dining_bench`, `bar_counter`, `fridge`, `stove` |
| 🏠 Structural | `stairs`, `column`, `partition_wall`, `room_divider`, `arch` |

Every item includes: `size`, `color`, `height`, `price_low`, `price_high`, `weight_kg`, `min_clearance`, `category`, `description`, `sustainability_score`, `assembly_time_min`, `retailer_links[]`, `ar_scale_anchor`, `material_variants[]`

---

## 🌐 Complete API Reference (v4.0)

### Core

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serves the frontend |
| `GET` | `/health` | Server status + room stats |
| `GET` | `/state` | Full room state JSON |
| `POST` | `/command` | Execute a natural language command |
| `POST` | `/reset` | Reset the room |
| `GET` | `/catalog` | Full furniture catalog |
| `GET` | `/projects` | List saved projects |
| `GET` | `/llm-status` | Check OpenRouter API connectivity |
| `WS` | `/ws` | WebSocket for real-time state updates |

### Phase 2 (Live)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/budget` | Itemized cost estimation |
| `GET` | `/measurements` | Inter-object distances & wall clearances |
| `POST` | `/versions/save` | Save named snapshot |
| `GET` | `/versions` | List snapshots |
| `GET` | `/versions/diff?a=id&b=id` | Diff two snapshots |
| `GET` | `/versions/{id}` | Load snapshot |
| `DELETE` | `/versions/{id}` | Delete snapshot |

### Phase 3 (Live)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/render` | AI photoreal image |
| `GET` | `/render/prompt` | Preview generation prompt |
| `POST` | `/import/blueprint` | Floor plan image → room data |
| `GET` | `/products?q=sofa&budget=800` | Product suggestions |
| `GET` | `/products/room` | Products for all placed furniture |

### Phase 4A — Camera & AR

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/scan/frame` | Base64 camera frame → detected dims + furniture |

### Phase 4B — Autonomous Design

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/goal` | Set a high-level design goal |
| `GET` | `/score` | Get 5-dimension layout score |
| `POST` | `/simulate` | What-if simulation |
| `POST` | `/autofix` | Trigger self-correcting engine |
| `GET` | `/zones` | Get detected functional zones |
| `POST` | `/preference` | Record user preference signal |
| `GET` | `/preference/profile` | Get learned preference profile |

### Phase 4C — 2D Floor Plan Editor

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/materials` | Full materials + textures library |
| `GET` | `/materials/{category}` | Materials by category |
| `POST` | `/floorplan/sync` | 2D canvas state → RoomState update |
| `GET` | `/floorplan/export?format=pdf` | Export 2D floor plan |
| `GET` | `/templates` | List all room templates |
| `GET` | `/templates/{id}` | Load a room template |
| `POST` | `/floorplan/walls` | Draw walls from polyline |

### Phase 4D — Life-Size Product AR

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ar/session` | Create AR session |
| `GET` | `/ar/session/{token}` | Load AR session state |
| `POST` | `/ar/session/{token}/place` | Place product in AR → RoomState |
| `POST` | `/ar/session/{token}/capture` | Save AR screenshot / video |
| `GET` | `/ar/session/{token}/qr` | QR code for cross-device handoff |
| `POST` | `/ar/session/{token}/save-to-design` | Import AR session into 3D design |
| `POST` | `/ar/measure` | LiDAR scan → room dimensions |
| `GET` | `/ar/product/{item_id}/preview` | AR-ready product metadata |

### Phase 5

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/import/photo` | Room photo → full state extraction |
| `GET` | `/import/photo/preview` | Preview extracted state |
| `POST` | `/style/detect` | Detect aesthetic from photo or state |
| `GET` | `/products/search` | Multi-retailer semantic search |
| `GET` | `/products/substitute/{id}` | Spatially-valid alternatives |
| `GET` | `/products/bundle` | Money-saving bundle suggestions |
| `GET` | `/products/availability` | Live stock + store locator |
| `GET` | `/budget/financing?months=12` | Monthly payment breakdown |
| `POST` | `/voice/command` | Audio blob → executed command |
| `POST` | `/import/inspiration` | Inspiration photo → style transfer |
| `POST` | `/import/sketch` | Hand-drawn floor plan → room state |
| `POST` | `/render/video` | Cinematic walkthrough video |
| `POST` | `/furniture/{id}/material` | Live material swap |
| `POST` | `/share` | Generate shareable link |
| `GET` | `/share/{token}` | Load shared project |
| `WS` | `/ws/collab/{room_id}` | Multiplayer session |
| `POST` | `/export/pdf` | Contractor-ready PDF |
| `POST` | `/export/dxf` | CAD DXF export |
| `GET` | `/export/materials` | Material takeoff sheet |
| `POST` | `/comments` | Add 3D comment pin |
| `GET` | `/comments` | List all comment pins |
| `POST` | `/home/rooms` | Add room to home project |
| `POST` | `/home/connect` | Connect two rooms |
| `GET` | `/home/flow` | Traffic flow analysis |
| `GET` | `/home/budget` | Whole-home aggregate budget |

---

## 📁 Full Project Structure (v4.0 Target)

```
AI-Interior-Designer/
│
├── README.md
├── start.bat
│
├── backend/
│   ├── api/
│   │   ├── server.py                    ← FastAPI — all REST + WebSocket
│   │   └── ikea_routes.py               ← NEW: IKEA catalog API routes
│   │
│   ├── graph/
│   │   └── designer_graph.py            ← LangGraph pipeline
│   │
│   ├── state/
│   │   ├── state_manager.py             ← RoomState TypedDict
│   │   └── home_state.py                ← NEW Phase 5.6: HomeState
│   │
│   ├── actions/
│   │   ├── add.py / move.py / rotate.py / delete.py / style.py / project.py
│   │   └── multiroom.py                 ← NEW Phase 5.6
│   │
│   ├── planner/
│   │   ├── spatial_rules.py / constraint_solver.py / clearance_checker.py
│   │   ├── goal_planner.py              ← NEW Phase 4B
│   │   ├── evaluator.py                 ← NEW Phase 4B
│   │   ├── what_if_engine.py            ← NEW Phase 4B
│   │   └── preference_store.py          ← NEW Phase 4B
│   │
│   ├── engine/
│   │   ├── layout_scorer.py             ← NEW Phase 4B
│   │   └── zoning.py                    ← NEW Phase 4B
│   │
│   ├── floorplan/
│   │   ├── canvas_sync.py               ← NEW Phase 4C: 2D ↔ RoomState
│   │   ├── wall_builder.py              ← NEW Phase 4C: polyline → 3D mesh
│   │   └── floorplan_export.py          ← NEW Phase 4C: PDF/SVG export
│   │
│   ├── ar/
│   │   ├── session_manager.py           ← NEW Phase 4D: session + QR tokens
│   │   ├── room_measure.py              ← NEW Phase 4D: LiDAR → dimensions
│   │   └── ar_capture_store.py          ← NEW Phase 4D: screenshots/videos
│   │
│   ├── environment/
│   │   ├── room.py
│   │   └── objects.py
│   │
│   ├── vision/
│   │   ├── room_scanner.py              ← NEW Phase 5.1
│   │   ├── furniture_recognizer.py      ← NEW Phase 5.1
│   │   ├── style_extractor.py           ← NEW Phase 5.1
│   │   └── live_scanner.py              ← NEW Phase 4A
│   │
│   ├── storage/
│   │   ├── project_store.py / version_store.py
│   │   └── collab_store.py              ← NEW Phase 5.5
│   │
│   ├── llm/
│   │   ├── prompt.py / parser.py / image_renderer.py
│   │
│   ├── rendering/
│   │   ├── video_renderer.py            ← NEW Phase 5.4
│   │   └── shadow_simulator.py          ← NEW Phase 5.4
│   │
│   ├── blueprint_import/
│   │   └── blueprint_parser.py
│   │
│   ├── catalog/
│   │   ├── product_search.py            ← UPGRADED: queries SQLite IKEA catalog
│   │   ├── multi_retailer.py            ← NEW Phase 5.2
│   │   ├── substitution_engine.py       ← NEW Phase 5.2
│   │   └── sustainability_scorer.py     ← NEW Phase 5.2
│   │
│   ├── scraper/
│   │   ├── ikea_scraper.py              ← NEW: async IKEA catalog scraper
│   │   ├── catalog_writer.py            ← NEW: JSON + SQLite writer
│   │   └── run_scraper.py               ← NEW: CLI runner
│   │
│   ├── export/
│   │   ├── pdf_exporter.py              ← NEW Phase 5.5
│   │   ├── dxf_exporter.py              ← NEW Phase 5.5
│   │   └── material_takeoff.py          ← NEW Phase 5.5
│   │
│   ├── collab/
│   │   ├── share_manager.py             ← NEW Phase 5.5
│   │   └── comment_store.py             ← NEW Phase 5.5
│   │
│   └── .env
│
├── frontend/
│   ├── index.html / style.css
│   └── js/
│       ├── app.js / api.js / scene.js / furniture.js / versions.js
│       │
│       ├── ── Phase 4A ──
│       ├── ar.js                        ← UPGRADED: full WebXR hit-test
│       ├── camera_background.js
│       ├── floor_raycaster.js
│       ├── ar_placement_overlay.js
│       ├── ar_sync.js
│       │
│       ├── ── Phase 4B ──
│       ├── scoring_panel.js
│       │
│       ├── ── Phase 4C ──
│       ├── floorplan_canvas.js          ← 2D canvas engine (Fabric.js / Konva.js)
│       ├── wall_tool.js
│       ├── snap_engine.js
│       ├── dimension_overlay.js
│       ├── material_library.js
│       ├── room_templates.js
│       ├── floorplan_export.js
│       │
│       ├── ── Phase 4D ──
│       ├── ar_product_browser.js        ← product-first AR flow
│       ├── ar_life_size.js              ← 1:1 scale AR session
│       ├── ar_label_overlay.js
│       ├── ar_capture.js
│       ├── ar_before_after.js
│       ├── ar_room_measure.js
│       ├── ar_qr_handoff.js
│       │
│       ├── ── Phase 5 ──
│       ├── voice_input.js
│       ├── sketch_input.js
│       ├── collab.js
│       └── export_panel.js
│
└── data/
    ├── furniture_catalog.json
    ├── ikea_catalog.json                ← NEW: full scraped IKEA catalog
    ├── ikea_catalog.db                  ← NEW: SQLite for fast queries
    ├── materials/
    │   ├── floors/                      ← NEW Phase 4C: floor textures
    │   ├── walls/                       ← NEW Phase 4C: wall finish textures
    │   └── fabrics/                     ← NEW Phase 4C: furniture textures
    ├── templates/                       ← NEW Phase 4C: room template JSON files
    ├── projects/ / versions/ / preferences/ / shared/
```

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/sherif2004/AI-Interior-Designer.git
cd AI-Interior-Designer
```

### 2. Configure the environment

```bash
copy backend\.env.example backend\.env
```

Edit `backend/.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=deepseek/deepseek-chat

IMAGE_RENDER_PROVIDER=mock         # mock | stability | replicate
STABILITY_API_KEY=sk-...
REPLICATE_API_KEY=r8_...

WAYFAIR_API_KEY=...                # Phase 5.2
AMAZON_PA_API_KEY=...              # Phase 5.2
SECRET_KEY=your-jwt-secret         # Phase 5.5
DATABASE_URL=postgresql://...      # Phase 6
REDIS_URL=redis://...              # Phase 6
```

### 3. Scrape IKEA catalog (optional but recommended)

```bash
pip install httpx aiofiles

# Quick test — sofas only (~2 min)
python -m backend.scraper.run_scraper --category sofas

# Full catalog (~10k products, ~30 min)
python -m backend.scraper.run_scraper --full
```

### 4. Launch

Double-click **`start.bat`** → open **http://localhost:8000**

> **HTTPS required for camera features.** `localhost` works natively. For production, TLS is mandatory for `getUserMedia`, WebXR hit-test, and ARKit/ARCore APIs.

---

## 💬 Example Commands

```plaintext
# Basic layout
Create a modern living room
Add a sofa near the north wall, rotate it 90 degrees
Make the walls warm white, use marble flooring

# 2D floor plan editor (Phase 4C)
[Draw walls on 2D canvas] → drag furniture from catalog sidebar
[Apply oak herringbone texture from materials library]
[Load "Master Bedroom" template] → customize from there
[Export 2D floor plan as PDF]

# Life-size AR shopping (Phase 4D)
[Browse IKEA catalog → tap EKTORP sofa → "View in AR"]
[Tap real floor → sofa appears at 1:1 scale in your room]
[Switch color variant in AR: beige → grey]
[Capture AR photo → share to social]
[Tap "Save to Design" → sofa added to 3D room + AI scores the layout]

# Camera mode (Phase 4A)
[Toggle camera mode] → click floor to place sofa live
[AR mode on mobile] → tap real floor to place bed

# Autonomous design (Phase 4B)
Make this room cozy
What if I add a dining table?
Fix all clearance issues automatically

# Intelligence (Phase 5)
[Upload room photo] → "Scan my room"
Find a similar sofa but under $300
```

---

## 🧠 Design Principles

**Separation of Concerns** — LLM handles reasoning, engine handles execution. No hallucinated coordinates.

**Deterministic Execution** — Every placement is validated by the constraint solver. Coordinates are computed, never generated.

**Stateful Interaction** — Context-aware commands. "Move it left" knows what "it" is.

**Extensible Graph** — The LangGraph pipeline makes it trivial to add new validation nodes.

**Embodied Intelligence** — The system operates *inside* a spatial environment, not just generates text about it.

**Camera as Input** — The live camera feed is a first-class input surface, not a peripheral feature.

**2D and 3D as equals** — The 2D canvas is a full editing environment, not a view-only toggle. Changes in 2D and 3D are always bidirectionally synced.

**AR bridges real and virtual** — Every AR placement carries back into the main design tool and is scored by the AI engine. The AR session is never a dead end.

**User Sovereignty** — Every AI decision is explainable, reversible, and overridable by the user.

---

## 🗺️ Build Roadmap

| Phase | Status | Key Deliverable | Inspired By |
|-------|--------|-----------------|-------------|
| Phase 1 | ✅ Complete | Interactive NL room editor | — |
| Phase 2 | ✅ Complete | Budget, clearance, versions | — |
| Phase 3 | ✅ Complete | AI render, blueprint import, AR stub | — |
| Phase 4A | ✅ Complete | Live camera + WebXR AR placement | IKEA Place |
| Phase 4B | ✅ Complete | Goal planner, scoring, autonomous design | — |
| Phase 4C | ✅ Complete | Professional 2D drag-and-drop floor plan editor | **Planner 5D** |
| Phase 4D | ✅ Complete | Life-size 1:1 product AR + product-first shopping | **IKEA Place** |
| Phase 5.1 | 🔄 Next | Room photo → full state import | — |
| Phase 5.2 | 📋 Planned | Multi-retailer commerce engine | — |
| Phase 5.3 | 📋 Planned | Voice + multimodal input | — |
| Phase 5.4 | 📋 Planned | First-person walkthrough + video export | — |
| Phase 5.5 | 📋 Planned | Collaboration + professional export | Planner 5D Pro |
| Phase 5.6 | 📋 Planned | Multi-room + whole-home planning | Planner 5D |
| Phase 6 | 🔭 Vision | User accounts, cloud sync, community | — |

---

## 📚 References

- Embodied AI agent systems for spatial reasoning tasks
- Spatial reasoning in language models (DS-STAR)
- LangGraph state machine design patterns
- Three.js PBR rendering pipeline
- WebXR Device API — Hit Test Module
- **ARKit** (Apple) — People Occlusion, LiDAR Mesh, Lighting Estimation
- **ARCore** (Google) — Environmental HDR, Depth API, Instant Placement
- **IKEA Place** — Life-size 1:1 AR product visualization (2017, ARKit launch)
- **Planner 5D** — 2D/3D drag-and-drop interior planning software (amateurs + professionals)
- `getUserMedia` and `VideoTexture` in Three.js

---

## 👤 Author

**Sherif Ashraf**
AI Engineer | Agent Systems | LLM Applications

---

## ⭐ Support

If you find this project useful, please ⭐ the repo!
