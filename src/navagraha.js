export const planetOrder = ['ravi', 'sukra', 'budha', 'chandra', 'sani', 'guru', 'kuja']

export const planets = {
  ravi: {
    telugu: 'రవి',
    english: 'Ravi',
    tone: 'from-amber-300 to-yellow-500',
    text: 'text-stone-950',
  },
  sukra: {
    telugu: 'శుక్ర',
    english: 'Sukra',
    tone: 'from-amber-300 to-yellow-500',
    text: 'text-stone-950',
  },
  budha: {
    telugu: 'బుధ',
    english: 'Budha',
    tone: 'from-amber-300 to-yellow-500',
    text: 'text-stone-950',
  },
  chandra: {
    telugu: 'చంద్ర',
    english: 'Chandra',
    tone: 'from-amber-300 to-yellow-500',
    text: 'text-stone-950',
  },
  sani: {
    telugu: 'శని',
    english: 'Sani',
    tone: 'from-stone-900 to-stone-700',
    text: 'text-white',
  },
  guru: {
    telugu: 'గురు',
    english: 'Guru',
    tone: 'from-amber-300 to-yellow-500',
    text: 'text-stone-950',
  },
  kuja: {
    telugu: 'కుజ',
    english: 'Kuja',
    tone: 'from-stone-900 to-stone-700',
    text: 'text-white',
  },
}

export const weekdayStartPlanet = {
  0: 'ravi',
  1: 'chandra',
  2: 'kuja',
  3: 'budha',
  4: 'guru',
  5: 'sukra',
  6: 'sani',
}

export const teluguWeekdays = [
  'ఆదివారం',
  'సోమవారం',
  'మంగళవారం',
  'బుధవారం',
  'గురువారం',
  'శుక్రవారం',
  'శనివారం',
]

export function toDateInputValue(date = new Date()) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function combineDateAndTime(dateValue, timeValue) {
  const [year, month, day] = dateValue.split('-').map(Number)
  const [hour, minute] = timeValue.split(':').map(Number)
  return new Date(year, month - 1, day, hour, minute, 0, 0)
}

export function getPlanetForSlot(date, slotIndex) {
  const firstPlanet = weekdayStartPlanet[date.getDay()]
  const startIndex = planetOrder.indexOf(firstPlanet)
  return planetOrder[(startIndex + slotIndex) % planetOrder.length]
}

export function buildNavagrahaSlots(sunriseDate, slotCount = 24) {
  return Array.from({ length: slotCount }, (_, index) => {
    const startsAt = new Date(sunriseDate.getTime() + index * 60 * 60 * 1000)
    const endsAt = new Date(startsAt.getTime() + 60 * 60 * 1000)
    return {
      id: `${startsAt.toISOString()}-${index}`,
      index,
      planetKey: getPlanetForSlot(sunriseDate, index),
      startsAt,
      endsAt,
    }
  })
}

export function findActiveSlot(slots, now = new Date()) {
  return slots.find((slot) => now >= slot.startsAt && now < slot.endsAt) || null
}
