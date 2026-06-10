<script>
  import { onMount } from 'svelte'
  import Highlight, { LineNumbers } from 'svelte-highlight'
  import equilibriumDark from 'svelte-highlight/styles/equilibrium-dark'
  import githubLight from 'svelte-highlight/styles/github'
  import { json, markdown } from 'svelte-highlight/languages'
  import constraints from '../../utils/constraints.js'
  import { sessionStore } from '../../utils/sessionStore.js'
  // import MarkdownRenderer from '../utils/MarkdownRenderer.svelte'

  // Props
  export let isOpen = false
  export let toolData = null
  export let stateData = null
  export let mode = 'tool' // "tool" or "state"
  export let modeName = '' // "tool" or "state"

  export let onClose = () => {}

  // Dark mode detection
  let isDarkMode = false // Default value until store updates

  // Load saved preferences on mount
  onMount(() => {
    try {
      const savedShowFullJson = localStorage.getItem(constraints.SHOW_FULL_JSON)
      if (savedShowFullJson !== null) {
        const parsedValue = JSON.parse(savedShowFullJson)
        sessionStore.update((state) => {
          state.showFullJson = parsedValue
          return state
        })
      }
    } catch (error) {
      console.error('Error loading showFullJson preference:', error)
    }
  })

  // Store subscription
  let showFullJson
  const unsubscribe = sessionStore.subscribe((state) => {
    showFullJson = state.showFullJson
    isDarkMode = state.isDarkMode
  })

  // Update show full JSON setting
  const updateShowFullJson = (value) => {
    sessionStore.update((state) => {
      state.showFullJson = value
      localStorage.setItem(constraints.SHOW_FULL_JSON, JSON.stringify(value))
      return state
    })
  }

  // Function to stringify JSON for display
  const stringifyJSON = (jsonObj) => {
    try {
      return JSON.stringify(jsonObj, null, 2)
    } catch (error) {
      console.error('Error stringifying JSON:', error)
      return String(jsonObj)
    }
  }

  // Close modal when clicking outside
  const handleClickOutside = (event) => {
    if (event.target.classList.contains('modal-overlay')) {
      onClose()
    }
  }

  // Handle ESC key to close modal
  const handleKeydown = (event) => {
    if (event.key === 'Escape' && isOpen) {
      onClose()
    }
  }

  // Copy to clipboard function
  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch (err) {
      console.error('Failed to copy text: ', err)
      return false
    }
  }

  // Track copy status for feedback
  let copyingInput = false
  let copyingOutput = false
  let copyingFull = false

  const toJsonString = (data) => JSON.stringify(data, null, 2)

  const copyInput = async () => {
    copyingInput = true
    await copyToClipboard(toJsonString(toolData.toolInput))
    setTimeout(() => {
      copyingInput = false
    }, 1500)
  }

  const copyOutput = async () => {
    copyingOutput = true
    await copyToClipboard(mode === 'tool' ? toolData.toolOutput : toJsonString(stateData))
    setTimeout(() => {
      copyingOutput = false
    }, 1500)
  }

  const copyFull = async () => {
    copyingFull = true
    await copyToClipboard(toJsonString(mode === 'tool' ? toolData : stateData))
    setTimeout(() => {
      copyingFull = false
    }, 1500)
  }

  // Get modal title based on mode
  $: modalTitle = mode === 'tool' ? `Tool: ${toolData?.tool || ''}` : modeName || 'State'

  // Get icon based on mode
  $: modalIcon =
    mode === 'tool'
      ? `<path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
       <path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2z"></path>
       <line x1="10" y1="13" x2="14" y2="13"></line>
       <line x1="10" y1="17" x2="14" y2="17"></line>`
      : `<path d="M21 10V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16v-2"></path>
       <path d="M16.5 9.4 7.55 4.24"></path>
       <polyline points="3.29 7 12 12 20.71 7"></polyline>
       <line x1="12" y1="22" x2="12" y2="12"></line>`

  // Get color class based on mode
  $: iconColorClass = mode === 'tool' ? 'text-indigo-600 dark:text-indigo-400' : 'text-purple-600 dark:text-purple-400'
</script>

<svelte:head>
  {@html isDarkMode ? equilibriumDark : githubLight}
</svelte:head>
<svelte:window on:keydown={handleKeydown} />

