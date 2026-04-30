import { useState, useRef, useEffect } from 'react'
import { Input } from '../ui/input'
import { Textarea } from '../ui/textarea'
import { cn } from '../../lib/utils'

interface EditableTextProps {
  value: string
  onSave: (newValue: string) => void
  multiline?: boolean
  className?: string
  placeholder?: string
}

export default function EditableText({ value, onSave, multiline = false, className = '', placeholder }: EditableTextProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)
  const inputRef = useRef<HTMLInputElement & HTMLTextAreaElement>(null)

  useEffect(() => { setDraft(value) }, [value])
  useEffect(() => { if (editing) inputRef.current?.focus() }, [editing])

  function handleSave() {
    setEditing(false)
    if (draft !== value) onSave(draft)
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape') { setDraft(value); setEditing(false) }
    else if (e.key === 'Enter' && !multiline) handleSave()
    else if (e.key === 'Enter' && multiline && !e.shiftKey) handleSave()
  }

  if (!editing) {
    return (
      <span
        className={cn('cursor-pointer hover:opacity-60 transition-opacity', className)}
        onClick={() => setEditing(true)}
        title="Nhấn để chỉnh sửa"
      >
        {value || <span className="text-[hsl(var(--muted-foreground))] italic">{placeholder ?? '(trống)'}</span>}
      </span>
    )
  }

  if (multiline) {
    return (
      <Textarea
        ref={inputRef as React.RefObject<HTMLTextAreaElement>}
        value={draft}
        placeholder={placeholder}
        onChange={e => setDraft(e.target.value)}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        rows={4}
        className={cn('resize-y', className)}
      />
    )
  }

  return (
    <Input
      ref={inputRef as React.RefObject<HTMLInputElement>}
      type="text"
      value={draft}
      placeholder={placeholder}
      onChange={e => setDraft(e.target.value)}
      onBlur={handleSave}
      onKeyDown={handleKeyDown}
      className={className}
    />
  )
}
