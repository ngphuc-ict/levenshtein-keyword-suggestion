import type { Word } from '../../types'
import './wordDefinition.css'

type WordDefinitionProps = { word: Word }

export function WordDefinition({ word }: WordDefinitionProps) {
  return (
    <article className="definition-card">
      <h3>{word.word}</h3>
      <p className="definition-text">{word.definition}</p>
    </article>
  )
}
