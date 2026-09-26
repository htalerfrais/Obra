import { useCallback, useEffect, useRef, useState } from 'react'
import type { TopicTrackingItem } from '../../types/tracking'

export const DAY_MS = 86400000

// Chart tokens (mirror tailwind.config.js — SVG attributes can't use Tailwind classes)
export const CHART = {
  accent: '#6366F1',
  context: '#3D4255',
  grid: 'rgba(255, 255, 255, 0.06)',
  surface: '#10131A',
  textMuted: '#5F6575',
  textSecondary: '#9BA1B0',
}

/** Ebbinghaus retention R = exp(-t / S), same model as the backend recall engine. */
export function retentionAt(daysSinceReview: number, stabilityDays: number): number {
  return Math.exp(-Math.max(0, daysSinceReview) / Math.max(0.1, stabilityDays))
}

export function daysSince(dateStr: string, now = Date.now()): number {
  return (now - new Date(dateStr).getTime()) / DAY_MS
}

export function isDue(topic: TopicTrackingItem, now = Date.now()): boolean {
  return !!topic.next_review_at && new Date(topic.next_review_at).getTime() <= now
}

export function retentionPct(topic: TopicTrackingItem): number {
  return Math.round((1 - topic.forgetting_score) * 100)
}

/** Tracks an element's rendered width so SVG charts can lay out in real pixels. */
export function useElementWidth<T extends HTMLElement>() {
  const [width, setWidth] = useState(0)
  const observerRef = useRef<ResizeObserver | null>(null)
  // Callback ref: works even when the element mounts after the first render
  const ref = useCallback((node: T | null) => {
    observerRef.current?.disconnect()
    observerRef.current = null
    if (!node) return
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(node)
    observerRef.current = observer
  }, [])
  useEffect(() => () => observerRef.current?.disconnect(), [])
  return { ref, width }
}
