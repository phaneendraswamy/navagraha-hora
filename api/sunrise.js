// Vercel serverless proxy — avoids CORS issues on browser
export default async function handler(req, res) {
  const { latitude, longitude, date } = req.query

  if (!latitude || !longitude || !date) {
    return res.status(400).json({ error: 'Missing parameters' })
  }

  const params = new URLSearchParams({
    latitude,
    longitude,
    daily: 'sunrise',
    timezone: 'auto',
    start_date: date,
    end_date: date,
  })

  try {
    const response = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`, {
      headers: { 'Accept': 'application/json' },
    })
    const data = await response.json()
    res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate') // cache 1h
    return res.status(200).json(data)
  } catch (error) {
    return res.status(502).json({ error: 'Upstream API failed', message: error.message })
  }
}
