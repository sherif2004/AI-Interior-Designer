import React, { useState } from 'react'
import { sendCommand } from '../../api/client'

export default function ChatCommandBar() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim()) return
    const cmd = input
    setInput('')
    setLoading(true)
    try {
      await sendCommand(cmd)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="ai-prompt-bar">
      <div style={{ padding: '8px', fontSize: '18px' }}>✨</div>
      <form onSubmit={handleSubmit} style={{ flex: 1, display: 'flex' }}>
        <input 
          type="text" 
          className="ai-input" 
          placeholder="Ask AI to design, add furniture, or modify layout..." 
          value={input}
          onChange={e => setInput(e.target.value)}
          disabled={loading}
          autoFocus
        />
        <button type="submit" className="btn btn-primary" style={{ border: 'none', background: 'transparent' }} disabled={loading}>
          {loading ? '⏳' : '↳'}
        </button>
      </form>
    </div>
  )
}
