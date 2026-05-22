import { onBeforeUnmount, ref } from 'vue'

export function usePolling() {
  const active = ref(false)
  let timer: number | null = null

  function stop() {
    active.value = false
    if (timer !== null) {
      window.clearTimeout(timer)
      timer = null
    }
  }

  async function start(job: () => Promise<boolean>, interval = 2000) {
    stop()
    active.value = true

    const run = async () => {
      const shouldContinue = await job()
      if (!shouldContinue) {
        stop()
        return
      }
      timer = window.setTimeout(run, interval)
    }

    await run()
  }

  onBeforeUnmount(stop)

  return {
    active,
    start,
    stop,
  }
}
