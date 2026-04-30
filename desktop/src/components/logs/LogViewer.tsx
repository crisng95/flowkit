import { useState, useEffect, useRef } from 'react'
import { Input } from '../ui/input'
import { Button } from '../ui/button'
import { ScrollArea } from '../ui/scroll-area'
import { Badge } from '../ui/badge'
import { cn } from '../../lib/utils'

interface LogLine {
    ts: string
    level: string
    type: string
    msg: string
}

export default function LogViewer() {
    const [lines, setLines] = useState<LogLine[]>([])
    const [filter, setFilter] = useState('')
    const bottomRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const ws = new WebSocket('ws://127.0.0.1:8100/ws/dashboard')
        ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data)
                const ts = new Date().toLocaleTimeString()
                if (data.type === 'log' && data.data?.message) {
                    setLines(prev => [...prev.slice(-499), {
                        ts, level: data.data.level ?? 'INFO', type: data.type, msg: data.data.message,
                    }])
                    return
                }
                const payload = data.data ? JSON.stringify(data.data) : ''
                setLines(prev => [...prev.slice(-499), {
                    ts,
                    level: data.type === 'request_failed' ? 'ERROR' : 'INFO',
                    type: data.type ?? 'event',
                    msg: payload ? `${data.type}: ${payload}` : String(data.type ?? 'event'),
                }])
            } catch { }
        }
        return () => ws.close()
    }, [])

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [lines])

    const filtered = filter
        ? lines.filter(l =>
            l.msg.toLowerCase().includes(filter.toLowerCase()) ||
            l.type.toLowerCase().includes(filter.toLowerCase()))
        : lines

    const levelColor = (level: string) => {
        if (level === 'ERROR') return 'text-red-500'
        if (level === 'WARNING') return 'text-amber-500'
        return 'text-[hsl(var(--muted-foreground))]'
    }

    return (
        <div className="flex flex-col h-full gap-3">
            {/* Toolbar */}
            <div className="flex items-center gap-2">
                <Input
                    value={filter}
                    onChange={e => setFilter(e.target.value)}
                    placeholder="Lọc nhật ký..."
                    className="flex-1 text-xs font-mono"
                />
                <Button variant="outline" size="sm" onClick={() => setLines([])}>
                    Xóa
                </Button>
                <Badge variant="secondary" className="text-xs">
                    {filtered.length} dòng
                </Badge>
            </div>

            {/* Log content */}
            <ScrollArea className="flex-1 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-3">
                {filtered.length === 0 && (
                    <div className="py-4 text-sm text-[hsl(var(--muted-foreground))]">
                        Chưa có nhật ký — đang chờ agent hoạt động...
                    </div>
                )}
                <div className="font-mono text-[11px] space-y-0.5">
                    {filtered.map((line, i) => (
                        <div key={i} className="flex gap-2">
                            <span className="text-[hsl(var(--muted-foreground))] flex-shrink-0">{line.ts}</span>
                            <span className={cn('flex-shrink-0 w-14', levelColor(line.level))}>{line.level}</span>
                            <span className="text-[hsl(var(--primary))] flex-shrink-0 w-32">{line.type}</span>
                            <span className="text-[hsl(var(--foreground))] break-all">{line.msg}</span>
                        </div>
                    ))}
                    <div ref={bottomRef} />
                </div>
            </ScrollArea>
        </div>
    )
}
