export type Word = {
  word: string
  definition: string
  category: string
}

export type Suggestion = Word & { distance: number }

export type NavigationItem = {
  label: string
}
