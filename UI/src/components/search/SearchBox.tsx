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
      <label className="search-label" htmlFor="keyword-search">Bạn muốn tìm từ nào?</label>
      <div className="search-input-wrap">
        <input id="keyword-search" aria-label="Tìm từ" value={query} onChange={(event) => onQueryChange(event.target.value)} onKeyDown={handleKeyDown} placeholder="Nhập từ cần tìm..." />
        <button className="search-submit" onClick={onSearch}>Tìm kiếm <span aria-hidden="true">↗</span></button>
      </div>
    </div>
  )
}
