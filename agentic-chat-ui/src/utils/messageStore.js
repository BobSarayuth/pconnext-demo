import { writable } from 'svelte/store'

const createChunkStore = () => {
  const { subscribe, update } = writable([])

  return {
    subscribe,
    add: (chunk) => update((chunks) => [...chunks, chunk]),
    clear: () => update(() => []),
  }
}

export const chunkStore = createChunkStore()

const regexSticker = /^:(https?:\/\/.+):/gi
const regexAttachment = /^https?:\/\/.+/gi
const createMessageStore = () => {
  const { subscribe, update } = writable([])

  return {
    subscribe,

    addHumanMessage: (question, files, username = 'user') => {
      const usedTools = []
      const isFileType = question.match(regexAttachment)
      const isSticker = question.match(regexSticker)
      if (isFileType) {
        usedTools.push({
          id: '',
          tool: 'image_thumbnails',
          toolInput: { image_url: question },
          toolOutput: question,
        })
        question = ''
      } else if (isSticker) {
        usedTools.push({
          id: '',
          tool: 'sticker',
          toolInput: { image_url: question.replace(regexSticker, '$1') },
          toolOutput: question.replace(regexSticker, '$1'),
        })
        question = question.replace(regexSticker, '').trim()
      }

      for (const file of files) {
        if (file.file.type.startsWith('image/')) {
          usedTools.push({
            id: '',
            tool: 'image_thumbnails',
            toolInput: { image_url: file.file.name },
            toolOutput: file.url,
          })
        }
      }

      return update((state) => [
        {
          role: 'HUMAN',
          content: question,
          createdDate: new Date().toISOString(),
          usedTools: [],
          agentReasoning: [{ state: { username }, usedTools }],
        },
        ...state,
      ])
    },

    // {
    //   "id": "run-89ce7dd1-31ae-4b2d-b971-8ff1de1c2bcc",
    //   "type": "AIMessageChunk",
    //   "name": null,
    //   "content": "สวัสดี",
    //   "tool_calls": [],
    //   "invalid_tool_calls": [],
    //   "usage": null,
    //   "langgraph_step": 1,
    //   "langgraph_node": "agent",
    //   "ls_provider": "google_vertexai",
    //   "ls_model_name": "gemini-2.0-flash-001",
    //   "ls_model_type": "chat"
    // }

    initAIMessage: () => {
      chunkStore.clear()
      return update((state) => [
        {
          chatId: null,
          sessionId: null,
          role: 'AI',
          content: '',
          structured: null,
          agentReasoning: [],
          usedTools: [],
          chatType: 'INTERNAL',
          createdDate: new Date().toISOString(),
        },
        ...state,
      ])
    },
    submitAIMessage: (message, tools, state_agent) =>
      update((state) => {
        const lastMessage = state[0]
        if (lastMessage.role === 'AI') {
          lastMessage.content = message
          lastMessage.usedTools = tools
          lastMessage.state = state_agent
          lastMessage.createdDate = new Date().toISOString()
          return [...state]
        }
      }),

    appendAIMessageChunk: (chunk) =>
      update((state) => {
        const lastMessage = state[0]

        const getTools = (tools = []) =>
          tools.map((e) => ({
            id: e.id,
            tool: e.name,
          }))

        if (lastMessage.role === 'AI') {
          const itemReason = lastMessage.agentReasoning.find((e) => e.nodeId === chunk.id)
          if (!itemReason) {
            lastMessage.agentReasoning.push({
              messages: chunk.type === 'tool' ? [] : [chunk.content],
              structured: chunk.structured,
              usedTools: getTools(chunk.tool_calls),
              invalids: [],
              state: chunk.state || {},
              nodeId: chunk.id,
              agentName: chunk.langgraph_node,
              meta: {
                step: chunk.langgraph_step,
                provider: chunk.ls_provider,
                modelName: chunk.ls_model_name,
                modelType: chunk.ls_model_type,
              },
            })
          } else {
            itemReason.messages.push(chunk.content)
            itemReason.usedTools = [...itemReason.usedTools, ...getTools(chunk.tool_calls)]
          }

          return [...state]
        }
      }),

    errorMessage: (chunk) => {
      return update((state) => {
        const lastMessage = state[0]
        lastMessage.agentError = true

        if (lastMessage.agentReasoning.length - 1 < 0) {
          window.setErrorMessage(chunk)
          return [...state]
        }

        const itemReason = lastMessage.agentReasoning[lastMessage.agentReasoning.length - 1]
        itemReason.invalids.push(chunk)

        return [...state]
      })
    },

    setMessages: (messages = []) => {
      return update(() => [
        ...messages.map((e) => {
          if (e.role !== 'AI') return e
          const itemReason = e.agentReasoning[e.agentReasoning.length - 1]
          return Object.assign(e, { error: itemReason.invalids.length !== 0 })
        }),
      ])
    },

    resetMessageStore: () => update(() => []),
  }
}

export const messageStore = createMessageStore()
