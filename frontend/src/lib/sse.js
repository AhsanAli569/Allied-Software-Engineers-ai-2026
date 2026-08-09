import { API_BASE, api, captureCsrfTokenFromResponse, getCsrfToken } from './api'

/**
 * Streams a Server-Sent-Events response from a POST endpoint. The browser's built-in
 * EventSource only supports GET, so this parses the `text/event-stream` body manually off
 * a regular fetch, which also gives us an AbortController-based cancel path for the
 * "stop generation" button.
 */
export async function streamMessage(path, body, options = {}, _isRetry = false) {
  const { onStart, onChunk, onDone, onError, signal } = options
  const headers = { 'Content-Type': 'application/json' }
  const csrfToken = getCsrfToken()
  if (csrfToken) headers['X-CSRF-Token'] = csrfToken

  let response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers,
      credentials: 'include',
      body: JSON.stringify(body),
      signal,
    })
  } catch (err) {
    if (err.name === 'AbortError') return
    onError?.('Could not reach ASE AI. Check your connection and try again.')
    return
  }

  captureCsrfTokenFromResponse(response)

  if (response.status === 403 && !_isRetry) {
    // Same stale-token-after-reload race the API client retries — refresh the CSRF token
    // once and retry the stream, instead of failing the user's very first message.
    let detail
    try {
      detail = (await response.clone().json())?.detail
    } catch {
      // non-JSON body — fall through and treat as a generic failure below
    }
    if (detail === 'CSRF validation failed') {
      try {
        await api.get('/auth/csrf')
      } catch {
        // not logged in, or the refresh itself failed — fall through to the generic error
      }
      if (getCsrfToken()) return streamMessage(path, body, options, true)
    }
  }

  if (!response.ok || !response.body) {
    onError?.('ASE AI is temporarily unable to answer. Please try again.')
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let boundary
      while ((boundary = buffer.indexOf('\n\n')) !== -1) {
        const rawEvent = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        dispatchEvent(rawEvent, { onStart, onChunk, onDone, onError })
      }
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      onError?.('The connection to ASE AI was interrupted.')
    }
  }
}

function dispatchEvent(rawEvent, { onStart, onChunk, onDone, onError }) {
  const eventMatch = rawEvent.match(/^event: (.+)$/m)
  const dataMatch = rawEvent.match(/^data: (.+)$/m)
  if (!dataMatch) return

  const eventType = eventMatch ? eventMatch[1] : 'message'
  let data
  try {
    data = JSON.parse(dataMatch[1])
  } catch {
    return
  }

  if (eventType === 'start') onStart?.(data)
  else if (eventType === 'chunk') onChunk?.(data.text)
  else if (eventType === 'done') onDone?.(data)
  else if (eventType === 'error') onError?.(data.message)
}
