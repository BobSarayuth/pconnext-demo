<script>
  import consts from '../../utils/constraints'
  import { onMount } from 'svelte'
  import { scale } from 'svelte/transition'
  import { sessionStore } from '../../utils/sessionStore'

  let handleSessionReset
  let isOpen = false
  let dropdownRef

  sessionStore.subscribe((store) => {
    handleSessionReset = store.handleSessionReset
  })

  function toggleDropdown() {
    isOpen = !isOpen
  }

  function openModal(modalType) {
    if (modalType === 'help' && window.helpModalEvents) {
      window.helpModalEvents.open()
    } else if (modalType === 'debug' && window.debugModalEvents) {
      window.debugModalEvents.open()
    }
    isOpen = false
  }

  function handleClickOutside(event) {
    if (dropdownRef && !dropdownRef.contains(event.target)) {
      isOpen = false
    }
  }

  function clearCache() {
    if (window.confirm('Are you sure you want to clear cache? This will reset your session, remove all settings and history, and reload the page. This action cannot be undone.')) {
      handleSessionReset()
      localStorage.removeItem(consts.MODEL_DROPDOWN)
      localStorage.removeItem(consts.INPUT_HISTORY)
      window.history.pushState({}, document.title, window.getRouteUrl ? window.getRouteUrl() : `${window.location.origin}`)
      window.location.reload()
    }
  }

  onMount(() => {
    document.addEventListener('click', handleClickOutside)
    return () => {
      document.removeEventListener('click', handleClickOutside)
    }
  })
</script>

<div class="flex items-center md:order-2 space-x-3 md:space-x-0 rtl:space-x-reverse relative" bind:this={dropdownRef}>
  <button
    type="button"
    class="flex w-8 h-8 text-sm rounded md:me-0 focus:ring-4 focus:ring-gray-300 dark:focus:ring-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-300 hover:dark:bg-gray-600 cursor-pointer transition-theme items-center justify-center"
    id="user-menu-button"
    aria-expanded={isOpen}
    on:click|stopPropagation={toggleDropdown}
    aria-label="Menu"
  >
    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
    </svg>
  </button>

  <!-- Dropdown menu with animation -->
  {#if isOpen}
    <div
      transition:scale={{ duration: 100, start: 0.95, opacity: 0 }}
      class="absolute right-0 top-8 z-50 mt-2 w-56 origin-top-right rounded-lg bg-white divide-y divide-gray-100 shadow-sm ring-1 ring-black/5 dark:bg-gray-700 dark:divide-gray-600"
      id="user-dropdown"
      role="menu"
      aria-orientation="vertical"
      aria-labelledby="user-menu-button"
    >
      <div class="px-4 py-3">
        <span class="block text-sm text-gray-900 dark:text-white">User</span>
        <span class="block text-sm text-gray-500 truncate dark:text-gray-400">user@scg.com</span>
      </div>
      <ul class="py-2" role="none">
        <li>
          <button
            on:click={clearCache}
            class="block w-full text-left px-4 py-2 text-sm cursor-pointer text-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 dark:text-gray-200 dark:hover:text-white"
            role="menuitem"
          >
            Clear Cache
          </button>
        </li>
        <li>
          <button
            on:click={() => openModal('debug')}
            class="block w-full text-left px-4 py-2 text-sm cursor-pointer text-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 dark:text-gray-200 dark:hover:text-white"
            role="menuitem"
          >
            Debug
          </button>
        </li>
        <li>
          <button
            on:click={() => openModal('help')}
            class="block w-full text-left px-4 py-2 text-sm cursor-pointer text-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 dark:text-gray-200 dark:hover:text-white"
            role="menuitem"
          >
            Help
          </button>
        </li>
      </ul>
    </div>
  {/if}
</div>
