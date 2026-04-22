import React, { useState, useEffect } from 'react'
import { getVersions, deleteVersion, sendCommand } from '../api/client'

export default function ProjectsPage() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchProjects = async () => {
    setLoading(true)
    try {
      const res = await getVersions()
      setProjects(res.versions || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  const handleLoad = async (id) => {
    try {
      await sendCommand(`Load version ${id}`)
      // In a real app, we might redirect to /editor here
      window.location.href = '/editor'
    } catch (e) {
      console.error(e)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this project?')) return
    try {
      await deleteVersion(id)
      fetchProjects()
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div style={{ padding: '32px', maxWidth: '800px', margin: '0 auto', flex: 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px' }}>
        <h2>Saved Projects</h2>
        <button className="btn btn-outline" onClick={fetchProjects}>Refresh</button>
      </div>

      {loading ? (
        <p>Loading projects...</p>
      ) : projects.length === 0 ? (
        <p style={{ color: 'var(--text-muted)' }}>No saved projects yet. Go to the Editor and say "Save version MyProject".</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {projects.map(p => (
            <div key={p.id} style={{ background: 'var(--saas-surface)', border: '1px solid var(--saas-border)', padding: '16px', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ fontSize: '16px', marginBottom: '4px' }}>{p.name}</h3>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{new Date(p.created_at * 1000).toLocaleString()}</span>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn btn-primary" onClick={() => handleLoad(p.id)}>Load</button>
                <button className="btn btn-danger" onClick={() => handleDelete(p.id)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
