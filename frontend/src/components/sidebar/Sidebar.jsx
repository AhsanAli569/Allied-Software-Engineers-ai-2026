import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import ConversationItem from './ConversationItem'
import ThemeToggle from '../ui/ThemeToggle'
import Logo from '../ui/Logo'
import Button from '../ui/Button'
import Footer from '../ui/Footer'

export default function Sidebar({
  conversations,
  activeConversationId,
  search,
  onSearchChange,
  onUpdateConversation,
  onDeleteConversation,
  isOpen,
  onClose,
}) {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [showArchived, setShowArchived] = useState(false)

  // Defensive: if the API ever returns something unexpected (a misconfigured backend URL
  // returning HTML, a transient error, etc.), fail to an empty list instead of crashing
  // the whole sidebar with "conversations.filter is not a function".
  const conversationList = Array.isArray(conversations) ? conversations : []
  const visible = conversationList.filter((c) => (showArchived ? c.archived : !c.archived))

  return (
    <>
      {isOpen && <div className="fixed inset-0 z-30 bg-black/30 md:hidden" onClick={onClose} />}
      {/* The sidebar is always Midnight Navy, independent of the light/dark toggle — a
          fixed brand element, like a permanent dark nav rail. */}
      <aside
        className={`fixed z-40 flex h-full w-72 flex-col bg-navy text-slate-100 transition-transform md:static md:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center gap-2 px-4 py-4">
          <Logo size={32} />
          <div className="min-w-0 leading-tight">
            <p className="truncate text-sm font-semibold text-white">Allied Software Engineers</p>
            <p className="text-xs text-slate-400">ASE AI</p>
          </div>
        </div>

        <div className="px-3">
          <Button
            variant="primary"
            className="w-full justify-start"
            onClick={() => {
              navigate('/chat')
              onClose?.()
            }}
          >
            + New chat
          </Button>
        </div>

        <div className="px-3 pt-3">
          <input
            type="search"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search chats…"
            className="w-full rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus:border-mint"
          />
        </div>

        <div className="flex-1 space-y-0.5 overflow-y-auto px-3 py-3">
          {visible.length === 0 && (
            <p className="px-2 py-4 text-center text-xs text-slate-500">
              {showArchived ? 'No archived chats.' : 'No conversations yet.'}
            </p>
          )}
          {visible.map((conversation) => (
            <ConversationItem
              key={conversation.id}
              conversation={conversation}
              isActive={conversation.id === activeConversationId}
              onUpdate={onUpdateConversation}
              onDelete={onDeleteConversation}
            />
          ))}
        </div>

        <button
          onClick={() => setShowArchived((s) => !s)}
          className="border-t border-white/10 px-4 py-2 text-left text-xs text-slate-400 hover:text-slate-200"
        >
          {showArchived ? '← Back to chats' : 'View archived chats'}
        </button>

        <div className="flex items-center justify-between border-t border-white/10 px-3 py-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-white">{user?.full_name}</p>
            <button onClick={logout} className="text-xs text-slate-400 hover:text-slate-200">
              Sign out
            </button>
          </div>
          <ThemeToggle />
        </div>

        <Footer className="border-t border-white/10 px-3 py-2" />
      </aside>
    </>
  )
}
