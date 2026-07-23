import type { ReactNode } from 'react'
import type { Source } from './types'

export function Icon({ name }: { name: string }) {
  const paths: Record<string, ReactNode> = {
    cases: <><path d="M4 7.5h16v12H4z"/><path d="M8 7.5V5h8v2.5"/></>,
    overview: <><rect x="4" y="4" width="6" height="6"/><rect x="14" y="4" width="6" height="6"/><rect x="4" y="14" width="6" height="6"/><rect x="14" y="14" width="6" height="6"/></>,
    docs: <><path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h7M9 17h7"/></>,
    timeline: <><path d="M6 3v18M6 7h10M6 12h8M6 17h11"/><circle cx="6" cy="7" r="1.5"/><circle cx="6" cy="12" r="1.5"/><circle cx="6" cy="17" r="1.5"/></>,
    evidence: <><path d="M5 4h14v17H5zM8 2h8v4H8z"/><path d="m9 13 2 2 4-5"/></>,
    traffic: <><path d="M3 16l2-7h14l2 7v4h-3v-2H6v2H3zM7 9l2-4h6l2 4"/><circle cx="7" cy="15" r="1"/><circle cx="17" cy="15" r="1"/></>,
    agent: <><rect x="5" y="7" width="14" height="12" rx="2"/><path d="M12 3v4M9 12h.01M15 12h.01M9 16h6"/></>,
    review: <><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></>,
    report: <><path d="M6 3h12v18H6zM9 8h6M9 12h6M9 16h4"/></>,
    quality: <><path d="M4 19V9M10 19V5M16 19v-7M22 19H2"/><path d="m3 6 5-3 5 4 7-5"/></>,
    plus: <path d="M12 5v14M5 12h14"/>, upload: <path d="M12 16V4m0 0L7 9m5-5 5 5M5 16v4h14v-4"/>,
    play: <path d="m8 5 11 7-11 7z"/>, arrow: <path d="m9 18 6-6-6-6"/>,
  }
  return <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>
}

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: string }) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty"><span>—</span><p>{children}</p></div>
}

export function SourceLinks({ sources = [] }: { sources?: Source[] }) {
  if (!sources.length) return <span className="source-none">暂无材料引用</span>
  return <div className="sources">{sources.map((source, index) => (
    <details key={`${source.document_id}-${index}`}>
      <summary>{source.filename} · 第 {source.page_number || 1} 页</summary>
      <blockquote>{source.quote}</blockquote>
      <button type="button" className="source-open" onClick={() => window.dispatchEvent(new CustomEvent('lcc:source-preview', { detail: source }))}>定位到原文</button>
    </details>
  ))}</div>
}

export const typeLabel: Record<string, string> = {
  traffic_injury: '交通事故人伤', contract: '合同纠纷', labor: '劳动争议',
  general_civil: '一般民事纠纷', other: '其他案件',
}

export const statusTone = (status: string) => status === 'accepted' ? 'success' : status === 'rejected' ? 'danger' : status === 'modified' ? 'info' : 'warning'
export const reviewLabel = (status: string) => ({ accepted: '律师已确认', rejected: '已驳回', modified: '律师已修改', unreviewed: '待复核' }[status] || status)
