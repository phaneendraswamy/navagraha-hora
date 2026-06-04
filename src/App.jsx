import { useEffect, useMemo, useRef, useState } from 'react'
import {
  CalendarDays,
  Clock3,
  LocateFixed,
  MapPin,
  RefreshCcw,
  Search,
  Sparkles,
  Sunrise,
  Crosshair,
} from 'lucide-react'
import {
  buildNavagrahaSlots,
  combineDateAndTime,
  findActiveSlot,
  planets,
  teluguWeekdays,
  toDateInputValue,
  weekdayStartPlanet,
} from './navagraha'

const defaultLocation = {
  name: 'Tadepalligudem, Andhra Pradesh',
  latitude: 16.8147,
  longitude: 81.5272,
}

const darkSignalPlanets = new Set(['kuja', 'sani'])

const teluguDateFormatter = new Intl.DateTimeFormat('te-IN', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
})

const teluguTimeFormatter = new Intl.DateTimeFormat('te-IN', {
  hour: 'numeric',
  minute: '2-digit',
  hour12: true,
})

const shortDateFormatter = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
})

function formatTime(date) {
  return teluguTimeFormatter.format(date)
}

function formatSlotRange(slot) {
  const displayStart = slot.index === 0 ? slot.startsAt : new Date(slot.startsAt.getTime() + 60 * 1000)
  return `${formatTime(displayStart)} - ${formatTime(slot.endsAt)}`
}

function hasDarkSignal(planetKey) {
  return darkSignalPlanets.has(planetKey)
}

function parseOpenMeteoTime(value) {
  const [datePart, timePart] = value.split('T')
  return combineDateAndTime(datePart, timePart.slice(0, 5))
}

async function fetchSunriseForLocation(location, dateValue) {
  const params = new URLSearchParams({
    latitude: String(location.latitude),
    longitude: String(location.longitude),
    daily: 'sunrise',
    timezone: 'auto',
    start_date: dateValue,
    end_date: dateValue,
  })
  const response = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`)
  if (!response.ok) throw new Error('Sunrise lookup failed')
  const data = await response.json()
  const sunriseValue = data?.daily?.sunrise?.[0]
  if (!sunriseValue) throw new Error('Sunrise time is unavailable')
  return parseOpenMeteoTime(sunriseValue)
}

async function searchLocation(query) {
  const params = new URLSearchParams({ name: query, count: '1', language: 'en', format: 'json' })
  const response = await fetch(`https://geocoding-api.open-meteo.com/v1/search?${params}`)
  if (!response.ok) throw new Error('Location search failed')
  const data = await response.json()
  const match = data?.results?.[0]
  if (!match) throw new Error('Location not found')
  return {
    name: [match.name, match.admin1, match.country].filter(Boolean).join(', '),
    latitude: match.latitude,
    longitude: match.longitude,
  }
}

// ── Loading Skeleton ────────────────────────────────────────────────────────
function LoadingCard({ message }) {
  return (
    <div className="relative overflow-hidden rounded-[1.75rem] bg-amber-200 p-4 shadow-[0_18px_50px_rgba(28,25,23,0.2)] sm:p-6">
      <div className="absolute inset-x-0 top-0 h-2 bg-amber-400" />
      {/* Shimmer overlay */}
      <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.4s_infinite] bg-gradient-to-r from-transparent via-white/40 to-transparent" />
      <div className="flex flex-col items-center justify-center gap-4 py-8">
        {/* Spinner */}
        <div className="relative flex h-20 w-20 items-center justify-center">
          <div className="absolute h-20 w-20 animate-spin rounded-full border-4 border-stone-950/10 border-t-stone-950" />
          <Sunrise size={32} className="text-stone-800" strokeWidth={2.2} />
        </div>
        <div className="text-center">
          <p className="text-base font-black text-stone-800">{message}</p>
          <p className="mt-1 text-sm font-bold text-stone-600">కొంచెం వేచి ఉండండి...</p>
        </div>
      </div>
      {/* Skeleton bars */}
      <div className="mt-2 grid grid-cols-2 gap-2">
        <div className="h-16 animate-pulse rounded-2xl bg-amber-300" />
        <div className="h-16 animate-pulse rounded-2xl bg-amber-300" />
      </div>
    </div>
  )
}

