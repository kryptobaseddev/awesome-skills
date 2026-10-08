import React from 'react'
type Props = { variant?: 'primary' | 'secondary'; children: React.ReactNode; onClick?: () => void }
export function Button({ variant = 'primary', children, onClick }: Props) {
  return (
    <button onClick={onClick} className={variant === 'primary' ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-2xl shadow-lg px-4 py-2' : 'border rounded-2xl px-4 py-2'}>
      {children}
    </button>
  )
}
