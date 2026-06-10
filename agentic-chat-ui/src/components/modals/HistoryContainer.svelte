<script>
  import dayjs from 'dayjs'
  import utc from 'dayjs/plugin/utc'
  import 'dayjs/locale/th'
  import { DatePicker } from '@svelte-plugins/datepicker'
  import BaseDebugModal from './ContainerModalBase.svelte'
  import { sessionStore } from '../../utils/sessionStore'

  // Initialize dayjs plugins
  dayjs.extend(utc)

  // ----- Date Utilities -----
  const getDateFromToday = (days) => {
    return Date.now() - days * MILLISECONDS_IN_DAY
  }

  const formatDate = (dateString) => {
    if (!dateString || isNaN(new Date(dateString))) {
      return ''
    }
    return dayjs(dateString).format(dateFormat)
  }

  // ----- Modal State -----
  let baseModal
  let isOpenHistory = false

  // ----- History Data State -----
  let history = []
  let loading = false
  let error = null
  let hasMoreData = true

  // ----- Pagination State -----
  let currentPage = 1
  let itemsPerPage = 50
  let totalItems = 0
  let skip = 0
  $: skip = (currentPage - 1) * itemsPerPage
  $: totalItems = history.length

  // ----- Sorting State -----
  let sortField = 'beginDate'
  let sortDirection = 'desc'

  // ----- Scroll State -----
  let previousScrollPosition = 0
  let shouldMaintainScroll = false
  let tableContainer

  // ----- Filter State -----
  let searchText = ''
  let deletedFilter = 'not_deleted' // Values: 'all', 'deleted', 'not_deleted'
  let filterChatType = ''

  // ----- Date Filter State -----
  const MILLISECONDS_IN_DAY = 24 * 60 * 60 * 1000
  let startDate = getDateFromToday(0)
  let endDate = getDateFromToday(0)
  let dateFormat = 'DD-MM-YYYY'
  let isDatePickerOpen = false
  let formattedStartDate = ''
  let formattedEndDate = ''
  $: formattedStartDate = formatDate(startDate)
  $: formattedEndDate = formatDate(endDate)

  const toggleDatePicker = () => (isDatePickerOpen = !isDatePickerOpen)

  // ----- Display Utilities -----
  const calculateDuration = (last) => {
    return dayjs(last).add(7, 'h').fromNow()
  }

  const truncateContent = (content, maxLength = 100) => {
    if (!content) return ''
    // Replace line breaks with spaces to ensure one-line display
    content = content.replace(/(\r\n|\n|\r)/gm, ' ')
    return content.length > maxLength ? content.substring(0, maxLength) + '...' : content
  }

  $: getSortIcon = (field) => {
    if (field !== sortField) return '↕'
    return sortDirection === 'asc' ? '↑' : '↓'
  }

  // INTERACTION HANDLERS

  // ----- Scroll Handlers -----
  const handleScroll = (event) => {
    const { scrollPercentage } = event.detail
    if (scrollPercentage >= 80 && !loading && hasMoreData) {
      loadMoreData()
    }
  }

  const handleTableScroll = () => {
    const scrollContainer = tableContainer
    if (scrollContainer) {
      previousScrollPosition = scrollContainer.scrollTop
    }
  }

  // ----- Sorting Handler -----
  const setSort = (field) => {
    if (field === sortField) {
      sortDirection = sortDirection === 'asc' ? 'desc' : 'asc'
    } else {
      sortField = field
      sortDirection = 'desc'
    }
    fetchHistory()
  }

  // ----- Filter Handlers -----
  const applyFilters = () => {
    currentPage = 1
    hasMoreData = true
    fetchHistory()
  }

  // ----- Data Loading Handlers -----
  const loadMoreData = () => {
    currentPage += 1
    fetchHistory(true) // true = append mode
  }

  // DATA OPERATIONS

  // ----- Data Fetching -----
  const fetchHistory = async (append = false) => {
    if (!isOpenHistory) return

    const agentRoute = $sessionStore.agentRoute
    loading = true
    error = null

    try {
      skip = (currentPage - 1) * itemsPerPage
      if (!append) {
        history = []
      }

      // Build query parameters
      const params = new URLSearchParams()

      if (startDate) {
        params.append('beginDate', dayjs(new Date(startDate)).format('YYYY-MM-DD'))
      }

      if (endDate) {
        params.append('lastDate', dayjs(new Date(endDate).getTime() + MILLISECONDS_IN_DAY).format('YYYY-MM-DD'))
      }

      if (filterChatType) {
        params.append('chatType', filterChatType)
      }

      if (searchText) {
        params.append('content', searchText)
      }

      if (deletedFilter === 'deleted') {
        params.append('deleted', 'true')
      } else if (deletedFilter === 'not_deleted') {
        params.append('deleted', 'false')
      }

      params.append('order', sortDirection.toUpperCase())
      params.append('limit', itemsPerPage.toString())
      params.append('skip', skip.toString())

      const url = `/history/?${params.toString()}`
      const res = await fetch(window.urlProxy(agentRoute, url))

      if (!res.ok) {
        throw new Error(`Error ${res.status}: ${res.statusText}`)
      }

      const data = await res.json()
      const newData = Array.isArray(data) ? data : [data]

      // Check if we got fewer items than requested (reached the end)
      hasMoreData = newData.length === itemsPerPage

      // Either append to existing data or replace it
      if (append) {
        history = [...history, ...newData]
      } else {
        history = newData
      }
    } catch (err) {
      error = err.message
      console.error('Failed to fetch history:', err)
    } finally {
      loading = false
    }
  }

  // MODAL CONTROLS
  export const open = () => {
    baseModal.open()
    isOpenHistory = true
    fetchHistory()
  }

  export const close = () => {
    baseModal.close()
    isOpenHistory = false
  }

  // Commented out for reference
  // // Re-fetch when filters change
  // $: {
  //   if (isOpenHistory) {
  //     currentPage = 1 // Reset page when filters change
  //     hasMoreData = true // Reset hasMoreData flag
  //     fetchHistory()
  //   }
  // }

  // // afterUpdate(() => {
  //   if (shouldMaintainScroll) {
  //     const scrollContainer = document.querySelector('.overflow-x-auto')
  //     if (scrollContainer) {
  //       scrollContainer.scrollTop = previousScrollPosition
  //     }
  //     shouldMaintainScroll = false
  //   }
  // })
