import { useEffect, useState } from 'react'
import { benchmarkExportUrl, createBenchmarkRun, fetchDictionaryStats, getBenchmarkRun } from '../../services/searchService'
import type { BenchmarkRun, DictionaryStats } from '../../services/searchService'
import './performancePage.css'

export function PerformancePage() {
  const [stats, setStats] = useState<DictionaryStats | null>(null)
  const [run, setRun] = useState<BenchmarkRun | null>(null)
  const [includeBaseline, setIncludeBaseline] = useState(false)
  const [runId, setRunId] = useState('')
  const [loadingStats, setLoadingStats] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    fetchDictionaryStats()
      .then((data) => { if (active) setStats(data) })
      .catch((requestError: unknown) => { if (active) setError(errorMessage(requestError)) })
      .finally(() => { if (active) setLoadingStats(false) })
    return () => { active = false }
  }, [])

  async function refreshStats() {
    setLoadingStats(true)
    setError('')
    try {
      setStats(await fetchDictionaryStats())
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setLoadingStats(false)
    }
  }

  async function startBenchmark() {
    setRunning(true)
    setError('')
    try {
      const result = await createBenchmarkRun(includeBaseline)
      setRun(result)
      setRunId(result.run_id)
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setRunning(false)
    }
  }

  async function loadBenchmarkRun() {
    const id = runId.trim()
    if (!id) return
    setRunning(true)
    setError('')
    try {
      const result = await getBenchmarkRun(id)
      setRun(result)
      setIncludeBaseline(result.include_baseline)
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setRunning(false)
    }
  }

  return (
    <section className="content performance-page">
      <div className="performance-title"><h1>Hiệu năng</h1><button onClick={refreshStats} disabled={loadingStats}>{loadingStats ? 'Đang tải...' : 'Làm mới'}</button></div>
      {error && <div className="page-error" role="alert">{error}</div>}
      {stats && (
        <>
          <div className="performance-metrics">
            <Metric label="Từ khóa" value={stats.dictionary.size.toLocaleString('vi-VN')} />
            <Metric label="Nạp từ điển" value={`${stats.dictionary.load_ms.toFixed(1)} ms`} />
            <Metric label="Cache hit" value={`${(stats.cache.hit_rate * 100).toFixed(1)}%`} />
            <Metric label="Số từ khóa có trong cache" value={stats.cache.size.toLocaleString('vi-VN')} />
          </div>
          <div className="algorithm-info">
            <strong>{stats.algorithm.name}</strong>
            <span>{stats.algorithm.distance}</span>
            <span>{stats.algorithm.candidate_filter}</span>
          </div>
        </>
      )}

      <div className="benchmark-panel">
        <div className="benchmark-heading"><div><h2>Benchmark</h2><p>Đo thời gian gợi ý trên các truy vấn mẫu của backend.</p></div></div>
        <div className="benchmark-controls">
          <label><input type="checkbox" checked={includeBaseline} onChange={(event) => setIncludeBaseline(event.target.checked)} /> So sánh với bản quét gốc</label>
          <button onClick={startBenchmark} disabled={running}>{running ? 'Đang chạy...' : 'Chạy benchmark'}</button>
        </div>
        <div className="benchmark-lookup">
          <input value={runId} onChange={(event) => setRunId(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') void loadBenchmarkRun() }} placeholder="Nhập run_id để mở kết quả đã lưu" aria-label="Mã lần chạy benchmark" />
          <button onClick={loadBenchmarkRun} disabled={running || !runId.trim()}>{running ? 'Đang tải...' : 'Mở kết quả'}</button>
        </div>
        {run && (
          <div className="benchmark-results">
            <div className="benchmark-run-meta"><span>ID: {run.run_id}</span><a className="benchmark-export" href={benchmarkExportUrl(run.run_id)}>Tải CSV</a></div>
            <div className="benchmark-summary">
              <Metric label="Trung bình" value={`${number(run.summary.mean_ms)} ms`} />
              <Metric label="P50" value={`${number(run.summary.p50_ms)} ms`} />
              <Metric label="P95" value={`${number(run.summary.p95_ms)} ms`} />
              {run.summary.speedup_vs_baseline != null && <Metric label="Nhanh hơn bản gốc" value={`${number(run.summary.speedup_vs_baseline)}×`} />}
            </div>
            <div className="benchmark-table">
              {run.results.map((result) => (
                <div className="benchmark-row" key={result.query}>
                  <span className="benchmark-query">{result.query}</span>
                  <span>{number(result.took_ms)} ms</span>
                  <span>{result.candidates.toLocaleString('vi-VN')} ứng viên</span>
                  <span className="benchmark-suggestions" title={result.suggestions.map((item) => item.keyword).join(', ')}>{result.suggestions.slice(0, 3).map((item) => item.keyword).join(', ')}</span>
                  {result.matches_baseline !== null && <span className="benchmark-match">{result.matches_baseline ? 'Khớp' : 'Lệch'}</span>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric-card"><span>{label}</span><strong>{value}</strong></div>
}

function number(value: number | null | undefined) {
  return value == null ? '—' : value.toFixed(2)
}

function errorMessage(error: unknown) {
  if (error instanceof TypeError) return 'Không kết nối được backend tại 127.0.0.1:8000.'
  return error instanceof Error ? error.message : 'Không thể tải dữ liệu hiệu năng.'
}
