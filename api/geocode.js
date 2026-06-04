// Vercel serverless proxy — avoids CORS issues on browser
export default async function handler(req, res) {
  const { name } = req.query

  if (!name) {
    return res.status(400).json({ error: 'Missing name parameter' })
  }

  const params = new URLSearchParams({
    name,
    count: '1',
    language: 'en',
    format: 'json',
  })

  try {
    const response = await fetch(`https://geocoding-api.open-meteo.com/v1/search?${params}`, {
      headers: { 'Accept': 'application/json' },
    })
    const data = await response.json()
    res.setHeader('Cache-Control', 's-maxage=86400, stale-while-revalidate') // cache 24h
    return res.status(200).json(data)
  } catch (error) {
    return res.status(502).json({ error: 'Upstream API failed', message: error.message })
  }
}
