import type { Suggestion } from '../../types'
import './suggestionList.css'

type SuggestionListProps = { suggestions: Suggestion[]; onSelect: (word: string) => void }

export function SuggestionList({ suggestions, onSelect }: SuggestionListProps) {
  if (!suggestions.length) {
    return <div className="suggestion-list"><div className="empty-state"><span className="empty-symbol" aria-hidden="true">Aa</span><strong>Chưa có từ phù hợp</strong><p>Nhập hoặc thử đổi từ khóa để xem các gợi ý gần nhất.</p></div></div>
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
