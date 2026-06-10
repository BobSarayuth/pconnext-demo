import { clearCookie, createCookie, getAuthCookies, isAuthEnabled } from '../../utils/auth'

export async function POST({ request }: { request: Request }) {
  if (!isAuthEnabled()) return new Response('Auth is disabled', { status: 400 })

  const body = await request.json().catch(() => ({}))
  const token = body.token || ''
  if (!token) {
    return new Response('Missing auth token', { status: 400 })
  }

  const expiresIn = Math.min(Number(body.expiresIn || 3600), 3600)
  const cookies = getAuthCookies()
  return new Response(JSON.stringify({ ok: true }), {
    headers: [
      ['Content-Type', 'application/json'],
      ['Set-Cookie', createCookie(cookies.token, token, expiresIn)],
      ['Set-Cookie', clearCookie(cookies.state)],
      ['Set-Cookie', clearCookie(cookies.returnTo)],
      ['Set-Cookie', clearCookie(cookies.verifier)],
    ],
  })
}
