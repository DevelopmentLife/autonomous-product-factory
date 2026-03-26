import { useEffect, useRef, useCallback } from 'react'
import { useAuthStore } from '../stores/authStore'
import { usePipelineStore } from '../stores/pipelineStore'

export function usePipelineWS(pipelineId: string) {
  const token = useAuthStore((s) => s.token)
  const updatePipeline = usePipelineStore((s) => s.updatePipeline)
  const wsRef = useRef<WebSocket | null>(null)

  const connect = useCallback(() => {
    if (!token || !pipelineId) return
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${proto}://${location.host}/ws/pipelines/${pipelineId}?token=${token}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data)
        if (data.pipeline_id === pipelineId) {
          updatePipeline(pipelineId, {
            status: data.pipeline_status ?? undefined,
            current_stage: data.stage ?? undefined,
          })
        }
      } catch {
        // ignore
      }
    }

    ws.onclose = () => {
      setTimeout(connect, 3_000)
    }
  }, [pipelineId, token, updatePipeline])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])
}
