import type { Ref } from 'vue'
import type { ImportProgress } from '@/types'

export function createProgressUpdater(importProgress: Ref<ImportProgress | null>) {
  return function updateProgress(
    status: string,
    progress: number,
    payload?: Partial<ImportProgress['payload']>
  ) {
    if (importProgress.value) {
      importProgress.value = {
        ...importProgress.value,
        status,
        progress,
        payload: { ...importProgress.value.payload, ...payload }
      }
    }
  }
}

export type ProgressUpdater = ReturnType<typeof createProgressUpdater>
