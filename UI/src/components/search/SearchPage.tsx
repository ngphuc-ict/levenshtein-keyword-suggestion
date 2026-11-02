import type { Suggestion, Word } from '../../types'
import { SearchBox } from './SearchBox'
import { SuggestionList } from './SuggestionList'
import { WordDefinition } from './WordDefinition'
import './searchPage.css'

type SearchPageProps = {
  query: string
  selectedWord: Word | null
  suggestions: Suggestion[]
  onQueryChange: (value: string) => void
  onSearch: () => void
  onSelectWord: (word: Word) => void
}

export function SearchPage({ query, selectedWord, suggestions, onQueryChange, onSearch, onSelectWord }: SearchPageProps) {
  return (
    <section className="content search-content">
      <h1>Tìm từ</h1>
      <SearchBox query={query} onQueryChange={onQueryChange} onSearch={onSearch} />
      <div className="results-heading">
        <h2>{selectedWord ? 'Kết quả' : 'Gợi ý'}</h2>
      </div>
      {selectedWord ? <WordDefinition word={selectedWord} /> : <SuggestionList suggestions={suggestions} onSelect={onSelectWord} />}
    </section>
  )
}
