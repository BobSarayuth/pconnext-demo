import { createAuthState, createCookie, createPkce, getAuthAuthority, getAuthCookies, getAuthScope, getPublicPath, getRedirectUri, isAuthEnabled } from '../../utils/auth'

export async function GET({ request, url }: { request: Request; url: URL }) {
  if (!isAuthEnabled()) return Response.redirect(new URL('/', request.url), 302)

  const authority = getAuthAuthority()
  const clientId = Bun.env.AUTH_CLIENT_ID || ''
  if (!authority || !clientId) {
    return new Response('AD login is not configured', { status: 500 })
  }

  const state = createAuthState()
  const pkce = await createPkce()
  const returnTo = getPublicPath(url.searchParams.get('returnTo') || '/')
  const authUrl = new URL(`${authority}/oauth2/v2.0/authorize`)
  authUrl.searchParams.set('client_id', clientId)
  authUrl.searchParams.set('response_type', 'code')
  authUrl.searchParams.set('redirect_uri', getRedirectUri(request))
  authUrl.searchParams.set('response_mode', 'query')
  authUrl.searchParams.set('scope', getAuthScope())
  authUrl.searchParams.set('state', state)
  authUrl.searchParams.set('code_challenge', pkce.challenge)
  authUrl.searchParams.set('code_challenge_method', 'S256')

  const cookies = getAuthCookies()
  return new Response(null, {
    status: 302,
    headers: [
      ['Location', authUrl.toString()],
      ['Set-Cookie', createCookie(cookies.state, state, 600)],
      ['Set-Cookie', createCookie(cookies.returnTo, returnTo, 600)],
      ['Set-Cookie', createCookie(cookies.verifier, pkce.verifier, 600)],
    ],
  })
}
