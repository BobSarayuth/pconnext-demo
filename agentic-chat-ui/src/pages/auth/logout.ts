import { clearCookie, getAuthCookies, getAuthPath } from '../../utils/auth'

export async function GET() {
  const cookies = getAuthCookies()
  return new Response(null, {
    status: 302,
    headers: [
      ['Location', getAuthPath('/') || '/'],
      ['Set-Cookie', clearCookie(cookies.token)],
      ['Set-Cookie', clearCookie(cookies.state)],
      ['Set-Cookie', clearCookie(cookies.returnTo)],
      ['Set-Cookie', clearCookie(cookies.verifier)],
    ],
  })
}
