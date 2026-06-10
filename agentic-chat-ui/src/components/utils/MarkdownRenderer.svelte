<script>
  import Markdown from 'markdown-hljs'

  // Props for the component
  export let content = ''
  export { className as class }

  let className = ''

  $: markedDown = Markdown(content)
</script>

<p class={'break-words ' + className}>
  {@html markedDown}
</p>

<style>
  :global(.hljs.json) {
    background: transparent !important;
    padding: 0.5em 0;
  }

  :global(a) {
    display: inline-flex;
    align-items: center;
    max-width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    position: relative;
    padding-left: 20px;
    text-decoration: underline;
  }

  :global(a:before) {
    content: '';
    position: absolute;
    left: 0;
    width: 14px;
    height: 14px;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='16' height='16'%3E%3Cpath fill='currentColor' d='M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V12H19V19Z'%3E%3C/path%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-size: contain;
  }

  :global(html.dark a:before) {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='16' height='16'%3E%3Cpath fill='white' d='M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V12H19V19Z'%3E%3C/path%3E%3C/svg%3E");
  }
</style>
