import type { Suggestion, Word } from '../types'

export function levenshteinDistance(source: string, target: string): number {
  const row = Array.from({ length: target.length + 1 }, (_, index) => index)

  for (let sourceIndex = 1; sourceIndex <= source.length; sourceIndex += 1) {
    let diagonal = row[0]
    row[0] = sourceIndex

    for (let targetIndex = 1; targetIndex <= target.length; targetIndex += 1) {
      const above = row[targetIndex]
      const substitutionCost = source[sourceIndex - 1] === target[targetIndex - 1] ? 0 : 1
      row[targetIndex] = Math.min(row[targetIndex] + 1, row[targetIndex - 1] + 1, diagonal + substitutionCost)
      diagonal = above
    }
  }

  return row[target.length]
}

export function findSuggestions(query: string, words: Word[], limit = 5): Suggestion[] {
  const normalizedQuery = query.trim().toLowerCase()
  if (!normalizedQuery) return []

  return words
    .map((word) => ({ ...word, distance: levenshteinDistance(normalizedQuery, word.word) }))
    .filter((word) => word.distance <= 4)
    .sort((first, second) => first.distance - second.distance || first.word.localeCompare(second.word))
    .slice(0, limit)
}
