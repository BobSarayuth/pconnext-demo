<script>
  import BaseDebugModal from './ContainerModalBase.svelte'
  import Highlight from 'svelte-highlight'
  import json from 'svelte-highlight/languages/json'

  // Reference to the base modal
  let baseModal

  // Expose the open/close methods
  export function open() {
    baseModal.open()
  }

  export function close() {
    baseModal.close()
  }
</script>

<BaseDebugModal bind:this={baseModal} title="Debug Info">
  <svelte:fragment slot="default" let:sessionData let:messageData let:formatJson>
    <!-- Message Store -->
    <div class="rounded overflow-hidden">
      <div class="px-3 py-2 border-b border-gray-700 flex justify-between items-center">
        <h2 class="text-sm font-medium text-gray-200">Message Store</h2>
      </div>
      <div class="overflow-auto">
        <Highlight language={json} code={formatJson(messageData)} />
      </div>
    </div>

    <!-- Session Store -->
    <div class="rounded overflow-hidden">
      <div class="px-3 py-2 border-b border-gray-700 flex justify-between items-center">
        <h2 class="text-sm font-medium text-gray-200">Session Store</h2>
      </div>
      <div class="overflow-auto max-h-[30vh]">
        <Highlight language={json} code={formatJson(sessionData)} />
      </div>
    </div>

    <!-- Local Storage -->
    <div class="rounded overflow-hidden">
      <div class="px-3 py-2 border-b border-gray-700 flex justify-between items-center">
        <h2 class="text-sm font-medium text-gray-200">Local Storage</h2>
      </div>
      <div class="overflow-auto max-h-[30vh]">
        <Highlight language={json} code={formatJson(Object.fromEntries(Object.keys(localStorage).map((key) => [key, localStorage.getItem(key)])))} />
      </div>
    </div>
  </svelte:fragment>
</BaseDebugModal>
