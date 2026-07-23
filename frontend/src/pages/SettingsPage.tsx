import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Badge } from '../components'
import type { CurrentUser, Member } from '../types'

export default function SettingsPage() {
  const [me, setMe] = useState<CurrentUser | null>(null)
  const [members, setMembers] = useState<Member[]>([])
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')
  const load = async () => {
    const current = await api.me(); setMe(current)
    if (current.workspace.role === 'admin' || current.workspace.role === 'lawyer') setMembers(await api.members(current.workspace.id))
  }
  useEffect(() => { load().catch(event => setError(event.message)) }, [])
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!me) return
    const payload = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>
    try { await api.addMember(me.workspace.id, payload); setOpen(false); await load() } catch (event) { setError((event as Error).message) }
  }
  return <div className="case-list-shell"><header className="topbar"><Link to="/" className="brand"><span className="brand-mark">L</span><div><strong>Lawyer Case Copilot</strong><small>返回案件工作台</small></div></Link><div className="top-actions"><Badge tone="info">{me?.workspace.role || '—'}</Badge><button className="ghost" onClick={() => { localStorage.removeItem('lcc_token'); location.href = '/login' }}>退出登录</button></div></header><main className="case-list-main"><section className="page-intro"><div><p className="eyebrow">WORKSPACE ADMIN</p><h1>律所工作空间</h1><p>管理成员与角色。第一阶段仅提供清晰的四级角色，不扩展到字段级权限。</p></div>{me?.workspace.role === 'admin' && <button className="primary" onClick={() => setOpen(true)}>添加成员</button>}</section>{error && <div className="alert">{error}</div>}<section className="panel table-panel"><div className="panel-head"><div><h3>{me?.workspace.name || '当前工作空间'}</h3><small>viewer 只读 · assistant 办案协作 · lawyer 律师复核 · admin 管理员</small></div><Badge tone="neutral">{members.length} 名成员</Badge></div><table><thead><tr><th>成员</th><th>邮箱</th><th>角色</th><th>状态</th></tr></thead><tbody>{members.map(member => <tr key={member.id}><td><strong>{member.display_name}</strong></td><td>{member.email}</td><td>{me?.workspace.role === 'admin' && member.id !== me.user.id ? <select className="category-select" value={member.role} onChange={async event => { await api.updateMember(me.workspace.id, member.id, event.target.value); await load() }}><option value="viewer">viewer</option><option value="assistant">assistant</option><option value="lawyer">lawyer</option><option value="admin">admin</option></select> : <Badge tone="info">{member.role}</Badge>}</td><td><Badge tone={member.status === 'active' ? 'success' : 'warning'}>{member.status}</Badge></td></tr>)}</tbody></table></section><section className="panel"><div className="panel-head"><h3>企业化安全状态</h3><Badge tone="success">已具备基础能力</Badge></div><div className="security-grid"><article><strong>租户隔离</strong><p>案件与知识资料按工作空间隔离。</p></article><article><strong>操作审计</strong><p>关键修改、复核和任务更新写入审计记录。</p></article><article><strong>对象存储</strong><p>支持本地加密和 S3/MinIO 后端。</p></article><article><strong>敏感信息边界</strong><p>外部模型默认禁用案件材料发送。</p></article></div></section></main>{open && <div className="modal-backdrop"><form className="modal" onSubmit={submit}><div className="modal-head"><div><p className="eyebrow">NEW MEMBER</p><h2>添加工作空间成员</h2></div><button type="button" className="ghost" onClick={() => setOpen(false)}>关闭</button></div><label>姓名<input name="display_name" required /></label><label>邮箱<input name="email" type="email" required /></label><label>初始密码<input name="password" type="password" minLength={12} required /></label><label>角色<select name="role" defaultValue="assistant"><option value="viewer">viewer</option><option value="assistant">assistant</option><option value="lawyer">lawyer</option><option value="admin">admin</option></select></label><button className="primary full">添加成员</button></form></div>}</div>
}
