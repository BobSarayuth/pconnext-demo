<script>
  import { onMount } from 'svelte'
  import consts from '../../utils/constraints'
  import { sessionStore } from '../../utils/sessionStore'
  import { tippy } from 'svelte-tippy'

  // Remove local isDarkMode variable and use store instead
  let sunAnimation = ''
  let moonAnimation = ''
  let moonHidden = 'hidden'
  let sunHidden = 'hidden'

  const animationToggle = () => {
    moonAnimation = $sessionStore.isDarkMode ? 'sunset-animation' : 'sunrise-animation'
    sunAnimation = $sessionStore.isDarkMode ? 'sunrise-animation' : 'sunset-animation'
  }

  const hiddenToggle = () => {
    moonHidden = $sessionStore.isDarkMode ? '' : 'hidden'
    sunHidden = $sessionStore.isDarkMode ? 'hidden' : ''
  }
  const toggleTheme = () => {
    const newTheme = $sessionStore.isDarkMode ? 'light' : 'dark'
    document.body.classList.add('transition')
    animationToggle()
    hiddenToggle()
    const timeTheme = setTimeout(() => {
      if (window.applyTheme) window.applyTheme(newTheme)
      sessionStore.update((state) => ({
        ...state,
        isDarkMode: newTheme === 'dark',
      }))
      hiddenToggle()
      clearTimeout(timeTheme)

      setTimeout(() => document.body.classList.remove('transition'), 300)
    }, 300)
  }

  onMount(() => {
    let initialTheme = 'light'
    if (typeof window !== 'undefined') {
      initialTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    if (typeof localStorage !== 'undefined') {
      initialTheme = localStorage.getItem(consts.THEME_NAME) || initialTheme
    }
    if (window.applyTheme) window.applyTheme(initialTheme)
    sessionStore.update((state) => ({
      ...state,
      isDarkMode: initialTheme === 'dark',
    }))

    sessionStore.update((state) => ({
      ...state,
      isDarkMode: document.documentElement.classList.contains('dark'),
    }))
    hiddenToggle()
  })
</script>

<button
  class="p-1 rounded-md w-8 h-8 hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none transition-theme cursor-pointer"
  onclick={toggleTheme}
  use:tippy={{
    content: $sessionStore.isDarkMode ? 'Moon' : 'Sun',
    placement: 'bottom',
    arrow: true,
    theme: 'custom',
  }}
>
  <!-- Sun icon for dark mode (visible when in light mode) -->
  <svg id="sun-icon" class="t-0 w-5.5 h-5.5 text-amber-700 dark:text-gray-300 {sunAnimation} {sunHidden}" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path
      stroke-linecap="round"
      stroke-linejoin="round"
      stroke-width="2"
      d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
    >
    </path>
  </svg>
  <!-- Moon icon for light mode (visible when in dark mode) -->
  <svg id="moon-icon" class="t-0 w-5.5 h-5.5 text-gray-700 dark:text-yellow-200 {moonAnimation} {moonHidden}" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"> </path>
  </svg>
</button>

<style>
  /* Animation for sunrise and sunset effect */
  @keyframes sunrise {
    0% {
      transform: translateY(0.8em) translateX(0.8em) scale(0.8) rotate(120deg);
      opacity: 0;
    }
    100% {
      transform: translateY(0) scale(1) rotate(0deg);
      opacity: 1;
    }
  }

  @keyframes sunset {
    0% {
      transform: translateY(0) scale(1) rotate(0deg);
      opacity: 1;
    }
    100% {
      transform: translateY(0.4em) translateX(-0.4em) scale(0.8) rotate(-45deg);
      opacity: 0;
    }
  }

  button > svg {
    transition: all 0.3s ease;
  }

  .sunrise-animation {
    animation: sunrise 0.3s ease-out forwards;
  }

  .sunset-animation {
    animation: sunset 0.3s ease-out forwards;
  }
</style>
