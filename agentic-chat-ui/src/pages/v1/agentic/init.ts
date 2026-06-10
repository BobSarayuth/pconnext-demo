// pages/api/[...slugs].ts
import { Elysia } from 'elysia'
import { logger } from '@bogeychan/elysia-logger'
import { ROUTE_API, ROUTE_PROXY } from '../../../types'

let updated = 0
const skip_time = 1 * 60 * 60
const app = new Elysia({ prefix: '/v1/agentic' })
  .use(
    logger({
      level: process.env.LOG_LEVEL,
    }),
  )
  .get('/init', async (ctx) => {
    const result = []

    // Check each proxy's availability and fetch settings
    for await (const route of Object.keys(ROUTE_PROXY)) {
      const proxy = ROUTE_PROXY[route]
      proxy.available = !!proxy.baseUrl
      if (!proxy.available) continue
      if (updated + skip_time > +new Date()) {
        result.push({ route, ...proxy })
        continue
      }

      // Fetch settings from remote proxy if available
      if (route !== 'local') {
        const url = `${proxy.baseUrl?.trim()}/api${ROUTE_API.setting}`
        try {
          const res = await fetch(url, { signal: AbortSignal.timeout(1000) })
          if (!res.ok) {
            console.warn(`Failed to fetch settings from ${url}: ${res.statusText}`)
            result.push({ route, ...proxy })
            continue
          }
          const settings = await res.json()
          proxy.name = settings.name
          proxy.display = settings.display || proxy.display
          proxy.version = settings.version
          proxy.model = settings.model || settings.model
        } catch (error: any) {
          console.error(`Error fetching settings from ${url}: ${error.message}`)
        }
      }

      // delete proxy.apiKey
      // delete proxy.baseUrl
      result.push({ route, ...proxy })
    }

    updated = +new Date()
    // Remove sensitive information before returning
    return result
  })

const handle = ({ request }: { request: Request }) => app.handle(request)

export const GET = handle
export const POST = handle