// ── Error Banner ────────────────────────────────────────────────────────────
function ErrorBanner({ onRetry, onManual }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-4">
      <p className="text-sm font-black text-red-700">⚠️ సూర్యోదయం సమయం రాలేదు</p>
      <p className="mt-1 text-xs font-bold text-red-500">
        Internet లేదా GPS సమస్య ఉండవచ్చు.
      </p>
      <div className="mt-3 flex gap-2">
        <button
          onClick={onRetry}
          className="flex-1 rounded-xl bg-red-600 py-2 text-xs font-black text-white transition hover:bg-red-700"
        >
          మళ్లీ ప్రయత్నించు
        </button>
        <button
          onClick={onManual}
          className="flex-1 rounded-xl border border-red-300 bg-white py-2 text-xs font-black text-red-700 transition hover:bg-red-50"
        >
          Manual సమయం పెట్టు
        </button>
      </div>
    </div>
  )
}

function getStatusText(status) {
  const messages = {
    idle: 'సిద్ధం',
    loading: 'సూర్యోదయం తెస్తున్నాము',
    locating: 'స్థానం చూస్తున్నాము',
    searching: 'స్థానం వెతుకుతున్నాము',
    manual: 'మాన్యువల్ సూర్యోదయం',
    error: 'సమయం దొరకలేదు',
  }
  return messages[status] || messages.idle
}

