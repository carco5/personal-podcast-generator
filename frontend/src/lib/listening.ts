// Fixed 15 s slots of the episode timeline, the same slots the dashboard counts (position // 15).
// A slot is reported once, with its start, when (almost) all its seconds have actually played;
// seconds already heard are remembered, so replays and pauses never add anything.
export const SLOT_SECONDS = 15
export const MAX_STEP_SECONDS = 5
export const MISSING_SECONDS_ALLOWED = 1

export function createListenTracker(
  duration: number,
  send: (slotStart: number) => void
) {
  let last: number | null = null
  const heard = new Set<number>()
  const sent = new Set<number>()

  function complete(slot: number): boolean {
    const first = slot * SLOT_SECONDS
    const end = Math.min(first + SLOT_SECONDS, Math.ceil(duration))
    let count = 0
    for (let second = first; second < end; second++)
      if (heard.has(second)) count++
    return count >= end - first - MISSING_SECONDS_ALLOWED
  }

  return {
    update(position: number) {
      if (last !== null) {
        const step = position - last
        if (step > 0 && step <= MAX_STEP_SECONDS) {
          for (
            let second = Math.floor(last);
            second < Math.ceil(position);
            second++
          ) {
            heard.add(second)
            const slot = Math.floor(second / SLOT_SECONDS)
            if (!sent.has(slot) && complete(slot)) {
              sent.add(slot)
              send(slot * SLOT_SECONDS)
            }
          }
        }
      }
      last = position
    },
    seek() {
      last = null
    },
  }
}
