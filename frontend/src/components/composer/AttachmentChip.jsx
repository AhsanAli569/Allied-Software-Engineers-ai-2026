import { formatFileSize } from '../../lib/attachments'

export default function AttachmentChip({ attachment, onRemove }) {
  const isImage = attachment.kind === 'image' || attachment.file?.type?.startsWith('image/')
  const isUploading = attachment.status === 'uploading'
  const isFailed = attachment.status === 'failed'

  return (
    <div className="relative flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 py-1.5 pl-2 pr-7 text-xs text-charcoal dark:border-white/15 dark:bg-white/5 dark:text-slate-200">
      <span aria-hidden="true">{isImage ? '🖼️' : '📄'}</span>
      <div className="min-w-0">
        <p className="max-w-[9rem] truncate font-medium">{attachment.original_filename}</p>
        <p className={isFailed ? 'text-error' : 'text-muted'}>
          {isFailed
            ? attachment.error || 'Upload failed'
            : isUploading
              ? `Uploading… ${attachment.progress ?? 0}%`
              : formatFileSize(attachment.size_bytes ?? 0)}
        </p>
      </div>
      <button
        onClick={() => onRemove(attachment.localId)}
        className="absolute right-1.5 top-1.5 text-muted hover:text-charcoal dark:hover:text-slate-200"
        aria-label={`Remove ${attachment.original_filename}`}
      >
        ✕
      </button>
    </div>
  )
}
