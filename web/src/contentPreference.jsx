/* eslint-disable react-refresh/only-export-components -- shared module: constants + helpers + provider live together by design */
import { createContext, useCallback, useContext, useMemo, useState } from 'react'

export const CONTENT_STORAGE_KEY = 'open-image-prompts-content'
export const CONTENT_MODES = ['blur', 'show', 'hide']

// Ratings come from the offline classifier pass (data/content-ratings.jsonl):
// 'sfw' never gates, 'borderline' and 'nsfw' do. Unrated (null) stays visible
// so a partial rating pass degrades to fewer gated images, never to a blank wall.
export function isGated(rating) {
  return rating === 'borderline' || rating === 'nsfw'
}

export function normalizeContentMode(value) {
  return CONTENT_MODES.includes(value) ? value : 'blur'
}

function readStoredMode() {
  try {
    return normalizeContentMode(localStorage.getItem(CONTENT_STORAGE_KEY))
  } catch {
    return 'blur'
  }
}

export const ContentPreferenceContext = createContext(null)

export function ContentPreferenceProvider({ children }) {
  const [mode, setModeState] = useState(readStoredMode)

  const setMode = useCallback((next) => {
    const normalized = normalizeContentMode(next)
    setModeState(normalized)
    try {
      localStorage.setItem(CONTENT_STORAGE_KEY, normalized)
    } catch {
      // storage unavailable (private mode) — session-only preference
    }
  }, [])

  const value = useMemo(() => ({ mode, setMode }), [mode, setMode])

  return (
    <ContentPreferenceContext.Provider value={value}>{children}</ContentPreferenceContext.Provider>
  )
}

export function useContentPreference() {
  const context = useContext(ContentPreferenceContext)
  if (!context) throw new Error('useContentPreference must be used within ContentPreferenceProvider')
  return context
}
