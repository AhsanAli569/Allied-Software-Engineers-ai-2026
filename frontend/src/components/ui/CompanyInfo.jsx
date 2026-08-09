const BRANCHES = ['Khanewal', 'Lahore', 'Karachi', 'Islamabad', 'Sahiwal', 'Kabirwala', 'Multan', 'Bahawalpur']

export default function CompanyInfo({ className = '' }) {
  return (
    <div
      className={`space-y-2 rounded-xl border border-slate-200 bg-white/60 p-4 text-center text-xs text-muted dark:border-white/10 dark:bg-white/5 ${className}`}
    >
      <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1">
        <a
          href="https://www.alliedsoftwareengineers.com"
          target="_blank"
          rel="noreferrer"
          className="hover:text-emerald hover:underline dark:hover:text-mint"
        >
          www.alliedsoftwareengineers.com
        </a>
        <span className="text-slate-300 dark:text-white/20">•</span>
        <a
          href="https://portals.alliedsoftwareengineers.com"
          target="_blank"
          rel="noreferrer"
          className="hover:text-emerald hover:underline dark:hover:text-mint"
        >
          portals.alliedsoftwareengineers.com
        </a>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1">
        <a href="mailto:hr@alliedsoftwareengineers.com" className="hover:text-emerald hover:underline dark:hover:text-mint">
          hr@alliedsoftwareengineers.com
        </a>
        <span className="text-slate-300 dark:text-white/20">•</span>
        <span>Mon–Sat, 9:00 AM–5:00 PM (Remote)</span>
      </div>

      <p>
        <span className="font-medium text-charcoal dark:text-slate-200">Branches:</span> {BRANCHES.join(' · ')}
      </p>

      <span className="inline-flex items-center gap-1 rounded-full bg-emerald/10 px-2 py-0.5 font-medium text-emerald dark:bg-mint/10 dark:text-mint">
        ✓ SECP Approved
      </span>
    </div>
  )
}
