const API_BASE_URL = "http://localhost:8000/api/v1";
"sửa API sau"

export interface Suggestion {
  word: string;
  distance: number;
}

export interface SuggestResponse {
  query: string;
  suggestions: Suggestion[];
  count: number;
}

export interface SearchResponse {
  query: string;
  found: boolean;
  word?: string;
  suggestions?: Suggestion[];
  message: string;
}

/**
 * Gọi API lấy danh sách từ gợi ý
 */
export async function fetchSuggestions(
  query: string,
  limit: number = 5,
  maxDistance: number = 2
): Promise<SuggestResponse> {
  const params = new URLSearchParams({
    q: query,
    limit: String(limit),
    max_distance: String(maxDistance),
  });

  const response = await fetch(
    `${API_BASE_URL}/search/suggest?${params.toString()}`
  );

  if (!response.ok) {
    throw new Error(`Search API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Gọi API tìm kiếm từ khóa chính thức
 */
export async function searchWord(
  query: string
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query });

  const response = await fetch(
    `${API_BASE_URL}/search?${params.toString()}`
  );

  if (!response.ok) {
    throw new Error(`Search API error: ${response.status}`);
  }

  return response.json();
}