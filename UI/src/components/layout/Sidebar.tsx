import type { NavigationItem } from '../../types'
import './sidebar.css'

type SidebarProps = {
  items: NavigationItem[]
  activePage: string
  onNavigate: (page: string) => void
}

export function Sidebar({ items, activePage, onNavigate }: SidebarProps) {
  return (
    <aside className="sidebar">
      <nav className="main-nav" aria-label="Main navigation">
        {items.map((item) => (
          <button key={item.label} className={`nav-item ${activePage === item.label ? 'active' : ''}`} onClick={() => onNavigate(item.label)}>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  )
}
