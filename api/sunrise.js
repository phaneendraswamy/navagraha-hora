// Vercel serverless proxy — tries open-meteo first, falls back to sunrise-sunset.org
export default async function handler(req, res) {
  const { latitude, longitude, date } = req.query

  if (!latitude || !longitude || !date) {
    return res.status(400).json({ error: 'Missing parameters' })
  }

  // ── Attempt 1: open-meteo ────────────────────────────────────────────────
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
      signal: AbortSignal.timeout(5000), // 5s timeout
    })
    if (response.ok) {
      const data = await response.json()
      const sunriseValue = data?.daily?.sunrise?.[0]
      if (sunriseValue) {
        res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate')
        res.setHeader('X-Source', 'open-meteo')
        return res.status(200).json({ sunrise: sunriseValue })
      }
    }
  } catch {
    // open-meteo failed — fall through to backup
  }

  // ── Attempt 2: sunrise-sunset.org (backup) ──────────────────────────────
  try {
    const params = new URLSearchParams({
      lat: latitude,
      lng: longitude,
      date,
      formatted: '0',
    })
    const response = await fetch(`https://api.sunrise-sunset.org/json?${params}`, {
      signal: AbortSignal.timeout(5000),
    })
    const data = await response.json()
    if (data?.status === 'OK' && data?.results?.sunrise) {
      // Convert UTC ISO string to local time string "HH:MM"
      const utcDate = new Date(data.results.sunrise)
      // Get offset in minutes from lat/lng using open-meteo timezone endpoint
      // Simpler: return the UTC time and let client handle with timezone offset
      const utcHours = String(utcDate.getUTCHours()).padStart(2, '0')
      const utcMins = String(utcDate.getUTCMinutes()).padStart(2, '0')
      // Return as ISO with date so client can parse correctly
      const sunriseISO = `${date}T${utcHours}:${utcMins}+00:00`
      res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate')
      res.setHeader('X-Source', 'sunrise-sunset.org')
      return res.status(200).json({ sunrise: sunriseISO, isUtc: true })
    }
  } catch {
    // both APIs failed
  }

  return res.status(502).json({ error: 'All sunrise APIs failed' })
}
