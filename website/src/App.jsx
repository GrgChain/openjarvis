import { useState, useEffect, useCallback } from 'react'
import { api } from './api.js'
import { LeftSidebar } from './components/LeftSidebar.jsx'
import { RightSidebar } from './components/RightSidebar.jsx'
import { ChatPanel } from './components/panels/ChatPanel.jsx'
import './styles/global.css'
import './styles/layout.css'
import './styles/chat.css'
import './styles/crons.css'
import './styles/left-sidebar.css'
import './styles/right-sidebar.css'

const WEB_KEY = 'web'
const POLL_MS = 30_000

export function App() {
  const [selectedKey, setSelectedKey] = useState(WEB_KEY)
  const [online, setOnline] = useState(null)
  const [refreshSig, setRefreshSig] = useState(0)

  const checkHealth = useCallback(async () => {
    try { await api.health(); setOnline(true) }
    catch { setOnline(false) }
  }, [])

  useEffect(() => {
    checkHealth()
    const id = setInterval(checkHealth, POLL_MS)
    return () => clearInterval(id)
  }, [checkHealth])

  const handleNewChat = () => setSelectedKey(WEB_KEY)
  const handleSessionsRefresh = () => setRefreshSig(s => s + 1)

  return (
    <div className="app-three-col">
      <LeftSidebar
        selectedKey={selectedKey}
        onSelect={setSelectedKey}
        onNewChat={handleNewChat}
        online={online}
        refreshSig={refreshSig}
      />
      <ChatPanel
        selectedKey={selectedKey}
        onSessionsRefresh={handleSessionsRefresh}
      />
      <RightSidebar />
    </div>
  )
}
