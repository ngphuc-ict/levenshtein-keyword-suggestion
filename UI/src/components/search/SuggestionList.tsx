import type { Suggestion, Word } from '../../types'
import './suggestionList.css'

type SuggestionListProps = { suggestions: Suggestion[]; onSelect: (word: Word) => void }

export function SuggestionList({ suggestions, onSelect }: SuggestionListProps) {
  if (!suggestions.length) {
    return <div className="suggestion-list"><div className="empty-state">Không tìm thấy từ phù hợp.</div></div>
  }

  return (
    <div className="suggestion-list">
      {suggestions.map((item) => (
        <button className="suggestion-row" key={item.word} onClick={() => onSelect(item)}>
          <span className="suggestion-main"><strong>{item.word}</strong><small>{item.definition}</small></span>
          <span className="distance-value">{item.distance}</span>
        </button>
      ))}
    </div>
  )
}
