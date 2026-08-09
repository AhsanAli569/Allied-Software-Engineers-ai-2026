export const MINIMUM_AGE = 18

/** Mirrors the backend's age calculation (app/schemas/auth.py::calculate_age) so the
 * frontend can give an immediate, friendly error instead of waiting on a round trip —
 * the backend re-validates this regardless, since client-side checks are never trusted
 * as the actual security/business-rule boundary. */
export function calculateAge(dateOfBirth, today = new Date()) {
  const born = new Date(dateOfBirth)
  let age = today.getFullYear() - born.getFullYear()
  const hasHadBirthdayThisYear =
    today.getMonth() > born.getMonth() ||
    (today.getMonth() === born.getMonth() && today.getDate() >= born.getDate())
  if (!hasHadBirthdayThisYear) age -= 1
  return age
}

export function isDateInFuture(dateOfBirth, today = new Date()) {
  return new Date(dateOfBirth) > today
}

/** For the date input's `max` attribute — today minus MINIMUM_AGE years, formatted
 * YYYY-MM-DD. Steers the native date picker away from underage dates by default,
 * though this alone doesn't stop manual/typed entry — calculateAge is the real check. */
export function maxDateOfBirthForMinimumAge(minimumAge = MINIMUM_AGE) {
  const d = new Date()
  d.setFullYear(d.getFullYear() - minimumAge)
  return d.toISOString().slice(0, 10)
}
