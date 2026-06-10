<script>
  import { onMount } from 'svelte'
  import packageInfo from '../../../package.json'

  let isOpen = false
  let isMac = false

  // Array of keyboard shortcuts
  const getKeyboardShortcuts = () => [
    { shortcut: isMac ? '⌘ + Space' : 'Ctrl + Space', action: 'Toggle batch mode' },
    { shortcut: '↑', action: 'Navigate to previous message in history' },
    { shortcut: '↓', action: 'Navigate to next message in history' },
    { shortcut: 'Enter', action: 'Send message' },
    { shortcut: isMac ? '⌘ + Enter' : 'Ctrl + Enter', action: 'Insert new line in message' },
    { shortcut: isMac ? '⌘ + Delete' : 'Ctrl + Delete', action: 'Delete matching words in saved history' },
    { shortcut: isMac ? '⌘ + R' : 'Ctrl + R', action: 'Reset session' },
    { shortcut: 'Esc', action: 'Close this help dialog' },
  ]

  let keyboardShortcuts = []

  function closeModal() {
    isOpen = false
  }

  function handleKeydown(event) {
    if (event.key === 'Escape') {
      closeModal()
    }
  }

  function handleOpenHelpModal() {
    isOpen = true
  }

  function handleCloseHelpModal() {
    isOpen = false
  }

  onMount(() => {
    // Detect if user is on Mac using navigator.userAgent instead of navigator.platform
    isMac = /Mac|iPhone|iPad|iPod/i.test(window.navigator.userAgent)
    keyboardShortcuts = getKeyboardShortcuts()

    document.addEventListener('openHelpModal', handleOpenHelpModal)
    document.addEventListener('closeHelpModal', handleCloseHelpModal)

    return () => {
      document.removeEventListener('openHelpModal', handleOpenHelpModal)
      document.removeEventListener('closeHelpModal', handleCloseHelpModal)
    }
  })
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
  <div class="fixed inset-0 z-50 overflow-auto bg-opacity-25 backdrop-blur-sm flex items-center justify-center p-4">
    <div class="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto transition-theme">
      <div class="flex justify-between items-center border-b border-gray-200 dark:border-gray-700 p-4">
        <h2 class="text-xl font-semibold text-gray-900 dark:text-white">Keyboard Shortcuts</h2>
        <button on:click={closeModal} class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 cursor-pointer" aria-label="Close">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <div class="p-6">
        <table class="w-full text-left text-gray-600 dark:text-gray-300">
          <thead>
            <tr class="border-b border-gray-200 dark:border-gray-700">
              <th class="pb-2">Shortcut</th>
              <th class="pb-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {#each keyboardShortcuts as { shortcut, action }}
              <tr class="border-b border-gray-100 dark:border-gray-800">
                <td class="py-3 pr-4">
                  <kbd class="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">{shortcut}</kbd>
                </td>
                <td class="py-3">{action}</td>
              </tr>
            {/each}
          </tbody>
        </table>

        <section>
          <h3 class="text-md font-medium text-gray-900 dark:text-white my-3">About</h3>
          <p class="text-gray-600 dark:text-gray-300 mb-2 sarabun">
            Agentic AI เป็นอินเทอร์เฟซแชทสำหรับการโต้ตอบกับโมเดล AI และเอเจนท์ต่างๆ ช่วยให้คุณสามารถใช้ประโยชน์จากความสามารถของ AI ที่หลากหลายสำหรับงานของคุณ
          </p>
          <p class="text-gray-600 dark:text-gray-300 sarabun">เลือกจากโมเดล AI ที่แตกต่างกันในเมนูแบบเลื่อนลงด้านบนเพื่อเข้าถึงความสามารถพิเศษ</p>
        </section>
      </div>

      <div class="flex justify-between items-center border-t border-gray-200 dark:border-gray-700 p-4">
        <div class="text-sm text-gray-500 dark:text-gray-400">
          <b>Version:</b>
          {packageInfo.name}@{!packageInfo.version.startsWith('dev') ? packageInfo.version : `v${packageInfo.version}`} ({packageInfo.run_number})
        </div>
        <button on:click={closeModal} class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 transition-colors">
          Close
        </button>
      </div>
    </div>
  </div>
{/if}
