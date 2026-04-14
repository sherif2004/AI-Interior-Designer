# 🏠 AI Interior Designer (Interactive)

### Stateful Embodied LLM for Real-Time Furniture Placement

---

## 🧠 Overview

AI Interior Designer is a **stateful, interactive embodied AI system** that allows users to design room layouts using natural language commands in real time.

Instead of generating a full layout at once, the system:

* Maintains a **persistent room state**
* Interprets **incremental user instructions**
* Executes **structured actions**
* Updates the environment continuously

This transforms the LLM from a passive generator into an **active agent operating inside a spatial environment**.

---

## 🎯 Key Features

### 🔁 Interactive Session (Core Feature)

* Start with an empty room
* Continuously modify layout through commands

Examples:

* “Add a bed”
* “Move it left”
* “Put a table in front of it”

---

### 🧠 Stateful Environment

* Persistent room state across interactions
* Object tracking via unique IDs
* Context-aware updates

---

### ⚙️ Structured Action System

Supports deterministic execution via action types:

* `ADD` → add new furniture
* `MOVE` → move existing object
* `ROTATE` → change orientation
* `DELETE` → remove object

---

### 📐 Spatial Reasoning Engine

Understands:

* relative placement (“next to”, “in front of”)
* absolute placement (“corner”, “center”)
* constraints (“near wall”)

---

### 🚫 Constraint-Based Layout

* Prevents collisions
* Enforces room boundaries
* Maintains realistic spacing

---

### 🪑 Full Furniture Support

Supports a wide catalog of objects:

#### 🛏️ Bedroom

* bed, nightstand, wardrobe, dresser

#### 🛋️ Living Room

* sofa, armchair, coffee table, TV stand

#### 🍽️ Dining

* dining table, chairs

#### 🧑‍💻 Workspace

* desk, office chair, bookshelf

#### 🚪 Structural

* doors, windows (fixed constraints)

All furniture defined with:

* size
* orientation
* placement constraints

---

## 🏗️ System Architecture

```
User Command
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

Transforms user input into structured actions.

#### Example:

Input:

```
Add a sofa near the wall
```

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
  "room": {"width": 6, "height": 5},
  "objects": [
    {
      "id": "sofa_1",
      "type": "sofa",
      "position": [0, 2],
      "rotation": 0
    }
  ]
}
```

---

### 3. Action Dispatcher

Routes actions to handlers:

* `handle_add()`
* `handle_move()`
* `handle_rotate()`
* `handle_delete()`

---

### 4. Spatial Reasoning Engine

Maps symbolic instructions → valid coordinates.

Examples:

* `corner` → (0,0) or nearest corner
* `next_to` → adjacent grid cell
* `in_front_of` → directional offset

---

### 5. Constraint Solver

Ensures:

* no overlap
* valid placement
* walkable space

---

### 6. Renderer

Options:

* 2D grid (MVP)
* 3D visualization (Three.js)

---

## 📁 Project Structure

```
ai-interior-designer/
│
├── README.md
├── demo/
├── docs/
│
├── backend/
│   ├── llm/
│   │   ├── prompt.py
│   │   ├── parser.py
│   │
│   ├── state/
│   │   └── state_manager.py
│   │
│   ├── actions/
│   │   ├── add.py
│   │   ├── move.py
│   │   ├── rotate.py
│   │   ├── delete.py
│   │
│   ├── planner/
│   │   ├── spatial_rules.py
│   │   ├── constraint_solver.py
│   │
│   ├── environment/
│   │   ├── room.py
│   │   ├── objects.py
│   │
│   ├── api/
│   │   └── server.py
│
├── frontend/
│   ├── viewer/
│   ├── components/
│
├── data/
│   └── furniture_catalog.json
│
└── examples/
    └── commands.txt
```

---

## 🪑 Furniture Catalog Example

```json
{
  "sofa": {
    "size": [2, 1],
    "constraints": ["against_wall"]
  },
  "bed": {
    "size": [2, 2],
    "constraints": ["corner_preferred"]
  },
  "table": {
    "size": [1, 1]
  }
}
```

---

## 🚀 Getting Started

### 1. Clone repo

```bash
git clone https://github.com/your-username/ai-interior-designer.git
cd ai-interior-designer
```

---

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 3. Run backend

```bash
python backend/api/server.py
```

---

### 4. Run frontend

```bash
npm install
npm run dev
```

---

## 🧪 Example Interaction

### Step 1

```
Add a bed
```

### Step 2

```
Move it left
```

### Step 3

```
Add a lamp next to it
```

---

## 🧠 Design Principles

### Separation of Concerns

* LLM → reasoning
* Engine → execution

---

### Deterministic Execution

* No hallucinated coordinates
* All placements validated

---

### Stateful Interaction

* Continuous environment updates
* Context-aware commands

---

## 📊 Evaluation

* Action success rate
* Collision rate
* Instruction accuracy
* User interaction efficiency

---

## 🔮 Future Work

* Multi-room support
* AR visualization
* Real furniture integration (IKEA, etc.)
* Voice commands
* Style-aware generation

---

## 📚 References

* Embodied AI agents
* Spatial reasoning systems
* Interior design applications
* Language-to-action research

---

## 👤 Author

Your Name
AI Engineer | Agent Systems | LLM Applications
