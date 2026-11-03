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
      <div className="sidebar-brand">
        <span className="brand-mark" aria-hidden="true">L<span>·</span></span>
        <div><strong>Levenshtein</strong><span>Keyword explorer</span></div>
      </div>
      <nav className="main-nav" aria-label="Main navigation">
        {items.map((item) => (
          <button key={item.label} className={`nav-item ${activePage === item.label ? 'active' : ''}`} aria-current={activePage === item.label ? 'page' : undefined} onClick={() => onNavigate(item.label)}>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-note"><span className="sidebar-note-rule" /><strong>Gần đúng. Đúng từ.</strong><p>Khám phá khoảng cách giữa những từ ngữ.</p><span className="sidebar-note-meta">Levenshtein distance</span></div>
    </aside>
  )
}
