import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { streamMessage } from '../lib/sse'
import Sidebar from '../components/sidebar/Sidebar'
import MessageList from '../components/chat/MessageList'
import Composer from '../components/composer/Composer'

function dedupeMessages(messages) {
  // Regenerate keeps the old assistant message and inserts a new one (same
  // parent_message_id, higher regeneration_number). Show only the latest per parent.
  const latestByParent = new Map()
  for (const m of messages) {
    if (m.role !== 'assistant') continue
    const key = m.parent_message_id ?? `standalone-${m.id}`
    const existing = latestByParent.get(key)
    if (!existing || m.regeneration_number >= existing.regeneration_number) {
      latestByParent.set(key, m)
    }
  }
  const latestAssistantIds = new Set([...latestByParent.values()].map((m) => m.id))
  return messages.filter((m) => m.role !== 'assistant' || latestAssistantIds.has(m.id))
}

export default function ChatPage() {
  const { conversationId } = useParams()
  const navigate = useNavigate()

  const [conversations, setConversations] = useState([])
  const [search, setSearch] = useState('')
  const [messages, setMessages] = useState([])
  const [isGenerating, setIsGenerating] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [attachments, setAttachments] = useState([])
  const abortRef = useRef(null)
  const activeMessageIdRef = useRef(null)

  const refreshConversations = useCallback(async (searchTerm) => {
    const list = await api.get(`/conversations${searchTerm ? `?search=${encodeURIComponent(searchTerm)}` : ''}`)
    setConversations(list)
  }, [])

  useEffect(() => {
    refreshConversations()
  }, [refreshConversations])

  useEffect(() => {
    const handle = setTimeout(() => refreshConversations(search), 250)
    return () => clearTimeout(handle)
  }, [search, refreshConversations])

  useEffect(() => {
    setAttachments([])
    if (!conversationId) {
      setMessages([])
      return
    }
    api
      .get(`/conversations/${conversationId}/messages`)
      .then((data) => setMessages(dedupeMessages(data)))
      .catch(() => setMessages([]))
  }, [conversationId])

  const runGeneration = (path, body) => {
    setIsGenerating(true)
    const controller = new AbortController()
    abortRef.current = controller

    activeMessageIdRef.current = null

    streamMessage(path, body, {
      signal: controller.signal,
      onStart: ({ message_id }) => {
        activeMessageIdRef.current = message_id
        // Model/provider are chosen automatically server-side and intentionally not
        // surfaced in the UI — ASE AI just answers, it doesn't advertise how.
        setMessages((prev) => [
          ...prev,
          { id: message_id, role: 'assistant', content: '', status: 'streaming', regeneration_number: 0 },
        ])
      },
      onChunk: (text) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === activeMessageIdRef.current ? { ...m, content: m.content + text } : m))
        )
      },
      onDone: () => {
        setMessages((prev) => prev.map((m) => (m.id === activeMessageIdRef.current ? { ...m, status: 'complete' } : m)))
        activeMessageIdRef.current = null
        refreshConversations(search)
      },
      onError: (message) => {
        setMessages((prev) => {
          const id = activeMessageIdRef.current
          if (id && prev.some((m) => m.id === id)) {
            return prev.map((m) => (m.id === id ? { ...m, content: message, status: 'failed' } : m))
          }
          return [...prev, { id: `error-${Date.now()}`, role: 'assistant', content: message, status: 'failed' }]
        })
        activeMessageIdRef.current = null
      },
    }).finally(() => {
      setIsGenerating(false)
    })
  }

  /** Returns the active conversation id, creating one first if this is a brand-new chat —
   * both sending a message and attaching a file need a real conversation to belong to.
   * No model_id is sent — routing is fully automatic server-side. */
  const ensureConversation = async () => {
    if (conversationId) return conversationId
    const conversation = await api.post('/conversations', {})
    setConversations((prev) => [conversation, ...prev])
    navigate(`/chat/${conversation.id}`, { replace: true })
    return conversation.id
  }

  const handleFilesSelected = async (fileList) => {
    const targetId = await ensureConversation()

    for (const file of Array.from(fileList)) {
      const localId = `pending-${crypto.randomUUID()}`
      setAttachments((prev) => [
        ...prev,
        { localId, original_filename: file.name, size_bytes: file.size, status: 'uploading', progress: 0 },
      ])

      try {
        const uploaded = await api.uploadFile(`/conversations/${targetId}/files`, file, (progress) => {
          setAttachments((prev) => prev.map((a) => (a.localId === localId ? { ...a, progress } : a)))
        })
        setAttachments((prev) => prev.map((a) => (a.localId === localId ? { ...uploaded, localId, status: 'ready' } : a)))
      } catch (err) {
        setAttachments((prev) =>
          prev.map((a) => (a.localId === localId ? { ...a, status: 'failed', error: err.detail || 'Upload failed' } : a))
        )
      }
    }
  }

  const handleRemoveAttachment = async (localId) => {
    const attachment = attachments.find((a) => a.localId === localId)
    setAttachments((prev) => prev.filter((a) => a.localId !== localId))
    if (attachment?.id && conversationId) {
      try {
        await api.delete(`/conversations/${conversationId}/files/${attachment.id}`)
      } catch {
        // already used in a sent message, or already gone — nothing to reconcile client-side
      }
    }
  }

  const handleSend = async (content) => {
    const targetId = await ensureConversation()
    const readyAttachments = attachments.filter((a) => a.status === 'ready')

    setMessages((prev) => [
      ...prev,
      {
        id: `local-${Date.now()}`,
        role: 'user',
        content,
        status: 'complete',
        regeneration_number: 0,
        attachments: readyAttachments,
      },
    ])
    setAttachments([])

    runGeneration(`/conversations/${targetId}/messages/stream`, {
      content,
      idempotency_key: crypto.randomUUID(),
      attachment_ids: readyAttachments.map((a) => a.id),
    })
  }

  const handleRegenerate = (messageId) => {
    if (!conversationId || isGenerating) return
    runGeneration(`/conversations/${conversationId}/messages/${messageId}/regenerate`, {})
  }

  const handleStop = () => {
    abortRef.current?.abort()
    const id = activeMessageIdRef.current
    if (id) {
      setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, status: 'cancelled' } : m)))
      activeMessageIdRef.current = null
    }
    setIsGenerating(false)
  }

  const handleUpdateConversation = async (id, patch) => {
    const updated = await api.patch(`/conversations/${id}`, patch)
    setConversations((prev) => prev.map((c) => (c.id === id ? updated : c)))
  }

  const handleDeleteConversation = async (id) => {
    await api.delete(`/conversations/${id}`)
    setConversations((prev) => prev.filter((c) => c.id !== id))
    if (id === conversationId) navigate('/chat')
  }

  return (
    <div className="flex h-full">
      <Sidebar
        conversations={conversations}
        activeConversationId={conversationId}
        search={search}
        onSearchChange={setSearch}
        onUpdateConversation={handleUpdateConversation}
        onDeleteConversation={handleDeleteConversation}
        isOpen={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b border-slate-200 bg-card px-3 py-2 text-charcoal md:hidden dark:border-white/10 dark:bg-navy dark:text-slate-100">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-white/10"
            aria-label="Open menu"
          >
            ☰
          </button>
          <span className="truncate text-sm font-medium">Allied Software Engineers</span>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <MessageList messages={messages} onRegenerate={handleRegenerate} />
        </div>

        <Composer
          onSend={handleSend}
          onStop={handleStop}
          isGenerating={isGenerating}
          attachments={attachments}
          onFilesSelected={handleFilesSelected}
          onRemoveAttachment={handleRemoveAttachment}
        />
      </div>
    </div>
  )
}
