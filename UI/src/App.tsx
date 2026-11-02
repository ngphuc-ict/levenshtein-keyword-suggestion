import { useEffect, useRef, useState } from 'react'
import './styles/app.css'
import { Sidebar } from './components/layout/Sidebar'
import { SearchPage } from './components/search/SearchPage'
import { DictionaryPage } from './components/dictionary/DictionaryPage'
import { PerformancePage } from './components/performance/PerformancePage'
import { AlgorithmPage } from './components/algorithm/AlgorithmPage'
import { fetchSuggestions, searchKeywords } from './services/searchService'
import type { NavigationItem, Suggestion } from './types'

const navigation: NavigationItem[] = [
  { label: 'Tìm kiếm' },
  { label: 'Từ điển' },
  { label: 'Hiệu năng' },
  { label: 'Thuật toán' },
]

function App() {
  const [activePage, setActivePage] = useState('Tìm kiếm')
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [selectedWord, setSelectedWord] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const requestSequence = useRef(0)

  useEffect(() => {
    const value = query.trim()
    if (!value) {
      setSuggestions([])
      setLoading(false)
      setError('')
      return
    }

    const requestId = ++requestSequence.current
    const controller = new AbortController()
    const timeout = window.setTimeout(async () => {
      setLoading(true)
      setError('')
      try {
        const nextSuggestions = await fetchSuggestions(value, controller.signal)
        if (requestSequence.current === requestId) setSuggestions(nextSuggestions)
      } catch (requestError) {
        if (!controller.signal.aborted && requestSequence.current === requestId) {
          setError(apiErrorMessage(requestError))
          setSuggestions([])
        }
      } finally {
        if (!controller.signal.aborted && requestSequence.current === requestId) setLoading(false)
      }
    }, 250)

    return () => {
      window.clearTimeout(timeout)
      controller.abort()
      if (requestSequence.current === requestId) requestSequence.current += 1
    }
  }, [query])

  async function submitSearch() {
    const value = query.trim()
    if (!value) return

    const requestId = ++requestSequence.current
    setLoading(true)
    setError('')
    setSelectedWord(null)
    try {
      const exactResults = await searchKeywords(value)
      if (requestSequence.current !== requestId) return
      if (exactResults.length) {
        setSuggestions(exactResults)
      } else {
        const fuzzyResults = await fetchSuggestions(value)
        if (requestSequence.current === requestId) setSuggestions(fuzzyResults)
      }
    } catch (requestError) {
      if (requestSequence.current === requestId) {
        setError(apiErrorMessage(requestError))
        setSuggestions([])
      }
    } finally {
      if (requestSequence.current === requestId) setLoading(false)
    }
  }

  function updateQuery(value: string) {
    setQuery(value)
    setSelectedWord(null)
    setError('')
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
            loading={loading}
            error={error}
            onQueryChange={updateQuery}
            onSearch={submitSearch}
            onSelectWord={setSelectedWord}
          />
        ) : activePage === 'Từ điển' ? <DictionaryPage /> : activePage === 'Hiệu năng' ? <PerformancePage /> : <AlgorithmPage />}
      </main>
    </div>
  )
}

export default App

function apiErrorMessage(error: unknown) {
  if (error instanceof TypeError) return 'Không kết nối được backend tại 127.0.0.1:8000.'
  return error instanceof Error ? error.message : 'Không thể kết nối backend.'
}
