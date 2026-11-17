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
      <div className="search-intro"><h1>Tra cứu từ khóa</h1></div>
      <SearchBox query={query} onQueryChange={onQueryChange} onSearch={onSearch} />
      <div className="results-heading">
        <h2>{selectedWord ? 'Kết quả' : 'Gợi ý'}</h2>
        <span>{selectedWord ? 'Từ khóa đã chọn' : 'Khoảng cách chỉnh sửa'}</span>
      </div>
      {loading && <div className="request-status">Đang tìm...</div>}
      {error && <div className="request-error" role="alert">{error}</div>}
      {!loading && !error && (selectedWord ? <WordDefinition word={selectedWord} /> : <SuggestionList suggestions={suggestions} onSelect={onSelectWord} />)}
      <div className="search-explainer"><span aria-hidden="true">a → b</span><p><strong>Mỗi thay đổi, một khoảng cách.</strong> Chèn, xóa hoặc thay một ký tự được tính là một phép chỉnh sửa. Khoảng cách càng nhỏ, từ càng gần.</p></div>
      <div className="search-radar" aria-hidden="true">
        <div className="radar-screen">
          <span className="radar-sweep" />
          <span className="radar-center" />
          <span className="radar-dot radar-dot-one" />
          <span className="radar-dot radar-dot-two" />
          <span className="radar-dot radar-dot-three" />
          <span className="radar-dot radar-dot-four" />
          <span className="radar-dot radar-dot-five" />
          <span className="radar-dot radar-dot-six" />
          <span className="radar-dot radar-dot-seven" />
          <span className="radar-dot radar-dot-eight" />
          <span className="radar-dot radar-dot-nine" />
          <span className="radar-dot radar-dot-ten" />
          <span className="radar-dot radar-dot-eleven" />
          <span className="radar-dot radar-dot-twelve" />
          <span className="radar-dot radar-dot-thirteen" />
          <span className="radar-dot radar-dot-fourteen" />
          <span className="radar-dot radar-dot-fifteen" />
        </div>
      </div>
    </section>
  )
}
