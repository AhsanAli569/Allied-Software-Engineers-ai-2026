import { API_BASE } from './api'

export function attachmentContentUrl(conversationId, attachmentId) {
  return `${API_BASE}/conversations/${conversationId}/files/${attachmentId}/content`
}

export function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
