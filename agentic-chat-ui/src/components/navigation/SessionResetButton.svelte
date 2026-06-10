<script>
  import { sessionStore } from '../../utils/sessionStore'
  import { writable } from 'svelte/store'
  import { tippy } from 'svelte-tippy'

  // Create a writable store for the rotating state that can be accessed externally
  export const rotatingState = writable(false)
  let rotating = false

  // Subscribe to our own rotating state to keep the local variable in sync
  rotatingState.subscribe((value) => {
    rotating = value
  })

  let handleSessionReset
  let isDisabled = false

  // Subscribe to the store to get the function references and disabled state
  sessionStore.subscribe((store) => {
    handleSessionReset = store.handleSessionReset
    isDisabled = store.isDisabled
  })

  sessionStore.update((store) => ({
    ...store,
    rotatingState,
  }))

  const tooltipOptions = {
    content: 'New session',
    placement: 'bottom',
    arrow: true,
    theme: 'custom',
  }

  const handleRefresh = () => {
    if (rotating || isDisabled) return

    if (handleSessionReset) {
      handleSessionReset()
    } else {
      console.warn('handleRefresh function not available yet')
    }

    rotatingState.set(true)
  }

  function handleAnimationEnd() {
    rotatingState.set(false)
  }
</script>

<button
  use:tippy={tooltipOptions}
  class="flex items-center justify-center p-1 w-8 h-8 rounded-md focus:outline-none transition-theme cursor-pointer disabled:cursor-default disabled:opacity-50
    bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-300 hover:bg-sky-50 dark:hover:bg-slate-700 disabled:bg-gray-100 disabled:dark:bg-slate-800
    "
  onclick={handleRefresh}
  onanimationend={handleAnimationEnd}
  disabled={isDisabled}
>
  <!-- Refresh icon -->
  <svg class="w-4.5 h-4.5 text-gray-700 dark:text-gray-300 {rotating ? 'rotate-animation' : ''}" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
  </svg>
</button>

<style>
  .rotate-animation {
    animation: rotate 0.4s ease-in-out;
  }
  @keyframes rotate {
    from {
      transform: rotate(360deg);
    }
    to {
      transform: rotate(0deg);
    }
  }
</style>
