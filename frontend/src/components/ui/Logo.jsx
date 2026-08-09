import logoIcon from '../../assets/logo-icon.png'

export default function Logo({ size = 32, className = '' }) {
  return (
    <img
      src={logoIcon}
      width={size}
      height={size}
      className={`rounded-[22%] ${className}`}
      alt="Allied Software Engineers"
    />
  )
}