function App() {
  const todayStr = useMemo(() => toDateInputValue(), [])
  const [dateValue, setDateValue] = useState(todayStr)
  const [location, setLocation] = useState(defaultLocation)
  const [locationQuery, setLocationQuery] = useState(defaultLocation.name)
  const [manualSunrise, setManualSunrise] = useState('')
  const [sunrise, setSunrise] = useState(() => combineDateAndTime(todayStr, '05:38'))
  const [status, setStatus] = useState('loading')
  const [notice, setNotice] = useState('')
  const [now, setNow] = useState(() => new Date())
  const [retryCount, setRetryCount] = useState(0)
  const calendarScrollRef = useRef(null)
  const manualInputRef = useRef(null)

  // Tick every 30s
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30 * 1000)
    return () => window.clearInterval(timer)
  }, [])

  // GPS runs silently in the background — does NOT block sunrise from loading
  // Sunrise fetches immediately with default location; GPS updates it if/when ready
  useEffect(() => {
    if (!navigator.geolocation) return
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          name: 'ప్రస్తుత స్థానం',
          latitude: Number(position.coords.latitude.toFixed(4)),
          longitude: Number(position.coords.longitude.toFixed(4)),
        })
        setLocationQuery('ప్రస్తుత స్థానం')
      },
      () => { /* silently ignore — default location already loaded */ },
      { enableHighAccuracy: false, timeout: 5000, maximumAge: 60000 },
    )
  }, [])

  // Fetch sunrise whenever location / date / manualSunrise / retryCount changes
  useEffect(() => {
    let cancelled = false

    async function loadSunrise() {
      if (manualSunrise) {
        setSunrise(combineDateAndTime(dateValue, manualSunrise))
        setStatus('manual')
        setNotice('Googleలో కనిపించిన sunrise సమయాన్ని ఉపయోగిస్తున్నాము.')
        return
      }

      setStatus('loading')
      setNotice('')

      try {
        const next = await fetchSunriseForLocation(location, dateValue)
        if (!cancelled) {
          setSunrise(next)
          setStatus('idle')
          setNotice('')
        }
      } catch {
        if (!cancelled) {
          // Auto-retry once with default location
          if (location !== defaultLocation) {
            try {
              const fallback = await fetchSunriseForLocation(defaultLocation, dateValue)
              if (!cancelled) {
                setSunrise(fallback)
                setLocation(defaultLocation)
                setLocationQuery(defaultLocation.name)
                setStatus('idle')
                setNotice('GPS స్థానం పనిచేయలేదు. Default స్థానం వాడుతున్నాము.')
              }
            } catch {
              if (!cancelled) setStatus('error')
            }
          } else {
            setStatus('error')
          }
        }
      }
    }

    loadSunrise()
    return () => { cancelled = true }
  }, [dateValue, location, manualSunrise, retryCount])

  // Scroll calendar so TODAY is the first visible day on mount
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      if (!calendarScrollRef.current) return
      const todayEl = calendarScrollRef.current.querySelector('[data-today="true"]')
      if (todayEl) {
        // Set scrollLeft directly so today lands at the left edge
        calendarScrollRef.current.scrollLeft =
          todayEl.offsetLeft - calendarScrollRef.current.offsetLeft
      }
    })
    return () => cancelAnimationFrame(frame)
  }, [])

  const slots = useMemo(() => buildNavagrahaSlots(sunrise, 24), [sunrise])
  const activeSlot = useMemo(() => findActiveSlot(slots, now), [slots, now])
  const dayStartPlanet = planets[weekdayStartPlanet[sunrise.getDay()]]
  const activePlanet = activeSlot ? planets[activeSlot.planetKey] : dayStartPlanet
  const activePlanetKey = activeSlot?.planetKey || weekdayStartPlanet[sunrise.getDay()]
  const activeIsDark = hasDarkSignal(activePlanetKey)
  const nextSlot = activeSlot ? slots[(activeSlot.index + 1) % slots.length] : slots[1]
  const nextPlanet = nextSlot ? planets[nextSlot.planetKey] : null
  const selectedWeekday = teluguWeekdays[sunrise.getDay()]
  const statusText = getStatusText(status)
  const isLoading = status === 'loading' || status === 'locating'

  // Calendar: 7 past days + today + 22 future = 30 days; today is always first visible
  const calendarDays = useMemo(() => {
    const base = new Date()
    base.setHours(12, 0, 0, 0)
    return Array.from({ length: 30 }, (_, i) => {
      const d = new Date(base)
      d.setDate(base.getDate() + i - 7) // 7 past days before today
      const value = toDateInputValue(d)
      const planetKey = weekdayStartPlanet[d.getDay()]
      return {
        value,
        label: shortDateFormatter.format(d),
        weekday: teluguWeekdays[d.getDay()],
        planet: planets[planetKey].telugu,
        planetKey,
        isToday: value === todayStr,
      }
    })
  }, [todayStr])

  async function handleUseMyLocation() {
    if (!navigator.geolocation) {
      setStatus('error')
      setNotice('ఈ browser లో location permission అందుబాటులో లేదు.')
      return
    }
    setStatus('locating')
    setNotice('')
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          name: 'ప్రస్తుత స్థానం',
          latitude: Number(position.coords.latitude.toFixed(4)),
          longitude: Number(position.coords.longitude.toFixed(4)),
        })
        setLocationQuery('ప్రస్తుత స్థానం')
        setManualSunrise('')
      },
      () => {
        setStatus('error')
        setNotice('Location permission రాలేదు. స్థానం పేరు లేదా manual sunrise ఉపయోగించండి.')
      },
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  async function handleSearchLocation(event) {
    event.preventDefault()
    const query = locationQuery.trim()
    if (!query) return
    setStatus('searching')
    setNotice('')
    try {
      const next = await searchLocation(query)
      setLocation(next)
      setLocationQuery(next.name)
      setManualSunrise('')
    } catch {
      setStatus('error')
      setNotice('ఆ స్థానం దొరకలేదు. నగరం పేరు మళ్లీ ప్రయత్నించండి.')
    }
  }

  return (
    <main className="min-h-screen overflow-x-hidden bg-[#f7f3ec] text-stone-950">
      {/* Shimmer keyframe */}
      <style>{`
        @keyframes shimmer {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(200%); }
        }
      `}</style>

      <section className="mx-auto w-full max-w-6xl px-3 py-3 pb-[calc(1rem+env(safe-area-inset-bottom))] sm:px-6 lg:px-8">
        {/* Nav */}
        <nav className="mb-4 flex items-center justify-between gap-3 rounded-[1.25rem] border border-white bg-white/90 p-3 shadow-[0_12px_36px_rgba(41,31,20,0.08)] backdrop-blur">
          <div className="flex min-w-0 items-center gap-3">
            <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-amber-400 text-stone-950 shadow-inner sm:h-14 sm:w-14">
              <Sunrise size={26} strokeWidth={2.4} />
            </span>
            <div className="min-w-0">
              <p className="truncate font-display text-xl font-black leading-tight sm:text-2xl">నవగ్రహ హోరా</p>
              <p className="truncate text-sm font-bold text-stone-500">Sunrise based calendar</p>
            </div>
          </div>
          <span className={`hidden rounded-full border px-3 py-1.5 text-xs font-black sm:block ${
            status === 'error'
              ? 'border-red-200 bg-red-50 text-red-700'
              : isLoading
                ? 'border-amber-200 bg-amber-50 text-amber-700'
                : 'border-emerald-200 bg-emerald-50 text-emerald-800'
          }`}>
            {isLoading && (
              <span className="mr-1.5 inline-block h-2 w-2 animate-pulse rounded-full bg-current" />
            )}
            {statusText}
          </span>
        </nav>

        <div className="grid gap-4 lg:grid-cols-[0.82fr_1.18fr] lg:items-start">
          <section className="grid gap-4">

            {/* ── Current Hora Card ─────────────────────────────── */}
            {isLoading ? (
              <LoadingCard message={status === 'locating' ? 'స్థానం చూస్తున్నాము...' : 'సూర్యోదయం తెస్తున్నాము...'} />
            ) : (
              <article
                className={`relative overflow-hidden rounded-[1.75rem] p-4 shadow-[0_18px_50px_rgba(28,25,23,0.2)] sm:p-6 ${
                  activeIsDark
                    ? 'bg-stone-950 text-white ring-4 ring-stone-300/70'
                    : 'bg-amber-300 text-stone-950 ring-4 ring-amber-100'
                }`}
              >
                <div className={`absolute inset-x-0 top-0 h-2 ${activeIsDark ? 'bg-stone-700' : 'bg-amber-500'}`} />
                <div className="flex items-start justify-between gap-3">
                  <p className={`inline-flex min-w-0 items-center gap-2 rounded-full px-3 py-1.5 text-sm font-black ${
                    activeIsDark ? 'bg-white/10 text-amber-100' : 'bg-white/60 text-stone-900'
                  }`}>
                    <Crosshair size={16} />
                    <span className="truncate">{selectedWeekday} మొదలు {dayStartPlanet.telugu}</span>
                  </p>
                  <span className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-black sm:hidden ${
                    activeIsDark ? 'bg-white text-stone-950' : 'bg-stone-950 text-white'
                  }`}>
                    {statusText}
                  </span>
                </div>

                <div className="mt-7">
                  <p className={`text-sm font-black uppercase tracking-[0.18em] ${
                    activeIsDark ? 'text-stone-400' : 'text-stone-700'
                  }`}>
                    ప్రస్తుత హోరా
                  </p>
                  <h1 className="mt-2 font-display text-[4.8rem] font-black leading-[0.95] tracking-normal sm:text-8xl">
                    {activePlanet.telugu}
                  </h1>
                  <p className={`mt-3 text-lg font-black ${activeIsDark ? 'text-stone-300' : 'text-stone-800'}`}>
                    {activePlanet.english}
                  </p>
                  <p className={`mt-5 rounded-2xl px-4 py-3 font-mono text-base font-black ${
                    activeIsDark ? 'bg-white text-stone-950' : 'bg-stone-950 text-white'
                  }`}>
                    {activeSlot ? formatSlotRange(activeSlot) : 'ఎంచుకున్న తేదీకి పట్టిక సిద్ధంగా ఉంది'}
                  </p>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-2">
                  <div className={`rounded-2xl p-3 ${activeIsDark ? 'bg-white/10' : 'bg-white/50'}`}>
                    <p className={`flex items-center gap-1.5 text-xs font-black ${activeIsDark ? 'text-stone-400' : 'text-stone-700'}`}>
                      <Sunrise size={15} /> సూర్యోదయం
                    </p>
                    <p className="mt-1 font-display text-2xl font-black">{formatTime(sunrise)}</p>
                  </div>
                  <div className={`rounded-2xl p-3 ${activeIsDark ? 'bg-white/10' : 'bg-white/50'}`}>
                    <p className={`flex items-center gap-1.5 text-xs font-black ${activeIsDark ? 'text-stone-400' : 'text-stone-700'}`}>
                      <Sparkles size={15} /> తదుపరి
                    </p>
                    <p className="mt-1 truncate font-display text-2xl font-black">{nextPlanet?.telugu || '-'}</p>
                  </div>
                </div>
              </article>
            )}

            {/* ── Controls Card ─────────────────────────────────── */}
            <article className="rounded-[1.5rem] border border-stone-200 bg-white p-3 shadow-[0_10px_30px_rgba(41,31,20,0.07)] sm:p-4">
              <form className="grid gap-3" onSubmit={handleSearchLocation}>
                <label className="grid min-w-0 gap-1.5">
                  <span className="text-sm font-black text-stone-600">స్థానం</span>
                  <span className="relative min-w-0">
                    <MapPin className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" size={19} />
                    <input
                      className="h-12 w-full min-w-0 rounded-2xl border border-stone-200 bg-stone-50 pl-10 pr-3 font-bold outline-none transition placeholder:text-stone-400 focus:border-amber-500 focus:bg-white focus:ring-4 focus:ring-amber-100"
                      value={locationQuery}
                      onChange={(e) => setLocationQuery(e.target.value)}
                      placeholder="City, State"
                    />
                  </span>
                </label>

                <div className="grid grid-cols-[1fr_auto_auto] gap-2">
                  <button
                    className="inline-flex h-12 min-w-0 items-center justify-center gap-2 rounded-2xl bg-stone-950 px-4 font-black text-white shadow-sm transition hover:bg-stone-800"
                    type="submit"
                  >
                    <Search size={18} />
                    <span className="truncate">వెతకండి</span>
                  </button>
                  <button
                    className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-stone-200 bg-white text-stone-800 transition hover:border-amber-400 hover:bg-amber-50"
                    type="button"
                    onClick={handleUseMyLocation}
                    title="నా ప్రస్తుత స్థానం"
                  >
                    <LocateFixed size={20} />
                  </button>
                  <button
                    className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-stone-200 bg-white text-stone-800 transition hover:border-amber-400 hover:bg-amber-50"
                    type="button"
                    onClick={() => setManualSunrise('')}
                    title="Auto sunrise refresh"
                  >
                    <RefreshCcw size={20} />
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <label className="grid min-w-0 gap-1.5">
                    <span className="text-sm font-black text-stone-600">తేదీ</span>
                    <span className="relative min-w-0">
                      <CalendarDays className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" size={18} />
                      <input
                        className="h-12 w-full min-w-0 rounded-2xl border border-stone-200 bg-stone-50 pl-10 pr-2 font-bold outline-none transition focus:border-amber-500 focus:bg-white focus:ring-4 focus:ring-amber-100"
                        type="date"
                        value={dateValue}
                        onChange={(e) => setDateValue(e.target.value)}
                      />
                    </span>
                  </label>

                  <label className="grid min-w-0 gap-1.5">
                    <span className="text-sm font-black text-stone-600">Sunrise</span>
                    <span className="relative min-w-0">
                      <Clock3 className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" size={18} />
                      <input
                        ref={manualInputRef}
                        className="h-12 w-full min-w-0 rounded-2xl border border-stone-200 bg-stone-50 pl-10 pr-2 font-bold outline-none transition focus:border-amber-500 focus:bg-white focus:ring-4 focus:ring-amber-100"
                        type="time"
                        value={manualSunrise}
                        onChange={(e) => setManualSunrise(e.target.value)}
                      />
                    </span>
                  </label>
                </div>
              </form>

              {/* Error banner */}
              {status === 'error' ? (
                <ErrorBanner
                  onRetry={() => setRetryCount((c) => c + 1)}
                  onManual={() => manualInputRef.current?.focus()}
                />
              ) : (
                <p className="mt-3 line-clamp-2 min-h-5 break-words text-sm font-bold text-stone-500">
                  {notice || location.name}
                </p>
              )}
            </article>
          </section>

          {/* ── Hora Table ──────────────────────────────────────── */}
          <section className="min-w-0 rounded-[1.75rem] border border-stone-200 bg-white p-3 shadow-[0_10px_30px_rgba(41,31,20,0.07)] sm:p-4">
            <div className="mb-3 flex items-end justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-black text-stone-500">హోరా పట్టిక</p>
                <h2 className="truncate font-display text-2xl font-black">{teluguDateFormatter.format(sunrise)}</h2>
              </div>
              {isLoading ? (
                <div className="hidden h-7 w-32 animate-pulse rounded-full bg-stone-100 sm:block" />
              ) : (
                <p className="hidden rounded-full bg-amber-100 px-3 py-1 text-xs font-black text-amber-900 sm:block">
                  {formatTime(sunrise)} మొదలు
                </p>
              )}
            </div>

            {/* ── Calendar Strip (starts from today) ────────────── */}
            <div ref={calendarScrollRef} className="touch-scroll -mx-3 overflow-x-auto px-3 pb-2 sm:mx-0 sm:px-0">
              <div className="flex min-w-max gap-2">
                {calendarDays.map((day) => (
                  <button
                    key={day.value}
                    data-today={day.isToday ? 'true' : 'false'}
                    className={`relative min-h-[4.8rem] w-28 shrink-0 rounded-2xl border p-2 text-left transition ${
                      day.value === dateValue
                        ? hasDarkSignal(day.planetKey)
                          ? 'border-stone-950 bg-stone-950 text-white shadow-lg'
                          : 'border-amber-500 bg-amber-300 text-stone-950 shadow-lg'
                        : hasDarkSignal(day.planetKey)
                          ? 'border-stone-800 bg-stone-900 text-white opacity-80 hover:opacity-100'
                          : 'border-amber-300 bg-amber-100 text-stone-950 hover:border-amber-500 hover:bg-amber-200'
                    }`}
                    type="button"
                    onClick={() => setDateValue(day.value)}
                  >
                    {day.isToday && (
                      <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    )}
                    <span className="block truncate text-[11px] font-black opacity-70">{day.weekday}</span>
                    <span className="mt-1 block truncate font-display text-base font-black leading-tight">{day.label}</span>
                    <span className="mt-1 block truncate text-xs font-black opacity-80">{day.planet}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* ── Hora Slots ──────────────────────────────────────── */}
            {isLoading ? (
              <div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: 12 }).map((_, i) => (
                  <div key={i} className="h-16 animate-pulse rounded-2xl bg-stone-100" />
                ))}
              </div>
            ) : (
              <div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                {slots.map((slot) => {
                  const planet = planets[slot.planetKey]
                  const isDark = hasDarkSignal(slot.planetKey)
                  const isActive = activeSlot?.id === slot.id
                  return (
                    <article
                      key={slot.id}
                      className={`grid grid-cols-[auto_1fr_auto] items-center gap-3 rounded-2xl border p-3 transition ${
                        isActive
                          ? isDark
                            ? 'border-white bg-stone-800 text-white shadow-xl ring-2 ring-white/30'
                            : 'border-amber-600 bg-amber-400 text-stone-950 shadow-xl ring-2 ring-amber-300'
                          : isDark
                            ? 'border-stone-950 bg-stone-950 text-white shadow-lg hover:bg-stone-800'
                            : 'border-amber-300 bg-amber-100 text-stone-950 shadow-sm hover:border-amber-500 hover:bg-amber-200'
                      }`}
                    >
                      <div className={`grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br ${planet.tone} ${planet.text} font-display text-lg font-black`}>
                        {planet.telugu.slice(0, 1)}
                      </div>
                      <div className="min-w-0">
                        <h3 className="truncate font-display text-xl font-black leading-tight">{planet.telugu}</h3>
                        <p className={`truncate text-xs font-black ${isDark ? 'text-white/80' : 'text-stone-700'}`}>
                          {formatSlotRange(slot)}
                        </p>
                      </div>
                      <span className={`rounded-full px-2.5 py-1 text-xs font-black ${
                        isDark ? 'bg-white text-stone-950' : 'bg-stone-950 text-white'
                      }`}>
                        {String(slot.index + 1).padStart(2, '0')}
                      </span>
                    </article>
                  )
                })}
              </div>
            )}
          </section>
        </div>
      </section>
    </main>
  )
}

export default App
