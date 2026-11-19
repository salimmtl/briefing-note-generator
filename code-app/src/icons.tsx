import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement> & { size?: number }

function Svg({ size = 20, children, ...rest }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  )
}

export const IconBriefings = (props: IconProps) => (
  <Svg {...props}>
    <path d="M6 3h9l4 4v14H6z" />
    <path d="M15 3v4h4" />
    <path d="M9 12h7M9 16h7M9 8h3" />
  </Svg>
)

export const IconAdd = (props: IconProps) => (
  <Svg {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 8v8M8 12h8" />
  </Svg>
)

export const IconReview = (props: IconProps) => (
  <Svg {...props}>
    <path d="M4 5h16v11H9l-5 4z" />
    <path d="m9 10 2 2 4-4" />
  </Svg>
)

export const IconChart = (props: IconProps) => (
  <Svg {...props}>
    <path d="M4 20V4" />
    <path d="M4 20h16" />
    <path d="M8 16v-5M12 16V8M16 16v-8" />
  </Svg>
)

export const IconRefresh = (props: IconProps) => (
  <Svg {...props}>
    <path d="M20 12a8 8 0 1 1-2.6-5.9" />
    <path d="M20 4v5h-5" />
  </Svg>
)

export const IconSun = (props: IconProps) => (
  <Svg {...props}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.2 5.2l1.4 1.4M17.4 17.4l1.4 1.4M18.8 5.2l-1.4 1.4M6.6 17.4l-1.4 1.4" />
  </Svg>
)

export const IconMoon = (props: IconProps) => (
  <Svg {...props}>
    <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z" />
  </Svg>
)

export const IconUpload = (props: IconProps) => (
  <Svg {...props}>
    <path d="M12 16V4" />
    <path d="m7 9 5-5 5 5" />
    <path d="M4 16v4h16v-4" />
  </Svg>
)

export const IconTrash = (props: IconProps) => (
  <Svg {...props}>
    <path d="M4 7h16" />
    <path d="M9 7V4h6v3" />
    <path d="M6 7l1 13h10l1-13" />
  </Svg>
)

export const IconBack = (props: IconProps) => (
  <Svg {...props}>
    <path d="M15 5l-7 7 7 7" />
  </Svg>
)

export const IconUp = (props: IconProps) => (
  <Svg {...props}>
    <path d="m6 15 6-6 6 6" />
  </Svg>
)

export const IconDown = (props: IconProps) => (
  <Svg {...props}>
    <path d="m6 9 6 6 6-6" />
  </Svg>
)

export const IconLink = (props: IconProps) => (
  <Svg {...props}>
    <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" />
    <path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" />
  </Svg>
)

export const IconAlert = (props: IconProps) => (
  <Svg {...props}>
    <path d="M12 3 2 20h20z" />
    <path d="M12 10v4M12 17h.01" />
  </Svg>
)

export function BrandMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <rect x="2" y="2" width="20" height="20" rx="5" fill="#0F6CBD" />
      <path d="M8 6.5h6l2.5 2.5v8.5H8z" fill="none" stroke="#fff" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M10 11.5h4.5M10 14.5h4.5" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}
