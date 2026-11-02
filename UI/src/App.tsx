import { useMemo, useState } from 'react'
import './styles/app.css'
import { Sidebar } from './components/layout/Sidebar'
import { SearchPage } from './components/search/SearchPage'
import { PlaceholderPage } from './components/common/PlaceholderPage'
import { sampleWords } from './data/sampleWords'
import { findSuggestions } from './utils/levenshtein'
import type { NavigationItem, Word } from './types'

const navigation: NavigationItem[] = [
  { label: 'Tìm kiếm' },
  { label: 'Từ điển' },
  { label: 'Hiệu năng' },
]

function App() {
  const [activePage, setActivePage] = useState('Tìm kiếm')
  const [query, setQuery] = useState('algoritm')
  const [selectedWord, setSelectedWord] = useState<Word | null>(null)

  const suggestions = useMemo(() => findSuggestions(query, sampleWords), [query])

  function selectWord(word: Word) {
    setQuery(word.word)
    setSelectedWord(word)
  }

  function submitSearch() {
    const exactMatch = sampleWords.find((word) => word.word.toLowerCase() === query.trim().toLowerCase())
    if (exactMatch) selectWord(exactMatch)
    else if (suggestions[0]) selectWord(suggestions[0])
  }

  function updateQuery(value: string) {
    setQuery(value)
    setSelectedWord(null)
  }

  return (
    <div className="app-shell">
      <Sidebar items={navigation} activePage={activePage} onNavigate={setActivePage} />
      <main className="main-area">
        {activePage === 'Tìm kiếm' ? (
          <SearchPage
            query={query}
            selectedWord={selectedWord}
            suggestions={suggestions}
            onQueryChange={updateQuery}
            onSearch={submitSearch}
            onSelectWord={selectWord}
          />
        ) : (
          <PlaceholderPage pageName={activePage} onBack={() => setActivePage('Tìm kiếm')} />
        )}
      </main>
    </div>
  )
}

export default App
