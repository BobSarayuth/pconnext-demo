import { writable } from 'svelte/store'

export const sessionStore = writable({
  handleSessionReset: null,
  modelOptions: {
    reasoning: true,
  },
  isDarkMode: false,
  isDisabled: false,
  isHiddenExternal: false,
  isBatchMode: false,
  isThinking: false,
  showFullJson: false,
  username: 'user',
  sessionId: null,
  agentRoute: null,
  modelSelected: null,
})
