// @ts-check
import { defineConfig } from 'astro/config'
import tailwind from '@tailwindcss/vite'
import svelte from '@astrojs/svelte'
import bun from '@nurodev/astro-bun'

const normalizeBasePath = (value = '') => {
  const basePath = value.trim()
  if (!basePath || basePath === '/') return '/'

  return `/${basePath.replace(/^\/+|\/+$/g, '')}`
}

const basePath = normalizeBasePath(process.env.AUTH_BASE_PATH || process.env.BASE_PATH || '')

// https://astro.build/config
export default defineConfig({
  adapter: bun(),
  output: 'server',
  build: {
    assets: 'dist',
    assetsPrefix: basePath === '/' ? undefined : basePath,
  },

  vite: {
    plugins: [tailwind()],
    server: {
      watch: {
        ignored: ['.github/**/*'],
      },
    },
  },
  security: {
    checkOrigin: false,
  },
  integrations: [svelte()],
})
