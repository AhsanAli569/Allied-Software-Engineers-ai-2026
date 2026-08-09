export default function Footer({ className = '' }) {
  return (
    <p className={`text-center text-xs text-slate-400 dark:text-slate-500 ${className}`}>
      © {new Date().getFullYear()} Allied Software Engineers. All Rights Reserved.
    </p>
  )
}
