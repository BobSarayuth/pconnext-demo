import {
  clearCookie,
  getAuthAuthority,
  getAuthCookies,
  getAuthPath,
  getAuthScope,
  getProxyTokenType,
  getRedirectUri,
  getStoredAuthState,
  getStoredCodeVerifier,
  getStoredReturnTo,
  isAuthEnabled,
} from '../../utils/auth'

function renderTokenExchangePage(config: Record<string, string>) {
  const serializedConfig = JSON.stringify(config).replace(/</g, '\\u003c')
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Signing in</title>
  </head>
  <body>
    <script>
      const config = ${serializedConfig};

      async function exchangeToken() {
        const form = new URLSearchParams();
        form.set('client_id', config.clientId);
        form.set('grant_type', 'authorization_code');
        form.set('code', config.code);
        form.set('redirect_uri', config.redirectUri);
        form.set('scope', config.scope);
        form.set('code_verifier', config.codeVerifier);

        const tokenRes = await fetch(config.tokenUrl, {
          method: 'POST',
          headers: { 'content-type': 'application/x-www-form-urlencoded' },
          body: form,
        });

        if (!tokenRes.ok) {
          const detail = await tokenRes.text();
          document.body.textContent = 'AD token exchange failed: ' + tokenRes.status + '\\n' + detail;
          throw new Error(detail);
        }

      const tokenBody = await tokenRes.json();
        let token = '';
        if (config.tokenType === 'id_token') {
          token = tokenBody.id_token || '';
        } else if (config.tokenType === 'access_token') {
          token = tokenBody.access_token || '';
        } else {
          token = config.scope.includes('api://') ? tokenBody.access_token || '' : tokenBody.id_token || '';
        }
        if (!token) throw new Error('AD token response missing selected token');

        const sessionRes = await fetch(config.sessionUrl, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({
            token,
            expiresIn: tokenBody.expires_in || 3600,
          }),
        });

        if (!sessionRes.ok) {
          const detail = await sessionRes.text();
          document.body.textContent = 'Session creation failed: ' + sessionRes.status + '\\n' + detail;
          throw new Error(detail);
        }

        window.location.replace(config.returnTo);
      }

      exchangeToken().catch((error) => console.error(error));
    </script>
  </body>
</html>`
}

export async function GET({ request, url }: { request: Request; url: URL }) {
  if (!isAuthEnabled()) return Response.redirect(new URL('/', request.url), 302)

  const code = url.searchParams.get('code') || ''
  const state = url.searchParams.get('state') || ''
  const expectedState = getStoredAuthState(request)
  const codeVerifier = getStoredCodeVerifier(request)
  if (!code || !state || state !== expectedState || !codeVerifier) {
    return new Response('Invalid AD login callback', { status: 401 })
  }

  const authority = getAuthAuthority()
  const clientId = Bun.env.AUTH_CLIENT_ID || ''
  if (!authority || !clientId) {
    return new Response('AD login is not configured', { status: 500 })
  }

  const cookies = getAuthCookies()
  return new Response(
    renderTokenExchangePage({
      clientId,
      code,
      codeVerifier,
      redirectUri: getRedirectUri(request),
      returnTo: getStoredReturnTo(request),
      scope: getAuthScope(),
      sessionUrl: getAuthPath('/auth/session'),
      tokenType: getProxyTokenType(),
      tokenUrl: `${authority}/oauth2/v2.0/token`,
    }),
    {
      headers: [
        ['Content-Type', 'text/html; charset=utf-8'],
        ['Set-Cookie', clearCookie(cookies.state)],
        ['Set-Cookie', clearCookie(cookies.returnTo)],
        ['Set-Cookie', clearCookie(cookies.verifier)],
      ],
    },
  )
}
