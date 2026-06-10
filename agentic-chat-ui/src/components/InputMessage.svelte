<script>
  import { onMount } from 'svelte'
  import consts from '../utils/constraints'
  import { sessionStore } from '../utils/sessionStore'
  import { messageStore } from '../utils/messageStore'
  import { XHR } from '../utils/XHR'
  import stickers from '../utils/stickerStore'
  import ImagePreviewItem from './input/ImagePreviewItem.svelte'
  import SessionResetButton from './navigation/SessionResetButton.svelte'
  import { tippy } from 'svelte-tippy'
  import { v7 as uuidv7 } from 'uuid'

  const { agent, id } = $props()

  let messageText = $state('')
  let isDisabled = $state(false)
  let isIterationMode = $state(false)
  let isAskAIMode = $state(false)
  let iterationCount = $state(10)
  let isThinking = $state(false)
  let elMessageInput = $state(null)
  let showStickerPopup = $state(false)

  let modelSelected = $state({})
  let modelAgents = $state([])
  let username = $state('user')
  let sessionId = $state(id)
  let agentRoute = $state(agent)
  let messages = []
  let rotatingState

  let messageHistory = []
  let historyIndex = -1

  let isHiddenExternal = $state(false)

  const handleSessionReset = () => {
    sessionId = ''
    showStickerPopup = false
    isHiddenExternal = false
    rotatingState.set(true)
    messageStore.resetMessageStore()
    updateSessionId()
    clearTextarea()
    adjustTextareaHeight()
    uploadAttachments = []
  }

  const updateSessionId = (sessionId, replaced = false) => {
    window.setTitle(modelSelected, sessionId)
    updateSessionStore()
    if (!replaced) {
      window.routePushState(agentRoute, sessionId)
    } else {
      window.routeReplaceState(agentRoute, sessionId)
    }
  }

  const updateSessionStore = () => {
    sessionStore.update((store) => ({
      ...store,
      handleSessionReset,
      isDisabled,
      isHiddenExternal,
      isThinking,
      isIterationMode,
      isAskAIMode,
      iterationCount,
      modelSelected,
      sessionId,
      agentRoute,
      username,
    }))
  }

  updateSessionStore()
  messageStore.subscribe((value) => {
    messages = value

    if (!messages.length) return

    const lastMessage = messages[0]
    if (lastMessage.chatType === 'EXTERNAL' && lastMessage.deleted) {
      isHiddenExternal = true
    } else {
      isHiddenExternal = false
    }
    updateSessionStore()
  })

  sessionStore.subscribe((store) => {
    rotatingState = store.rotatingState
    modelSelected = store.modelSelected
    modelAgents = store.modelAgents
    agentRoute = store.agentRoute
    username = store.username || 'user'
  })

  const clearTextarea = () => {
    messageText = ''
    historyIndex = -1
  }

  const disableMessage = () => {
    isDisabled = true
    updateSessionStore()
  }

  const enableMessage = () => {
    isDisabled = false
    updateSessionStore()
  }

  const toggleBatchMessage = () => {
    if (isDisabled) return
    isIterationMode = !isIterationMode
    if (iterationCount == '') {
      iterationCount = 1
    }
  }

  const toggleAskAI = () => {
    if (isDisabled) return
    isAskAIMode = !isAskAIMode
  }

  const saveMessageToHistory = (message) => {
    if (!message.trim()) return

    const existingIndex = messageHistory.findIndex((m) => m === message)

    if (existingIndex !== -1) {
      messageHistory.splice(existingIndex, 1)
    }

    messageHistory.unshift(message)

    if (messageHistory.length > 50) {
      messageHistory = messageHistory.slice(0, 50)
    }

    localStorage.setItem(consts.INPUT_HISTORY, JSON.stringify(messageHistory))
  }

  const navigateHistory = (direction) => {
    if (messageHistory.length === 0) return

    let resetPosition = false
    if (direction === 'up') {
      if (historyIndex < messageHistory.length - 1) {
        historyIndex++
        messageText = messageHistory[historyIndex]
        resetPosition = true
      }
    } else if (direction === 'down') {
      if (historyIndex > 0) {
        historyIndex--
        messageText = messageHistory[historyIndex]
        resetPosition = true
      } else if (historyIndex === 0) {
        resetPosition = true
      }
    }

    if (resetPosition) {
      setTimeout(() => {
        adjustTextareaHeight()
        if (elMessageInput) {
          elMessageInput.selectionStart = elMessageInput.selectionEnd = elMessageInput.value.length
        }
      }, 0)
    }
  }

  const fetchHistory = async () => {
    if (!sessionId || !modelSelected) return

    try {
      const res = await fetch(window.urlProxy(agentRoute, `/chat/${sessionId}/history?order=desc`))
      if (!res.ok) {
        throw new Error(`API History :: ${res.status}`)
      }

      const data = await res.json()
      if (!data.length) return window.routePushState(agentRoute)
      messageStore.setMessages(data)
    } catch (ex) {
      if (ex.message === 'Failed to fetch') ex = { message: 'server is not available' }
      window.setErrorMessage(ex)
    }
  }

  const createTableTimer = (debug = true) => {
    const timers = {}
    const timeState = $state([])

    return {
      start: (name) => {
        timers[name] = {
          name,
          start: new Date(),
          elapsed: 0,
        }
        timeState.push(name)
      },
      end: (name) => {
        if (!timers[name]) {
          console.warn(`Timer "${name}" not found`)
          return 0
        }

        const timer = timers[name]
        timer.elapsed = new Date() - timer.start
        timer.end = new Date()

        return timer.elapsed
      },
      print: () => {
        if (debug) {
          console.table(
            Object.values(timers).map((t) => ({
              Name: t.name,
              Duration: t.elapsed > 1000 ? `${(t.elapsed / 1000).toFixed(2)}s` : `${t.elapsed.toFixed(2)}ms`,
            })),
          )
        }
      },
      getTimeState: () => timeState,
    }
  }

  const timer = createTableTimer(false)
  const chatPrediction = (question, files = []) =>
    new Promise((resolve, reject) => {
      timer.start('chat-prediction')
      timer.start('http-sended')

      messageStore.addHumanMessage(question, uploadAttachments.length ? uploadAttachments : files, username)
      messageStore.initAIMessage()
      isThinking = true
      updateSessionStore()

      const handleStreamMessage = (e) => {
        const { mode, chunk } = JSON.parse(e.data)

        if (mode === 'init') {
          timer.start('ui-rendered')
          updateSessionId(chunk.sessionId, true)
        } else if (mode === 'messages') {
          messageStore.appendAIMessageChunk(chunk)
        } else if (mode === 'summary') {
          const { message, tools, state } = chunk
          messageStore.submitAIMessage(message, tools, state)
          timer.end('ui-rendered')
        } else {
          messageStore.errorMessage(chunk)
          window.setErrorMessage(chunk.message)
        }
      }

      const handleStreamError = (e) => {
        window.setErrorMessage(e.reason)
        reject(e.reason)
      }

      const handleStreamOpen = (e) => {
        timer.end('http-sended')
      }

      const handleStreamClose = (e) => {
        isThinking = false
        updateSessionStore()
        enableMessage()
        timer.end('chat-prediction')
        timer.print()
        if (e.type != 'error') {
          return resolve()
        }
        reject(e)
      }

      const userAgent = agentRoute === 'local' ? 'localhost-ai-ui@1.0' : ''
      const payload = { userAgent, question, attachments: [], sessionId, username, streaming: true }
      // check type
      payload.attachments = [...payload.attachments, ...files.filter((file) => file.type.startsWith('image/')).map((file) => file.url)]

      const stream = XHR(window.urlProxy(agentRoute, `/chat/prediction`), { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) })

      stream.addEventListener('message', handleStreamMessage)
      stream.addEventListener('error', handleStreamError)
      stream.addEventListener('open', handleStreamOpen)
      stream.addEventListener('close', handleStreamClose)
    })

  const sendMessage = async (saveHistory = true) => {
    if (!modelSelected) return
    let question = messageText.trim()
    if (!question && !uploadAttachments.length) return

    clearTextarea()
    adjustTextareaHeight()
    if (saveHistory) saveMessageToHistory(question)
    disableMessage()

    try {
      // Upload all attachments first
      if (!sessionId) sessionId = uuidv7()
      const uploadedFiles = await Promise.all(uploadAttachments.map((attachment) => uploadFiles(attachment.file)))

      const validFiles = uploadedFiles.filter((file) => file !== null)

      if (question.match(/^https?:\/\/.+/gi)) {
        // Fetch URL content type before adding it as an attachment
        try {
          // const response = await fetch(question, { method: 'GET' })
          // const contentType = response.headers.get('content-type')
          // console.log('URL content type:', contentType)
          const contentType = 'image/jpeg'
          // If the URL points to an image, add it as an attachment
          validFiles.push({ file: { type: contentType, name: question }, type: contentType, url: question })
          question = ''
        } catch (ex) {
          console.warn('Failed to fetch URL content type:', ex)
        }
      }

      if (validFiles.length > 0) {
        await chatPrediction(question, validFiles)
      } else if (isIterationMode) {
        for (let i = 0; i < iterationCount; i++) {
          for (const text of question.split('\n')) {
            if (text.trim()) await chatPrediction(text.trim())
          }
        }
      } else {
        await chatPrediction(question)
      }
    } catch (ex) {
      console.error('Send error:', ex)
      window.setErrorMessage(ex.message)
    } finally {
      uploadAttachments = []
    }
    focusMessageInput()
  }

  const adjustTextareaHeight = () => {
    if (!elMessageInput) return
    setTimeout(() => {
      elMessageInput.style.height = 'auto'
      if (!isDisabled) {
        elMessageInput.style.height = elMessageInput.scrollHeight + 'px'
      }
    }, 0)
    focusMessageInput()
  }

  const focusMessageInput = () => {
    if (elMessageInput) elMessageInput.focus()
  }

  const handleKeyDown = (e) => {
    const commandKey = e.ctrlKey || e.metaKey

    if (e.code === 'ArrowUp' && !e.shiftKey) {
      const cursorPosition = elMessageInput.selectionStart
      const textBeforeCursor = messageText.substring(0, cursorPosition)
      const isAtFirstLine = !textBeforeCursor.includes('\n')

      if (isAtFirstLine && (!messageText || messageHistory.includes(messageText))) {
        e.preventDefault()
        navigateHistory('up')
      }
    } else if (e.code === 'ArrowDown' && !e.shiftKey) {
      const cursorPosition = elMessageInput.selectionStart
      const textAfterCursor = messageText.substring(cursorPosition)
      const isAtLastLine = !textAfterCursor.includes('\n')

      if (isAtLastLine && (!messageText || messageHistory.includes(messageText))) {
        e.preventDefault()
        navigateHistory('down')
      }
    } else if (e.code === 'Enter' && !e.shiftKey && !commandKey) {
      sendMessage()
      historyIndex = -1
      e.preventDefault()
    } else if (e.code === 'Enter' && commandKey) {
      const curPos = elMessageInput.selectionStart
      const currentValue = elMessageInput.value
      elMessageInput.value = currentValue.substring(0, curPos) + '\n' + currentValue.substring(curPos)
      elMessageInput.selectionStart = elMessageInput.selectionEnd = curPos + 1
      adjustTextareaHeight()
    } else if (commandKey && e.code === 'KeyR') {
      historyIndex = -1
      // handleSessionReset()
      // Trigger rotate animation on the refresh button
      e.preventDefault()
      return
    } else if (commandKey && e.code === 'Delete') {
      historyIndex = -1
      e.preventDefault()
      const messageToDelete = messageText.trim()
      if (messageToDelete) {
        const indexToDelete = messageHistory.findIndex((m) => m === messageToDelete)
        if (indexToDelete !== -1) {
          messageHistory.splice(indexToDelete, 1)
          localStorage.setItem(consts.INPUT_HISTORY, JSON.stringify(messageHistory))
          clearTextarea()
        }
      }
    }
  }

  const handleWindowBeforeUnload = (e) => {
    // Save current state to localStorage if needed
    if (messageText.trim()) {
      localStorage.setItem(consts.INPUT_DRAFT, messageText)

      // Optionally show a confirmation dialog if there's unsaved content
      // Note: Many browsers ignore custom messages now for security reasons
      const confirmationMessage = 'You have unsaved changes. Are you sure you want to leave?'
      e.returnValue = confirmationMessage
      return confirmationMessage
    }
    const container = document.querySelector('body > #container')
    if (container) container.classList.add('opacity-0')
  }

  // Handle keyboard shortcut for batch message mode
  const handleBatchMessageToggle = (e) => {
    if (uploadAttachments.length) return
    toggleBatchMessage()
    e.preventDefault()
  }

  // Handle keyboard shortcut for session reset
  const handleResetSession = (e) => {
    historyIndex = -1
    handleSessionReset()
    e.preventDefault()
  }

  // Handle keyboard shortcut to focus message input
  const handleFocusInput = () => {
    historyIndex = -1
    focusMessageInput()
  }

  // Handle keyboard shortcuts with modifier keys (Ctrl/Cmd)
  const handleModifierKeyShortcuts = (e) => {
    // Skip if disabled
    if (isDisabled) return false

    const ctrlKey = e.ctrlKey || e.metaKey
    if (!ctrlKey) return false

    // Handle different keyboard shortcuts
    switch (e.code) {
      case 'Space':
        handleBatchMessageToggle(e)
        return true
      case 'KeyR':
        handleResetSession(e)
        return true
      case 'KeyV':
        const isInInputField = ['TEXTAREA', 'INPUT'].includes(document.activeElement.tagName)
        if (!isInInputField || document.activeElement.id === 'chat-textarea') {
          handleFocusInput()
          return true
        }
        break
    }

    return false
  }

  // Check if we should ignore keyboard events
  const shouldIgnoreKeyboardEvent = (e) => {
    const isInInputField = ['TEXTAREA', 'INPUT'].includes(document.activeElement.tagName)
    const isInOtherInputField = isInInputField && document.activeElement.id !== 'chat-textarea'

    // Don't capture keypresses in other input fields
    if (isInOtherInputField) return true

    // Ignore if already in an input or using special keys
    if (isInInputField || e.metaKey || e.altKey || e.ctrlKey || e.code === 'Enter') {
      return true
    }

    return false
  }

  const setupGlobalKeyboardEvents = () => {
    window.addEventListener('keydown', (e) => {
      // Skip processing if input is disabled
      if (isDisabled) return

      // Handle shortcuts with modifier keys first
      if (handleModifierKeyShortcuts(e)) return

      // Skip if we should ignore this keyboard event
      if (shouldIgnoreKeyboardEvent(e)) return

      // For all other keypresses when not in an input field, focus the message input
      focusMessageInput()
    })

    // Add window close/refresh event listener to save draft
    window.addEventListener('beforeunload', handleWindowBeforeUnload)
  }

  const cleanupGlobalKeyboardEvents = () => {
    window.removeEventListener('keydown', () => {})
    window.removeEventListener('beforeunload', handleWindowBeforeUnload)
  }

  let uploadAttachments = $state([])
  const MAX_IMAGES = 5
  const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5MB

  const uploadFiles = async (file) => {
    try {
      const res = await fetch(window.urlProxy(agentRoute, `/files/${sessionId}`), {
        method: 'POST',
        headers: {
          'Content-Type': file.type,
        },
        body: file,
      })

      if (!res.ok) {
        throw new Error('Failed to upload file')
      }

      return res.json()
    } catch (ex) {
      console.warn('Upload:', ex)
      return null
    }
  }

  const readFileAsDataURL = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target.result)
      reader.onerror = (e) => reject(e)
      reader.readAsDataURL(file)
    })

  const handleFileSelect = async (files) => {
    for (const file of files) {
      if (uploadAttachments.length >= MAX_IMAGES) {
        console.warn(`Maximum ${MAX_IMAGES} images allowed`)
        return
      }
      if (file.size > MAX_FILE_SIZE) {
        console.warn('Image size must be less than 5MB')
        return
      }

      // Check for duplicate files
      const isDuplicate = uploadAttachments.some((existingFile) => existingFile.file.name === file.name && existingFile.file.size === file.size)

      if (isDuplicate) {
        console.warn(`File "${file.name}" has already been added`)
        continue
      }

      try {
        const dataUrl = await readFileAsDataURL(file)
        uploadAttachments.push({ url: dataUrl, file: file })
      } catch (ex) {
        console.error('reading:', { file, ex })
      }
    }
    adjustTextareaHeight()
  }

  const handlePaste = async (e) => {
    const items = e.clipboardData?.items
    if (!items) return

    for (const item of items) {
      if (item.type.startsWith('image/')) {
        const file = item.getAsFile()
        handleFileSelect([file])
      }
    }
  }

  const removeImage = (index) => {
    uploadAttachments = uploadAttachments.filter((_, i) => i !== index)
    adjustTextareaHeight()
  }

  // Function to handle sticker selection and sending
  const selectSticker = (sticker) => {
    if (isDisabled) return
    showStickerPopup = false

    messageText = `:${sticker}:`
    sendMessage(false)
  }

  onMount(async () => {
    // if (!modelSelected) {
    //   window.routeReplaceState()
    // }

    isHiddenExternal = false
    messageStore.resetMessageStore()
    window.setTitle(modelSelected, sessionId)
    await fetchHistory()

    const inputHistory = localStorage.getItem(consts.INPUT_HISTORY)
    if (inputHistory) {
      try {
        messageHistory = JSON.parse(inputHistory)
      } catch (ex) {
        console.error('Error parsing message history:', ex)
        window.setErrorMessage(ex)
        messageHistory = []
      }
    }

    const inputBatchMode = localStorage.getItem(consts.INPUT_BATCH)
    if (inputBatchMode !== null) {
      try {
        isIterationMode = JSON.parse(inputBatchMode)
      } catch (ex) {
        console.error('Error parsing batch mode state:', ex)
        window.setErrorMessage(ex)
      }
    }

    // Check for draft message from previous session
    const draftMessage = localStorage.getItem(consts.INPUT_DRAFT)
    if (draftMessage) {
      messageText = draftMessage
      localStorage.removeItem(consts.INPUT_DRAFT)
    }

    adjustTextareaHeight()
    setupGlobalKeyboardEvents()

    const container = document.querySelector('body > .opacity-0')
    if (container) container.classList.remove('opacity-0')

    elMessageInput.addEventListener('paste', handlePaste)
    return () => {
      elMessageInput.removeEventListener('paste', handlePaste)
      cleanupGlobalKeyboardEvents()
    }
  })
