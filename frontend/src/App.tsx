import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { api } from './api'
import CasesPage from './pages/CasesPage'
import WorkspacePage from './pages/WorkspacePage'
import LoginPage from './pages/LoginPage'
import KnowledgePage from './pages/KnowledgePage'
import SettingsPage from './pages/SettingsPage'
import { AuthStatus, DemoModeProvider } from './demoMode'

function Protected({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<'loading' | 'allowed' | 'login'>('loading')
  const [status, setStatus] = useState<AuthStatus | null>(null)
  const location = useLocation()
  useEffect(() => {
    api.authStatus().then(async status => {
      setStatus(status)
      if (!status.login_required) return setState('allowed')
      if (!localStorage.getItem('lcc_token')) return setState('login')
      try { await api.me(); setState('allowed') } catch { localStorage.removeItem('lcc_token'); setState('login') }
    }).catch(() => setState('allowed'))
  }, [])
  if (state === 'loading') return <div className="loading-screen">正在检查工作空间…</div>
  if (state === 'login') return <Navigate to="/login" state={{ from: location.pathname }} replace />
  return <DemoModeProvider status={status || { mode: 'disabled', login_required: false, bootstrap_required: false, public_demo: false, read_only: false }}>{children}</DemoModeProvider>
}

export default function App() {
  return <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/" element={<Protected><CasesPage /></Protected>} />
    <Route path="/knowledge" element={<Protected><KnowledgePage /></Protected>} />
    <Route path="/settings" element={<Protected><SettingsPage /></Protected>} />
    <Route path="/cases/:caseId/:section?" element={<Protected><WorkspacePage /></Protected>} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
}
