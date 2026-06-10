<script>
  import DarkModeButton from './navigation/DarkModeButton.svelte'
  import DebugContainer from './modals/DebugContainer.svelte'
  import HistoryContainer from './modals/HistoryContainer.svelte'
  import MenuButton from './navigation/MenuButton.svelte'
  import packageInfo from '../../package.json'
  import { fade, slide } from 'svelte/transition'
  import { onMount } from 'svelte'
  import { sessionStore } from '../utils/sessionStore'
  import { tippy } from 'svelte-tippy'

  export let agent

  let modelSelected
  let isDisabled = false
  let isModelDropdownOpen = false
  let elDropdownList
  let elToggleButton
  let modelAgents = []
  let searchQuery = ''
  let filteredModels = []
  let tentativeSelection = null
  let handleSessionReset
  let debugModal
  let historyModal
  let activeModal = null
  let searchInput

  // Unified modal handling
  const openModal = (modalType) => {
    if (modalType === 'debug') {
      activeModal = 'debug'
      debugModal.open()
    } else if (modalType === 'history') {
      activeModal = 'history'
      historyModal.open()
    } else if (modalType === 'help') {
      window.helpModalEvents?.open()
    }
  }

  const closeModals = () => {
    debugModal.close()
    historyModal.close()
    closeDropdown()
  }

  sessionStore.subscribe((store) => {
    modelSelected = store.modelSelected
    isDisabled = store.isDisabled
    handleSessionReset = store.handleSessionReset
  })

  const selectClickModel = (model) => {
    if (!model || !model.available || !handleSessionReset) return
    selectModel(model)
    handleSessionReset()
    closeDropdown()
  }

  const selectModel = (model) => {
    modelSelected = model

    sessionStore.update((store) => ({
      ...store,
      agentRoute: model.route,
      modelSelected: model,
    }))

    window.setTitle(model)
    // window.routeReplaceState(model.route)
  }

  const setTentativeSelection = (model) => {
    if (!modelSelected) {
      selectModel(model)
      handleSessionReset()
      closeDropdown()
      return
    }
    tentativeSelection = model
  }

  const cancelSelection = () => {
    tentativeSelection = null
  }

  const toggleDropdown = async () => {
    if (isDisabled) return
    window.fetchInitModel().then((res) => {
      modelAgents = res

      updateFilteredModels()

      isModelDropdownOpen = !isModelDropdownOpen
      tentativeSelection = null
      searchQuery = ''

      // Auto-focus search input when dropdown opens
      if (isModelDropdownOpen) {
        setTimeout(() => {
          searchInput?.focus()
        }, 100)
      }
    })
  }

  const closeDropdown = () => {
    sessionStore.update((store) => ({
      ...store,
      modelAgents,
    }))

    isModelDropdownOpen = false
    tentativeSelection = null
    searchQuery = ''
  }

  const handleClickOutside = (e) => {
    if (isModelDropdownOpen && elDropdownList && !elDropdownList.contains(e.target)) {
      if (elToggleButton && !elToggleButton.contains(e.target)) {
        isModelDropdownOpen = false
        tentativeSelection = null
      }
    }
  }

  const updateFilteredModels = () => {
    if (!searchQuery) {
      filteredModels = modelAgents
      return
    }

    const query = searchQuery.toLowerCase()
    filteredModels = modelAgents.filter(
      (model) => model.name.toLowerCase().includes(query) || model.display.toLowerCase().includes(query) || model.model.toLowerCase().includes(query) || model.icon.toLowerCase().includes(query),
    )
  }

  const handleKeydown = (event) => {
    if (event.key === 'Escape') closeModals()

    // When Enter is pressed and there's exactly one filtered model, select it
    if (event.key === 'Enter' && isModelDropdownOpen && filteredModels.length === 1) {
      const model = filteredModels[0]
      if (model.available) {
        setTentativeSelection(model)
        selectClickModel(model)
      }
    }
  }

  const getModelName = (model) => {
    const isVersion = (model.version || '0.0') !== '0.0'
    return `${model.display || model.name}${isVersion ? ` (${model.version})` : ''}`
  }

  $: (searchQuery, updateFilteredModels())

  onMount(async () => {
    modelAgents = await window.fetchInitModel()
    modelSelected = modelAgents.find((model) => model.route === agent)

    // Update the session store with the fetched model agents
    sessionStore.update((store) => ({
      ...store,
      modelAgents,
      modelSelected: modelSelected,
      agentRoute: agent,
    }))

    filteredModels = modelAgents

    if (agent) {
      selectModel(modelAgents.find((e) => e.route === agent))
    }

    document.addEventListener('click', handleClickOutside)

    // Set up debug modal events for global access
    window.debugModalEvents = {
      open: () => openModal('debug'),
      close: closeModals,
      updateHeaderState: (state) => {
        activeModal = state ? 'debug' : null
      },
    }

    return () => {
      document.removeEventListener('click', handleClickOutside)
    }
  })
