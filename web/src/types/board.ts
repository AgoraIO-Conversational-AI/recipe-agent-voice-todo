export interface BoardTask {
  id: number
  title: string
}

export interface BoardSnapshot {
  todo: BoardTask[]
  in_progress: BoardTask[]
  done: BoardTask[]
}
