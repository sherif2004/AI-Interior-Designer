# 🏠 AI Interior Designer (Interactive)

### Stateful Embodied LLM for Real-Time Home Design & Visualization

---

## 🧠 Overview

AI Interior Designer is a **stateful, interactive embodied AI system** that allows users to design room layouts and visualize their future home using natural language commands in real time.

Instead of generating a full layout at once, the system:

* Maintains a **persistent room and project state**
* Interprets **incremental user instructions**
* Executes **structured actions**
* Updates the environment continuously
* Supports **save/load project workflows**

This transforms the LLM from a passive generator into an **active agent operating inside a spatial environment**, making it a practical tool for home planning.

---

## 🎯 Implemented Features (v1.0)

### 🔁 Interactive Session

* Start with an empty room
* Continuously modify layout through natural language commands

Examples:

* "Add a bed"
* "Move it left"
* "Put a table in front of it"

---

### 🧠 Stateful Environment & Projects

* Persistent room state across interactions
* Object tracking via unique IDs
* **Project save/load** — design and come back later
* **Multiple theme presets** — modern, minimalist, scandinavian, cozy, luxury, industrial, bohemian

---

### ⚙️ Structured Action System

Supports deterministic execution via action types:

* `ADD` → add new furniture
* `MOVE` → move existing object
* `ROTATE` → change orientation
* `DELETE` → remove object
* `SET_WALL_STYLE` → change wall color/material
* `SET_FLOOR_STYLE` → change floor material
* `SET_ROOM_STYLE` → apply theme preset
* `GENERATE_LAYOUT` → auto-create full room
* `SET_ROOM_DIMENSIONS` → resize room & ceiling
* `ADD_WINDOW` → add structural window
* `ADD_DOOR` → add structural door
* `SAVE_PROJECT` → save to disk
* `LOAD_PROJECT` → load from disk
* `NEW_PROJECT` → start fresh

---

### 📐 Spatial Reasoning Engine

Understands:

* relative placement ("next to", "in front of", "north_of", "south_of", etc.)
* absolute placement ("corner", "center")
* constraints ("near wall")
* cardinal positioning

---

### 🚫 Constraint-Based Layout

* Prevents collisions
* Enforces room boundaries
* Maintains realistic spacing

---

### 🎨 Room Styling & Materials

* **Wall styles**: paint, panels, stone, wallpaper
* **Floor styles**: wood, tile, marble, concrete, carpet
* **Rich color palette**: white, beige, cream, gray, navy, sage, oak, walnut, terracotta, and more
* **Theme presets**: modern, minimalist, scandinavian, cozy, luxury, industrial, bohemian
* **Auto-generated layouts** with styled rooms

---

### 🪑 Full Furniture Support

Supports a wide catalog of objects:

#### 🛏️ Bedroom

* bed, single_bed, nightstand, wardrobe, dresser

#### 🛋️ Living Room

* sofa, armchair, coffee_table, tv_stand

#### 🍽️ Dining

* dining_table, chair

#### 🧑‍💻 Workspace

* desk, office_chair, bookshelf

#### 🏠 Additional

* lamp, plant, rug

All furniture defined with:

* size
* orientation
* placement constraints

---

### 🏠 Structural Elements

* **Doors** — add on any wall with position control
* **Windows** — add on any wall with position control
* **Room dimensions** — set width, height, and ceiling height

---

### 📂 Project Persistence

* Save designs to local JSON files
* Load previous projects
* List saved projects from UI

---

### 🖥️ Frontend Features

* **3D visualization** (Three.js)
* **2D top-down view**
* Real-time WebSocket updates
* Project panel with save/load controls
* Style badges showing theme, wall, and floor info
* Quick command chips for common actions

---

## 🏗️ System Architecture

```
User Command (Natural Language)
     ↓
LLM Planner (Intent → Action JSON)
     ↓
Action Dispatcher
     ↓
State Manager (Single Source of Truth)
     ↓
Spatial Reasoning Engine
     ↓
Constraint Solver
     ↓
Renderer (2D / 3D)
     ↓
Updated State → Loop
```

---

## 🧩 Core Components

### 1. LLM Planner

Transforms user input into structured actions using OpenRouter.

#### Example:

Input: `Add a sofa near the wall`

Output:

```json
{
  "type": "ADD",
  "object": "sofa",
  "constraints": {"placement": "near_wall"}
}
```

---

### 2. State Manager

Maintains full environment state:

```json
{
  "project": {"id": "my_home", "name": "My Home Project"},
  "room": {
    "width": 6,
    "height": 5,
    "ceiling_height": 3.0,
    "wall_style": {"color": "#f3efe8", "material": "paint"},
    "floor_style": {"color": "#b08968", "material": "wood"},
    "theme": "modern",
    "windows": [],
    "doors": []
  },
  "objects": [...]
}
```

