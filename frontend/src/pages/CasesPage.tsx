import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Badge, Icon, typeLabel } from '../components'
import type { CaseItem, PortfolioMetrics } from '../types'
import { useDemoMode } from '../demoMode'

export default function CasesPage() {
  const { readOnly } = useDemoMode()
  const [cases, setCases] = useState<CaseItem[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [identity, setIdentity] = useState<{ name: string; workspace: string; role: string } | null>(null)
  const [workspaces, setWorkspaces] = useState<Array<{ id: string; name: string; role: string }>>([])
  const [metrics, setMetrics] = useState<PortfolioMetrics | null>(null)

  const load = () => api.cases().then(setCases).catch(e => setError(e.message)).finally(() => setLoading(false))
  useEffect(() => {
    void load()
    api.portfolioMetrics().then(setMetrics).catch(() => undefined)
    api.me().then(me => setIdentity({ name: me.user.display_name, workspace: me.workspace.name, role: me.workspace.role }))
    api.workspaces().then(setWorkspaces)
  }, [])

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
      <section className="summary-row portfolio-summary">
        <div><span>虚构案例</span><strong>{metrics?.case_count ?? cases.length}</strong><small>通用 + 专业模块</small></div>
        <div><span>材料引用覆盖</span><strong>{metrics ? `${Math.round(metrics.fact_source_coverage * 100)}%` : '—'}</strong><small>事实均可回到原文</small></div>
        <div><span>赔偿项目矩阵</span><strong>{metrics?.compensation_item_count ?? '—'}</strong><small>仅整理证据与参数</small></div>
        <div><span>工作流节点</span><strong>{metrics?.workflow_node_count ?? '—'}</strong><small>可观察、可重跑</small></div>
      </section>
      <section className="portfolio-proof">
        <div>
          <p className="eyebrow">3-MINUTE PRODUCT TOUR</p>
          <h2>从材料到律师复核，一条可追溯办案链路</h2>
          <p>材料解析 → 事实与时间线 → 专业规则检查 → 风险提示 → 律师复核 → 辅助报告</p>
        </div>
        <ol>
          <li><strong>01</strong><span>发现住院日期与票据日期冲突</span></li>
          <li><strong>02</strong><span>识别护理证明等材料缺口</span></li>
          <li><strong>03</strong><span>定位风险项对应的材料原文</span></li>
          <li><strong>04</strong><span>由案件负责律师接受、修改或驳回</span></li>
        </ol>
        {cases.find(item => item.case_type === 'traffic_injury') && <Link className="tour-link" to={`/cases/${cases.find(item => item.case_type === 'traffic_injury')!.id}/traffic`}>
          进入交通事故专业演示 <Icon name="arrow" />
        </Link>}
        <small>{metrics?.disclaimer || '所有演示数据均为虚构，不评价法律结论或案件结果。'}</small>
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
