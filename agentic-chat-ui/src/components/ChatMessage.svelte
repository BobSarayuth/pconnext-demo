<script>
  import dayjs from 'dayjs'
  import relativeTime from 'dayjs/plugin/relativeTime'
  import isToday from 'dayjs/plugin/isToday'
  import isYesterday from 'dayjs/plugin/isYesterday'

  import { onMount } from 'svelte'

  import { messageStore } from '../utils/messageStore.js'
  import { sessionStore } from '../utils/sessionStore.js'

  import MarkdownRenderer from './utils/MarkdownRenderer.svelte'
  import RobotIcon from './utils/RobotIcon.svelte'
  import MessageTimestamp from './utils/MessageTimestamp.svelte'
  import ToolDataModal from './modals/ToolDataModal.svelte'

  // Modal state
  let isModalOpen = false
  let currentToolData = null
  let currentStateData = null
  let modalMode = 'tool'
  let modalModeName = ''
  let isHiddenExternal = false
  let modelSelected = {}
  let modelOptions = {}
  let messages = []
  let isThinking = true
  let elMainBox

  sessionStore.subscribe((store) => {
    modelOptions = store.modelOptions
    modelSelected = store.modelSelected
    isThinking = store.isThinking
    isHiddenExternal = store.isHiddenExternal
  })

  const openToolModal = (tool) => {
    currentToolData = tool || {}
    currentStateData = null
    modalMode = 'tool'
    isModalOpen = true
  }

  const openStateModal = (state, name) => {
    currentStateData = state
    currentToolData = null
    modalMode = 'state'
    isModalOpen = true
    modalModeName = name
  }

  const closeModal = () => {
    isModalOpen = false
    currentToolData = null
    currentStateData = null
  }

  dayjs.extend(relativeTime)
  dayjs.extend(isToday)
  dayjs.extend(isYesterday)

  // Function to scroll chat to bottom
  function adjustScrollHeight() {
    if (!elMainBox) return
    elMainBox.scrollTop = elMainBox.scrollHeight
  }

  // Subscribe to the message store
  onMount(() => {
    const unsubscribe = messageStore.subscribe((value) => {
      messages = value
      // Apply animation classes after DOM update
      setTimeout(() => {
        // animateMessages()
        adjustScrollHeight()
      }, 0)
    })

    return () => {
      unsubscribe()
    }
  })

  // function animateMessages() {
  //   if (!elMessageBox) return

  //   const messageElements = elMessageBox.querySelectorAll('#box-hm, #box-ai')
  //   messageElements.forEach((element, index) => {
  //     // Stagger the animations for a nice effect
  //     setTimeout(() => {
  //       element.classList.add('show-message')
  //     }, index * 100)
  //   })
  // }

  // Update toggle function to handle Tailwind classes
  function toggleReasoning(event, isLastMessage) {
    if (isLastMessage) return

    const button = event.currentTarget
    const target = button.getAttribute('collapse-data')
    const collapseElement = document.querySelector(`[collapse-target="${target}"]`)

    if (collapseElement.classList.contains('max-h-0')) {
      collapseElement.classList.remove('max-h-0', 'opacity-0')
      collapseElement.classList.add('opacity-100', 'py-3')
      button.classList.remove('border-b', 'rounded-b-md')
    } else {
      collapseElement.classList.add('max-h-0', 'opacity-0')
      collapseElement.classList.remove('opacity-100', 'py-3')
      button.classList.add('border-b', 'rounded-b-md')
    }
  }

  // Extract username from message
  function getUsernameFromMessage(message) {
    if (!message.agentReasoning.length) return 'user'
    const [reason] = message.agentReasoning

    const showUser = reason?.state?.username || 'user'
    return showUser.substr(0, 12) + (showUser.length > 12 ? '...' : '')
  }

  // Format date for display
  function formatDate(dateString) {
    if (!dateString) return 'Today'

    const date = dayjs(dateString)

    if (date.isToday()) {
      return 'Today'
    } else if (date.isYesterday()) {
      return 'Yesterday'
    } else {
      return date.format('MMMM D, YYYY')
    }
  }

  // Function to determine if we should show date for this message
  function shouldShowDate(message, index) {
    if (index === messages.length - 1) return true
    if (!message.createdDate) return false

    const prevMessage = messages[index + 1]
    if (!prevMessage || !prevMessage.createdDate) return true

    const messageDate = dayjs(message.createdDate).format('YYYY-MM-DD')
    const prevMessageDate = dayjs(prevMessage.createdDate).format('YYYY-MM-DD')

    return messageDate !== prevMessageDate
  }

  // If next message is not deleted
  function shouldShowDeletedDivider(message, index) {
    if (index === 0 && message.deleted) return true
    const nextMessage = messages[index - 1]
    return message.deleted != nextMessage.deleted
  }

  // Add these variables for image modal
  let isImageModalOpen = false
  let currentImageUrl = ''

  const openImageModal = (url) => {
    currentImageUrl = url
    isImageModalOpen = true
  }

  const closeImageModal = () => {
    isImageModalOpen = false
    currentImageUrl = ''
  }
