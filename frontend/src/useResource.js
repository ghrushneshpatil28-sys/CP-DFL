import { useCallback, useEffect, useState } from 'react'
import { api } from './api'

export function useResource(path, poll = 0) {
  const [state, setState] = useState({ path: null, data: null, error: '' })
  const [revision, setRevision] = useState(0)
  const reload = useCallback(() => setRevision(value => value + 1), [])
  useEffect(() => {
    let active = true
    let controller = null
    const load = async () => {
      if (controller) return
      const request = new AbortController()
      controller = request
      try {
        const data = await api(path, { signal: request.signal })
        if (active) setState({ path, data, error: '' })
      } catch (error) {
        if (active && error.name !== 'AbortError') setState({ path, data: null, error: error.message })
      } finally { if (controller === request) controller = null }
    }
    load()
    const timer = poll ? setInterval(load, poll) : null
    return () => { active = false; controller?.abort(); if (timer) clearInterval(timer) }
  }, [path, revision, poll])
  return { data: state.path === path ? state.data : null, error: state.path === path ? state.error : '',
    loading: state.path !== path || (!state.data && !state.error), reload }
}
