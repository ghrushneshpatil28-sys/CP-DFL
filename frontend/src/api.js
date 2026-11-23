let csrfToken = ''

export async function api(path, options = {}) {
  const headers = { ...options.headers }
  if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json'
  if (options.method && options.method !== 'GET') headers['X-CSRF-Token'] = csrfToken
  let response
  try {
    response = await fetch(`/api${path}`, { credentials: 'include', ...options, headers,
      body: options.body instanceof FormData ? options.body : options.body ? JSON.stringify(options.body) : undefined })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error('Cannot connect to the API. Start the application with START.cmd or python -m backend.dev, then try again.')
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 401 && path !== '/auth/login') window.dispatchEvent(new Event('session-expired'))
    throw new Error(Array.isArray(data.detail) ? data.detail.map(item => item.msg).join('; ') : data.detail || (response.status >= 500 ? 'The backend API is unavailable. Check the application terminal or backend/storage/logs, then try again.' : `Request failed (${response.status})`))
  }
  if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('The server did not return an API response. Open the application URL printed by START.cmd.')
  if (data.csrf_token) csrfToken = data.csrf_token
  return data
}

export function navigate(path) { window.location.hash = `/${path}` }