---

### 3. Action Handlers

* `add.py` — furniture placement
* `move.py` — repositioning
* `rotate.py` — orientation changes
* `delete.py` — removal
* `style.py` — wall/floor/room styling + auto-layout generation
* `project.py` — dimensions, openings, save/load

---

### 4. Spatial Reasoning Engine

Maps symbolic instructions → valid coordinates.

---

### 5. Constraint Solver

Ensures: no overlap, valid placement, walkable space.

---

### 6. Renderer

* **3D** — Three.js with PBR materials
* **2D** — Canvas 2D top-down view

---

## 📁 Project Structure

```
ai-interior-designer/
│
├── README.md
│
├── docs/
│   └── PHASE1_ROADMAP.md
│
├── backend/
│   ├── llm/
│   │   ├── prompt.py
│   │   └── parser.py
│   │
│   ├── state/
│   │   └── state_manager.py
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
│   │   └── constraint_solver.py
│   │
│   ├── environment/
│   │   ├── room.py
│   │   └── objects.py
│   │
│   ├── storage/
│   │   └── project_store.py
│   │
│   ├── graph/
│   │   └── designer_graph.py
│   │
│   ├── api/
│   │   └── server.py
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── js/
│       ├── app.js
│       ├── api.js
│       ├── scene.js
│       └── furniture.js
│
├── data/
│   ├── furniture_catalog.json
│   └── projects/          ← saved projects
│
└── examples/
    └── commands.txt
```

---

## 🪑 Furniture Catalog Example

```json
{
  "sofa": {
    "size": [2.5, 0.9],
    "color": "#4A7FA5",
    "height": 0.8,
    "constraints": ["against_wall"]
  },
  "bed": {
    "size": [2.0, 2.0],
    "color": "#6B5B95",
    "height": 0.5,
    "constraints": ["corner_preferred"]
  }
}
```

---

## 🚀 Getting Started

### 1. Clone repo

```bash
git clone https://github.com/sherif2004/AI-Interior-Designer.git
cd AI-Interior-Designer
```

### 2. Configure the LLM

Duplicate the environment example file:

```bash
cp backend/.env.example backend/.env
```

Inside `.env`, insert your OpenRouter API key:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=deepseek/deepseek-chat
```

### 3. Install & Launch (Windows)

1. Double click `start.bat`
2. Open your web browser to `http://localhost:8000`
3. Enjoy the AI Assistant!

### Example Commands

```plaintext
Add a bed in the corner
Add a sofa near the wall
Move it left
Rotate the sofa 90 degrees
Make the walls beige
Use wood flooring
Create a cozy bedroom
Make the room 6 by 4 meters
Set the ceiling height to 3.2 meters
Add a window on the north wall
Save this as family home
Load project family_home
```

---

## 🧠 Design Principles

### Separation of Concerns

* LLM → reasoning
* Engine → execution

### Deterministic Execution

* No hallucinated coordinates
* All placements validated

### Stateful Interaction

* Continuous environment updates
* Context-aware commands

### Project-Based Workflow

* Save and load designs
* Room resizing and structural elements

---

## 🔮 Future Work

This project follows a phased development roadmap:

### Phase 1 — Strong MVP (Foundation Complete ✅)
- ✅ Room style editing (walls, floors, themes)
- ✅ Better layout generation (template-based auto-layout)
- ✅ Structural editing for doors/windows
- ✅ Save/load project
- ✅ Rich materials and color palette
- ✅ Basic 3D visualization

*In progress:* Multi-room support, first-person camera

### Phase 2 — Practical Home Planner
- Measurements and distance tools
- Clearance checks and walking path validation
- Realistic product dimensions
- Version comparison (save design options A vs B)
- Better lighting and shadows
- Budget estimation

### Phase 3 — "See It Like Real Life"
- Photoreal rendering
- Blueprint import (upload 2D plans)
- Product catalogs (IKEA, furniture databases)
- AI photoreal previews
- AR preview (phone-based visualization)

### Long-Term Vision
- Multi-floor home support
- Collaboration tools (architect ↔ client)
- Voice commands
- Smart suggestions based on room size/usage
- Cost breakdown and material takeoff

---

## 📚 References

* Embodied AI agents
* Spatial reasoning systems
* Interior design applications
* Language-to-action research

---

## 👤 Author

Sherif Ashraf
AI Engineer | Agent Systems | LLM Applications

---

## 🭐 Support

If you find this project useful, please ⭐ the repo!