import './wordDefinition.css'

type WordDefinitionProps = { word: string }

export function WordDefinition({ word }: WordDefinitionProps) {
  return (
    <article className="definition-card">
      <h3>{word}</h3>
    </article>
  )
}
