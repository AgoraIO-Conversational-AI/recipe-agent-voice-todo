import { useEffect, useState } from 'react'

import { getBoard } from '@/services/api'
import type { BoardSnapshot } from '@/types/board'

const EMPTY_BOARD: BoardSnapshot = { todo: [], in_progress: [], done: [] }

/**
 * Poll GET /api/board while `active` (i.e. a conversation is connected).
 * Returns the latest snapshot; stops polling on unmount or when inactive.
 */
export function useBoardPolling(active: boolean, intervalMs = 1000): BoardSnapshot {
  const [board, setBoard] = useState<BoardSnapshot>(EMPTY_BOARD)

  useEffect(() => {
    if (!active) return
    let cancelled = false

    const tick = async () => {
      try {
        const next = await getBoard()
        if (!cancelled) setBoard(next)
      } catch {
        // transient fetch error — keep the last good board, try again next tick
      }
    }

    tick()
    const id = setInterval(tick, intervalMs)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [active, intervalMs])

  return board
}
