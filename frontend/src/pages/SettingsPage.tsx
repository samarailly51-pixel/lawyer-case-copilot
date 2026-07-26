import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api } from '../api'
import { Badge } from '../components'
import type { CurrentUser, Member, ReadinessReport } from '../types'

export default function SettingsPage() {
  const [me, setMe] = useState<CurrentUser | null>(null)
  const [members, setMembers] = useState<Member[]>([])
  const [readiness, setReadiness] = useState<ReadinessReport | null>(null)
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    const current = await api.me()
    setMe(current)
    if (current.workspace.role === 'admin' || current.workspace.role === 'lawyer') {
      setMembers(await api.members(current.workspace.id))
    }
    if (current.workspace.role === 'admin') {
      setReadiness(await api.systemReadiness())
    }
  }

  useEffect(() => { load().catch(event => setError(event.message)) }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!me) return
    const payload = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>
    try {
      await api.addMember(me.workspace.id, payload)
      setOpen(false)
      await load()
    } catch (event) {
      setError((event as Error).message)
    }
  }

  return <div className="case-list-shell">
    <header className="topbar">
      <Link to="/" className="brand"><span className="brand-mark">L</span><div><strong>Lawyer Case Copilot</strong><small>返回案件工作台</small></div></Link>
      <div className="top-actions"><Badge tone="info">{me?.workspace.role || '—'}</Badge><button className="ghost" onClick={() => { localStorage.removeItem('lcc_token'); location.href = '/login' }}>退出登录</button></div>
    </header>
    <main className="case-list-main">
      <section className="page-intro">
        <div><p className="eyebrow">WORKSPACE ADMIN</p><h1>律所工作空间</h1><p>管理成员与角色，并查看部署配置是否满足生产准入门禁。</p></div>
        {me?.workspace.role === 'admin' && <button className="primary" onClick={() => setOpen(true)}>添加成员</button>}
      </section>
      {error && <div className="alert">{error}</div>}
      <section className="panel table-panel">
        <div className="panel-head"><div><h3>{me?.workspace.name || '当前工作空间'}</h3><small>viewer 只读 · assistant 办案协作 · lawyer 律师复核 · admin 管理员</small></div><Badge tone="neutral">{members.length} 名成员</Badge></div>
        <table><thead><tr><th>成员</th><th>邮箱</th><th>角色</th><th>状态</th></tr></thead><tbody>{members.map(member => <tr key={member.id}><td><strong>{member.display_name}</strong></td><td>{member.email}</td><td>{me?.workspace.role === 'admin' && member.id !== me.user.id ? <select className="category-select" value={member.role} onChange={async event => { await api.updateMember(me.workspace.id, member.id, event.target.value); await load() }}><option value="viewer">viewer</option><option value="assistant">assistant</option><option value="lawyer">lawyer</option><option value="admin">admin</option></select> : <Badge tone="info">{member.role}</Badge>}</td><td><Badge tone={member.status === 'active' ? 'success' : 'warning'}>{member.status}</Badge></td></tr>)}</tbody></table>
      </section>
      <section className="panel">
        <div className="panel-head">
          <div><h3>生产准入检查</h3><small>展示代码可自动验证的配置，不替代人工安全与合规评审。</small></div>
          {readiness && <Badge tone={readiness.ready ? 'success' : 'warning'}>{readiness.ready ? '配置就绪' : `${readiness.failure_count} 项阻断`}</Badge>}
        </div>
        {me?.workspace.role !== 'admin'
          ? <div className="empty"><p>仅管理员可查看生产准入配置。</p></div>
          : readiness && <div className="readiness-list">{readiness.checks.map(check => <article key={check.id}><Badge tone={check.status === 'pass' ? 'success' : check.status === 'warn' ? 'warning' : 'danger'}>{check.status.toUpperCase()}</Badge><div><strong>{check.id}</strong><p>{check.message}</p></div></article>)}</div>}
        {readiness && <p className="readiness-disclaimer">{readiness.disclaimer}</p>}
      </section>
    </main>
    {open && <div className="modal-backdrop"><form className="modal" onSubmit={submit}><div className="modal-head"><div><p className="eyebrow">NEW MEMBER</p><h2>添加工作空间成员</h2></div><button type="button" className="ghost" onClick={() => setOpen(false)}>关闭</button></div><label>姓名<input name="display_name" required /></label><label>邮箱<input name="email" type="email" required /></label><label>初始密码<input name="password" type="password" minLength={12} required /></label><label>角色<select name="role" defaultValue="assistant"><option value="viewer">viewer</option><option value="assistant">assistant</option><option value="lawyer">lawyer</option><option value="admin">admin</option></select></label><button className="primary full">添加成员</button></form></div>}
  </div>
}