</script>

<svelte:window on:keydown={handleKeydown} />

<DebugContainer bind:this={debugModal} />
<HistoryContainer bind:this={historyModal} />

<header
  class="shadow absolute t-0 w-full transition-theme h-auto
    {isModelDropdownOpen ? 'pb-6 bg-slate-100 dark:bg-slate-800 ' : ''} 
    px-4 py-2 flex flex-col transition-theme duration-300 ease-in-out border-b border-gray-200 dark:border-gray-700 backdrop-blur-sm z-50 transition-theme"
>
  <div class="flex justify-between items-center min-h-14">
    <div class="flex items-center space-x-4 {isModelDropdownOpen ? 'w-1/4' : ''}">
      <div id="title-model" class="flex flex-col border-r pr-5 mr-5 border-gray-300 dark:border-gray-600 transition-theme">
        <svg width="140" height="16" viewBox="0 0 179 21" fill="none" xmlns="http://www.w3.org/2000/svg">
          <g clip-path="url(#clip0_481_4834)">
            <path
              d="M8.54753 8.65648C6.61224 7.82079 4.8309 7.10239 4.8309 5.79753C4.8309 4.22877 6.57559 4.05284 7.38929 4.05284C9.03136 4.05284 10.7467 4.44869 12.4988 5.22574L12.9019 5.40901V1.63373L12.726 1.56042C11.2965 0.944644 9.30259 0.592773 7.25001 0.592773C2.16987 0.600104 0 3.43706 0 6.08343C0 9.46286 3.13019 10.7824 5.80587 11.9479C7.83646 12.835 9.55916 13.6047 9.55916 15.0561C9.55916 16.5076 7.99774 16.9988 6.363 16.9988C4.36907 16.9988 2.07457 15.8478 0.923662 15.1661L0.491153 14.9095V18.6408L0.630436 18.7215C2.26517 19.7038 3.78994 20.4588 6.46563 20.4588C11.3185 20.4588 14.3974 18.1717 14.3974 14.7702C14.3974 11.1929 11.1719 9.7854 8.54753 8.65648Z"
              class="fill-[#E0251C]"
            />
            <path
              d="M50.6478 10.5258V16.5003C49.7828 16.8082 48.5365 16.9914 47.2683 16.9914C42.8186 16.9914 40.2236 14.5283 40.2236 10.5625C40.2236 6.59657 43.0166 4.04551 47.9061 4.04551C49.9733 4.04551 51.784 4.44869 53.7266 5.28439L54.1298 5.45299V1.61173L53.9246 1.54576C51.8793 0.915322 49.7021 0.592773 47.4809 0.592773C40.2089 0.592773 35.2607 4.7859 35.2607 10.797C35.2607 16.8082 39.8204 20.4515 46.8432 20.4515C49.6801 20.4515 52.7077 19.8797 54.9435 18.9121L55.1195 18.8388V10.5185H50.6478V10.5258Z"
              class="fill-[#E0251C]"
            />
            <path
              d="M33.3611 15.7159C31.5577 16.6029 29.9743 16.9988 28.1343 16.9988C23.8752 16.9988 21.3462 14.477 21.3462 10.5698C21.3462 6.66255 23.7433 4.06017 28.083 4.06017C30.1869 4.06017 31.2352 4.59531 32.8553 5.32837L33.2511 5.51164V1.67038L33.0972 1.6044H33.0752C31.6237 1.04727 30.2309 0.592773 27.8484 0.592773C20.9723 0.592773 16.376 4.82989 16.376 10.6797C16.376 16.5296 20.5105 20.4588 27.5259 20.4588C29.7251 20.4588 31.0813 20.1216 33.581 18.9414L33.7496 18.8607V15.5106L33.3464 15.7086L33.3611 15.7159Z"
              class="fill-[#E0251C]"
            />
            <path
              d="M78.8342 1.77892C77.2362 0.957886 75.3595 0.540039 73.2483 0.540039H65.1846V20.5161H73.2483C75.3595 20.5161 77.2362 20.0982 78.8342 19.2772C80.4396 18.4488 81.6932 17.2686 82.5582 15.7658C83.4232 14.263 83.8631 12.5037 83.8631 10.5244C83.8631 8.54511 83.4232 6.78575 82.5582 5.28297C81.6859 3.78018 80.4323 2.59262 78.8342 1.77159V1.77892ZM80.3224 10.5244C80.3224 11.9172 80.0291 13.1341 79.4573 14.153C78.8855 15.1647 78.0499 15.9564 76.9869 16.5135C75.9093 17.0706 74.6191 17.3492 73.1383 17.3492H68.6153V3.70688H73.1383C74.6191 3.70688 75.9093 3.98544 76.9869 4.54257C78.0572 5.09237 78.8855 5.89141 79.4573 6.90304C80.0365 7.922 80.3224 9.14622 80.3224 10.5244Z"
              class="fill-gray-800 dark:fill-white transition-theme"
            />
            <path d="M91.3331 0.540039H87.9023V20.5161H91.3331V0.540039Z" class="fill-gray-800 dark:fill-white transition-theme" />
            <path
              d="M115.436 9.3962H105.532V12.4238H111.991C111.851 13.3621 111.551 14.1978 111.089 14.9308C110.554 15.7812 109.821 16.4483 108.919 16.9174C108.01 17.3866 106.947 17.6212 105.767 17.6212C104.411 17.6212 103.209 17.3206 102.175 16.7195C101.149 16.1257 100.335 15.2827 99.7631 14.2124C99.1913 13.1422 98.8981 11.9033 98.8981 10.5324C98.8981 9.16162 99.1913 7.9374 99.7778 6.86713C100.364 5.80418 101.185 4.96116 102.219 4.36004C103.26 3.75893 104.455 3.45838 105.767 3.45838C106.881 3.45838 107.907 3.67096 108.816 4.08881C109.725 4.50666 110.495 5.10777 111.111 5.87749L111.265 6.06809L113.845 3.89088L113.699 3.70762C112.797 2.60802 111.646 1.743 110.275 1.14922C108.912 0.555439 107.394 0.254883 105.774 0.254883C103.802 0.254883 102.006 0.702052 100.43 1.5744C98.8541 2.45408 97.6006 3.68563 96.7063 5.24705C95.8119 6.80115 95.3574 8.5825 95.3574 10.5398C95.3574 12.4971 95.8046 14.2711 96.6769 15.8325C97.5566 17.3939 98.7955 18.6255 100.364 19.5052C101.933 20.3775 103.736 20.8247 105.738 20.8247C107.739 20.8247 109.359 20.4068 110.825 19.5858C112.299 18.7648 113.457 17.5699 114.27 16.0451C115.077 14.5203 115.487 12.7023 115.487 10.6424C115.487 10.3199 115.473 9.98265 115.443 9.63078L115.429 9.41086L115.436 9.3962Z"
              class="fill-gray-800 dark:fill-white transition-theme"
            />
            <path d="M122.965 0.540039H119.534V20.5161H122.965V0.540039Z" class="fill-gray-800 dark:fill-white transition-theme" />
            <path d="M142.559 0.540039H126.007V3.70688H132.568V20.5161H135.999V3.70688H142.559V0.540039Z" class="fill-gray-800 dark:fill-white transition-theme" />
            <path d="M149.099 0.540039L140.61 20.5161H144.217L150.91 4.60122L157.595 20.5161H161.261L152.757 0.540039H149.099Z" class="fill-gray-800 dark:fill-white transition-theme" />
            <path d="M167.447 17.3492V0.540039H164.017V20.5161H178.157V17.3492H167.447Z" class="fill-gray-800 dark:fill-white transition-theme" />
          </g>
          <defs>
            <clipPath id="clip0_481_4834">
              <rect width="178.157" height="20.5625" fill="white" transform="translate(0 0.248047)" />
            </clipPath>
          </defs>
        </svg>
        <span class="text-[10px] pl-0.5 pt-0.5 font-medium text-gray-600 dark:text-gray-400 transition-theme">Agentic AI {packageInfo.version}</span>
      </div>

      {#if !isModelDropdownOpen}
        <!-- Model dropdown toggle button -->
        <div class="relative">
          <button
            bind:this={elToggleButton}
            disabled={isDisabled || !modelAgents.length}
            aria-label="Toggle model selection dropdown"
            class="navbar-model-dropdown flex items-center gap-3 px-2 py-1 rounded-lg text-gray-700 dark:text-gray-200 transition-theme duration-300 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-300/20 dark:focus:ring-blue-700/30 border-transparent
            {isDisabled || !modelAgents.length ? 'opacity-60 cursor-not-allowed' : 'border-1 cursor-pointer hover:border-gray-300 dark:hover:border-gray-600'}"
            on:click|stopPropagation={toggleDropdown}
          >
            <div class="flex flex-col items-start">
              <span class="text-xs font-medium leading-tight">{modelSelected ? `${getModelName(modelSelected)}` : 'Choose AI model'}</span>
              <span class="text-[10px] text-gray-500 dark:text-gray-400 leading-tight truncate max-w-[180px]">
                {modelSelected ? modelSelected.model : 'Select a model from the list'}
              </span>
            </div>

            <div class="ml-1 flex items-center">
              <svg
                class="dropdown-arrow w-3.5 h-3.5 transition-transform duration-200 text-gray-400 dark:text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7"></path>
              </svg>
            </div>
          </button>
        </div>
      {/if}
    </div>

    {#if isModelDropdownOpen}
      <!-- Centered search input that replaces the dropdown button -->
      <div class="inline-search-container my-2 absolute left-1/2 transform -translate-x-1/2 w-1/2 min-w-[320px]">
        <div class="relative flex items-center">
          <input
            bind:this={searchInput}
            type="text"
            placeholder="Search models..."
            class="w-full px-2 py-1 rounded-sm border border-gray-300 dark:border-gray-600 text-gray-800 dark:text-gray-200 shadow-sm focus:ring-2 focus:ring-blue-300 dark:focus:ring-blue-700 focus:border-transparent focus:outline-none transition-theme duration-200 pl-10"
            bind:value={searchQuery}
            on:keydown={handleKeydown}
          />
          <svg class="absolute left-3 w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
          </svg>
          <button
            aria-label="close dropdown"
            class="absolute right-3 p-1 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors duration-200"
            on:click={closeDropdown}
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
      </div>
    {/if}

    <div class="button-group flex gap-1 items-center space-x-2">
      {#if activeModal}
        <button
          on:click={closeModals}
          aria-label="Close modal"
          class="flex items-center justify-center w-9 h-9 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300/20 dark:focus:ring-blue-700/30 transition-theme duration-200 cursor-pointer"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      {:else}
        {#if modelSelected}
          <button
            on:click={() => openModal('history')}
            aria-label="History"
            use:tippy={{
              content: 'History',
              placement: 'bottom',
              arrow: true,
              theme: 'custom',
            }}
            class="flex items-center justify-center w-9 h-9 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300/20 dark:focus:ring-blue-700/30 transition-theme duration-200 {!modelSelected
              ? 'disabled text-gray-400 dark:text-gray-600'
              : 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer'}"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </button>
        {/if}
        <DarkModeButton />

        <div class="h-6 border-l mr-5 border-gray-300 dark:border-gray-600 mx-1 transition-theme"></div>
        <MenuButton />
      {/if}
    </div>
  </div>

  {#if isModelDropdownOpen}
    <div class="dropdown-container w-full" transition:slide={{ duration: 300, axis: 'y' }}>
      <div class="dropdown-content-wrapper mt-2 pt-4 border-t border-gray-200/60 dark:border-gray-700/60">
        <div bind:this={elDropdownList} class="w-full max-h-[calc(80vh-6rem)] overflow-y-auto z-20 mx-auto">
          <!-- Grid layout for models -->
          <div class="flex flex-wrap justify-center gap-4 p-5">
            {#each filteredModels as model}
              <div
                role="menuitem"
                tabindex={model.available ? '0' : '-1'}
                class="group flex items-center gap-3 p-3 text-sm text-gray-700 dark:text-gray-300 relative rounded-lg transition-theme duration-200
                  w-[280px] max-w-full
                  {!model.available ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'} 
                  {tentativeSelection && tentativeSelection.route === model.route
                  ? 'ring-2 ring-blue-500 dark:ring-blue-400 bg-blue-50 dark:bg-gray-700/70'
                  : 'hover:bg-gray-50 dark:hover:bg-gray-700/50 border border-gray-200 dark:border-gray-700'}"
                on:click={() => setTentativeSelection(model)}
                on:keydown={(e) => {}}
              >
                <div class="icon-bg p-2 rounded-md bg-gray-100 dark:bg-gray-700 flex items-center justify-center {!model.available ? 'disabled' : ''}">
                  <svg aria-labelledby="{model.route}-title" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" class="w-6 h-6">
                    <title id="{model.route}-title">{getModelName(model)}</title>
                    <text y="20" fill="currentColor" font-size="20" font-style="italic" font-weight="bold">{model.icon}</text>
                  </svg>
                </div>

                <div class="details flex flex-col gap-1 min-h-[2.5rem] overflow-hidden flex-1">
                  <!-- Add confirm/cancel buttons when this model is tentatively selected -->
                  {#if tentativeSelection && tentativeSelection.route === model.route}
                    <div
                      class="absolute inset-0 left-0 top-0 flex flex-col justify-center items-center bg-white dark:bg-gray-800 z-10 p-3 rounded-md shadow-md border border-gray-200 dark:border-gray-700"
                    >
                      <div class="text-xs font-medium mb-2 w-full">Reset the session?</div>
                      <div class="flex justify-between gap-3 w-full">
                        <button
                          class="flex-1 px-3 py-1.5 text-xs bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors duration-200 cursor-pointer"
                          on:click|stopPropagation={cancelSelection}
                        >
                          Cancel
                        </button>
                        <button
                          class="flex-1 px-3 py-1.5 text-xs bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors duration-200 cursor-pointer"
                          on:click|stopPropagation={() => selectClickModel(model)}
                        >
                          Confirm
                        </button>
                      </div>
                    </div>
                  {/if}
                  <div class="title font-medium leading-tight">{getModelName(model)}</div>
                  <div class="subtitle text-xs opacity-80 truncate overflow-hidden whitespace-nowrap">{model.model}</div>
                </div>
              </div>
            {/each}

            {#if filteredModels.length === 0}
              <div class="col-span-full py-12 text-center text-gray-500 dark:text-gray-400">
                <svg class="w-12 h-12 mx-auto mb-3 text-gray-400 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <p class="text-lg">No models found matching your search.</p>
                <p class="text-sm mt-1">Try using different keywords.</p>
              </div>
            {/if}
          </div>
        </div>
      </div>
    </div>
  {/if}
</header>

{#if isModelDropdownOpen}
  <!-- Backdrop overlay -->
  <button
    type="button"
    class="fixed inset-0 bg-black/30 dark:bg-black/60 backdrop-blur-sm z-35 transition-opacity duration-200 cursor-default focus:outline-none"
    on:click={closeDropdown}
    transition:fade={{ duration: 200 }}
    aria-label="Close dropdown"
  ></button>
{/if}
