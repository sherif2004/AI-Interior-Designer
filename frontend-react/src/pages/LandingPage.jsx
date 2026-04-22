import React from 'react'
import { Link } from 'react-router-dom'

export default function LandingPage() {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '0 24px' }}>
      <h1 style={{ fontSize: '48px', marginBottom: '24px', background: 'linear-gradient(to right, #6366f1, #22d3ee)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
        AI Interior Design Platform
      </h1>
      <p style={{ fontSize: '18px', color: 'var(--text-muted)', maxWidth: '600px', marginBottom: '40px', lineHeight: 1.6 }}>
        Design your dream space in real-time. Use natural language commands to place life-size IKEA 3D models, edit dimensions, and visualize your ideas.
      </p>
      
      <div style={{ display: 'flex', gap: '16px' }}>
        <Link to="/editor" className="btn btn-primary" style={{ padding: '16px 32px', fontSize: '16px' }}>
          Start Designing
        </Link>
        <Link to="/catalog" className="btn btn-outline" style={{ padding: '16px 32px', fontSize: '16px' }}>
          Browse Catalog
        </Link>
      </div>

      <div style={{ display: 'flex', gap: '32px', marginTop: '80px' }}>
        <FeatureCard icon="🤖" title="AI Architect" desc="Chat to edit your room instantly." />
        <FeatureCard icon="🪑" title="IKEA 3D Assets" desc="Place real 3D models from the catalog." />
        <FeatureCard icon="📐" title="Precision Control" desc="Adjust walls, floors, and shapes manually." />
      </div>
    </div>
  )
}

function FeatureCard({ icon, title, desc }) {
  return (
    <div style={{ background: 'var(--saas-surface)', padding: '24px', borderRadius: '16px', border: '1px solid var(--saas-border)', width: '250px' }}>
      <div style={{ fontSize: '32px', marginBottom: '16px' }}>{icon}</div>
      <h3 style={{ fontSize: '18px', marginBottom: '8px' }}>{title}</h3>
      <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: 1.5 }}>{desc}</p>
    </div>
  )
}
