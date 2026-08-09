import { useRef, useState } from 'react'
import AttachmentChip from './AttachmentChip'

const ACCEPTED_TYPES = '.png,.jpg,.jpeg,.webp,.pdf,.docx,.txt,.md,.csv'

export default function Composer({ onSend, onStop, isGenerating, attachments, onFilesSelected, onRemoveAttachment }) {
  const [value, setValue] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)

  const isUploading = attachments.some((a) => a.status === 'uploading')
  const hasReadyAttachment = attachments.some((a) => a.status === 'ready')
  const canSend = (value.trim() || hasReadyAttachment) && !isUploading && !isGenerating

  const handleSend = () => {
    if (!canSend) return
    onSend(value.trim())
    setValue('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e) => {
    setValue(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`
  }

  const handleFileInputChange = (e) => {
    if (e.target.files?.length) onFilesSelected(e.target.files)
    e.target.value = ''
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files?.length) onFilesSelected(e.dataTransfer.files)
  }

  return (
    <div
      className="border-t border-slate-200 bg-card px-4 py-3 dark:border-white/10 dark:bg-navy"
      onDragOver={(e) => {
        e.preventDefault()
        setDragOver(true)
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      <div className="mx-auto flex max-w-3xl flex-col gap-2">
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {attachments.map((attachment) => (
              <AttachmentChip key={attachment.localId} attachment={attachment} onRemove={onRemoveAttachment} />
            ))}
          </div>
        )}

        <div
          className={`flex items-end gap-2 rounded-2xl border bg-white p-2 focus-within:border-mint dark:bg-white/5 ${
            dragOver ? 'border-mint border-dashed' : 'border-slate-300 dark:border-white/15'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={ACCEPTED_TYPES}
            onChange={handleFileInputChange}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="shrink-0 rounded-full p-2 text-muted hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-white/10"
            aria-label="Attach image or document"
            type="button"
          >
            <AttachIcon />
          </button>

          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Message ASE AI…"
            className="max-h-[200px] flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-charcoal outline-none dark:text-slate-100"
          />
          {isGenerating ? (
            <button
              onClick={onStop}
              className="shrink-0 rounded-full bg-navy p-2 text-white hover:bg-emerald-deep dark:bg-white/15 dark:hover:bg-white/25"
              aria-label="Stop generating"
            >
              <StopIcon />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!canSend}
              className="shrink-0 rounded-full bg-mint p-2 text-navy hover:bg-mint-dark disabled:bg-slate-200 disabled:text-slate-400 dark:disabled:bg-white/10 dark:disabled:text-slate-500"
              aria-label="Send message"
            >
              <SendIcon />
            </button>
          )}
        </div>
        <p className="text-center text-xs text-muted">ASE AI can make mistakes. Verify important information.</p>
      </div>
    </div>
  )
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 2 11 13" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M22 2 15 22l-4-9-9-4 20-7Z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function StopIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  )
}

function AttachIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path
        d="M21.44 11.05l-9.19 9.19a5 5 0 01-7.07-7.07l9.19-9.19a3.5 3.5 0 014.95 4.95l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
