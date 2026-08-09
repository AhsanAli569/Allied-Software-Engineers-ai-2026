import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function ConversationItem({ conversation, isActive, onUpdate, onDelete }) {
  const navigate = useNavigate()
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(conversation.title)
  const [menuOpen, setMenuOpen] = useState(false)

  const commitRename = () => {
    setEditing(false)
    const trimmed = title.trim()
    if (trimmed && trimmed !== conversation.title) {
      onUpdate(conversation.id, { title: trimmed })
    } else {
      setTitle(conversation.title)
    }
  }

  return (
    <div
      className={`group flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm transition-colors duration-150 ${
        isActive ? 'bg-emerald text-white' : 'text-slate-300 hover:bg-white/10'
      }`}
    >
      {editing ? (
        <input
          autoFocus
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={commitRename}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commitRename()
            if (e.key === 'Escape') {
              setTitle(conversation.title)
              setEditing(false)
            }
          }}
          className="flex-1 rounded border border-mint bg-white/10 px-1 py-0.5 text-sm text-white outline-none"
        />
      ) : (
        <button
          onClick={() => navigate(`/chat/${conversation.id}`)}
          className="flex-1 truncate text-left"
          title={conversation.title}
        >
          {conversation.pinned && <span className="mr-1">📌</span>}
          {conversation.title}
        </button>
      )}

      <div className="relative shrink-0">
        <button
          onClick={() => setMenuOpen((o) => !o)}
          className="rounded p-1 text-slate-400 opacity-0 hover:bg-white/15 hover:text-white group-hover:opacity-100"
          aria-label="Conversation options"
        >
          ⋯
        </button>
        {menuOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
            <div className="absolute right-0 z-20 mt-1 w-36 rounded-lg border border-slate-200 bg-card py-1 text-xs text-charcoal shadow-lg">
              <MenuItem
                onClick={() => {
                  setEditing(true)
                  setMenuOpen(false)
                }}
              >
                Rename
              </MenuItem>
              <MenuItem
                onClick={() => {
                  onUpdate(conversation.id, { pinned: !conversation.pinned })
                  setMenuOpen(false)
                }}
              >
                {conversation.pinned ? 'Unpin' : 'Pin'}
              </MenuItem>
              <MenuItem
                onClick={() => {
                  onUpdate(conversation.id, { archived: !conversation.archived })
                  setMenuOpen(false)
                }}
              >
                {conversation.archived ? 'Unarchive' : 'Archive'}
              </MenuItem>
              <MenuItem
                danger
                onClick={() => {
                  setMenuOpen(false)
                  onDelete(conversation.id)
                }}
              >
                Delete
              </MenuItem>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function MenuItem({ children, onClick, danger }) {
  return (
    <button
      onClick={onClick}
      className={`block w-full px-3 py-1.5 text-left hover:bg-slate-100 ${danger ? 'text-error' : ''}`}
    >
      {children}
    </button>
  )
}
