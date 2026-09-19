import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { IconContext } from '@phosphor-icons/react'
import './index.css'
import App from './App.jsx'
import { ContentPreferenceProvider } from './contentPreference.jsx'
import { LangProvider } from './LangProvider.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <IconContext.Provider value={{ weight: 'regular', mirrored: false }}>
      <LangProvider>
        <ContentPreferenceProvider>
          <App />
        </ContentPreferenceProvider>
      </LangProvider>
    </IconContext.Provider>
  </StrictMode>,
)
