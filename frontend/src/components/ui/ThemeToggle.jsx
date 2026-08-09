import { useTheme } from '../../context/ThemeContext'

const OPTIONS = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'System' },
]

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <div className="inline-flex rounded-lg border border-white/15 p-0.5">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          onClick={() => setTheme(opt.value)}
          aria-pressed={theme === opt.value}
          className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
            theme === opt.value ? 'bg-mint text-navy' : 'text-slate-300 hover:bg-white/10'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
