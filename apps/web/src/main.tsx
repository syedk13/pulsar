import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'

// Minimal compile entrypoint only. No Pulsar screens are implemented yet.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <main className="p-6 font-sans">Pulsar web scaffold</main>
  </StrictMode>,
)
