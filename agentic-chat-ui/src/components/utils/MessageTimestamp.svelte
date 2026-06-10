<script>
  import dayjs from 'dayjs'

  export let index
  export let messages = []
  export let elapsed = false
  export { className as class }
  let className = ''

  const message = messages[index]

  // Format time for display
  function formatTime(dateString) {
    if (!dateString) return ''
    return dayjs(dateString).format('h:mm A')
  }

  // Calculate elapsed seconds
  function getElapsedSeconds(message, index) {
    const prevMessage = messages[index + 1]
    if (!prevMessage || !prevMessage.createdDate) return ''

    const seconds = dayjs(message.createdDate).diff(dayjs(prevMessage.createdDate), 'millisecond')
    return `(${(seconds / 1000).toFixed(2)} sec)`
  }
</script>

<span class={className}>
  {formatTime(message.createdDate)}
  {#if elapsed}
    <span class="text-gray-400 dark:text-gray-500 transition-theme">{getElapsedSeconds(message, index)}</span>
  {/if}
</span>
