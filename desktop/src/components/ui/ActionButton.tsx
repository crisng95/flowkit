/**
 * ActionButton — backward-compatible shim over Shadcn Button.
 * Existing code still works: <ActionButton variant="primary" size="sm" icon={...} />
 */
import React from 'react'
import { Button, type ButtonProps } from './button'
import { cn } from '../../lib/utils'

type LegacyVariant = 'primary' | 'danger' | 'ghost' | 'secondary' | 'outline'

interface ActionButtonProps extends Omit<ButtonProps, 'variant'> {
    /** Legacy FlowKit variants — mapped to Shadcn Button variants */
    variant?: LegacyVariant | ButtonProps['variant']
    /** Optional leading icon */
    icon?: React.ReactNode
    loading?: boolean
}

const variantMap: Record<LegacyVariant, ButtonProps['variant']> = {
    primary: 'default',
    danger: 'destructive',
    ghost: 'ghost',
    secondary: 'secondary',
    outline: 'outline',
}

export function ActionButton({
    variant = 'primary',
    icon,
    loading,
    children,
    disabled,
    className,
    ...props
}: ActionButtonProps) {
    const shadcnVariant = variantMap[variant as LegacyVariant] ?? (variant as ButtonProps['variant'])

    return (
        <Button
            variant={shadcnVariant}
            disabled={disabled || loading}
            className={cn('gap-1.5', className)}
            {...props}
        >
            {loading ? (
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
            ) : icon}
            {children}
        </Button>
    )
}

export default ActionButton
