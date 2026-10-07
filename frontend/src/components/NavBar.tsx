interface Props {
  currentPath: string
}

export function NavBar({ currentPath }: Props) {
  const nav = [
    { href: '/chat', label: 'Chat' },
    { href: '/dashboards', label: 'Tableaux de bord' },
    { href: '/upload', label: 'Importer' },
  ]

  const handleLogout = () => {
    sessionStorage.removeItem('sovereign_api_key')
    window.location.href = '/login'
  }

  return (
    <nav
      data-testid="navbar"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        padding: '10px 20px',
        background: '#1e40af',
        color: '#fff',
      }}
    >
      <strong style={{ marginRight: '16px' }}>SovereignBI</strong>
      {nav.map(({ href, label }) => (
        <a
          key={href}
          href={href}
          style={{
            color: currentPath === href ? '#bfdbfe' : '#fff',
            textDecoration: 'none',
            fontWeight: currentPath === href ? 700 : 400,
          }}
        >
          {label}
        </a>
      ))}
      <button
        onClick={handleLogout}
        style={{ marginLeft: 'auto', background: 'transparent', color: '#fff', border: '1px solid #93c5fd', borderRadius: '4px', padding: '4px 10px', cursor: 'pointer' }}
      >
        Déconnexion
      </button>
    </nav>
  )
}
