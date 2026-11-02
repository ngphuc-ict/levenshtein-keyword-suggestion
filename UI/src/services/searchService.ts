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
