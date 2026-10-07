import { useState } from 'react'

export function LoginPage() {
  const [key, setKey] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!key.trim()) { setError('Veuillez saisir une clé API.'); return }
    sessionStorage.setItem('sovereign_api_key', key.trim())
    window.location.href = '/chat'
  }

  return (
    <div style={{ maxWidth: '360px', margin: '80px auto', padding: '24px', border: '1px solid #e5e7eb', borderRadius: '8px' }}>
      <h1 style={{ fontSize: '1.4rem', marginBottom: '16px' }}>SovereignBI — Connexion</h1>
      <form onSubmit={handleSubmit}>
        <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem' }}>
          Clé API
          <input
            type="password"
            value={key}
            onChange={e => setKey(e.target.value)}
            placeholder="sk-..."
            style={{ display: 'block', width: '100%', padding: '8px', marginTop: '4px', border: '1px solid #d1d5db', borderRadius: '4px', boxSizing: 'border-box' }}
            autoFocus
          />
        </label>
        {error && <p style={{ color: '#dc2626', fontSize: '0.85rem' }}>{error}</p>}
        <button
          type="submit"
          style={{ width: '100%', padding: '10px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}
        >
          Connexion
        </button>
      </form>
    </div>
  )
}
