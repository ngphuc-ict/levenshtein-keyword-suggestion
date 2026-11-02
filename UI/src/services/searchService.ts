import type { Suggestion } from '../types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

type SuggestionResponse = {
  query: string
  suggestions: Suggestion[]
  count: number
}

type SearchResponse = {
  query: string
  total: number
  count: number
  items: Array<{
    keyword: string
    length: number
    match_index: number
  }>
}

export type DictionaryEntry = { keyword: string; length: number }
export type DictionaryPageResponse = {
  total: number
  page: number
  page_size: number
  pages: number
  count: number
  items: DictionaryEntry[]
}

export type DictionaryStats = {
  dictionary: {
    size: number
    min_length: number
    max_length: number
    average_length: number
    distinct_lengths: number
    source: string
    load_ms: number
  }
  algorithm: {
    name: string
    distance: string
    candidate_filter: string
    bounded_distance: string
    default_limit: number
    max_limit: number
  }
  cache: {
    capacity: number
    size: number
    hits: number
    misses: number
    evictions: number
    hit_rate: number
  }
  uptime_seconds: number
}

export type BenchmarkRun = {
  run_id: string
  status: string
  created_at: string
  duration_ms: number
  limit: number
  repeats: number
  include_baseline: boolean
  query_count: number
  summary: Record<string, number | null>
  results: Array<{
    query: string
    took_ms: number
    candidates: number
    suggestions: Suggestion[]
    baseline_ms: number | null
    matches_baseline: boolean | null
  }>
}

export type DistanceResult = {
  source: string
  target: string
  normalized_source: string
  normalized_target: string
  distance: number
  raw_distance: number
  source_length: number
  target_length: number
}

export type VisualizeResult = {
  source: string
  target: string
  normalized_source: string
  normalized_target: string
  distance: number
  rows: number
  columns: number
  matrix: number[][]
  row_labels: string[]
  column_labels: string[]
  path: Array<{
    row: number
    column: number
    operation: string
    source_char: string
    target_char: string
    value: number
  }>
}

async function readJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`, { signal })

  if (!response.ok) {
    let message = `API trả về lỗi ${response.status}.`
    try {
      const body = await response.json() as { message?: string; detail?: string }
      message = body.message ?? body.detail ?? message
    } catch {
      // Keep the status based message when the server response is not JSON.
    }
    throw new Error(message)
  }

  return response.json() as Promise<T>
}

export async function fetchSuggestions(query: string, signal?: AbortSignal): Promise<Suggestion[]> {
  const params = new URLSearchParams({ q: query, limit: '5' })
  const response = await readJson<SuggestionResponse>(`/search/suggest?${params.toString()}`, signal)
  return response.suggestions
}

export async function searchKeywords(query: string, signal?: AbortSignal): Promise<Suggestion[]> {
  const params = new URLSearchParams({ q: query, limit: '20', mode: 'contains' })
  const response = await readJson<SearchResponse>(`/search?${params.toString()}`, signal)
  return response.items.map((item) => ({ keyword: item.keyword, distance: 0 }))
}

export async function fetchDictionary(
  query: string,
  page: number,
  pageSize = 50,
  sort: 'alphabet' | 'length' = 'alphabet',
  signal?: AbortSignal,
): Promise<DictionaryPageResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize), sort })
  if (query.trim()) params.set('q', query.trim())
  return readJson<DictionaryPageResponse>(`/dictionary?${params.toString()}`, signal)
}

export async function fetchDictionaryStats(signal?: AbortSignal): Promise<DictionaryStats> {
  return readJson<DictionaryStats>('/dictionary/stats', signal)
}

export async function createBenchmarkRun(includeBaseline: boolean): Promise<BenchmarkRun> {
  const response = await fetch(`${API_BASE_URL}/benchmark/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ include_baseline: includeBaseline }),
  })
  if (!response.ok) {
    let message = `API trả về lỗi ${response.status}.`
    try {
      const body = await response.json() as { message?: string; detail?: string }
      message = body.message ?? body.detail ?? message
    } catch {
      // Keep the status based message when the server response is not JSON.
    }
    throw new Error(message)
  }
  return response.json() as Promise<BenchmarkRun>
}

export async function getBenchmarkRun(runId: string): Promise<BenchmarkRun> {
  return readJson<BenchmarkRun>(`/benchmark/runs/${encodeURIComponent(runId)}`)
}

export async function getEditDistance(source: string, target: string, normalize = true): Promise<DistanceResult> {
  const params = new URLSearchParams({ source, target, normalize: String(normalize) })
  return readJson<DistanceResult>(`/algorithm/distance?${params.toString()}`)
}

export async function visualizeDistance(source: string, target: string, normalize = true): Promise<VisualizeResult> {
  const response = await fetch(`${API_BASE_URL}/algorithm/visualize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, target, normalize }),
  })
  if (!response.ok) {
    let message = `API trả về lỗi ${response.status}.`
    try {
      const body = await response.json() as { message?: string; detail?: string }
      message = body.message ?? body.detail ?? message
    } catch {
      // Keep the status based message when the server response is not JSON.
    }
    throw new Error(message)
  }
  return response.json() as Promise<VisualizeResult>
}

export function benchmarkExportUrl(runId: string) {
  return `${API_BASE_URL}/benchmark/runs/${encodeURIComponent(runId)}/export`
}
