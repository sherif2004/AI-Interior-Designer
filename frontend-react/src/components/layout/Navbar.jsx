import React, { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { checkLLMStatus } from '../../api/client'

export default function Navbar() {
  const location = useLocation()
  const [llmOk, setLlmOk] = useState(false)

  useEffect(() => {
    checkLLMStatus().then(res => setLlmOk(res.connected)).catch(() => setLlmOk(false))
  }, [])

  return (
    <nav style={{
      height: 'var(--topbar-h)',
      display: 'flex',
      alignItems: 'center',
      padding: '0 24px',
      background: 'rgba(11, 17, 32, 0.9)',
      borderBottom: '1px solid var(--saas-border)',
      justifyContent: 'space-between',
      backdropFilter: 'blur(10px)'
    }}>
      <div style={{ display: 'flex', gap: '32px', alignItems: 'center' }}>
        <div style={{ fontSize: '18px', fontWeight: 'bold', color: 'white' }}>
          🏠 AI Interior Design
        </div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <NavLink to="/" current={location.pathname}>Home</NavLink>
          <NavLink to="/editor" current={location.pathname}>Editor</NavLink>
          <NavLink to="/catalog" current={location.pathname}>Catalog</NavLink>
          <NavLink to="/projects" current={location.pathname}>Projects</NavLink>
        </div>
      </div>
      
      <div style={{ display: 'flex', gap: '16px', alignItems: 'center', fontSize: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ 
            width: 8, height: 8, borderRadius: '50%', 
            background: llmOk ? 'var(--emerald)' : 'var(--rose)' 
          }} />
          <span style={{ color: 'var(--text-muted)' }}>{llmOk ? 'LLM Connected' : 'LLM Offline'}</span>
        </div>
      </div>
    </nav>
  )
}

function NavLink({ to, current, children }) {
  const active = current === to
  return (
    <Link to={to} style={{
      color: active ? 'var(--text-main)' : 'var(--text-muted)',
      fontWeight: active ? 600 : 400,
      textDecoration: 'none'
    }}>
      {children}
    </Link>
  )
}
