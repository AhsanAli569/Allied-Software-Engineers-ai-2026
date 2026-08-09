import { useParams } from 'react-router-dom'
import { attachmentContentUrl, formatFileSize } from '../../lib/attachments'

export default function AttachmentList({ attachments, align = 'start' }) {
  const { conversationId } = useParams()

  return (
    <div className={`mb-1.5 flex flex-wrap gap-2 ${align === 'end' ? 'justify-end' : 'justify-start'}`}>
      {attachments.map((attachment) =>
        attachment.kind === 'image' ? (
          <a
            key={attachment.id}
            href={attachmentContentUrl(conversationId, attachment.id)}
            target="_blank"
            rel="noreferrer"
          >
            <img
              src={attachmentContentUrl(conversationId, attachment.id)}
              alt={attachment.original_filename}
              className="h-28 w-28 rounded-lg object-cover ring-1 ring-slate-200 dark:ring-white/15"
            />
          </a>
        ) : (
          <a
            key={attachment.id}
            href={attachmentContentUrl(conversationId, attachment.id)}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 rounded-lg border border-slate-200 bg-card px-3 py-2 text-xs text-charcoal hover:bg-slate-100 dark:border-white/15 dark:bg-white/5 dark:text-slate-200 dark:hover:bg-white/10"
          >
            <span aria-hidden="true">📄</span>
            <span className="max-w-[10rem] truncate">{attachment.original_filename}</span>
            <span className="text-muted">{formatFileSize(attachment.size_bytes)}</span>
          </a>
        )
      )}
    </div>
  )
}
