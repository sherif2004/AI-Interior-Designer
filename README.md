# 🏠 AI Interior Designer

### Stateful Embodied LLM for Real-Time Home Design & Visualization

![Phase](https://img.shields.io/badge/Phase-2_%26_3_Complete-7c3aed?style=flat-square)
![Stack](https://img.shields.io/badge/Stack-FastAPI_%7C_LangGraph_%7C_Three.js-0ea5e9?style=flat-square)
![LLM](https://img.shields.io/badge/LLM-OpenRouter-f5c842?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-22d3a5?style=flat-square)

---

## 🧠 Overview

AI Interior Designer is a **stateful, interactive embodied AI system** that lets you design full room layouts using natural language — and now visualize them with **budget estimates**, **clearance validation**, **AI-generated photoreal renders**, **floor plan import**, and **real product suggestions**.

Instead of generating a full layout at once, the system:

- Maintains a **persistent room and project state**
- Interprets **incremental user commands** ("Move the sofa left", "Add a window")
- Executes **structured, deterministic actions** validated by a spatial engine
- Updates a live **3D visualization** with real-time WebSocket streaming
- Supports full **save/load/version** project workflows

This transforms the LLM from a passive generator into an **active agent operating inside a spatial environment** — a practical tool for actual home planning.

---

## ✅ What's Implemented (v2.0 — Phase 2 & 3 Complete)

### 🏗️ Phase 1 — Strong MVP (Complete)

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

### 🏠 Phase 2 — Practical Home Planner (Complete)

| Feature | Description |
|---------|-------------|
| 💰 Budget estimation | Itemized cost ranges by furniture, grouped by category |
| ⚠️ Clearance checks | Validates 60cm walkways between all objects, red/yellow halos in 3D |
| 📊 Accessibility score | 0–100% walkability score updated after every action |
| 📏 Measurement tool | Click any 2 objects to draw a 3D measurement line with meter label |
| 🌅 Day/Night cycle | Sun arc slider (0–24h) controlling position, warmth, and intensity |
| 🔀 Version comparison | Save named snapshots, compare any two with a split-screen 2D diff canvas |
| 📦 Realistic dimensions | Industry-standard furniture sizes, `price_low/high`, `weight_kg`, `min_clearance` in catalog |

### ✨ Phase 3 — See It Like Real Life (Complete)

| Feature | Description |
|---------|-------------|
| 🎨 AI photoreal render | Builds scene prompt from state → Stability AI / Replicate SDXL / mock Unsplash |
| 📐 Blueprint import | Upload PNG/JPG floor plan → LLM vision extracts room dimensions, doors, windows |
| 🛍️ Product catalog | IKEA-style product cards (photo, price, dimensions, buy link) for all placed furniture |
| 📱 AR preview | WebXR immersive-AR session — walk your room at 1:1 scale on mobile |

---

## 🏗️ System Architecture

```
User Command (Natural Language)
     ↓
LLM Planner (Intent → Action JSON)        ← OpenRouter API
     ↓
Action Dispatcher (14 action types)
     ↓
State Manager (RoomState — single source of truth)
     ↓
Spatial Reasoning Engine
     ↓
Constraint Solver (collision, boundary, walkability)
     ↓
Clearance Checker (accessibility score + warnings)  ← NEW
     ↓
WebSocket Broadcast → Frontend
     ↓
Three.js 3D Renderer / Canvas 2D View
     ↓
Phase 2/3 Panels (Budget, Clearance, Versions, Products, AR)
```

---

## ⚙️ Action System

14 structured action types supported:

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

---

## 🪑 Furniture Catalog

17 furniture types across 5 categories, each with industry-standard sizing:

| Category | Items |
|----------|-------|
| 🛏️ Bedroom | `bed`, `single_bed`, `nightstand`, `wardrobe`, `dresser` |
| 🛋️ Living Room | `sofa`, `armchair`, `coffee_table`, `tv_stand`, `rug` |
| 🍽️ Dining | `dining_table`, `chair` |
| 🧑‍💻 Workspace | `desk`, `office_chair`, `bookshelf` |
| 🏠 Accents | `lamp`, `plant` |

Every item includes: real `size`, `color`, `height`, `price_low`, `price_high`, `weight_kg`, `min_clearance`, `category`, `description`.

---

## 🌐 API Reference

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

### Phase 2

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/budget` | Itemized cost estimation for all placed furniture |
| `GET` | `/measurements` | Inter-object distances & wall clearances |
| `POST` | `/versions/save` | Save current design as a named snapshot |
| `GET` | `/versions` | List all saved snapshots |
| `GET` | `/versions/diff?a=id&b=id` | Diff two snapshots |
| `GET` | `/versions/{id}` | Load a specific snapshot |
| `DELETE` | `/versions/{id}` | Delete a snapshot |

### Phase 3

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/render` | Generate an AI photoreal image of the current room |
| `GET` | `/render/prompt` | Preview the image generation prompt |
| `POST` | `/import/blueprint` | Upload a floor plan image and extract room data |
| `GET` | `/products?q=sofa&budget=800` | Search real product suggestions by type |
| `GET` | `/products/room` | Product suggestions for all furniture in the room |

---

## 📁 Project Structure

```
AI-Interior-Designer/
│
├── README.md
├── start.bat                   ← Windows launcher
│
├── backend/
│   ├── api/
│   │   └── server.py           ← FastAPI — REST + WebSocket (Phase 2/3 endpoints)
│   │
│   ├── graph/
│   │   └── designer_graph.py   ← LangGraph pipeline (planner → dispatcher → clearance)
│   │
│   ├── state/
│   │   └── state_manager.py    ← RoomState TypedDict
│   │
│   ├── actions/
│   │   ├── add.py
│   │   ├── move.py
│   │   ├── rotate.py
│   │   ├── delete.py
│   │   ├── style.py
│   │   └── project.py
│   │
│   ├── planner/
│   │   ├── spatial_rules.py
│   │   ├── constraint_solver.py
│   │   └── clearance_checker.py   ← NEW: walkability + accessibility score
│   │
│   ├── environment/
│   │   ├── room.py
│   │   └── objects.py
│   │
│   ├── storage/
│   │   ├── project_store.py
│   │   └── version_store.py    ← NEW: design snapshots + diff
│   │
│   ├── llm/
│   │   ├── prompt.py
│   │   ├── parser.py
│   │   └── image_renderer.py   ← NEW: AI photoreal rendering
│   │
│   ├── blueprint_import/
│   │   └── blueprint_parser.py ← NEW: LLM vision floor plan import
│   │
│   ├── catalog/
│   │   └── product_search.py   ← NEW: IKEA-style product suggestions
│   │
│   └── .env                    ← API keys (not committed)
│
├── frontend/
│   ├── index.html              ← 7-tab layout with all Phase 2/3 panels
│   ├── style.css               ← Premium dark UI + all new component styles
│   └── js/
│       ├── app.js              ← Main app — all Phase 2/3 UI wired up
│       ├── api.js              ← API client for all endpoints
│       ├── scene.js            ← Three.js — VSM shadows, day/night, measure lines
│       ├── furniture.js        ← 3D mesh generation
│       ├── versions.js         ← NEW: version save/compare UI
│       └── ar.js               ← NEW: WebXR AR preview
│
└── data/
    ├── furniture_catalog.json  ← 17 types with pricing & clearance data
    ├── projects/               ← saved design projects
    └── versions/               ← saved version snapshots
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
# Required — OpenRouter API key for the LLM planner
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=deepseek/deepseek-chat

# Optional — AI photoreal rendering (default: mock Unsplash image)
IMAGE_RENDER_PROVIDER=mock         # options: mock | stability | replicate
STABILITY_API_KEY=sk-...           # if using Stability AI
REPLICATE_API_KEY=r8_...           # if using Replicate SDXL
```

### 3. Launch

Double-click **`start.bat`** → open **http://localhost:8000**

---

## 💬 Example Commands

```plaintext
Create a modern living room
Create a cozy bedroom
Add a sofa near the north wall
Move the sofa left 1 meter
Rotate the chair 90 degrees
Make the walls warm white
Use marble flooring
Make the room 8 by 6 meters
Set the ceiling height to 3.5 meters
Add a window on the east wall
Save this as Design A
```

---

## 🔧 New in v2.0

### Phase 2 highlights

- **Day/Night slider** in the header — smoothly moves the sun from sunrise to night
- **Budget tab** — e.g. *"Modern living room: $825–$7,000 USD"*
- **Clearance tab** — accessibility score (%) + exact gap warnings like *"Only 0.30m between coffee_table and lamp"*
- **Measure mode** — click any 2 objects to draw a live measurement line in the 3D view
- **Version Compare** — save "Design A" and "Design B" and see a side-by-side diff canvas

### Phase 3 highlights

- **✨ AI Render** button — generates a room description prompt and calls the image API (or returns a high-quality Unsplash photo in mock mode)
- **📐 Blueprint import tab** — upload any PNG/JPG floor plan, AI extracts dimensions/doors/windows
- **🛍️ Shop tab** — IKEA product cards for every piece of furniture in the room (photo, price, buy link)
- **📱 AR Preview** — WebXR button appears automatically on supported mobile browsers

---

## 🧠 Design Principles

**Separation of Concerns** — LLM handles reasoning, engine handles execution. No hallucinated coordinates.

**Deterministic Execution** — Every placement is validated by the constraint solver. Coordinates are computed, not generated.

**Stateful Interaction** — Context-aware commands. "Move it left" knows what "it" is.

**Extensible Graph** — The LangGraph pipeline makes it easy to add new validation nodes (clearance check is a real node in the graph).

---

## 🔮 Future Work

### Near-Term
- [ ] Multi-room support (bedroom + living room in one project)
- [ ] First-person walkthrough camera
- [ ] Voice command input (Web Speech API)

### Long-Term Vision
- [ ] Collaboration tools (architect ↔ client, real-time multiplayer)
- [ ] Multi-floor home support
- [ ] Smart suggestions based on room dimensions and usage patterns
- [ ] Material takeoff + contractor-ready cost estimation
- [ ] Export to DXF / SketchUp format

---

## 📚 References

- Embodied AI agent systems
- Spatial reasoning in language models
- LangGraph state machine design
- Three.js PBR rendering
- WebXR Augmented Reality API

---

## 👤 Author

**Sherif Ashraf**
AI Engineer | Agent Systems | LLM Applications

---

## ⭐ Support

If you find this project useful, please ⭐ the repo!