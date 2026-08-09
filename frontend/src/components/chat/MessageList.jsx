import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import Logo from '../ui/Logo'

export default function MessageList({ messages, onRegenerate }) {
  const bottomRef = useRef(null)
  const lastMessageContent = messages[messages.length - 1]?.content

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, lastMessageContent])

  const lastAssistantId = [...messages].reverse().find((m) => m.role === 'assistant')?.id

  if (messages.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-muted">
        <Logo size={40} className="opacity-70" />
        <p className="text-sm">Ask ASE AI anything — questions, code, analysis, and more.</p>
      </div>
    )
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-6">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          isLatestAssistant={message.id === lastAssistantId}
          onRegenerate={() => onRegenerate(message.id)}
        />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
