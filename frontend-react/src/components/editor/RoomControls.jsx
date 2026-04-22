import React from 'react'
import { sendCommand } from '../../api/client'
import { useRoomState } from '../../hooks/useRoomState'

export default function RoomControls() {
  const { state } = useRoomState()

  const handleCommand = (cmdStr) => {
    sendCommand(cmdStr).catch(console.error)
  }

  // Derived current values for uncontrolled inputs
  const currentWidth = state?.room_width || 10
  const currentHeight = state?.room_depth || 8
  const currentCeiling = state?.ceiling_height || 3
  const currentShape = state?.room_shape || 'rectangle'
  const currentTheme = state?.style?.theme || 'modern'
  const currentWallColor = state?.style?.wall_color || '#ffffff'
  const currentFloorColor = state?.style?.floor_color || '#d4b483'

  return (
    <div className="left-panel">
      <div className="panel-header">
        <h3>Room Configuration</h3>
      </div>
      
      <div className="control-group">
        <label>Dimensions (meters)</label>
        <div className="control-row">
          <div>
            <span style={{fontSize:10,color:'#94a3b8'}}>Width</span>
            <input type="number" className="input-base" defaultValue={currentWidth} 
              onBlur={e => handleCommand(`Set room width to ${e.target.value}m`)} 
              onKeyDown={e => e.key === 'Enter' && e.target.blur()} />
          </div>
          <div>
            <span style={{fontSize:10,color:'#94a3b8'}}>Depth</span>
            <input type="number" className="input-base" defaultValue={currentHeight} 
              onBlur={e => handleCommand(`Set room depth to ${e.target.value}m`)}
              onKeyDown={e => e.key === 'Enter' && e.target.blur()} />
          </div>
          <div>
            <span style={{fontSize:10,color:'#94a3b8'}}>Ceiling</span>
            <input type="number" className="input-base" defaultValue={currentCeiling} step="0.1"
              onBlur={e => handleCommand(`Set ceiling height to ${e.target.value}m`)}
              onKeyDown={e => e.key === 'Enter' && e.target.blur()} />
          </div>
        </div>
      </div>

      <div className="control-group">
        <label>Room Shape</label>
        <select className="input-base" value={currentShape} onChange={e => handleCommand(`Make the room ${e.target.value}`)}>
          <option value="rectangle">Rectangle</option>
          <option value="L_shape">L-Shape</option>
          <option value="T_shape">T-Shape</option>
        </select>
      </div>

      <div className="control-group">
        <label>Style Theme</label>
        <select className="input-base" value={currentTheme} onChange={e => handleCommand(`Change theme to ${e.target.value}`)}>
          <option value="modern">Modern</option>
          <option value="scandinavian">Scandinavian</option>
          <option value="industrial">Industrial</option>
          <option value="minimalist">Minimalist</option>
          <option value="bohemian">Bohemian</option>
        </select>
      </div>

      <div className="control-group">
        <label>Wall Finish</label>
        <div className="control-row">
          <input type="color" defaultValue={currentWallColor} onBlur={e => handleCommand(`Set wall color to ${e.target.value}`)} />
          <select className="input-base" onChange={e => handleCommand(`Set wall material to ${e.target.value}`)}>
            <option value="paint">Paint</option>
            <option value="brick">Brick</option>
            <option value="wood_panel">Wood Panel</option>
            <option value="concrete">Concrete</option>
            <option value="wallpaper">Wallpaper</option>
          </select>
        </div>
      </div>

      <div className="control-group">
        <label>Floor Finish</label>
        <div className="control-row">
          <input type="color" defaultValue={currentFloorColor} onBlur={e => handleCommand(`Set floor color to ${e.target.value}`)} />
          <select className="input-base" onChange={e => handleCommand(`Set floor material to ${e.target.value}`)}>
            <option value="wood">Hardwood</option>
            <option value="tile">Tile</option>
            <option value="concrete">Concrete</option>
            <option value="carpet">Carpet</option>
            <option value="marble">Marble</option>
          </select>
        </div>
      </div>
    </div>
  )
}
