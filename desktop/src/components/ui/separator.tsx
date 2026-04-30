import * as React from 'react'
import { cn } from '../../lib/utils'

type SeparatorProps = React.HTMLAttributes<HTMLDivElement> & {
    orientation?: 'horizontal' | 'vertical'
    decorative?: boolean
}

const Separator = React.forwardRef<HTMLDivElement, SeparatorProps>(
    ({ className, orientation = 'horizontal', decorative = true, ...props }, ref) => (
        <div
            ref={ref}
            role={decorative ? 'none' : 'separator'}
            aria-orientation={orientation}
            className={cn(
                'shrink-0 bg-[var(--border)]',
                orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px',
                className,
            )}
            {...props}
        />
    ),
)

Separator.displayName = 'Separator'

export { Separator }
