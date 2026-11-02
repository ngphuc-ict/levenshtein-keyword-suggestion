import type { KeyboardEvent } from 'react'
import './searchBox.css'

type SearchBoxProps = {
  query: string
  onQueryChange: (value: string) => void
  onSearch: () => void
}

export function SearchBox({ query, onQueryChange, onSearch }: SearchBoxProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter') onSearch()
  }

  return (
    <div className="search-panel">
      <div className="search-input-wrap">
        <input aria-label="Tìm từ" value={query} onChange={(event) => onQueryChange(event.target.value)} onKeyDown={handleKeyDown} placeholder="Nhập từ cần tìm..." />
        <button className="search-submit" onClick={onSearch}>Tìm</button>
      </div>
    </div>
  )
}