{#if isOpen && (toolData || stateData)}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="modal-overlay fixed inset-0 bg-opacity-50 flex items-center justify-center z-50" on:click={handleClickOutside} role="presentation">
    <div class="modal-content bg-white dark:bg-slate-900 rounded-sm w-full max-w-3xl max-h-[70vh] overflow-hidden shadow-xl">
      <div class="modal-header p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
          <svg class="w-5 h-5 mr-2 {iconColorClass}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            {@html modalIcon}
          </svg>
          {modalTitle}
        </h3>
        {#if mode !== 'state'}
          <div class="flex items-center gap-4">
            <label class="flex items-center cursor-pointer gap-2">
              <span class="text-xs font-medium text-gray-700 dark:text-gray-300">Full JSON</span>
              <div class="relative">
                <input type="checkbox" class="sr-only" checked={showFullJson} on:change={() => updateShowFullJson(!showFullJson)} aria-label="Toggle raw JSON view" />
                <div class="toggle-bg w-10 h-5 bg-gray-200 dark:bg-gray-700 rounded-full border border-gray-300 dark:border-gray-600"></div>
                <div class="toggle-dot absolute left-1 top-1 bg-white w-3 h-3 rounded-full transition-transform duration-300 ease-in-out {showFullJson ? 'transform translate-x-2' : ''}"></div>
              </div>
            </label>
          </div>
        {/if}
      </div>
      <div class="modal-body p-4 overflow-y-auto rounded-md max-h-[calc(70vh-6em)]">
        {#if mode === 'tool' && toolData && !showFullJson}
          <div class="mb-4">
            <div class="bg-gray-100 dark:bg-slate-800 rounded-sm overflow-hidden">
              <div class="hljs flex justify-between items-center p-3 bg-gray-400 text-gray-700 dark:text-gray-300">
                <span class="font-medium">Input</span>
                <div class="flex relative">
                  <button class="copy-btn p-1 rounded-full hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors cursor-pointer" on:click={copyInput} aria-label="Copy input">
                    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      {#if copyingInput}
                        <path d="M20 6L9 17l-5-5"></path>
                      {:else}
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                      {/if}
                    </svg>
                  </button>
                </div>
              </div>
              <div class="-mt-3.5">
                <Highlight language={json} code={stringifyJSON(toolData.toolInput)} let:highlighted>
                  <LineNumbers {highlighted} wrapLines hideBorder />
                </Highlight>
              </div>
            </div>
          </div>

          {#if toolData.toolOutput}
            <div>
              <div class="bg-gray-100 dark:bg-slate-800 rounded-sm overflow-hidden">
                <div class="hljs flex justify-between items-center p-3 text-gray-700 dark:text-gray-300">
                  <span class="font-medium">Output</span>
                  <div class="flex relative">
                    <button class="copy-btn p-1 rounded-full hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors cursor-pointer" on:click={copyOutput} aria-label="Copy output">
                      <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        {#if copyingOutput}
                          <path d="M20 6L9 17l-5-5"></path>
                        {:else}
                          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        {/if}
                      </svg>
                    </button>
                  </div>
                </div>
                <!-- <MarkdownRenderer class="-mt-0.5" content={toolData.toolOutput} /> -->
                <div class="-mt-3.5">
                  <Highlight language={markdown} code={toolData.toolOutput} class="break-words" let:highlighted>
                    <LineNumbers {highlighted} wrapLines hideBorder />
                  </Highlight>
                </div>
              </div>
            </div>
          {/if}
        {:else}
          <div>
            <div class="rounded-sm overflow-hidden">
              <div class="flex relative justify-between items-center p-3 text-gray-700 dark:text-gray-300 z-10">
                <span class="font-medium"></span>
                <div class="flex relative">
                  <button class="copy-btn p-1 rounded-full hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors cursor-pointer" on:click={copyFull} aria-label="Copy full JSON">
                    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      {#if copyingFull}
                        <path d="M20 6L9 17l-5-5"></path>
                      {:else}
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                      {/if}
                    </svg>
                  </button>
                </div>
              </div>
              <div class="-mt-12">
                <Highlight language={json} code={stringifyJSON(mode === 'tool' ? toolData : stateData)} let:highlighted>
                  <LineNumbers {highlighted} wrapLines hideBorder />
                </Highlight>
              </div>
            </div>
          </div>
        {/if}
      </div>
    </div>
  </div>
  <style>
    /* Modal styles */
    .modal-overlay {
      backdrop-filter: blur(2px);
      animation: fadeIn 0.3s ease forwards;
    }

    pre > code {
      font-family: 'Fira Code', 'Sarabun', monospace;
      font-optical-sizing: auto;
    }

    /* Scrollbar styles for vertical scrolling in modal body */
    .modal-body::-webkit-scrollbar {
      width: 8px;
    }

    .modal-body::-webkit-scrollbar-track {
      background: transparent;
    }

    .modal-body::-webkit-scrollbar-thumb {
      background: #888;
      border-radius: 3px;
    }

    .modal-body::-webkit-scrollbar-thumb:hover {
      background: #555;
    }

    /* Scrollbar styles for horizontal scrolling in code blocks */
    pre::-webkit-scrollbar {
      height: 8px;
    }

    pre::-webkit-scrollbar-track {
      background: transparent;
    }

    pre::-webkit-scrollbar-thumb {
      background: #888;
      border-radius: 3px;
    }

    pre::-webkit-scrollbar-thumb:hover {
      background: #555;
    }

    /* Animation keyframes */
    @keyframes fadeIn {
      from {
        opacity: 0;
        backdrop-filter: blur(0px);
      }
      to {
        opacity: 1;
        backdrop-filter: blur(2px);
      }
    }

    /* Toggle switch styles */
    input:checked ~ .toggle-dot {
      transform: translateX(100%);
    }

    input:checked ~ .toggle-bg {
      background-color: #4f46e5;
    }

    .toggle-bg {
      transition: background-color 0.3s ease-in-out;
    }
  </style>
{/if}
