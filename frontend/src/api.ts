import type { CaseItem, CurrentUser, DocumentPreview, KnowledgeSource, Member, PortfolioMetrics, QualityReport, ReadinessReport, Workspace } from './types'
import type { AuthStatus } from './demoMode'

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('lcc_token')
  const workspace = localStorage.getItem('lcc_workspace')
  const headers = new Headers(options?.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (workspace) headers.set('X-Workspace-ID', workspace)
  const response = await fetch(`${BASE}${path}`, { ...options, headers })
  if (!response.ok) {
    let message = `请求失败 (${response.status})`
    try { message = (await response.json()).detail || message } catch { /* no-op */ }
    throw new Error(message)
  }
  return response.json()
}

export const api = {
  authStatus: () => request<AuthStatus>('/auth/status'),
  login: (email: string, password: string) => request<any>('/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }),
  }),
  me: () => request<CurrentUser>('/auth/me'),
  workspaces: () => request<Array<{ id: string; name: string; slug: string; role: string }>>('/workspaces'),
  cases: () => request<CaseItem[]>('/cases'),
  portfolioMetrics: () => request<PortfolioMetrics>('/portfolio-metrics'),
  createCase: (payload: Record<string, string>) => request<CaseItem>('/cases', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  }),
  workspace: (id: string) => request<Workspace>(`/cases/${id}/workspace`),
  quality: (id: string) => request<QualityReport>(`/cases/${id}/quality`),
  knowledge: () => request<KnowledgeSource[]>('/knowledge/sources'),
  addKnowledge: (payload: Record<string, unknown>) => request<KnowledgeSource>('/knowledge/sources', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  }),
  upload: (id: string, file: File) => {
    const body = new FormData(); body.append('file', file)
    return request(`/cases/${id}/documents`, { method: 'POST', body })
  },
  reclassify: (documentId: string, category: string) => request(`/documents/${documentId}/classification`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ category }),
  }),
  run: (id: string) => request<Record<string, any>>(`/cases/${id}/runs`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ trigger_type: 'manual' }),
  }),
  runs: (id: string) => request<Array<Record<string, any>>>(`/cases/${id}/runs`),
  runDetail: (id: string) => request<Record<string, any>>(`/runs/${id}`),
  rerunNode: (runId: string, node: string) => request(`/runs/${runId}/nodes/${node}/rerun`, { method: 'POST' }),
  review: (payload: Record<string, unknown>) => request('/reviews', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  }),
  batchReview: (payload: Record<string, unknown>) => request<{ processed: number }>('/reviews/batch', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  }),
  reviewHistory: (targetType: string, targetId: string) => request<{ current: Record<string, unknown>; history: Array<Record<string, any>> }>(`/reviews/${targetType}/${targetId}/history`),
  documentPreview: (documentId: string, page = 1, highlight = '') => request<DocumentPreview>(`/documents/${documentId}/preview?page=${page}&highlight=${encodeURIComponent(highlight)}`),
  openDocument: async (documentId: string) => {
    const token = localStorage.getItem('lcc_token'); const workspace = localStorage.getItem('lcc_workspace')
    const headers: Record<string, string> = {}; if (token) headers.Authorization = `Bearer ${token}`; if (workspace) headers['X-Workspace-ID'] = workspace
    const response = await fetch(`${BASE}/documents/${documentId}/content`, { headers })
    if (!response.ok) throw new Error('原始材料不可用，请使用文本预览')
    const url = URL.createObjectURL(await response.blob()); window.open(url, '_blank', 'noopener,noreferrer')
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  },
  reportCitations: (caseId: string, reportId: string) => request<Array<Record<string, any>>>(`/cases/${caseId}/reports/${reportId}/citations`),
  updateTask: (taskId: string, payload: Record<string, unknown>) => request(`/tasks/${taskId}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  }),
  auditLogs: (caseId: string) => request<Array<Record<string, any>>>(`/cases/${caseId}/audit-logs`),
  trafficRules: () => request<Array<Record<string, any>>>('/traffic-injury/rules'),
  systemReadiness: () => request<ReadinessReport>('/system/readiness'),
  compensationScenario: (caseId: string, parameters: Record<string, number>) => request<Record<string, any>>(`/cases/${caseId}/compensation-scenario`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ parameters }),
  }),
  members: (workspaceId: string) => request<Member[]>(`/workspaces/${workspaceId}/members`),
  addMember: (workspaceId: string, payload: Record<string, string>) => request<Member>(`/workspaces/${workspaceId}/members`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  }),
  updateMember: (workspaceId: string, userId: string, role: string) => request(`/workspaces/${workspaceId}/members/${userId}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ role }),
  }),
  downloadReport: async (caseId: string, reportId: string, format: 'docx' | 'md') => {
    const token = localStorage.getItem('lcc_token'); const workspace = localStorage.getItem('lcc_workspace')
    const headers: Record<string, string> = {}; if (token) headers.Authorization = `Bearer ${token}`; if (workspace) headers['X-Workspace-ID'] = workspace
    const response = await fetch(`${BASE}/cases/${caseId}/reports/${reportId}/export?format=${format}`, { headers })
    if (!response.ok) throw new Error('报告导出失败')
    const url = URL.createObjectURL(await response.blob()); const anchor = document.createElement('a')
    anchor.href = url; anchor.download = `案件辅助报告.${format}`; anchor.click(); URL.revokeObjectURL(url)
  },
}
