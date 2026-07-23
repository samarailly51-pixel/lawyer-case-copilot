import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Badge, Icon, typeLabel } from '../components'
import type { CaseItem } from '../types'
import { useDemoMode } from '../demoMode'

export default function CasesPage() {
  const { readOnly } = useDemoMode()
  const [cases, setCases] = useState<CaseItem[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [identity, setIdentity] = useState<{ name: string; workspace: string; role: string } | null>(null)
  const [workspaces, setWorkspaces] = useState<Array<{ id: string; name: string; role: string }>>([])

  const load = () => api.cases().then(setCases).catch(e => setError(e.message)).finally(() => setLoading(false))
  useEffect(() => { void load(); api.me().then(me => setIdentity({ name: me.user.display_name, workspace: me.workspace.name, role: me.workspace.role })); api.workspaces().then(setWorkspaces) }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>
    try { await api.createCase(data); setOpen(false); load() } catch (e) { setError((e as Error).message) }
  }

  return <div className="case-list-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-mark">L</span><div><strong>Lawyer Case Copilot</strong><small>律师案件智能助理</small></div></div>
      <div className="top-actions"><Link to="/knowledge" className="ghost">知识资料库</Link><Link to="/settings" className="ghost">律所设置</Link>{workspaces.length > 1 && <select className="workspace-select" value={localStorage.getItem('lcc_workspace') || ''} onChange={e => { localStorage.setItem('lcc_workspace', e.target.value); location.reload() }}>{workspaces.map(w => <option value={w.id} key={w.id}>{w.name}</option>)}</select>}<div className="user-chip"><span>{identity?.name?.slice(0, 1) || '律'}</span><div>{identity?.name || '案件负责人'}<small>{identity?.workspace || '本地工作空间'} · {identity?.role || 'lawyer'}</small></div></div></div>
    </header>
    <main className="case-list-main">
      <section className="page-intro">
        <div><p className="eyebrow">CASE WORKSPACE</p><h1>案件工作台</h1><p>围绕具体案件整理材料、事实、证据与风险，所有 AI 结果均等待律师复核。</p></div>
        <button className="primary" disabled={readOnly} onClick={() => setOpen(true)}><Icon name="plus" />{readOnly ? '公开只读演示' : '创建案件'}</button>
      </section>
      <section className="summary-row">
        <div><span>进行中案件</span><strong>{cases.filter(c => c.status === 'active').length}</strong><small>本地演示工作区</small></div>
        <div><span>待复核</span><strong>{cases.length ? '2' : '0'}</strong><small>包含高风险提示</small></div>
        <div><span>专业模块</span><strong>{cases.filter(c => c.case_type === 'traffic_injury').length}</strong><small>交通事故人伤</small></div>
      </section>
      {error && <div className="alert">{error}</div>}
      <section className="case-grid">
        {loading ? <p>正在载入案件…</p> : cases.map(item => <Link className="case-card" to={`/cases/${item.id}/overview`} key={item.id}>
          <div className="card-top"><Badge tone={item.case_type === 'traffic_injury' ? 'indigo' : 'neutral'}>{typeLabel[item.case_type]}</Badge>{item.is_demo && <Badge tone="info">完全虚构 Demo</Badge>}</div>
          <h2>{item.title}</h2>
          <p className="case-meta">委托人：{item.client_name || '待录入'}</p>
          <p className="case-meta">阶段：{item.stage}</p>
          <div className="progress"><span style={{ width: `${item.progress}%` }} /></div>
          <footer><span>{item.lead_lawyer}</span><span className="enter">进入案件 <Icon name="arrow" /></span></footer>
        </Link>)}
      </section>
      <div className="safety-note"><strong>安全边界</strong><span>系统只提供办案辅助，不构成正式法律意见；责任、因果关系、鉴定与规则适用由案件负责律师判断。</span></div>
    </main>
    {open && <div className="modal-backdrop" onMouseDown={() => setOpen(false)}><form className="modal" onSubmit={submit} onMouseDown={e => e.stopPropagation()}>
      <div className="modal-head"><div><p className="eyebrow">NEW CASE</p><h2>创建案件</h2></div><button type="button" className="ghost" onClick={() => setOpen(false)}>关闭</button></div>
      <label>案件名称<input name="title" required placeholder="例如：某服务合同纠纷" /></label>
      <label>案件类型<select name="case_type" defaultValue="contract"><option value="traffic_injury">交通事故人伤</option><option value="contract">合同纠纷</option><option value="labor">劳动争议</option><option value="general_civil">一般民事纠纷</option><option value="other">其他案件</option></select></label>
      <div className="form-row"><label>委托人<input name="client_name" /></label><label>对方当事人<input name="opposing_party" /></label></div>
      <div className="form-row"><label>案件阶段<input name="stage" defaultValue="intake" /></label><label>负责人<input name="lead_lawyer" defaultValue="案件负责律师" /></label></div>
      <button className="primary full" type="submit">创建案件工作区</button>
    </form></div>}
  </div>
}
