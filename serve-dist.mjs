import { appendFileSync, createReadStream, existsSync, statSync } from 'node:fs'
import { createServer } from 'node:http'
import { extname, join, resolve } from 'node:path'

const root = resolve('dist')
const port = Number(process.env.PORT || 4173)

const mimeTypes = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
}

appendFileSync('serve-dist.log', `starting ${new Date().toISOString()}\n`)

const server = createServer((request, response) => {
  const url = new URL(request.url, `http://${request.headers.host}`)
  const requestedPath = decodeURIComponent(url.pathname)
  const filePath = resolve(join(root, requestedPath === '/' ? 'index.html' : requestedPath))
  const safePath = filePath.startsWith(root) ? filePath : join(root, 'index.html')
  const finalPath = existsSync(safePath) && statSync(safePath).isFile() ? safePath : join(root, 'index.html')

  response.setHeader('Content-Type', mimeTypes[extname(finalPath)] || 'application/octet-stream')
  createReadStream(finalPath).pipe(response)
})

server.on('error', (error) => {
  appendFileSync('serve-dist.log', `${error.stack || error.message}\n`)
})

server.listen(port, '127.0.0.1', () => {
  appendFileSync('serve-dist.log', `running http://127.0.0.1:${port}\n`)
})
