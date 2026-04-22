import React, { useEffect, useRef } from 'react'
import { initScene, buildRoom, syncObjects } from '../../three/sceneManager'
import { useRoomState } from '../../hooks/useRoomState'

export default function ThreeCanvas() {
  const containerRef = useRef(null)
  const { state } = useRoomState()

  useEffect(() => {
    if (containerRef.current) {
      // initScene requires a canvas element. We can pass a canvas inside the ref.
      const canvas = containerRef.current.querySelector('canvas')
      initScene(canvas)
    }
  }, [])

  useEffect(() => {
    if (state) {
      buildRoom(state)
      syncObjects(state.objects || [])
    }
  }, [state])

  return (
    <div className="canvas-container" ref={containerRef}>
      <canvas className="three-canvas" id="three-canvas" />
    </div>
  )
}
