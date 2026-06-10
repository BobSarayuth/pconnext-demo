// pages/api/[...slugs].ts
import { Elysia } from 'elysia'
import { logger } from '@bogeychan/elysia-logger'
import { ROUTE_PROXY } from '../../types'
import { v7 as uuidv7 } from 'uuid'
import pkg from '../../../package.json'
import { getAuthToken, isAuthEnabled } from '../../utils/auth'

const app = new Elysia({ prefix: '/v1' }).use(
  logger({
    level: process.env.LOG_LEVEL,
    autoLogging: {
      ignore: (ctx) => ctx.path === '/v1/_debug/healthz',
    },
  }),
)

function getProxyBody(request: any) {
  if (['GET', 'HEAD'].includes(request.method)) return undefined
  return request.arrayBuffer()
}

function getProxyHeaders(request: Request, headers: any, proxy: any) {
  const proxyHeaders: Record<string, string> = {
    ...headers,
    'x-cap-trace-id': headers['x-cap-trace-id'] || uuidv7(),
    'user-agent': `${pkg.name}@${pkg.version}`,
  }

  delete proxyHeaders.cookie
  delete proxyHeaders.authorization

  if (isAuthEnabled()) {
    const token = getAuthToken(request)
    if (token) proxyHeaders.authorization = `Bearer ${token}`
    delete proxyHeaders['x-cap-api-key']
  } else {
    proxyHeaders['x-cap-api-key'] = proxy.apiKey
  }

  return proxyHeaders
}

const proxyRoute = () => {
  const routes = Object.keys(ROUTE_PROXY)
  return async (ctx: any) => {
    if (!routes.includes(ctx.params.route)) {
      ctx.set.status = 400
      return { error: 'bad request' }
    }
    const { request, url, params, headers } = ctx
    const proxy = ROUTE_PROXY[params.route]
    const uri = new URL(url.replace(new RegExp(`^.+/v1/_proxy/${params.route}/`, 'ig'), '/api/'), proxy.baseUrl)

    if ((process.env.DISABLE_HISTORY || '').toLowerCase() === 'true' && uri.pathname.includes('/api/history')) {
      ctx.set.status = 401
      return { error: 'unauthorized' }
    }

    const body = await getProxyBody(request)
    if (isAuthEnabled() && !getAuthToken(request)) {
      ctx.set.status = 401
      return { error: 'unauthorized' }
    }

    const proxyHeaders = getProxyHeaders(request, headers, proxy)

    const res = await fetch(uri, {
      method: request.method,
      headers: proxyHeaders,
      body,
    })
    if (!res.headers.get('content-disposition')) return res
    res.headers.delete('transfer-encoding')
    res.headers.delete('date')
    return new Response(await res.blob(), { headers: res.headers })
  }
}

app.get(
  '/_debug/healthz',
  (ctx) =>
    new Response('☕', {
      headers: { 'Content-Type': 'text/plain; charset=utf-8' },
    }),
)
app.all(`/_proxy/:route/*`, proxyRoute())

const handle = ({ request }: { request: Request }) => app.handle(request)

export const GET = handle
export const POST = handle
export const DELETE = handle
