'use client'

import { useState } from 'react'

import { useBoardPolling } from '@/lib/board'
import { resetBoard } from '@/services/api'
import type { BoardSnapshot } from '@/types/board'

const COLUMNS: { key: keyof BoardSnapshot; label: string }[] = [
  { key: 'todo', label: 'To Do' },
  { key: 'in_progress', label: 'In Progress' },
  { key: 'done', label: 'Done' },
]

export function TodoBoard({ active }: { active: boolean }) {
  const board = useBoardPolling(active)
  const [resetting, setResetting] = useState(false)

  const handleReset = async () => {
    setResetting(true)
    try {
      await resetBoard()
    } catch {
      // ignore — the next poll reflects the true state
    } finally {
      setResetting(false)
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Todo Board
        </h2>
        <button
          type="button"
          onClick={handleReset}
          disabled={resetting}
          className="rounded-md border px-2 py-1 text-xs text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
        >
          {resetting ? 'Resetting…' : 'Reset board'}
        </button>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 sm:grid-cols-3">
        {COLUMNS.map((col) => (
          <div key={col.key} className="flex min-h-0 flex-col gap-2 rounded-lg bg-muted/40 p-2">
            <div className="px-1 text-xs font-medium text-muted-foreground">
              {col.label} · {board[col.key].length}
            </div>
            <div className="flex flex-col gap-2 overflow-y-auto">
              {board[col.key].map((task) => (
                <div
                  key={task.id}
                  className="rounded-md border bg-background p-2 text-sm shadow-sm transition-all duration-300"
                >
                  {task.title}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
