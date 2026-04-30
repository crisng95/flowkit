import * as React from 'react'
import { type ToastProps } from '../components/ui/toast'


const TOAST_LIMIT = 5
const TOAST_REMOVE_DELAY = 4000

type ToasterToast = ToastProps & {
    id: string
    title?: React.ReactNode
    description?: React.ReactNode
    action?: React.ReactElement
}

type Action =
    | { type: 'ADD_TOAST'; toast: ToasterToast }
    | { type: 'UPDATE_TOAST'; toast: Partial<ToasterToast> }
    | { type: 'DISMISS_TOAST'; toastId?: string }
    | { type: 'REMOVE_TOAST'; toastId?: string }

interface State {
    toasts: ToasterToast[]
}

let count = 0
function genId() {
    count = (count + 1) % Number.MAX_SAFE_INTEGER
    return count.toString()
}

const toastTimeouts = new Map<string, ReturnType<typeof setTimeout>>()

function addToRemoveQueue(toastId: string) {
    if (toastTimeouts.has(toastId)) return
    const timeout = setTimeout(() => {
        toastTimeouts.delete(toastId)
        dispatch({ type: 'REMOVE_TOAST', toastId })
    }, TOAST_REMOVE_DELAY)
    toastTimeouts.set(toastId, timeout)
}

function reducer(state: State, action: Action): State {
    switch (action.type) {
        case 'ADD_TOAST':
            return { ...state, toasts: [action.toast, ...state.toasts].slice(0, TOAST_LIMIT) }
        case 'UPDATE_TOAST':
            return { ...state, toasts: state.toasts.map(t => t.id === action.toast.id ? { ...t, ...action.toast } : t) }
        case 'DISMISS_TOAST': {
            const { toastId } = action
            if (toastId) addToRemoveQueue(toastId)
            else state.toasts.forEach(t => addToRemoveQueue(t.id))
            return { ...state, toasts: state.toasts.map(t => (t.id === toastId || !toastId) ? { ...t, open: false } : t) }
        }
        case 'REMOVE_TOAST':
            return { ...state, toasts: action.toastId ? state.toasts.filter(t => t.id !== action.toastId) : [] }
    }
}

const listeners: ((state: State) => void)[] = []
let memoryState: State = { toasts: [] }

function dispatch(action: Action) {
    memoryState = reducer(memoryState, action)
    listeners.forEach(l => l(memoryState))
}

type Toast = Omit<ToasterToast, 'id'>

function toast({ ...props }: Toast) {
    const id = genId()
    const update = (props: ToasterToast) => dispatch({ type: 'UPDATE_TOAST', toast: { ...props, id } })
    const dismiss = () => dispatch({ type: 'DISMISS_TOAST', toastId: id })
    dispatch({ type: 'ADD_TOAST', toast: { ...props, id, open: true, onOpenChange: (open: boolean) => { if (!open) dismiss() } } })

    return { id, dismiss, update }
}

function useToast() {
    const [state, setState] = React.useState<State>(memoryState)
    React.useEffect(() => {
        listeners.push(setState)
        return () => {
            const idx = listeners.indexOf(setState)
            if (idx > -1) listeners.splice(idx, 1)
        }
    }, [])
    return { ...state, toast, dismiss: (toastId?: string) => dispatch({ type: 'DISMISS_TOAST', toastId }) }
}

export { useToast, toast }
