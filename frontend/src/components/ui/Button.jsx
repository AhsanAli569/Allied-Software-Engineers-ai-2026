const VARIANTS = {
  primary:
    'bg-mint text-navy shadow-sm hover:bg-mint-dark hover:shadow-md disabled:bg-mint/40 disabled:text-navy/50 font-semibold',
  secondary:
    'bg-card text-charcoal hover:bg-slate-200 dark:bg-white/10 dark:text-slate-100 dark:hover:bg-white/15',
  ghost: 'text-muted hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-white/10',
  danger: 'bg-error text-white hover:bg-error/90 disabled:bg-error/40',
}

export default function Button({ variant = 'primary', className = '', children, ...props }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150 ease-out hover:-translate-y-px active:translate-y-0 active:scale-[0.98] disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:active:scale-100 ${VARIANTS[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
