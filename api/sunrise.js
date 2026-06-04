// Vercel serverless proxy — tries open-meteo first, falls back to sunrise-sunset.org
export default async function handler(req, res) {
  const { latitude, longitude, date } = req.query

  if (!latitude || !longitude || !date) {
    return res.status(400).json({ error: 'Missing parameters' })
  }

  // ── Attempt 1: open-meteo ───────────────────────────────────────────────
  try {
    const params = new URLSearchParams({
      latitude,
      longitude,
      daily: 'sunrise',
      timezone: 'auto',
      start_date: date,
      end_date: date,
    })
    const response = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`, {
      signal: AbortSignal.timeout(5000),
    })
    if (response.ok) {
      const data = await response.json()
      const sunriseValue = data?.daily?.sunrise?.[0]
      if (sunriseValue) {
        res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate')
        res.setHeader('X-Source', 'open-meteo')
        // Returns local time string like "2026-06-04T05:29"
        return res.status(200).json({ sunrise: sunriseValue, isUtc: false })
      }
    }
  } catch {
    // open-meteo failed — fall through to backup
  }

  // ── Attempt 2: sunrise-sunset.org (backup) ─────────────────────────────
  try {
    const params = new URLSearchParams({
      lat: latitude,
      lng: longitude,
      date,
      formatted: '0', // returns full ISO 8601 UTC datetime
    })
    const response = await fetch(`https://api.sunrise-sunset.org/json?${params}`, {
      signal: AbortSignal.timeout(5000),
    })
    const data = await response.json()

    if (data?.status === 'OK' && data?.results?.sunrise) {
      // IMPORTANT: return the raw UTC ISO string as-is.
      // e.g. "2026-06-03T23:58:00+00:00" for a 5:28 AM IST sunrise on June 4.
      // The client does new Date(utcString) which correctly converts to local time.
      res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate')
      res.setHeader('X-Source', 'sunrise-sunset.org')
      return res.status(200).json({ sunrise: data.results.sunrise, isUtc: true })
    }
  } catch {
    // both APIs failed
  }

  return res.status(502).json({ error: 'All sunrise APIs failed' })
}
