export async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // fall through to the legacy path below (e.g. permission denied in some embedded contexts)
    }
  }

  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  let succeeded = false
  try {
    succeeded = document.execCommand('copy')
  } catch {
    succeeded = false
  }
  document.body.removeChild(textarea)
  return succeeded
}
