/**
 * Processes a streaming response
 *
 * @param {EventTarget} eventTarget - Event target to dispatch events to
 * @param {string} uri - URI to fetch
 * @param {Object} opts - Fetch options
 * @returns {Promise<void>}
 */
const fetchStream = async (eventTarget, uri, opts) => {
  let res

  try {
    res = await fetch(uri, opts)
  } catch (ex) {
    console.error('XHR::fetch:', ex)
    eventTarget.dispatchEvent(new CloseEvent('error', { reason: `XHR::fetch - ${ex.message}` }))
    return
  }

  eventTarget.dispatchEvent(
    new Event('open', {
      status: res.status,
      headers: res.headers,
      url: res.url,
    }),
  )

  try {
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ message: res.statusText }))
      throw new Error(`${res.statusText} ${res.status} :: ${JSON.stringify(errorData)}`)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      let index
      while ((index = buffer.indexOf('\n\n')) >= 0) {
        const chunk = buffer.slice(0, index).trim()
        if (chunk.startsWith('data:')) {
          const data = chunk.slice(5).trim()
          eventTarget.dispatchEvent(new MessageEvent('message', { data }))
        }
        buffer = buffer.slice(index + 2)
      }
    }

    eventTarget.dispatchEvent(new CloseEvent('close'))
  } catch (ex) {
    console.error('XHR::stream:', ex)
    eventTarget.dispatchEvent(new CloseEvent('error', { reason: `XHR::stream - ${ex.message}` }))
  }
}

export const XHR = (uri, opts) => {
  const eventTarget = new EventTarget()
  fetchStream(eventTarget, uri, opts)
  return eventTarget
}
