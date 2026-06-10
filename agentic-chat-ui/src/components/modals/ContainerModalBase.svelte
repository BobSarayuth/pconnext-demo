<script>
  import { fade } from 'svelte/transition'
  import { onMount } from 'svelte'
  import equilibriumDark from 'svelte-highlight/styles/equilibrium-dark'
  import { messageStore } from '../../utils/messageStore'
  import { sessionStore } from '../../utils/sessionStore'

  // Props
  export let title = ''

  // State
  let isOpen = false
  let sessionData = {}
  let messageData = {}

  // Subscribe to stores to get latest data
  sessionStore.subscribe((store) => {
    sessionData = store
  })

  messageStore.subscribe((store) => {
    messageData = store
  })

  // Setup open/close methods that can be called from outside
  export function open() {
    isOpen = true
    if (window.debugModalEvents && window.debugModalEvents.updateHeaderState) {
      window.debugModalEvents.updateHeaderState(true)
    }
  }

  export function close() {
    isOpen = false
    if (window.debugModalEvents && window.debugModalEvents.updateHeaderState) {
      window.debugModalEvents.updateHeaderState(false)
    }
  }

  // Register global events to allow opening modal from anywhere
  onMount(() => {
    window.debugModalEvents = {
      open,
      close,
    }

    return () => {
      window.debugModalEvents = undefined
    }
  })

  // Format JSON for display
  function formatJson(obj) {
    return JSON.stringify(obj, null, 2)
  }

  // For scrollbar tracking
  let tableContainer
  let scrollPercentage = 0

  // Create a custom event for scrolling
  import { createEventDispatcher } from 'svelte'
  const dispatch = createEventDispatcher()

  function handleScroll() {
    const { scrollTop, scrollHeight, clientHeight } = tableContainer
    scrollPercentage = Math.round((scrollTop / (scrollHeight - clientHeight)) * 100)

    // Dispatch the scroll event with percentage
    dispatch('scroll', { scrollPercentage })
  }
</script>

<svelte:head>
  {@html equilibriumDark}
</svelte:head>

{#if isOpen}
  <div class="fixed inset-0 bg-gray-50 dark:bg-slate-800 z-30 pt-20 flex flex-col overflow-auto" transition:fade={{ duration: 150 }}>
    {#if title}
      <div class="p-2 flex justify-between items-center sticky top-0 backdrop-blur-sm shadow-sm z-10">
        <h1 class="text-lg font-medium text-white">{title}</h1>
      </div>
    {/if}
    <div bind:this={tableContainer} on:scroll={handleScroll} class="container-panel p-3 flex-1 overflow-auto space-y-3">
      <slot {sessionData} {messageData} {formatJson} />
    </div>
  </div>
{/if}

<style>
  .container-panel::-webkit-scrollbar {
    width: 8px;
  }

  .container-panel::-webkit-scrollbar-track {
    background: transparent;
  }

  .container-panel::-webkit-scrollbar-thumb {
    background: #888;
    border-radius: 3px;
  }

  .container-panel::-webkit-scrollbar-thumb:hover {
    background: #555;
  }
</style>
