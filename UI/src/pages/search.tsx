import { useState } from "react";
import {
  fetchSuggestions,
  searchWord,
  type Suggestion,
  type SearchResponse,
} from "../services/searchService.tsx";


export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Gợi ý từ khóa
  async function handleSuggest(value: string) {
    setQuery(value);
    setResult(null);
    setError("");

    if (!value.trim()) {
      setSuggestions([]);
      return;
    }

    try {
      setLoading(true);

      const data = await fetchSuggestions(value);
      setSuggestions(data.suggestions);
    } catch {
      setError("Không thể kết nối đến máy chủ.");
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  }

  // Tìm kiếm chính thức
  async function handleSearch(value = query) {
    if (!value.trim()) return;

    try {
      setLoading(true);
      setError("");

      const data = await searchWord(value);
      setResult(data);
      setSuggestions([]);
    } catch {
      setError("Tìm kiếm thất bại.");
    } finally {
      setLoading(false);
    }
  }

  // Chọn một từ gợi ý
  function handleSelectSuggestion(word: string) {
    setQuery(word);
    setSuggestions([]);
    handleSearch(word);
  }
  
  return (
    <div>
      <input
        value={query}
        onChange={(e) => handleSuggest(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSearch();
        }}
        placeholder="Nhập từ khóa..."
      />

      {loading && <p>Đang xử lý...</p>}
      {error && <p>{error}</p>}

      {suggestions.map((item) => (
        <div
          key={item.word}
          onClick={() => handleSelectSuggestion(item.word)}
        >
          <span>{item.word}</span>
          <span>Distance: {item.distance}</span>
        </div>
      ))}

      {result && (
        <div>
          <h3>{result.message}</h3>
          {result.found && <p>{result.word}</p>}
        </div>
      )}
    </div>
  );
}