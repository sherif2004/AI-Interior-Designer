# Phase 1 Roadmap, from room demo to home planning tool

## Goal
Turn the current single-room AI layout demo into the foundation of a real home planning product.

## Priority outcomes
1. Support real room editing, not only furniture placement
2. Support multiple rooms in one home/project
3. Persist projects to disk
4. Improve realism with better material and lighting state
5. Add measurement and clearance awareness
6. Add first-person / walkthrough-ready camera support

---

## Current limitations
- Single in-memory room only
- No saved projects
- No editable structural walls/doors/windows workflow
- No multi-room home model
- Renderer is still MVP-level stylized
- No measurement tools or clearance reporting

---

## Phase 1 architecture changes

### 1. State model evolution
Move from:
- one `room`
- one `objects` list

Toward:
- one `project`
- many `rooms`
- active room selection
- project metadata

Suggested shape:

```json
{
  "project": {
    "id": "project_1",
    "name": "My Home",
    "active_room_id": "living_room",
    "rooms": [
      {
        "id": "living_room",
        "name": "Living Room",
        "width": 6,
        "height": 4,
        "ceiling_height": 3,
        "wall_style": {},
        "floor_style": {},
        "doors": [],
        "windows": [],
        "objects": []
      }
    ]
  }
}
```

### 2. New action families
#### Structural editing
- `SET_ROOM_DIMENSIONS`
- `ADD_ROOM`
- `SWITCH_ROOM`
- `ADD_WINDOW`
- `ADD_DOOR`
- `MOVE_DOOR`
- `MOVE_WINDOW`

#### Project persistence
- `SAVE_PROJECT`
- `LOAD_PROJECT`
- `NEW_PROJECT`

#### Analysis
- `MEASURE_DISTANCE`
- `CHECK_CLEARANCE`
- `LIST_ISSUES`

### 3. Backend modules to add
- `backend/actions/structure.py`
- `backend/actions/project.py`
- `backend/actions/analysis.py`
- `backend/storage/project_store.py`
- `backend/planner/clearance_rules.py`

### 4. Frontend additions
- Room selector
- Project name/status
- Save/load controls
- Basic issue panel
- Measurement overlay

---

## Implementation order

### Step A
Add project persistence and room metadata without breaking current UI.

### Step B
Add structural editing actions for room dimensions, doors, and windows.

### Step C
Add multi-room support in state and APIs.

### Step D
Add analysis, measurements, and clearance warnings.

### Step E
Add improved camera/view modes.

---

## Definition of done for Phase 1
- User can create and save a project
- User can add at least two rooms and switch between them
- User can resize a room and add/move windows and doors
- User can reload the project later
- User can request a basic clearance check
- UI shows current room and project state clearly
