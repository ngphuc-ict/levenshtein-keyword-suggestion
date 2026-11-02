import type { Suggestion } from '../../types'
import { SearchBox } from './SearchBox'
import { SuggestionList } from './SuggestionList'
import { WordDefinition } from './WordDefinition'
import './searchPage.css'

type SearchPageProps = {
  query: string
  selectedWord: string | null
  suggestions: Suggestion[]
  loading: boolean
  error: string
  onQueryChange: (value: string) => void
  onSearch: () => void
  onSelectWord: (word: string) => void
}

export function SearchPage({ query, selectedWord, suggestions, loading, error, onQueryChange, onSearch, onSelectWord }: SearchPageProps) {
  return (
    <section className="content search-content">
      <h1>Tìm từ</h1>
      <SearchBox query={query} onQueryChange={onQueryChange} onSearch={onSearch} />
      <div className="results-heading">
        <h2>{selectedWord ? 'Kết quả' : 'Gợi ý'}</h2>
      </div>
      {loading && <div className="request-status">Đang tìm...</div>}
      {error && <div className="request-error" role="alert">{error}</div>}
      {!loading && !error && (selectedWord ? <WordDefinition word={selectedWord} /> : <SuggestionList suggestions={suggestions} onSelect={onSelectWord} />)}
    </section>
  )
}
