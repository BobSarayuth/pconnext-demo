const TOKEN_COOKIE = 'agentic_auth_token'
const STATE_COOKIE = 'agentic_auth_state'
const RETURN_COOKIE = 'agentic_auth_return'
const VERIFIER_COOKIE = 'agentic_auth_verifier'

const DEFAULT_SCOPE = 'openid profile email'

export function isAuthEnabled() {
  return (Bun.env.AUTH_ENABLED || '').toLowerCase() === 'true'
}

function getCookie(request: Request, name: string) {
  const cookie = request.headers.get('cookie') || ''
  const match = cookie.match(new RegExp(`(?:^|; )${name}=([^;]+)`))
  return match ? decodeURIComponent(match[1]) : ''
}

export function getAuthToken(request: Request) {
  return getCookie(request, TOKEN_COOKIE)
}

export function getAuthBasePath() {
  const basePath = (Bun.env.AUTH_BASE_PATH || '').trim()
  if (!basePath || basePath === '/') return ''

  return `/${basePath.replace(/^\/+|\/+$/g, '')}`
}

export function getAuthPath(path: string) {
  return `${getAuthBasePath()}${path.startsWith('/') ? path : `/${path}`}`
}

export function getPublicPath(path: string) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const basePath = getAuthBasePath()
  if (!basePath || normalizedPath === basePath || normalizedPath.startsWith(`${basePath}/`)) {
    return normalizedPath
  }

  return `${basePath}${normalizedPath}`
}

export function requireAuth(Astro: any) {
  if (!isAuthEnabled() || getAuthToken(Astro.request)) return undefined

  const returnTo = getPublicPath(Astro.url.pathname + Astro.url.search)
  return Astro.redirect(`${getAuthPath('/auth/login')}?returnTo=${encodeURIComponent(returnTo)}`)
}

export function getAuthAuthority() {
  const authority = Bun.env.AUTH_AUTHORITY || (Bun.env.AUTH_TENANT_ID ? `https://login.microsoftonline.com/${Bun.env.AUTH_TENANT_ID}` : '')
  return authority.replace(/\/+$/, '').replace(/\/v2\.0$/i, '')
}

export function getRedirectUri(request: Request) {
  return Bun.env.AUTH_REDIRECT_URI || new URL(getAuthPath('/auth/callback'), request.url).toString()
}

export function getAuthScope() {
  return Bun.env.AUTH_SCOPE || DEFAULT_SCOPE
}

export function getProxyTokenType() {
  const tokenType = (Bun.env.AUTH_PROXY_TOKEN_TYPE || 'auto').toLowerCase()
  return ['access_token', 'id_token', 'auto'].includes(tokenType) ? tokenType : 'auto'
}

export function createAuthState() {
  return crypto.randomUUID()
}

export function createCookie(name: string, value: string, maxAge: number) {
  const secure = (Bun.env.AUTH_COOKIE_SECURE || '').toLowerCase() === 'true' ? '; Secure' : ''
  return `${name}=${encodeURIComponent(value)}; Path=${getAuthPath('/') || '/'}; HttpOnly; SameSite=Lax; Max-Age=${maxAge}${secure}`
}

export function clearCookie(name: string) {
  return `${name}=; Path=${getAuthPath('/') || '/'}; HttpOnly; SameSite=Lax; Max-Age=0`
}

export function getAuthCookies() {
  return {
    returnTo: RETURN_COOKIE,
    state: STATE_COOKIE,
    token: TOKEN_COOKIE,
    verifier: VERIFIER_COOKIE,
  }
}

export function getStoredAuthState(request: Request) {
  return getCookie(request, STATE_COOKIE)
}

export function getStoredReturnTo(request: Request) {
  return getPublicPath(getCookie(request, RETURN_COOKIE) || '/')
}

export function getStoredCodeVerifier(request: Request) {
  return getCookie(request, VERIFIER_COOKIE)
}

function base64UrlEncode(bytes: Uint8Array) {
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

export async function createPkce() {
  const random = crypto.getRandomValues(new Uint8Array(32))
  const verifier = base64UrlEncode(random)
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))
  return {
    challenge: base64UrlEncode(new Uint8Array(digest)),
    verifier,
  }
}
