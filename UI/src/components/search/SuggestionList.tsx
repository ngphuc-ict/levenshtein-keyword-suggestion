import type { Suggestion } from '../../types'
import './suggestionList.css'

type SuggestionListProps = { suggestions: Suggestion[]; onSelect: (word: string) => void }

export function SuggestionList({ suggestions, onSelect }: SuggestionListProps) {
  if (!suggestions.length) {
    return <div className="suggestion-list"><div className="empty-state">Không tìm thấy từ phù hợp.</div></div>
  }

  return (
    <div className="suggestion-list">
      {suggestions.map((item) => (
        <button className="suggestion-row" key={item.keyword} onClick={() => onSelect(item.keyword)}>
          <span className="suggestion-main"><strong>{item.keyword}</strong></span>
          <span className="distance-value">{item.distance}</span>
        </button>
      ))}
    </div>
  )
}
