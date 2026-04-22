import React, { useEffect, useState } from 'react'
import { useRoomState } from '../../hooks/useRoomState'
import { getBudget, selectObject } from '../../api/client'

export default function RightPanel() {
  const { state } = useRoomState()
  const [budget, setBudget] = useState(null)

  useEffect(() => {
    if (state) getBudget().then(setBudget).catch(() => {})
  }, [state])

  const objects = state?.objects || []

  return (
    <div className="right-panel">
      <div className="widget-box">
        <h4>Room Objects</h4>
        {objects.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>No furniture placed yet.</p>
        ) : (
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {objects.map(obj => (
              <li key={obj.id} 
                  style={{ background: 'rgba(255,255,255,0.05)', padding: '8px', borderRadius: '4px', display: 'flex', justifyContent: 'space-between', cursor: 'pointer' }}
                  onClick={() => selectObject(obj.id)}>
                <span style={{ fontSize: 12 }}>{obj.name || obj.type}</span>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{obj.w}x{obj.d}m</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="widget-box">
        <h4>Budget Estimate</h4>
        {budget ? (
          <div>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: 'var(--accent-light)', marginBottom: 8 }}>
              {budget.total_low} - {budget.total_high} EGP
            </div>
            {budget.by_category && Object.entries(budget.by_category).map(([cat, val]) => (
              <div key={cat} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                <span style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>{cat}</span>
                <span>{val.low} - {val.high}</span>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>Add furniture to estimate.</p>
        )}
      </div>
    </div>
  )
}
