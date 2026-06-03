import { useEffect, useMemo, useState } from 'react'
import {
  CalendarDays,
  Clock3,
  Crosshair,
  LocateFixed,
  MapPin,
  RefreshCcw,
  Search,
  Sparkles,
  Sunrise,
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

const shortDateFormatter = new Intl.DateTimeFormat('te-IN', {
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

  if (!response.ok) {
    throw new Error('Sunrise lookup failed')
  }

  const data = await response.json()
  const sunriseValue = data?.daily?.sunrise?.[0]

  if (!sunriseValue) {
    throw new Error('Sunrise time is unavailable')
  }

  return parseOpenMeteoTime(sunriseValue)
}

async function searchLocation(query) {
  const params = new URLSearchParams({
    name: query,
    count: '1',
    language: 'en',
    format: 'json',
  })
  const response = await fetch(`https://geocoding-api.open-meteo.com/v1/search?${params}`)

  if (!response.ok) {
    throw new Error('Location search failed')
  }

  const data = await response.json()
  const match = data?.results?.[0]

  if (!match) {
    throw new Error('Location not found')
  }

  return {
    name: [match.name, match.admin1, match.country].filter(Boolean).join(', '),
    latitude: match.latitude,
    longitude: match.longitude,
  }
}

function getStatusText(status) {
  const messages = {
    idle: 'సిద్ధం',
    loading: 'సూర్యోదయం చూస్తున్నాము',
    locating: 'మీ స్థానాన్ని చూస్తున్నాము',
    searching: 'స్థానం వెతుకుతున్నాము',
    manual: 'మాన్యువల్ సూర్యోదయం',
    error: 'సమయం దొరకలేదు',
  }
  return messages[status] || messages.idle
}

function App() {
  const [dateValue, setDateValue] = useState(() => toDateInputValue())
  const [location, setLocation] = useState(defaultLocation)
  const [locationQuery, setLocationQuery] = useState(defaultLocation.name)
  const [manualSunrise, setManualSunrise] = useState('')
  const [sunrise, setSunrise] = useState(() => combineDateAndTime(toDateInputValue(), '05:38'))
  const [status, setStatus] = useState('loading')
  const [notice, setNotice] = useState('')
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30 * 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    let cancelled = false

    async function loadSunrise() {
      if (manualSunrise) {
        setSunrise(combineDateAndTime(dateValue, manualSunrise))
        setStatus('manual')
        setNotice('Googleలో కనిపించిన sunrise సమయాన్ని ఇక్కడ ఉపయోగిస్తున్నాము.')
        return
      }

      setStatus('loading')
      setNotice('')

      try {
        const nextSunrise = await fetchSunriseForLocation(location, dateValue)
        if (!cancelled) {
          setSunrise(nextSunrise)
          setStatus('idle')
        }
      } catch (error) {
        if (!cancelled) {
          setStatus('error')
          setNotice('స్వయంచాలక sunrise రాలేదు. Google సమయాన్ని manual field లో పెట్టండి.')
        }
      }
    }

    loadSunrise()
    return () => {
      cancelled = true
    }
  }, [dateValue, location, manualSunrise])

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
  const calendarDays = useMemo(() => {
    const selected = combineDateAndTime(dateValue, '12:00')
    return Array.from({ length: 7 }, (_, index) => {
      const itemDate = new Date(selected)
      itemDate.setDate(selected.getDate() + index - 3)
      const value = toDateInputValue(itemDate)
      const planetKey = weekdayStartPlanet[itemDate.getDay()]
      const startPlanet = planets[planetKey]
      return {
        value,
        label: shortDateFormatter.format(itemDate),
        weekday: teluguWeekdays[itemDate.getDay()],
        planet: startPlanet.telugu,
        planetKey,
      }
    })
  }, [dateValue])

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
        const nextLocation = {
          name: 'ప్రస్తుత స్థానం',
          latitude: Number(position.coords.latitude.toFixed(4)),
          longitude: Number(position.coords.longitude.toFixed(4)),
        }
        setLocation(nextLocation)
        setLocationQuery(nextLocation.name)
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

    if (!query) {
      return
    }

    setStatus('searching')
    setNotice('')

    try {
      const nextLocation = await searchLocation(query)
      setLocation(nextLocation)
      setLocationQuery(nextLocation.name)
      setManualSunrise('')
    } catch (error) {
      setStatus('error')
      setNotice('ఆ స్థానం దొరకలేదు. నగరం పేరు మళ్లీ ప్రయత్నించండి.')
    }
  }

  return (
    <main className="min-h-screen overflow-x-hidden bg-[#f7f3ec] text-stone-950">
      <section className="mx-auto w-full max-w-6xl px-3 py-3 pb-[calc(1rem+env(safe-area-inset-bottom))] sm:px-6 lg:px-8">
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
          <span className="hidden rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-black text-emerald-800 sm:block">
            {statusText}
          </span>
        </nav>

        <div className="grid gap-4 lg:grid-cols-[0.82fr_1.18fr] lg:items-start">
          <section className="grid gap-4">
            <article
              className={`relative overflow-hidden rounded-[1.75rem] p-4 shadow-[0_18px_50px_rgba(28,25,23,0.2)] sm:p-6 ${
                activeIsDark
                  ? 'bg-stone-950 text-white ring-4 ring-stone-300/70'
                  : 'bg-amber-300 text-stone-950 ring-4 ring-amber-100'
              }`}
            >
              <div
                className={`absolute inset-x-0 top-0 h-2 ${
                  activeIsDark ? 'bg-stone-700' : 'bg-amber-500'
                }`}
              />
              <div className="flex items-start justify-between gap-3">
                <p
                  className={`inline-flex min-w-0 items-center gap-2 rounded-full px-3 py-1.5 text-sm font-black ${
                    activeIsDark ? 'bg-white/10 text-amber-100' : 'bg-white/60 text-stone-900'
                  }`}
                >
                  <Crosshair size={16} />
                  <span className="truncate">{selectedWeekday} మొదలు {dayStartPlanet.telugu}</span>
                </p>
                <span
                  className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-black sm:hidden ${
                    activeIsDark ? 'bg-white text-stone-950' : 'bg-stone-950 text-white'
                  }`}
                >
                  {statusText}
                </span>
              </div>

              <div className="mt-7">
                <p
                  className={`text-sm font-black uppercase tracking-[0.18em] ${
                    activeIsDark ? 'text-stone-400' : 'text-stone-700'
                  }`}
                >
                  ప్రస్తుత హోరా
                </p>
                <h1 className="mt-2 font-display text-[4.8rem] font-black leading-[0.95] tracking-normal sm:text-8xl">
                  {activePlanet.telugu}
                </h1>
                <p className={`mt-3 text-lg font-black ${activeIsDark ? 'text-stone-300' : 'text-stone-800'}`}>
                  {activePlanet.english}
                </p>
                <p
                  className={`mt-5 rounded-2xl px-4 py-3 font-mono text-base font-black ${
                    activeIsDark ? 'bg-white text-stone-950' : 'bg-stone-950 text-white'
                  }`}
                >
                  {activeSlot ? formatSlotRange(activeSlot) : 'ఎంచుకున్న తేదీకి పట్టిక సిద్ధంగా ఉంది'}
                </p>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2">
                <div className={`rounded-2xl p-3 ${activeIsDark ? 'bg-white/10' : 'bg-white/50'}`}>
                  <p
                    className={`flex items-center gap-1.5 text-xs font-black ${
                      activeIsDark ? 'text-stone-400' : 'text-stone-700'
                    }`}
                  >
                    <Sunrise size={15} />
                    సూర్యోదయం
                  </p>
                  <p className="mt-1 font-display text-2xl font-black">{formatTime(sunrise)}</p>
                </div>
                <div className={`rounded-2xl p-3 ${activeIsDark ? 'bg-white/10' : 'bg-white/50'}`}>
                  <p
                    className={`flex items-center gap-1.5 text-xs font-black ${
                      activeIsDark ? 'text-stone-400' : 'text-stone-700'
                    }`}
                  >
                    <Sparkles size={15} />
                    తదుపరి
                  </p>
                  <p className="mt-1 truncate font-display text-2xl font-black">{nextPlanet?.telugu || '-'}</p>
                </div>
              </div>
            </article>

            <article className="rounded-[1.5rem] border border-stone-200 bg-white p-3 shadow-[0_10px_30px_rgba(41,31,20,0.07)] sm:p-4">
              <form className="grid gap-3" onSubmit={handleSearchLocation}>
                <label className="grid min-w-0 gap-1.5">
                  <span className="text-sm font-black text-stone-600">స్థానం</span>
                  <span className="relative min-w-0">
                    <MapPin className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" size={19} />
                    <input
                      className="h-12 w-full min-w-0 rounded-2xl border border-stone-200 bg-stone-50 pl-10 pr-3 font-bold outline-none transition placeholder:text-stone-400 focus:border-amber-500 focus:bg-white focus:ring-4 focus:ring-amber-100"
                      value={locationQuery}
                      onChange={(event) => setLocationQuery(event.target.value)}
                      placeholder="City, State"
                    />
                  </span>
                </label>

                <div className="grid grid-cols-[1fr_auto_auto] gap-2">
                  <button
                    className="inline-flex h-12 min-w-0 items-center justify-center gap-2 rounded-2xl bg-stone-950 px-4 font-black text-white shadow-sm transition hover:bg-stone-800"
                    type="submit"
                    title="స్థానం వెతకండి"
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
                      <CalendarDays
                        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-stone-400"
                        size={18}
                      />
                      <input
                        className="h-12 w-full min-w-0 rounded-2xl border border-stone-200 bg-stone-50 pl-10 pr-2 font-bold outline-none transition focus:border-amber-500 focus:bg-white focus:ring-4 focus:ring-amber-100"
                        type="date"
                        value={dateValue}
                        onChange={(event) => setDateValue(event.target.value)}
                      />
                    </span>
                  </label>

                  <label className="grid min-w-0 gap-1.5">
                    <span className="text-sm font-black text-stone-600">Sunrise</span>
                    <span className="relative min-w-0">
                      <Clock3 className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" size={18} />
                      <input
                        className="h-12 w-full min-w-0 rounded-2xl border border-stone-200 bg-stone-50 pl-10 pr-2 font-bold outline-none transition focus:border-amber-500 focus:bg-white focus:ring-4 focus:ring-amber-100"
                        type="time"
                        value={manualSunrise}
                        onChange={(event) => setManualSunrise(event.target.value)}
                      />
                    </span>
                  </label>
                </div>
              </form>
              <p className="mt-3 line-clamp-2 min-h-5 break-words text-sm font-bold text-stone-500">
                {notice || location.name}
              </p>
            </article>
          </section>

          <section className="min-w-0 rounded-[1.75rem] border border-stone-200 bg-white p-3 shadow-[0_10px_30px_rgba(41,31,20,0.07)] sm:p-4">
            <div className="mb-3 flex items-end justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-black text-stone-500">హోరా పట్టిక</p>
                <h2 className="truncate font-display text-2xl font-black">{teluguDateFormatter.format(sunrise)}</h2>
              </div>
              <p className="hidden rounded-full bg-amber-100 px-3 py-1 text-xs font-black text-amber-900 sm:block">
                {formatTime(sunrise)} మొదలు
              </p>
            </div>

            <div className="touch-scroll -mx-3 overflow-x-auto px-3 pb-2 sm:mx-0 sm:px-0">
              <div className="flex min-w-max gap-2 lg:grid lg:min-w-0 lg:grid-cols-7">
                {calendarDays.map((day) => (
                  <button
                    key={day.value}
                    className={`min-h-[4.8rem] w-28 shrink-0 rounded-2xl border p-2 text-left transition lg:w-auto ${
                      day.value === dateValue
                        ? hasDarkSignal(day.planetKey)
                          ? 'border-stone-950 bg-stone-950 text-white shadow-lg'
                          : 'border-amber-500 bg-amber-300 text-stone-950 shadow-lg'
                        : hasDarkSignal(day.planetKey)
                          ? 'border-stone-950 bg-stone-950 text-white shadow-lg hover:bg-stone-800'
                          : 'border-amber-300 bg-amber-100 text-stone-950 hover:border-amber-500 hover:bg-amber-200'
                    }`}
                    type="button"
                    onClick={() => setDateValue(day.value)}
                  >
                    <span className="block truncate text-[11px] font-black opacity-70">{day.weekday}</span>
                    <span className="mt-1 block truncate font-display text-base font-black leading-tight">{day.label}</span>
                    <span className="mt-1 block truncate text-xs font-black opacity-80">{day.planet}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {slots.map((slot) => {
                const planet = planets[slot.planetKey]
                const isDarkSignal = hasDarkSignal(slot.planetKey)
                return (
                  <article
                    className={`grid grid-cols-[auto_1fr_auto] items-center gap-3 rounded-2xl border p-3 transition ${
                      isDarkSignal
                        ? 'border-stone-950 bg-stone-950 text-white shadow-lg hover:bg-stone-800'
                        : 'border-amber-300 bg-amber-100 text-stone-950 shadow-sm hover:border-amber-500 hover:bg-amber-200'
                    }`}
                    key={slot.id}
                  >
                    <div
                      className={`grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br ${planet.tone} ${planet.text} font-display text-lg font-black`}
                    >
                      {planet.telugu.slice(0, 1)}
                    </div>
                    <div className="min-w-0">
                      <h3 className="truncate font-display text-xl font-black leading-tight">{planet.telugu}</h3>
                      <p className={`truncate text-xs font-black ${isDarkSignal ? 'text-white/80' : 'text-stone-700'}`}>
                        {formatSlotRange(slot)}
                      </p>
                    </div>
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-black ${
                        isDarkSignal ? 'bg-white text-stone-950' : 'bg-stone-950 text-white'
                      }`}
                    >
                      {String(slot.index + 1).padStart(2, '0')}
                    </span>
                  </article>
                )
              })}
            </div>
          </section>
        </div>
      </section>
    </main>
  )
}

export default App