</script>

<BaseDebugModal bind:this={baseModal} on:scroll={handleScroll}>
  <div class="rounded overflow-hidden p-2 sm:p-4 min-h-[calc(100vh-6.5em)]">
    <!-- Filters -->
    <div class="mb-6">
      <div class="grid sm:grid-cols-2 md:grid-cols-6 lg:grid-cols-12 gap-2 md:gap-3">
        <div class="flex gap-2 items-center col-span-1 sm:col-span-2 md:col-span-3 lg:col-span-3">
          <label for="searchText" class="text-gray-700 dark:text-gray-200 text-sm font-medium whitespace-nowrap w-16 sm:w-14">Search:</label>
          <input
            id="searchText"
            type="text"
            bind:value={searchText}
            placeholder="Search content"
            class="bg-white dark:bg-slate-800 text-gray-900 dark:text-white px-3 py-2 rounded border border-gray-300 dark:border-gray-600 text-sm w-full min-w-0 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div class="flex gap-2 items-center col-span-1 sm:col-span-2 md:col-span-3 lg:col-span-3">
          <label for="dateRange" class="text-gray-700 dark:text-gray-200 text-sm font-medium whitespace-nowrap w-16 sm:w-14">Date:</label>
          <div class="date-filter w-full min-w-0">
            <DatePicker id="dateRange" theme="custom-datepicker" bind:isOpen={isDatePickerOpen} bind:startDate bind:endDate isRange>
              <button type="button" on:click={toggleDatePicker} aria-expanded={isDatePickerOpen} class="date-field" class:open={isDatePickerOpen}>
                <i class="icon-calendar"></i>
                <span class="date">
                  {formattedStartDate === formattedEndDate ? formattedStartDate : `${formattedStartDate} - ${formattedEndDate}`}
                </span>
              </button>
            </DatePicker>
          </div>
        </div>

        <div class="flex gap-2 items-center col-span-1 sm:col-span-2 md:col-span-2 lg:col-span-2">
          <label for="chatType" class="text-gray-700 dark:text-gray-200 text-sm font-medium whitespace-nowrap w-16 sm:w-14">Type:</label>
          <select
            id="chatType"
            bind:value={filterChatType}
            class="bg-white dark:bg-slate-800 text-gray-900 dark:text-white px-3 py-2 rounded border border-gray-300 dark:border-gray-600 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent w-full min-w-0"
          >
            <option value="">All</option>
            <option value="INTERNAL">INTERNAL</option>
            <option value="EXTERNAL">EXTERNAL</option>
          </select>
        </div>

        <div class="flex gap-2 items-center col-span-1 sm:col-span-2 md:col-span-2 lg:col-span-2">
          <label for="deletedFilter" class="text-gray-700 dark:text-gray-200 text-sm font-medium whitespace-nowrap w-16 sm:w-14">Status:</label>
          <select
            id="deletedFilter"
            bind:value={deletedFilter}
            class="bg-white dark:bg-slate-800 text-gray-900 dark:text-white px-3 py-2 rounded border border-gray-300 dark:border-gray-600 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent w-full min-w-0"
          >
            <option value="all">All</option>
            <option value="deleted">Deleted</option>
            <option value="not_deleted">Not Deleted</option>
          </select>
        </div>

        <div class="flex items-center col-span-1 sm:col-span-2 md:col-span-2 mt-2 md:mt-0">
          <button
            on:click={applyFilters}
            class="bg-blue-600 text-white px-4 py-2 rounded font-medium text-sm hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 w-full"
          >
            Search
          </button>
        </div>
      </div>
    </div>

    <!-- History Table -->
    <div class="overflow-x-auto rounded-lg" bind:this={tableContainer} on:scroll={handleTableScroll}>
      <table class="min-w-full text-gray-800 dark:text-gray-200 border-collapse">
        <thead class="sticky top-0">
          <tr class="bg-blue-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
            <th class="px-2 sm:px-4 py-3 text-left w-auto whitespace-nowrap min-w-[120px] sm:min-w-[160px]">
              <button
                on:click={() => setSort('lastDate')}
                class="font-medium text-xs sm:text-sm flex items-center gap-1 text-blue-700 dark:text-blue-300 hover:text-blue-600 dark:hover:text-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                Last Date {getSortIcon('lastDate')}
              </button>
            </th>
            <th class="px-2 sm:px-4 py-3 text-left whitespace-nowrap min-w-[345px]">
              <span class="font-medium text-xs sm:text-sm text-blue-700 dark:text-blue-300">Session ID</span>
            </th>
            <th class="px-2 sm:px-4 py-3 text-left w-full min-w-[150px] sm:min-w-[200px] hidden sm:table-cell">
              <span class="font-medium text-xs sm:text-sm text-blue-700 dark:text-blue-300">Content</span>
            </th>
            <th class="px-2 sm:px-4 py-3 text-left w-auto min-w-[150px] whitespace-nowrap hidden lg:table-cell">
              <span class="font-medium text-xs sm:text-sm text-blue-700 dark:text-blue-300">Tools</span>
            </th>
            <th class="px-2 sm:px-4 py-3 text-left w-auto whitespace-nowrap hidden lg:table-cell">
              <span class="font-medium text-xs sm:text-sm text-blue-700 dark:text-blue-300">Type</span>
            </th>
            <th class="px-2 sm:px-4 py-3 text-left w-auto whitespace-nowrap hidden sm:table-cell">
              <span class="font-medium text-xs sm:text-sm text-blue-700 dark:text-blue-300">Duration</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {#each history as item}
            <tr class="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700">
              <td class="px-4 py-2 text-sm">
                {dayjs(item.lastDate).add(7, 'h').format('YYYY-MM-DD HH:mm:ss')}
              </td>
              <td class="px-2 sm:px-4 py-2">
                <a
                  href="/{$sessionStore.agentRoute}/{item.sessionId}"
                  target="_blank"
                  class="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline text-xs sm:text-sm block w-full max-w-[100px] sm:max-w-full"
                >
                  {item.sessionId}
                </a>
              </td>
              <td class="px-2 sm:px-4 py-2 text-xs sm:text-sm w-full hidden sm:table-cell">
                <div class="truncate w-[calc(100vw-70em)]">{item.content}</div>
              </td>
              <td class="px-2 sm:px-4 py-2 w-auto whitespace-nowrap hidden lg:table-cell">
                <div class="flex flex-wrap gap-1">
                  {#each item.usedTools as tool}
                    <span class="bg-purple-700 text-xs px-2 py-0.5 rounded-full text-white">
                      {tool}
                    </span>
                  {/each}
                </div>
              </td>
              <td class="px-2 sm:px-4 py-2 w-auto whitespace-nowrap hidden lg:table-cell">
                <span class="bg-green-700 text-xs px-2 py-0.5 rounded-full text-white">
                  {item.chatType}
                </span>
              </td>
              <td class="px-2 sm:px-4 py-2 text-xs sm:text-sm w-auto whitespace-nowrap hidden sm:table-cell">
                {calculateDuration(item.lastDate)}
              </td>
            </tr>
          {/each}
          {#if loading}
            <tr class="border-b border-gray-200 dark:border-gray-700">
              <td colspan="6" class="text-center py-2 text-gray-600 dark:text-gray-300 text-sm">Loading history data... </td>
            </tr>
          {:else if error}
            <tr class="border-b border-gray-200 dark:border-gray-700">
              <td colspan="6">
                <div class="flex items-center p-4 mb-4 text-sm text-red-800 rounded-lg dark:text-red-400" role="alert">
                  <svg class="shrink-0 inline w-4 h-4 me-3" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      d="M10 .5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 .5ZM9.5 4a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3ZM12 15H8a1 1 0 0 1 0-2h1v-3H8a1 1 0 0 1 0-2h2a1 1 0 0 1 1 1v4h1a1 1 0 0 1 0 2Z"
                    />
                  </svg>
                  <div>
                    <span class="font-medium">Error!</span>
                    {error}
                  </div>
                </div>
              </td>
            </tr>
          {:else if history.length === 0}
            <tr class="border-b border-gray-200 dark:border-gray-700">
              <td colspan="6" class="text-center py-8 text-gray-600 dark:text-gray-300 text-sm"> No history records found matching your filters. </td>
            </tr>
          {/if}
        </tbody>
      </table>
    </div>
  </div>
</BaseDebugModal>

<style>
  :global(.date-field) {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    background-color: white;
    border: 1px solid #e2e8f0;
    border-radius: 0.25rem;
    padding: 0.5rem 0.75rem;
    font-size: 0.875rem;
    color: #374151;
    transition: all 0.2s;
  }

  :global(.dark .date-field) {
    background-color: #1e293b;
    border-color: #475569;
    color: #f1f5f9;
  }

  :global(.date-field:hover) {
    border-color: #cbd5e1;
  }

  :global(.dark .date-field:hover) {
    border-color: #64748b;
  }

  :global(.date-field:focus, .date-field.open) {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3);
  }

  :global(.date-field .date) {
    flex: 1;
    text-align: left;
  }

  :global(.date-field .date) {
    flex: 1;
    text-align: left;
  }

  :global(.date-field .icon-calendar) {
    background: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAACXBIWXMAABYlAAAWJQFJUiTwAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAEmSURBVHgB7ZcPzcIwEMUfXz4BSCgKwAGgACRMAg6YBBxsOMABOAAHFAXgAK5Z2Y6lHbfQ8SfpL3lZaY/1rb01N+BHUKSMNBfEJjZWISA56Uo6C2KvVpkgFn9oRx9vICFtUT1JKO3tvRtZdjBxXQs+YY+1FenIfuesPUGVVLzfRWKvmrSzbbN19wS+kAb2+sCEuUxrYzkbe4YvCVM2Vr5NPAkVa+van7Wn38U95uTpN5TJ/A8ZKemAakmbmJJGpI0gVmwA0huieFItjG19DgTHtwIZhCfZq3ztCuzQYh+FKBSvusjAGs8PnLYkLgMf34JoIBqIBqKBaIAb0Kw9RlhMCTbzzPWAqYq7LsuPaGDUsYmznaOk5zChUJTNQ4TFVMkrOL4HPsoNn26PxROHCggAAAAASUVORK5CYII=)
      no-repeat center center;
    background-size: 14px 14px;
    height: 14px;
    width: 14px;
  }
  :global(.dark .date-field .icon-calendar) {
    filter: invert(1);
  }

  :global(.datepicker[data-picker-theme='custom-datepicker']) {
    --datepicker-container-border: 1px solid #c5dcfd;

    --datepicker-calendar-header-text-color: #374151;
    --datepicker-calendar-dow-color: #4b5563;
    --datepicker-calendar-day-color: #374151;
    --datepicker-calendar-day-color-disabled: #9ca3af;
    --datepicker-calendar-range-selected-background: #3b82f6;

    --datepicker-calendar-header-month-nav-background-hover: #dbeafe;
    --datepicker-calendar-header-month-nav-icon-next-filter: none;
    --datepicker-calendar-header-month-nav-icon-prev-filter: none;
    --datepicker-calendar-header-year-nav-icon-next-filter: none;
    --datepicker-calendar-header-year-nav-icon-prev-filter: none;

    --datepicker-calendar-split-border: 1px solid #dbeafe;

    --datepicker-presets-border: 1px solid #dbeafe;
    --datepicker-presets-button-background-active: #3b82f6;
    --datepicker-presets-button-color: #374151;
    --datepicker-presets-button-color-active: #fff;
    --datepicker-presets-button-color-hover: #2563eb;
    --datepicker-presets-button-color-focus: #2563eb;
  }

  :global(.dark .datepicker[data-picker-theme='custom-datepicker']) {
    --datepicker-container-border: 1px solid #4b5563;
    --datepicker-container-background: #1e293b;

    --datepicker-calendar-header-text-color: #f1f5f9;
    --datepicker-calendar-dow-color: #cbd5e1;
    --datepicker-calendar-day-color: #f1f5f9;
    --datepicker-calendar-day-color-disabled: #64748b;
    --datepicker-calendar-range-selected-background: #3b82f6;

    --datepicker-calendar-header-month-nav-background-hover: #334155;
    --datepicker-calendar-header-month-nav-icon-next-filter: invert(1);
    --datepicker-calendar-header-month-nav-icon-prev-filter: invert(1);
    --datepicker-calendar-header-year-nav-icon-next-filter: invert(1);
    --datepicker-calendar-header-year-nav-icon-prev-filter: invert(1);

    --datepicker-calendar-split-border: 1px solid #334155;

    --datepicker-presets-border: 1px solid #334155;
    --datepicker-presets-background: #1e293b;
    --datepicker-presets-button-background-active: #3b82f6;
    --datepicker-presets-button-color: #f1f5f9;
    --datepicker-presets-button-color-active: #fff;
    --datepicker-presets-button-color-hover: #60a5fa;
    --datepicker-presets-button-color-focus: #60a5fa;
  }
</style>
