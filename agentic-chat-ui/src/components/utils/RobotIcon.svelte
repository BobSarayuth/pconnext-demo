<script>
  export let isThinking = false
</script>

<div id="robot">
  {#if !isThinking}
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      class="w-8 h-8 text-gray-700 dark:text-white rounded-full mr-2 bg-sky-100 dark:bg-sky-900 p-1.5 transition-theme"
    >
      <path d="M12 8V4H8"></path><rect width="16" height="12" x="4" y="8" rx="2"></rect><path d="M2 14h2"></path><path d="M20 14h2"></path><path d="M15 13v2"></path><path d="M9 13v2"></path>
    </svg>
  {:else}
    <svg id="loading" class="relative animate-spin text-sky-50 dark:text-sky-900 w-8 h-8 rounded-full mr-2 bg-slate-800 dark:bg-gray-100 p-1.5 transition-theme" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
  {/if}
</div>
