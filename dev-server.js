import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DIST = path.join(__dirname, 'frontend-dist')
const PORT = 8000
const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:5000'

const MIME = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf'
}

function proxyToBackend (req, res) {
  const url = new URL(req.url, BACKEND)
  const opts = {
    hostname: url.hostname,
    port: url.port,
    path: url.pathname + url.search,
    method: req.method,
    headers: { ...req.headers, host: url.host }
  }
  const proxy = http.request(opts, (upstream) => {
    res.writeHead(upstream.statusCode, upstream.headers)
    upstream.pipe(res)
  })
  proxy.on('error', () => {
    res.writeHead(502)
    res.end('Backend unavailable')
  })
  req.pipe(proxy)
}

function serveStatic (req, res) {
  let filePath = path.join(DIST, req.url === '/' ? 'index.html' : req.url)
  if (!fs.existsSync(filePath)) {
    filePath = path.join(DIST, 'index.html')
  }
  const ext = path.extname(filePath)
  const mime = MIME[ext] || 'application/octet-stream'
  const content = fs.readFileSync(filePath)
  res.writeHead(200, { 'Content-Type': mime })
  res.end(content)
}

const server = http.createServer((req, res) => {
  if (req.url.startsWith('/api/') || req.url.startsWith('/api?')) {
    proxyToBackend(req, res)
  } else {
    serveStatic(req, res)
  }
})

server.listen(PORT, () => {
  console.log(`Fractal dev server running at http://localhost:${PORT}`)
  console.log(`API proxy → ${BACKEND}`)
})
