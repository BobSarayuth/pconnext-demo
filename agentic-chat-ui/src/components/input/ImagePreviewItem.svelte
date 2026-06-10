<script>
  export let image
  export let index
  export let onRemove
</script>

<div
  class="relative flex items-center bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-2 pr-8 gap-2.5 flex-shrink-0 z-0 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors duration-200 group"
>
  <div class="w-8 h-8 rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-900 flex-shrink-0">
    <img src={image.url} alt={`Preview of ${image.file.name}`} class="h-full w-full object-cover" />
  </div>
  <div class="flex-grow min-w-0">
    <p class="text-xs font-medium truncate text-slate-800 dark:text-slate-200">
      {image.file.name.length > 15 ? image.file.name.slice(0, 9) + '...' + image.file.name.slice(-4) : image.file.name}
    </p>
    <p class="text-[10px] text-slate-500 dark:text-slate-400">
      {(image.file.size / 1024).toFixed(1)} KB
    </p>
  </div>
  <button
    on:click={() => onRemove(index)}
    class="absolute -top-1.5 -right-1.5 p-1 m-0 rounded-md bg-slate-200 dark:bg-slate-800 border-none transition-colors duration-200 z-20 opacity-0 group-hover:opacity-100 hover:bg-slate-700 dark:hover:bg-slate-600"
    tabindex="0"
    aria-label={`Remove image ${image.file.name}`}
  >
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      class="lucide lucide-x h-3 w-3 text-slate-600 dark:text-slate-300"
    >
      <path d="M18 6 6 18"></path>
      <path d="m6 6 12 12"></path>
    </svg>
  </button>
</div>
