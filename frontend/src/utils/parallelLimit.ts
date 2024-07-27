export async function parallelLimit<T, R>(
  items: T[],
  limit: number,
  iteratee: (item: T, index: number) => Promise<R>
): Promise<R[]> {
  const results: R[] = []
  let index = 0

  async function worker(): Promise<void> {
    while (index < items.length) {
      const currentIndex = index++
      results[currentIndex] = await iteratee(items[currentIndex], currentIndex)
    }
  }

  const workers = Array(Math.min(limit, items.length))
    .fill(null)
    .map(() => worker())

  await Promise.all(workers)
  return results
}
