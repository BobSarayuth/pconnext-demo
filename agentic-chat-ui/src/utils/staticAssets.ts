const ASSET_ROOT = '/app/dist/client/dist'

const CONTENT_TYPES: Record<string, string> = {
  '.css': 'text/css; charset=utf-8',
  '.gif': 'image/gif',
  '.ico': 'image/x-icon',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml; charset=utf-8',
  '.wasm': 'application/wasm',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
}

function getContentType(path: string) {
  const extension = path.match(/\.[^.]+$/)?.[0]?.toLowerCase() || ''
  return CONTENT_TYPES[extension] || 'application/octet-stream'
}

export async function serveStaticAsset(path: string) {
  if (!path || path.includes('..') || path.startsWith('/')) {
    return new Response('Not found', { status: 404 })
  }

  const file = Bun.file(`${ASSET_ROOT}/${path}`)
  if (!(await file.exists())) {
    return new Response('Not found', { status: 404 })
  }

  return new Response(file, {
    headers: {
      'Cache-Control': 'public, max-age=31536000, immutable',
      'Content-Type': getContentType(path),
    },
  })
}
