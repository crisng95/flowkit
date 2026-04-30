/**
 * Modal — backward-compatible shim over Shadcn Dialog.
 * Existing usage: <Modal title="..." onClose={...} width={...}>{children}</Modal>
 */
import React from 'react'
import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from './dialog'

interface ModalProps {
    title?: React.ReactNode
    onClose?: () => void
    open?: boolean
    width?: number | string
    children: React.ReactNode
    className?: string
    /** Extra classes for the DialogContent */
    contentClassName?: string
}

export function Modal({
    title,
    onClose,
    open = true,
    width,
    children,
    contentClassName,
}: ModalProps) {
    return (
        <Dialog open={open} onOpenChange={v => { if (!v && onClose) onClose() }}>
            <DialogContent
                className={contentClassName}
                style={width ? { maxWidth: typeof width === 'number' ? `${width}px` : width } : undefined}
            >
                {title && (
                    <DialogHeader className="shrink-0 px-5 pt-5 pb-3 border-b border-[hsl(var(--border))]">
                        <DialogTitle>{title}</DialogTitle>
                    </DialogHeader>
                )}
                <div className="flex-1 overflow-y-auto p-5">
                    {children}
                </div>
            </DialogContent>
        </Dialog>
    )
}

export default Modal
