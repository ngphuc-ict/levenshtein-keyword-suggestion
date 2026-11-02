import { useState, type FormEvent } from 'react'
import { getEditDistance, visualizeDistance } from '../../services/searchService'
import type { DistanceResult, VisualizeResult } from '../../services/searchService'
import './algorithmPage.css'

export function AlgorithmPage() {
  const [source, setSource] = useState('kitten')
  const [target, setTarget] = useState('sitting')
  const [normalize, setNormalize] = useState(true)
  const [distance, setDistance] = useState<DistanceResult | null>(null)
  const [visualization, setVisualization] = useState<VisualizeResult | null>(null)
  const [loading, setLoading] = useState<'distance' | 'visualize' | null>(null)
  const [error, setError] = useState('')

  async function calculateDistance(event: FormEvent) {
    event.preventDefault()
    setLoading('distance')
    setError('')
    try {
      setDistance(await getEditDistance(source, target, normalize))
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setLoading(null)
    }
  }

  async function showVisualization() {
    setLoading('visualize')
    setError('')
    try {
      setVisualization(await visualizeDistance(source, target, normalize))
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setLoading(null)
    }
  }

  const pathCells = new Set(visualization?.path.map((step) => `${step.row}-${step.column}`) ?? [])

  return (
    <section className="content algorithm-page">
      <h1>Thuật toán</h1>
      <form className="algorithm-form" onSubmit={calculateDistance}>
        <label>Từ nguồn<input value={source} onChange={(event) => setSource(event.target.value)} maxLength={200} required /></label>
        <label>Từ đích<input value={target} onChange={(event) => setTarget(event.target.value)} maxLength={200} required /></label>
        <label className="normalize-option"><input type="checkbox" checked={normalize} onChange={(event) => setNormalize(event.target.checked)} /> Chuẩn hóa chữ hoa và dấu câu</label>
        <div className="algorithm-actions">
          <button type="submit" disabled={loading !== null}>{loading === 'distance' ? 'Đang tính...' : 'Tính khoảng cách'}</button>
          <button type="button" className="secondary-action" disabled={loading !== null || source.length > 60 || target.length > 60} onClick={showVisualization}>{loading === 'visualize' ? 'Đang dựng bảng...' : 'Dựng bảng DP'}</button>
        </div>
        <small className="visualize-limit">Bảng DP hỗ trợ tối đa 60 ký tự cho mỗi từ.</small>
      </form>

      {error && <div className="page-error" role="alert">{error}</div>}
      {distance && <div className="distance-result"><span>Khoảng cách Levenshtein</span><strong>{distance.distance}</strong><small>Khoảng cách nguyên bản: {distance.raw_distance}</small></div>}
      {visualization && (
        <section className="visualization-result">
          <div className="visualization-heading"><h2>Bảng quy hoạch động</h2><span>Khoảng cách: {visualization.distance}</span></div>
          <div className="matrix-scroll">
            <table className="dp-matrix">
              <thead><tr><th />{visualization.column_labels.map((label, index) => <th key={`column-${index}`}>{label || '∅'}</th>)}</tr></thead>
              <tbody>{visualization.matrix.map((row, rowIndex) => (
                <tr key={`row-${rowIndex}`}>
                  <th>{visualization.row_labels[rowIndex] || '∅'}</th>
                  {row.map((value, columnIndex) => <td className={pathCells.has(`${rowIndex}-${columnIndex}`) ? 'path-cell' : ''} key={`${rowIndex}-${columnIndex}`}>{value}</td>)}
                </tr>
              ))}</tbody>
            </table>
          </div>
          <div className="edit-steps"><strong>Bước biến đổi</strong><div>{visualization.path.map((step, index) => <span className="edit-step" key={`${step.row}-${step.column}-${index}`}>{operationLabel(step.operation)}{step.source_char || step.target_char ? ` (${step.source_char || '∅'} → ${step.target_char || '∅'})` : ''}</span>)}</div></div>
        </section>
      )}
    </section>
  )
}

function operationLabel(operation: string) {
  const labels: Record<string, string> = { match: 'Giữ', substitute: 'Thay', insert: 'Chèn', delete: 'Xóa' }
  return labels[operation] ?? operation
}

function errorMessage(error: unknown) {
  if (error instanceof TypeError) return 'Không kết nối được backend tại 127.0.0.1:8000.'
  return error instanceof Error ? error.message : 'Không thể gọi API thuật toán.'
}