</script>

<main
  bind:this={elMainBox}
  class="flex flex-col flex-1 pt-16 m-1 overflow-y-auto overflow-x-hidden transition-theme
  {isHiddenExternal ? 'pb-8' : 'pb-40'}
  "
>
  <div class="max-w-4xl w-full mx-auto flex flex-col-reverse flex-1 transition-theme">
    {#each messages as message, index}
      {@const isLastMessage = index === 0}
      {@const isCurrentThinking = isLastMessage && isThinking}

      {#if message.deleted && shouldShowDeletedDivider(message, index)}
        <div class="flex items-center justify-center my-5 opacity-50">
          <div class="w-full max-w-2xl flex items-center">
            <div class="flex-grow border-t border-gray-300 dark:border-gray-600 transition-theme"></div>
            <div class="mx-4 text-sm italic text-gray-500 dark:text-gray-400 transition-theme">This session has ended.</div>
            <div class="flex-grow border-t border-gray-300 dark:border-gray-600 transition-theme"></div>
          </div>
        </div>
      {/if}
      {#if message.role === 'HUMAN'}
        {@const username = getUsernameFromMessage(message)}
        {@const usedTools = message.agentReasoning.length > 0 ? message.agentReasoning.flatMap((e) => e.usedTools).filter((e) => e) : []}
        <div id="box-hm" class="flex flex-col items-end text-sm sarabun transition-theme show-message">
          <span class="text-xs text-gray-500 dark:text-gray-400 mb-1 transition-theme username">{username}</span>

          {#if message.content}
            <div class="max-w-md bg-blue-500 text-white rounded-lg py-2 px-4 shadow">
              <p class="content text-sm break-words">{message.content}</p>
            </div>
          {/if}
          {#if usedTools.length > 0}
            <div class="flex flex-row gap-2 max-w-md py-2">
              {#each usedTools as tool}
                {#if tool?.tool === 'image_thumbnails' || tool?.tool === 'image_thumtails'}
                  <div class="flex flex-col">
                    {#if !tool.toolInput.image_url.startsWith('http')}
                      <img src={tool.toolOutput} alt="Generated thumbnail" class="rounded-lg max-w-60 max-h-60 shadow-md transition-transform transform" />
                    {:else}
                      <button
                        type="button"
                        aria-label="Open full size image"
                        on:click={() => openImageModal(tool.toolInput.image_url)}
                        on:keydown={(e) => e.key === 'Enter' && openImageModal(tool.toolInput.image_url)}
                        class="relative group text-left"
                      >
                        <img
                          src={tool.toolOutput}
                          alt="Thumbnail with expand option"
                          class="rounded-lg bg-gray-100 max-w-60 max-h-60 shadow-md transition-transform transform hover:scale-110 animate-bounce-gentle hover:shadow-lg"
                        />
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          class="absolute top-2 right-2 w-5 h-5 text-white bg-black bg-opacity-50 rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          stroke-width="2"
                          stroke-linecap="round"
                          stroke-linejoin="round"
                        >
                          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                          <polyline points="15 3 21 3 21 9"></polyline>
                          <line x1="10" y1="14" x2="21" y2="3"></line>
                        </svg>
                      </button>
                    {/if}
                  </div>
                {:else if tool?.tool === 'sticker'}
                  <div class="flex flex-col">
                    <img src={tool.toolOutput} alt="Sticker" class="rounded-lg w-50 transition-transform transform hover:scale-110 animate-bounce-gentle" />
                  </div>
                {:else}
                  <p class="content text-sm break-words">{message.content}</p>
                {/if}
              {/each}
            </div>
          {/if}
          <MessageTimestamp class="text-xs text-gray-500 dark:text-gray-400 mt-1 transition-theme" {messages} {index} />
        </div>
      {:else}
        {@const isExpanded = isLastMessage || isCurrentThinking}
        {@const isLoading = isCurrentThinking && modelOptions.reasoning}
        <div id="box-ai" class="flex items-start text-sm sarabun transition-theme show-message">
          <RobotIcon isThinking={isLoading} />
          <div class="flex flex-col">
            <span class="text-xs text-gray-500 dark:text-gray-400 mb-1 transition-theme {isLoading ? 'loading-dots' : ''}">{isLoading ? 'Thinking' : modelSelected?.name || 'AI'}</span>
            {#if modelOptions.reasoning}
              {#if message.agentReasoning.length === 0}
                <div class="max-w-2xl w-100 border border-sky-400 dark:border-sky-800 rounded-lg py-3 px-4 transition-theme mb-2 overflow-hidden">
                  <div class="flex items-center mb-2">
                    <div class="shimmer w-24 h-5 rounded bg-gradient-to-r from-gray-200 via-white to-gray-200 dark:from-gray-700 dark:via-gray-600 dark:to-gray-700"></div>
                  </div>
                  <div class="flex flex-col space-y-3">
                    <div class="shimmer w-full h-4 rounded bg-gradient-to-r from-gray-200 via-white to-gray-200 dark:from-gray-700 dark:via-gray-600 dark:to-gray-700"></div>
                    <div class="shimmer w-5/6 h-4 rounded bg-gradient-to-r from-gray-200 via-white to-gray-200 dark:from-gray-700 dark:via-gray-600 dark:to-gray-700"></div>
                  </div>
                  <div class="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700">
                    <div class="shimmer w-20 h-3 rounded bg-gradient-to-r from-gray-200 via-white to-gray-200 dark:from-gray-700 dark:via-gray-600 dark:to-gray-700"></div>
                  </div>
                </div>
              {:else}
                <div class="max-w-2xl min-w-2xs z-1">
                  <button
                    collapse-data={'collapse-' + index}
                    on:click={(e) => toggleReasoning(e, isLastMessage)}
                    class="flex items-center justify-center gap-1 px-3 py-1.5 text-xs font-medium rounded-t-md
                      border-x border-t transition-theme duration-200 bg-slate-100 dark:bg-slate-800
                      {message.error
                      ? ' border-red-600 dark:border-red-500/30 text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/20'
                      : ' border-sky-600 dark:border-sky-700/30 text-sky-900 dark:text-sky-300'}
                      {isLastMessage ? '' : `cursor-pointer ${message.error ? 'hover:bg-red-100 dark:hover:bg-red-700/30' : 'hover:bg-sky-100 dark:hover:bg-sky-700/50'}`}
                      {isExpanded ? '' : 'border-b rounded-b-md'}"
                  >
                    <span class="flex items-center">
                      <span class="mx-1">Agent Reasoning</span>
                    </span>
                    <svg class="w-3.5 h-3.5 transition-transform duration-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path
                        d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
                      ></path>
                    </svg>
                  </button>
                </div>
                <div
                  id="think-box"
                  collapse-target={'collapse-' + index}
                  class="w-full overflow-hidden transition-theme duration-300 ease-out border-1 mb-0
                    min-w-lg max-w-2xl rounded-b-lg rounded-tr-lg px-3
                    {message.error ? ' border-red-600 dark:border-red-500/30' : ' border-sky-600 dark:border-sky-700/30'}
                    {isExpanded ? 'opacity-100 py-3' : 'max-h-0 opacity-0'}"
                  style="margin-top: -1px;"
                >
                  {#each message.agentReasoning as reason}
                    {#if reason.messages.join('').length || reason.usedTools.length}
                      <div class="flex flex-col dark:text-gray-300 text-gray-600 sarabun transition-theme mb-1">
                        <div class="transition-all duration-300">
                          <div class="flex items-center mb-2">
                            <div class="agent-info flex flex-col">
                              <span class="font-medium text-sky-800 dark:text-sky-300 text-sm transition-theme">{reason.agentName}</span>
                              <span class="text-xs -mt-0.5 text-gray-500 dark:text-gray-400 transition-theme">{reason.meta.modelName}</span>
                            </div>
                          </div>
                          <div class="pl-2">
                            {#if Object.keys(reason.state).length}
                              <button
                                on:click={() => openStateModal(reason.state)}
                                class="inline-flex items-center px-2 py-1 mb-1 text-xs font-medium rounded-md
                              bg-indigo-100 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-200
                              hover:bg-indigo-200 dark:hover:bg-indigo-800 border border-sky-100
                              dark:border-indigo-800/50 cursor-pointer transition-theme
                              hover:shadow transform transition-all duration-150"
                              >
                                <svg class="w-3.5 h-3.5 mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                  <path d="M21 10V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16v-2"></path>
                                  <path d="M16.5 9.4 7.55 4.24"></path>
                                  <polyline points="3.29 7 12 12 20.71 7"></polyline>
                                  <line x1="12" y1="22" x2="12" y2="12"></line>
                                </svg>
                                <span class="relative"> state </span>
                              </button>
                            {/if}
                            {#each reason.usedTools as used}
                              {@const usedTool = message.usedTools.find((e) => e.id === used.id)}
                              <button
                                on:click={() => openToolModal(usedTool)}
                                class="inline-flex items-center text-xs font-medium rounded-md transition-theme transform transition-all duration-150 bg-sky-50 dark:bg-sky-900/30 text-sky-700 dark:text-sky-300 hover:bg-sky-100 dark:hover:bg-sky-800 border border-sky-100 hover:shadow dark:border-sky-800/50 cursor-pointer px-2 py-1 mb-1"
                              >
                                <svg class="w-3.5 h-3.5 mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                  <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
                                </svg>
                                {used.tool}
                              </button>
                            {/each}
                            {#each reason.invalids as used}
                              <div class="max-w-4xl mx-auto mb-2 overflow-hidden transition-all duration-200">
                                <div class="flex items-center gap-2 py-1 text-xs">
                                  <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                                    <path
                                      fill-rule="evenodd"
                                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                                      clip-rule="evenodd"
                                    />
                                  </svg>
                                  <span class="flex">{used.name} :: {used.message}</span>
                                </div>
                              </div>
                            {/each}
                          </div>
                          <MarkdownRenderer class="reasoning-content pl-2 border-sky-100 dark:border-sky-900/30 transition-theme" content={reason.messages.join('')} />
                        </div>
                      </div>
                    {/if}
                  {/each}
                </div>
                <div
                  class="pb-2 border-b border-gray-200 dark:border-gray-700 transition-theme {!message.usedTools.length && !Object.keys(message.state?.artifact || {}).length
                    ? 'border-hidden'
                    : 'mt-3 mb-1'}"
                >
                  <div class="flex flex-wrap gap-2">
                    {#if Object.keys(message.state?.artifact || {}).length}
                      <button
                        on:click={() => openStateModal(message.state.artifact, 'Artifact')}
                        class="px-2 py-1 bg-indigo-100 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200 rounded-md text-xs font-medium flex items-center hover:bg-indigo-200 dark:hover:bg-indigo-800 transition-colors cursor-pointer transition-theme"
                      >
                        <svg class="w-3.5 h-3.5 mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M21 10V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16v-2"></path>
                          <path d="M16.5 9.4 7.55 4.24"></path>
                          <polyline points="3.29 7 12 12 20.71 7"></polyline>
                          <line x1="12" y1="22" x2="12" y2="12"></line>
                        </svg>
                        <span class="relative font-semibold"> ARTIFACT </span>
                      </button>
                    {/if}

                    {#if message.usedTools.length > 0}
                      {#each message.usedTools as tool}
                        {#if tool.toolOutput}
                          <button
                            on:click={() => openToolModal(tool)}
                            class="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md
                              bg-sky-50 dark:bg-sky-900 text-sky-700 dark:text-sky-300
                              hover:bg-sky-100 dark:hover:bg-sky-800 border border-sky-100
                              dark:border-sky-800/50 cursor-pointer transition-theme
                              hover:shadow transform transition-all duration-150"
                          >
                            <svg class="w-3.5 h-3.5 mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
                            </svg>
                            {tool.tool}
                          </button>
                        {/if}
                      {/each}
                    {/if}
                  </div>
                </div>
              {/if}
            {/if}
            {#if message.content.trim()}
              <div id="message-box" class="max-w-xl bg-gray-200 dark:bg-gray-700 rounded-lg py-2 px-4 mt-2 mb-0 shadow text-gray-800 dark:text-white transition-theme">
                <div class="whitespace-pre-wrap break-words">{@html message.content.replace(/[\n]/gi, '<br>')}</div>
              </div>
            {:else if !modelOptions.reasoning}
              <div id="message-box" class="max-w-xl bg-gray-200 dark:bg-gray-700 rounded-lg py-2 px-4 mt-2 mb-0 shadow text-gray-800 dark:text-white transition-theme">
                <div class="whitespace-pre-wrap break-words">
                  {#if message.agentReasoning.length === 0}
                    <span class="loading-dots">Writing</span>
                  {:else}
                    {@const reason = message.agentReasoning[message.agentReasoning.length - 1]}
                    {@const msgs = reason.messages.filter((e) => e.trim().length)}
                    {#if msgs.length === 0}
                      <span class="loading-dots">Using tools {reason.usedTools.map((e) => e.tool).join(', ')} </span>
                    {:else}
                      {@html reason.messages.join('').replace(/[\n]/gi, '<br>')}
                    {/if}
                  {/if}
                </div>
              </div>
            {/if}
            {#if !isThinking}
              <MessageTimestamp class="text-xs text-gray-500 dark:text-gray-400 mt-1 transition-theme" elapsed={true} {messages} {index} />
            {/if}
          </div>
        </div>
      {/if}

      {#if shouldShowDate(message, index)}
        <div class="flex justify-center my-4">
          <div class="px-4 py-1 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs transition-theme">
            {formatDate(message.createdDate)}
          </div>
        </div>
      {/if}
    {/each}
  </div>
  <!-- Use unified ToolDataModal component for both tools and state -->
  <ToolDataModal isOpen={isModalOpen} toolData={currentToolData} stateData={currentStateData} mode={modalMode} modeName={modalModeName} onClose={closeModal} />
</main>

<!-- Add image modal at the bottom -->
{#if isImageModalOpen}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-opacity-50 backdrop-blur-sm transition-opacity" on:click={closeImageModal}>
    <div class="relative max-w-screen-xl max-h-screen p-4">
      <img src={currentImageUrl} alt="Fullscreen view" class="max-w-full max-h-[90vh] object-contain" />
    </div>
  </div>
{/if}

<style>
  @keyframes loadingDots {
    0% {
      content: '';
    }
    33% {
      content: '.';
    }
    66% {
      content: '..';
    }
    100% {
      content: '...';
    }
  }

  @keyframes dot-pulse {
    0% {
      transform: scale(0.2);
      opacity: 0.6;
    }
    50% {
      transform: scale(1);
      opacity: 1;
    }
    100% {
      transform: scale(0.2);
      opacity: 0.6;
    }
  }

  @keyframes shimmer {
    0% {
      background-position: -200% 0;
    }
    100% {
      background-position: 200% 0;
    }
  }

  .shimmer {
    background-size: 200% 100%;
    animation: shimmer 2s infinite linear;
  }

  .loading-dots {
    position: relative;
  }

  .loading-dots::after {
    content: '';
    animation: loadingDots 1s infinite;
    display: inline-block;
    position: relative;
  }

  #box-hm.show-message,
  #box-ai.show-message {
    animation: popup 0.2s ease-out forwards;
  }

  .username {
    display: inline-block;
  }

  .username::first-letter {
    text-transform: uppercase;
  }

  button {
    transition: background-color 0.2s ease;
  }

  .transition-opacity {
    transition: opacity 0.2s ease-in-out;
  }

  @keyframes ping {
    75%,
    100% {
      transform: scale(2);
      opacity: 0;
    }
  }

  .animate-ping {
    animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
  }
</style>
