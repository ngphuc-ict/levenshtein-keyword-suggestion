import { useEffect, useState } from 'react'
import { fetchDictionary } from '../../services/searchService'
import type { DictionaryPageResponse } from '../../services/searchService'
import './dictionaryPage.css'

const PAGE_SIZE = 50

export function DictionaryPage() {
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState<'alphabet' | 'length'>('alphabet')
  const [result, setResult] = useState<DictionaryPageResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(async () => {
      setLoading(true)
      setError('')
      try {
        const response = await fetchDictionary(query, page, PAGE_SIZE, sort, controller.signal)
        if (!controller.signal.aborted) setResult(response)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(requestError instanceof Error ? requestError.message : 'Không thể tải từ điển.')
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }, 180)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [query, page, sort])

  function updateQuery(value: string) {
    setQuery(value)
    setPage(1)
  }

  return (
    <section className="content dictionary-page">
      <h1>Từ điển</h1>
      <div className="dictionary-controls">
        <input value={query} onChange={(event) => updateQuery(event.target.value)} placeholder="Lọc từ khóa..." aria-label="Lọc từ khóa" />
        <select value={sort} onChange={(event) => setSort(event.target.value as 'alphabet' | 'length')} aria-label="Sắp xếp từ khóa">
          <option value="alphabet">A–Z</option>
          <option value="length">Theo độ dài</option>
        </select>
      </div>
      {error ? <div className="page-error" role="alert">{error}</div> : (
        <>
          <div className="dictionary-summary">{loading ? 'Đang tải...' : `${result?.total.toLocaleString('vi-VN') ?? 0} từ khóa`}</div>
          <div className="dictionary-list">
            {result?.items.map((item) => <div className="dictionary-row" key={item.keyword}><span>{item.keyword}</span><small>{item.length} ký tự</small></div>)}
            {!loading && result?.count === 0 && <div className="dictionary-empty">Không tìm thấy từ khóa.</div>}
          </div>
          <div className="dictionary-pagination">
            <span>Trang {result?.page ?? page} / {result?.pages ?? 0}</span>
            <div>
              <button disabled={loading || page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Trước</button>
              <button disabled={loading || !result || page >= result.pages} onClick={() => setPage((current) => current + 1)}>Sau</button>
            </div>
          </div>
        </>
      )}
    </section>
  )
}
