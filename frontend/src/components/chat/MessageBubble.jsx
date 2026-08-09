import { useState } from 'react'
import MarkdownRenderer from './MarkdownRenderer'
import { copyText } from '../../lib/clipboard'
import AttachmentList from './AttachmentList'

export default function MessageBubble({ message, onRegenerate, isLatestAssistant }) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'
  const hasCopyableContent = Boolean(message.content)

  const handleCopy = async () => {
    const ok = await copyText(message.content)
    setCopied(ok)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className={`flex animate-fade-slide-up ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] sm:max-w-[75%] ${isUser ? '' : 'w-full'}`}>
        {message.attachments?.length > 0 && (
          <AttachmentList attachments={message.attachments} align={isUser ? 'end' : 'start'} />
        )}

        <div
          className={
            isUser
              ? 'rounded-2xl bg-emerald px-4 py-2.5 text-sm text-white shadow-sm transition-shadow'
              : 'rounded-2xl bg-card px-4 py-2.5 text-sm text-charcoal shadow-sm transition-shadow dark:bg-white/10 dark:text-slate-100'
          }
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : message.content ? (
            <MarkdownRenderer content={message.content} />
          ) : message.status === 'streaming' ? (
            <span className="inline-flex gap-1 py-1" aria-label="ASE AI is thinking">
              <Dot /> <Dot delay="150ms" /> <Dot delay="300ms" />
            </span>
          ) : (
            <p className="italic text-warning">Generation stopped.</p>
          )}
        </div>

        {hasCopyableContent && message.status !== 'streaming' && (
          <div className={`mt-1 flex items-center gap-3 px-1 text-xs text-muted ${isUser ? 'justify-end' : ''}`}>
            <button
              onClick={handleCopy}
              className={`transition-colors duration-150 ${copied ? 'text-success' : 'hover:text-emerald dark:hover:text-mint'}`}
            >
              {copied ? 'Copied ✓' : 'Copy'}
            </button>
            {!isUser && isLatestAssistant && (
              <button onClick={onRegenerate} className="transition-colors duration-150 hover:text-emerald dark:hover:text-mint">
                Regenerate
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function Dot({ delay = '0ms' }) {
  return (
    <span
      className="h-1.5 w-1.5 animate-bounce rounded-full bg-emerald dark:bg-mint"
      style={{ animationDelay: delay }}
    />
  )
}
