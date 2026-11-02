import './placeholderPage.css'

type PlaceholderPageProps = { pageName: string; onBack: () => void }

export function PlaceholderPage({ pageName, onBack }: PlaceholderPageProps) {
  return (
    <section className="content placeholder-content">
      <h1>{pageName}</h1>
      <div className="coming-card"><button onClick={onBack}>Quay lại</button></div>
    </section>
  )
}