</script>

<div class="absolute w-full p-4 bottom-0 transition-theme">
  <div id="error-message" class="max-w-4xl mx-auto mb-2 overflow-hidden transition-theme duration-200 hidden">
    <div class="flex items-center gap-2 p-3 text-sm font-medium text-red-800 bg-red-50 dark:bg-red-900/80 dark:text-red-200 rounded-lg border border-red-200 dark:border-red-800/50 shadow-sm">
      <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
      </svg>
      <span class="error flex-1"></span>
    </div>
  </div>
  <div class="input-message relative flex flex-col items-center mb-2 z-20 {isHiddenExternal ? 'hidden' : ''}">
    <div class="flex flex-col gap-2 max-w-4xl w-full backdrop-blur-sm sarabun rounded-md">
      {#if uploadAttachments.length && !isDisabled}
        <div class="w-full">
          <div class="flex flex-row gap-1.5 overflow-x-hidden pt-2 max-h-28 z-10 px-2 scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-700 scrollbar-track-transparent">
            {#each uploadAttachments as image, i}
              <ImagePreviewItem {image} index={i} onRemove={removeImage} />
            {/each}
          </div>
        </div>
      {/if}

      <div
        class="input-box resize-none max-h-[350px] text-base border-2 border-transparent flex max-w-4xl mx-auto w-full overflow-x-auto px-3 py-5 pb-12 text-gray-800 dark:text-white placeholder-gray-400 dark:placeholder-gray-400 transition-[height] duration-300 ease-in-out rounded-2xl
    {!isDisabled
          ? 'bg-white/60 dark:bg-slate-800/60 focus-within:outline-none ring-2 ring-gray-300 dark:ring-sky-900 focus-within:ring-sky-500 dark:focus-within:ring-sky-500'
          : '[background:linear-gradient(45deg,#f7fafc,#e2e8f0_50%,#f7fafc)_padding-box,conic-gradient(from_var(--border-angle),theme(colors.slate.300/.5)_80%,_theme(colors.sky.500)_86%,_theme(colors.sky.300)_90%,_theme(colors.sky.500)_94%,_theme(colors.slate.300/.5))_border-box] dark:[background:linear-gradient(45deg,#172033,theme(colors.slate.800)_50%,#172033)_padding-box,conic-gradient(from_var(--border-angle),theme(colors.slate.600/.48)_80%,_theme(colors.sky.500)_86%,_theme(colors.sky.300)_90%,_theme(colors.sky.500)_94%,_theme(colors.slate.600/.48))_border-box] animate-border h-0 pt-0'}"
      >
        {#if showStickerPopup}
          <div class="grid grid-cols-12 gap-2">
            {#each stickers as sticker}
              <button
                class="w-16 h-16 flex items-center justify-center bg-gray-100 dark:bg-slate-900 rounded-md hover:bg-gray-200 dark:hover:bg-slate-600 cursor-pointer"
                onclick={() => selectSticker(sticker)}
              >
                <img src={sticker} alt={sticker} class="w-14 h-14" />
              </button>
            {/each}
          </div>
        {:else}
          <textarea
            id="chat-textarea"
            bind:this={elMessageInput}
            bind:value={messageText}
            oninput={adjustTextareaHeight}
            onkeydown={handleKeyDown}
            disabled={isDisabled}
            class="resize-none text-base min-h-[36px] mx-auto mb-2 w-full overflow-hidden text-gray-800 dark:text-white placeholder-gray-400 dark:placeholder-gray-400 transition-all focus:outline-none disabled:min-h-0 disabled:mb-0"
            placeholder="Type your message here..."
            rows="1"
          ></textarea>
        {/if}
      </div>
    </div>

    <div class="absolute w-full h-[2.6em] bottom-0">
      <div class="max-w-4xl mx-auto flex gap-2 px-2">
        <div class="py-1 bg-transparent transition-theme" style="margin-top: -4px">
          <label
            class="flex gap-2 items-center justify-center h-8 p-2 px-3 text-sm transition-theme rounded-md
              {isAskAIMode ? 'bg-sky-100 dark:bg-slate-700' : 'bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-300'}
              {true ? 'opacity-50' : 'hover:bg-sky-50 dark:hover:bg-slate-700 cursor-pointer'}"
          >
            <input type="checkbox" id="ask-ai-checkbox" bind:checked={isAskAIMode} class="sr-only" disabled={true} />
            <div class="relative h-3 w-3 flex items-center justify-center">
              <svg
                class="absolute w-3.5 h-3.5 {isAskAIMode ? 'text-yellow-400 dark:text-yellow-300' : 'text-gray-500 dark:text-gray-400'} transition-theme"
                style="left: -4px; top: 1px;"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M12,1L9,9L1,12L9,15L12,23L15,15L23,12L15,9L12,1Z" />
              </svg>
              <svg
                class="absolute w-2 h-2 {isAskAIMode ? 'text-yellow-400 dark:text-yellow-300' : 'text-gray-500 dark:text-gray-400'} transition-theme"
                style="left: 6px; top: -3px;"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M12,1L9,9L1,12L9,15L12,23L15,15L23,12L15,9L12,1Z" />
              </svg>
            </div>
            <span class="text-gray-700 dark:text-gray-300 transition-theme">Ask AI</span>
          </label>
        </div>
        {#if isIterationMode}
          <div class="py-1 bg-transparent transition-theme" style="margin-top: -4px">
            <input
              type="number"
              min="1"
              max="100"
              maxlength="3"
              defaultvalue="10"
              bind:value={iterationCount}
              class="w-12 h-8 p-2 text-sm text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-slate-800 rounded-md text-center
              ring-gray-200 dark:ring-gray-800 focus:outline-none ring-2 focus:ring-sky-400 dark:focus:ring-sky-500 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none transition-theme"
              disabled={isDisabled}
              oninput={(e) => {
                if (e.target.value > 100) iterationCount = 100
                if (e.target.value < 1 && e.target.value != '') iterationCount = 1
              }}
            />
          </div>
        {/if}
        <div class="py-1 bg-transparent transition-theme" style="margin-top: -4px">
          <label
            class="flex gap-2 items-center justify-center h-8 p-2 px-3 text-sm transition-theme rounded-md
              {isIterationMode ? 'bg-sky-100 dark:bg-slate-700' : 'bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-300'}
              {true ? 'opacity-50' : 'hover:bg-sky-50 dark:hover:bg-slate-700 cursor-pointer'}"
          >
            <input type="checkbox" id="batch-checkbox" bind:checked={isIterationMode} class="sr-only" disabled={true} />
            {#if isIterationMode}
              <svg class="w-4 h-4 text-sky-600 dark:text-sky-500 transition-theme" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            {:else}
              <svg class="w-4 h-4 text-gray-600 dark:text-gray-400 transition-theme" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            {/if}
            <span class="text-gray-700 dark:text-gray-300 transition-theme">iterations</span>
          </label>
        </div>
        <SessionResetButton />
        <button type="button" class="flex-1" onclick={focusMessageInput} aria-label="Focus message input"> </button>

        <button
          type="button"
          use:tippy={{
            content: 'Sticker',
            placement: 'bottom',
            arrow: true,
            theme: 'custom',
            onShow: () => !isDisabled,
          }}
          class="flex items-center justify-center w-8 h-8 p-1 rounded-md focus:outline-none transition-theme
          {isDisabled ? 'opacity-50' : 'hover:bg-gray-100 dark:hover:bg-slate-700 cursor-pointer'}
          {showStickerPopup ? 'bg-sky-100 dark:bg-slate-700' : ''}"
          onclick={() => (!isDisabled ? (showStickerPopup = !showStickerPopup) : false)}
          aria-label="Toggle sticker popup"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="w-4 h-4 text-gray-600 dark:text-gray-400 {showStickerPopup ? 'text-sky-600 dark:text-sky-400' : ''} transition-theme"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M8 14s1.5 2 4 2 4-2 4-2" />
            <line x1="9" y1="9" x2="9.01" y2="9" />
            <line x1="15" y1="9" x2="15.01" y2="9" />
          </svg>
        </button>
        <label
          use:tippy={{
            content: 'Upload attactment',
            placement: 'bottom',
            arrow: true,
            theme: 'custom',
            onShow: () => !isDisabled,
          }}
          class="flex items-center justify-center w-8 h-8 p-1 rounded-md focus:outline-none transition-theme
          {isDisabled ? 'opacity-50' : 'hover:bg-gray-100 dark:hover:bg-slate-700 cursor-pointer'}"
        >
          <input
            type="file"
            accept="image/*"
            multiple
            class="hidden"
            disabled={isDisabled}
            onchange={(e) => {
              handleFileSelect(Array.from(e.target.files))
              iterationCount = ''
            }}
          />
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="w-4 h-4 text-gray-600 dark:text-gray-400 transition-theme"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
          </svg>
        </label>
        <button
          aria-label="Send message"
          use:tippy={{
            content: 'Send message',
            placement: 'bottom',
            arrow: true,
            theme: 'custom',
            onShow: () => !isDisabled,
          }}
          onclick={sendMessage}
          disabled={isDisabled}
          class="flex items-center justify-center w-8 h-8 p-1 rounded-md focus:outline-none transition-theme
          hover:bg-gray-100 dark:hover:bg-slate-700 cursor-pointer disabled:opacity-50 disabled:cursor-default disabled:hover:bg-transparent"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-gray-700 dark:text-gray-300 transition-theme" viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z"
              clip-rule="evenodd"
            />
          </svg>
        </button>
      </div>
    </div>
  </div>
</div>

<style>
  @property --border-angle {
    inherits: false;
    initial-value: 0deg;
    syntax: '<angle>';
  }

  .animate-border {
    animation: rotate-border 5s linear infinite;
    background-size: 120% 120%;
    transition: all 0.3s ease;
  }

  .animate-border:hover {
    --border-angle: 180deg;
  }

  @keyframes rotate-border {
    0% {
      --border-angle: 0deg;
    }
    100% {
      --border-angle: 360deg;
    }
  }
</style>
