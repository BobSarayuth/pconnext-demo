// Define proxy config type
type ProxyConfig = {
  name?: string
  display: string
  icon: string
  model: string
  baseUrl: string | undefined
  apiKey: string | undefined
  available?: boolean
  version?: string
}

type ProxyConfigs = {
  [key: string]: ProxyConfig
}

// Define AI_ROUTE constant
export const ROUTE_API = {
  health: '/healthz',
  setting: '/settings/',
}

// Get config from environment or import it
// {"name":"Bot","display":"Agentic AI","version":"0.0","model":"scghome-vertex-gemini-2.0-flash-001"}
export const ROUTE_PROXY = {
  local: { display: 'Localhost', icon: 'LL', model: 'Development', baseUrl: Bun.env.LOCAL_BASE_URL, apiKey: '' },
  agentic: { display: 'Agentic AI', icon: 'AI', model: 'N/A', baseUrl: Bun.env.AGENTIC_BASE_URL, apiKey: Bun.env.AGENTIC_API_KEY },
  'scg-home': { display: 'homie', icon: 'HI', model: 'N/A', baseUrl: Bun.env.SCGHOME_BASE_URL, apiKey: Bun.env.SCGHOME_API_KEY },
  smartliving: { display: 'smartliving-chatbot', icon: 'SL', model: 'N/A', baseUrl: Bun.env.SMARTLIVING_BASE_URL, apiKey: Bun.env.SMARTLIVING_API_KEY },
} as ProxyConfigs
