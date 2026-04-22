import React from 'react'
import ThreeCanvas from '../components/editor/ThreeCanvas'
import RoomControls from '../components/editor/RoomControls'
import RightPanel from '../components/editor/RightPanel'
import ChatCommandBar from '../components/editor/ChatCommandBar'
import '../styles/editor.css'

export default function EditorPage() {
  return (
    <div className="editor-layout">
      <RoomControls />
      <div style={{ flex: 1, position: 'relative', display: 'flex', flexDirection: 'column' }}>
        <ThreeCanvas />
        <ChatCommandBar />
      </div>
      <RightPanel />
    </div>
  )
}
