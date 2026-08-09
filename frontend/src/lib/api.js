// Relative by default — works via the Vite dev proxy locally and via nginx reverse-proxying
// /api on a single-domain deployment (the VPS setup in docs/DEPLOYMENT.md). Set VITE_API_URL
// at build time when the frontend and backend are on different domains (e.g. Netlify +
// Render) — see docs/DEPLOYMENT_NETLIFY_RENDER.md. Accepts either the bare backend origin
// (https://your-backend.onrender.com) or one that already includes /api/v1 — normalized
// below so either form works and the suffix is never duplicated.
function resolveApiBase() {
  const configured = import.meta.env.VITE_API_URL
  if (!configured) return '/api/v1'
  const trimmed = configured.replace(/\/+$/, '')
  return trimmed.endsWith('/api/v1') ? trimmed : `${trimmed}/api/v1`
}

const API_BASE = resolveApiBase()
const CSRF_HEADER = 'X-CSRF-Token'

function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

// The CSRF cookie's Domain belongs to the *backend's* host. When the frontend and backend
// are on different registrable domains (Netlify + Render, not just different ports),
// document.cookie on the frontend can never read it — that's browser cookie isolation, not
// a SameSite issue. The backend also echoes the token back via the X-CSRF-Token response
// header on auth endpoints (see backend app/api/v1/auth.py); this in-memory value is that
// captured copy. Falls back to the cookie for same-origin deployments (VPS/local dev),
// where reading it directly still works fine and this may not be populated yet.
let inMemoryCsrfToken = null

function getCsrfToken() {
  return inMemoryCsrfToken || readCookie('ase_csrf_token')
}

function captureCsrfTokenFromResponse(response) {
  const token = response.headers.get(CSRF_HEADER)
  if (token) inMemoryCsrfToken = token
}

class ApiError extends Error {
  constructor(status, detail) {
    super(detail || 'Request failed')
    this.status = status
    this.detail = detail
  }
}

/**
 * Thin fetch wrapper: sends cookies, attaches the CSRF header (double-submit pattern) on
 * state-changing requests, and throws ApiError with the backend's friendly message on failure.
 */
async function request(path, { method = 'GET', body, signal } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (method !== 'GET' && method !== 'HEAD') {
    const csrfToken = getCsrfToken()
    if (csrfToken) headers[CSRF_HEADER] = csrfToken
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    credentials: 'include',
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  })

  captureCsrfTokenFromResponse(response)

  if (response.status === 204) return null

  const isJson = response.headers.get('content-type')?.includes('application/json')
  const data = isJson ? await response.json() : await response.text()

  if (!response.ok) {
    const detail = isJson ? data.detail : data
    throw new ApiError(response.status, typeof detail === 'string' ? detail : 'Something went wrong')
  }

  return data
}

/**
 * Uploads a file with progress reporting (fetch has no reliable cross-browser upload
 * progress event, so this uses XMLHttpRequest instead).
 */
function uploadFile(path, file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE}${path}`)
    xhr.withCredentials = true
    const csrfToken = getCsrfToken()
    if (csrfToken) xhr.setRequestHeader(CSRF_HEADER, csrfToken)

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100))
    }

    xhr.onload = () => {
      const headerToken = xhr.getResponseHeader(CSRF_HEADER)
      if (headerToken) inMemoryCsrfToken = headerToken

      let data = null
      try {
        data = JSON.parse(xhr.responseText)
      } catch {
        // non-JSON error body — fall through with data=null
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data)
      } else {
        reject(new ApiError(xhr.status, data?.detail || 'Upload failed'))
      }
    }
    xhr.onerror = () => reject(new ApiError(0, 'Could not reach ASE AI. Check your connection and try again.'))

    const formData = new FormData()
    formData.append('file', file)
    xhr.send(formData)
  })
}

export const api = {
  get: (path, opts) => request(path, { ...opts, method: 'GET' }),
  post: (path, body, opts) => request(path, { ...opts, method: 'POST', body }),
  patch: (path, body, opts) => request(path, { ...opts, method: 'PATCH', body }),
  delete: (path, opts) => request(path, { ...opts, method: 'DELETE' }),
  uploadFile,
}

export { ApiError, readCookie, getCsrfToken, captureCsrfTokenFromResponse, API_BASE }
