import { useState, useEffect } from 'react'
import { createWebSocket, getState } from '../api/client'

export function useRoomState() {
  const [state, setState] = useState(null)
  const [wsStatus, setWsStatus] = useState('connecting')

  useEffect(() => {
    // Initial fetch
    getState().then(setState).catch(console.error)

    // WS sync
    const ws = createWebSocket((msg) => {
      if (msg.type === 'state_update') {
        setState(msg.state)
      }
    })

    ws.addEventListener('open', () => setWsStatus('connected'))
    ws.addEventListener('close', () => setWsStatus('error'))
    ws.addEventListener('error', () => setWsStatus('error'))

    return () => ws.close()
  }, [])

  return { state, wsStatus }
}
