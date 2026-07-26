import { ChangeEvent, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { api } from '../api'
import { Badge, Empty, Icon, reviewLabel, SourceLinks, statusTone, typeLabel } from '../components'
import type { DocumentPreview, QualityReport, Reviewable, Source, Workspace } from '../types'
import { useDemoMode } from '../demoMode'

const sections = [
  ['overview', 'overview', '案件总览'], ['documents', 'docs', '材料中心'], ['timeline', 'timeline', '事实与时间线'],
  ['evidence', 'evidence', '证据矩阵'], ['traffic', 'traffic', '交通事故分析'], ['agent', 'agent', 'Agent 执行'],
  ['review', 'review', '律师复核'], ['reports', 'report', '报告中心'],
  ['relationships', 'evidence', '主体关系'], ['tasks', 'timeline', '办案任务'],
  ['quality', 'quality', '质量与安全'],
]

export default function WorkspacePage() {
  const { readOnly } = useDemoMode()
  const { caseId = '', section = 'overview' } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState<Workspace | null>(null)
  const [runs, setRuns] = useState<Array<Record<string, any>>>([])
  const [runDetail, setRunDetail] = useState<Record<string, any> | null>(null)
  const [quality, setQuality] = useState<QualityReport | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState<DocumentPreview | null>(null)
  const [previewBusy, setPreviewBusy] = useState(false)
  const load = () => api.workspace(caseId).then(setData).catch(e => setError(e.message))
  useEffect(() => { load() }, [caseId])
  useEffect(() => {
    if (section === 'agent') api.runs(caseId).then(async items => { setRuns(items); if (items[0]) setRunDetail(await api.runDetail(items[0].id)) })
  }, [caseId, section])
  useEffect(() => { if (section === 'quality') api.quality(caseId).then(setQuality) }, [caseId, section])
  useEffect(() => {
    const handler = (event: Event) => {
      const source = (event as CustomEvent<Source>).detail
      setPreviewBusy(true)
      api.documentPreview(source.document_id, source.page_number || 1, source.quote).then(setPreview).catch(e => setError(e.message)).finally(() => setPreviewBusy(false))
    }
    window.addEventListener('lcc:source-preview', handler)
    return () => window.removeEventListener('lcc:source-preview', handler)
  }, [])

  async function runAnalysis() {
    setBusy(true); setError('')
    try {
      const run = await api.run(caseId)
      if (['pending', 'processing'].includes(run.status)) {
        for (let attempt = 0; attempt < 60; attempt += 1) {
          await new Promise(resolve => window.setTimeout(resolve, 1000))
          const detail = await api.runDetail(run.id)
          if (['awaiting_review', 'failed'].includes(detail.status)) break
        }
      }
      await load()
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; if (!file) return
    setBusy(true)
    try { await api.upload(caseId, file); await load() } catch (e) { setError((e as Error).message) } finally { setBusy(false); event.target.value = '' }
  }

  async function review(targetType: string, item: Reviewable, action: 'accepted' | 'modified' | 'rejected', revisedValue: Record<string, string> = {}) {
    await api.review({ case_id: caseId, target_type: targetType, target_id: item.id, action, reviewer: '案件负责律师', revised_value: revisedValue, comment: action === 'accepted' ? '已核对现有材料' : action === 'modified' ? '律师修改后确认' : '当前结果不采纳' })
    await load()
  }

  const pending = useMemo(() => data ? [...data.facts, ...data.missing_materials, ...data.traffic_risks, ...data.reports].filter(x => x.review_status === 'unreviewed').length : 0, [data])
  if (!data) return <div className="loading-screen">{error || '正在打开案件工作区…'}</div>
  const c = data.case

  return <div className="workspace-shell">
    <aside className="sidebar">
      <Link to="/" className="brand side-brand"><span className="brand-mark">L</span><div><strong>Case Copilot</strong><small>律师案件智能助理</small></div></Link>
      <div className="case-switch"><small>当前案件</small><strong>{c.title}</strong><span>{typeLabel[c.case_type]}</span></div>
      <nav>{sections.filter(([key]) => key !== 'traffic' || c.case_type === 'traffic_injury').map(([key, icon, label]) =>
        <button className={section === key ? 'active' : ''} onClick={() => navigate(`/cases/${caseId}/${key}`)} key={key}><Icon name={icon} />{label}{key === 'review' && pending > 0 && <i>{pending}</i>}</button>
      )}</nav>
      <div className="sidebar-disclaimer"><span>AI 办案辅助</span><p>重要结论须经案件负责律师复核。</p></div>
    </aside>
    <main className="workspace-main">
      <header className="workspace-header"><div><div className="breadcrumbs"><Link to="/">案件工作台</Link><span>/</span><span>{typeLabel[c.case_type]}</span></div><h1>{c.title}</h1><div className="header-meta"><Badge tone="success">{c.status === 'active' ? '办理中' : c.status}</Badge><span>负责人：{c.lead_lawyer}</span><span>阶段：{c.stage}</span>{c.is_demo && <Badge tone="info">完全虚构 Demo</Badge>}</div></div><button className="primary" disabled={busy || readOnly} onClick={runAnalysis}><Icon name="play" />{readOnly ? '公开只读演示' : busy ? '处理中…' : '运行案件分析'}</button></header>
      {error && <div className="alert">{error}</div>}
      <div className="content-area">
        {section === 'overview' && <Overview data={data} pending={pending} />}
        {section === 'documents' && <Documents data={data} busy={busy} upload={upload} preview={id => api.documentPreview(id).then(setPreview).catch(e => setError(e.message))} reclassify={async (id, category) => { await api.reclassify(id, category); await load() }} />}
        {section === 'timeline' && <Timeline data={data} />}
        {section === 'evidence' && <EvidenceMatrix data={data} />}
        {section === 'traffic' && <Traffic data={data} />}
        {section === 'agent' && <AgentRuns detail={runDetail} runs={runs} rerun={async node => { if (runDetail) { await api.rerunNode(runDetail.id, node); setRunDetail(await api.runDetail(runDetail.id)); await load() } }} />}
        {section === 'review' && <ReviewCenter data={data} review={review} reload={load} caseId={caseId} />}
        {section === 'reports' && <Reports data={data} caseId={caseId} />}
        {section === 'relationships' && <Relationships data={data} />}
        {section === 'tasks' && <Tasks data={data} reload={load} />}
        {section === 'quality' && <QualityView data={data} quality={quality} />}
      </div>
      {(preview || previewBusy) && <SourcePreview preview={preview} busy={previewBusy} close={() => setPreview(null)} changePage={page => preview && api.documentPreview(preview.id, page, preview.highlight).then(setPreview)} />}
    </main>
  </div>
}

function SectionTitle({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <div className="section-title"><p className="eyebrow">{eyebrow}</p><h2>{title}</h2><p>{description}</p></div>
}

function Overview({ data, pending }: { data: Workspace; pending: number }) {
  const high = data.traffic_risks.filter(r => r.level === 'high').length + data.risks.filter(r => r.level === 'high').length
  return <><SectionTitle eyebrow="CASE OVERVIEW" title="案件总览" description="查看材料处理进度、AI 提取结果和需要优先处理的事项。" />
    <div className="metric-grid"><div><span>案件材料</span><strong>{data.documents.length}</strong><small>{data.documents.filter(d => d.parse_status === 'parsed').length} 份已解析</small></div><div><span>提取事实</span><strong>{data.facts.length}</strong><small>{data.facts.filter(f => f.review_status === 'accepted').length} 项已确认</small></div><div><span>待复核</span><strong>{pending}</strong><small>AI 结果等待确认</small></div><div className={high ? 'danger-metric' : ''}><span>高风险提示</span><strong>{high}</strong><small>必须人工处理</small></div></div>
    <div className="two-column"><section className="panel"><div className="panel-head"><h3>案件摘要</h3><Badge tone="warning">AI 提取</Badge></div><p className="summary-text">{data.case.summary || '运行案件分析后生成摘要。'}</p><div className="boundary"><strong>分析边界</strong><span>系统未对责任、因果关系或证据效力作确定判断。</span></div></section><section className="panel"><div className="panel-head"><h3>优先处理</h3><span>{data.missing_materials.length} 项</span></div><div className="stack-list">{data.missing_materials.slice(0, 4).map(item => <div className="list-row" key={item.id}><span className={`dot dot-${item.priority}`} /><div><strong>{item.name}</strong><p>{item.reason}</p></div><Badge tone={item.priority === 'high' ? 'danger' : 'warning'}>{item.priority === 'high' ? '高' : '中'}</Badge></div>)}</div></section></div>
    <section className="panel"><div className="panel-head"><h3>最近时间线</h3><button className="link-button">查看全部</button></div><div className="mini-timeline">{data.timeline.slice(-4).map(item => <div key={item.id}><time>{item.event_date || '日期待确认'}</time><span /><article><strong>{item.title}</strong><p>{item.description}</p></article></div>)}</div></section>
  </>
}

const documentCategories = ['身份主体材料', '合同及协议', '沟通记录', '付款凭证', '行政或司法文书', '道路交通事故认定书', '车辆及保险材料', '门诊病历', '住院病历', '医疗费用票据', '医疗费用清单', '伤残鉴定材料', '收入及误工证明', '护理证明', '其他证据']

function Documents({ data, busy, upload, preview, reclassify }: { data: Workspace; busy: boolean; upload: (e: ChangeEvent<HTMLInputElement>) => void; preview: (id: string) => void; reclassify: (id: string, category: string) => Promise<void> }) {
  return <><SectionTitle eyebrow="DOCUMENT CENTER" title="材料中心" description="上传、解析并分类案件材料；AI 自动分类结果可由律师调整。" />
    <label className="upload-zone"><input type="file" accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg" onChange={upload} disabled={busy} /><Icon name="upload" /><strong>{busy ? '正在处理材料…' : '上传案件材料'}</strong><span>支持 PDF、Word、图片和文本，单文件最大 20MB</span></label>
    <section className="panel table-panel"><table><thead><tr><th>材料名称</th><th>分类（可调整）</th><th>解析状态</th><th>页数</th><th>操作</th></tr></thead><tbody>{data.documents.map(doc => <tr key={doc.id}><td><strong>{doc.filename}</strong>{doc.parse_warning && <small className="warning-text">{doc.parse_warning}</small>}</td><td><select className="category-select" value={doc.category} onChange={e => reclassify(doc.id, e.target.value)}>{[...new Set([doc.category, ...documentCategories])].map(category => <option value={category} key={category}>{category}</option>)}</select></td><td><Badge tone={doc.parse_status === 'parsed' ? 'success' : 'warning'}>{doc.parse_status === 'parsed' ? '已解析' : '需人工处理'}</Badge></td><td>{doc.page_count}</td><td><button className="ghost small" onClick={() => preview(doc.id)}>预览与定位</button></td></tr>)}</tbody></table></section></>
}

function Timeline({ data }: { data: Workspace }) {
  return <><SectionTitle eyebrow="FACTS & TIMELINE" title="事实与时间线" description="每项事实保留材料来源、AI 置信度、冲突和律师确认状态。" />
    <div className="fact-layout"><section className="panel"><div className="panel-head"><h3>关键事实</h3><span>{data.facts.length} 项</span></div>{data.facts.map(f => <article className="fact-card" key={f.id}><div><Badge tone="neutral">{f.fact_type}</Badge>{f.has_conflict && <Badge tone="danger">存在冲突</Badge>}<Badge tone={statusTone(f.review_status)}>{reviewLabel(f.review_status)}</Badge></div><p>{f.content}</p><footer><span>置信度 {Math.round((f.confidence || 0) * 100)}%</span><SourceLinks sources={f.sources} /></footer></article>)}</section>
      <section className="panel"><div className="panel-head"><h3>案件时间线</h3></div><div className="vertical-timeline">{data.timeline.map(e => <article key={e.id}><time>{e.event_date || '待确认'}</time><i className={e.has_conflict ? 'conflict' : ''} /><div><strong>{e.title}</strong><p>{e.description}</p>{e.needs_verification && <Badge tone="warning">需进一步核实</Badge>}</div></article>)}</div></section></div></>
}

function EvidenceMatrix({ data }: { data: Workspace }) {
  return <><SectionTitle eyebrow="EVIDENCE MATRIX" title="事实与证据矩阵" description="连接待证明事实、当前证据、材料来源和缺失项。" />
    <section className="panel table-panel"><table><thead><tr><th>当前证据</th><th>证据类型</th><th>证明目的</th><th>来源及状态</th></tr></thead><tbody>{data.evidence.map(e => <tr key={e.id}><td><strong>{e.name}</strong></td><td>{e.evidence_type}</td><td>{e.fact_to_prove}</td><td><Badge tone={statusTone(e.review_status)}>{reviewLabel(e.review_status)}</Badge><SourceLinks sources={e.sources} /></td></tr>)}</tbody></table></section>
    <section className="panel"><div className="panel-head"><h3>材料缺口</h3><span>{data.missing_materials.length} 项</span></div><div className="cards-3">{data.missing_materials.map(m => <article className="missing-card" key={m.id}><div><Badge tone={m.priority === 'high' ? 'danger' : 'warning'}>{m.priority === 'high' ? '高优先级' : '中优先级'}</Badge>{m.rule_id && <code>{m.rule_id}</code>}</div><h4>{m.name}</h4><p>{m.reason}</p><small>{m.suggested_action}</small></article>)}</div></section></>
}

function Traffic({ data }: { data: Workspace }) {
  const info = data.traffic_accident[0]
  const [scenario, setScenario] = useState<Record<string, any> | null>(null)
  const [scenarioOpen, setScenarioOpen] = useState(false)
  return <><SectionTitle eyebrow="TRAFFIC INJURY MODULE" title="交通事故人伤专业分析" description="整理事故、治疗、费用、赔偿证据与专业风险，不替代责任或医疗判断。" />
    {info && <section className="panel accident-banner"><div><Badge tone="indigo">事故信息</Badge><h3>{info.accident_date} · {info.location}</h3><p>{info.responsibility_text}</p></div><SourceLinks sources={info.sources} /></section>}
    <div className="two-column"><section className="panel"><div className="panel-head"><h3>伤情与治疗</h3><Badge tone="warning">不得作为医疗诊断</Badge></div>{data.injuries.map(i => <article className="detail-row" key={i.id}><span>{i.body_part}</span><div><strong>{i.diagnosis_text}</strong>{i.has_conflict && <Badge tone="danger">前后信息待核查</Badge>}<SourceLinks sources={i.sources} /></div></article>)}{data.treatments.map(t => <article className="detail-row" key={t.id}><span>{t.start_date}<br/>至 {t.end_date}</span><div><strong>{t.institution} · {t.treatment_type}</strong><p>{t.description}</p></div></article>)}</section>
      <section className="panel"><div className="panel-head"><h3>医疗费用整理</h3><span>{data.medical_expenses.length} 张票据</span></div>{data.medical_expenses.map(m => <article className="expense" key={m.id}><div><span>票据金额</span><strong>¥ {m.amount.toLocaleString('zh-CN')}</strong></div><p>票据号：{m.invoice_number} · {m.expense_date}</p>{m.conflict_note && <div className="risk-inline">{m.conflict_note}</div>}<SourceLinks sources={m.sources} /></article>)}</section></div>
    <section className="panel table-panel"><div className="panel-head"><h3>赔偿项目证据矩阵</h3><div className="report-actions"><Badge tone="warning">不自动认定项目成立</Badge><button className="ghost small" onClick={() => setScenarioOpen(true)}>参数情景测算</button></div></div><table><thead><tr><th>赔偿项目</th><th>已有证据</th><th>缺失证据</th><th>复核状态</th></tr></thead><tbody>{data.compensation_items.map(item => <tr key={item.id}><td><strong>{item.name}</strong></td><td>{item.evidence_summary}</td><td className={item.missing_evidence ? 'warning-text' : ''}>{item.missing_evidence || '待结合主张核查'}</td><td><Badge tone={statusTone(item.review_status)}>{reviewLabel(item.review_status)}</Badge></td></tr>)}</tbody></table></section>
    <section className="panel"><div className="panel-head"><h3>专业风险提示</h3><span>{data.traffic_risks.length} 项</span></div><div className="cards-3">{data.traffic_risks.map(r => <article className="risk-card" key={r.id}><Badge tone={r.level === 'high' ? 'danger' : 'warning'}>{r.level === 'high' ? '高风险' : '中风险'}</Badge><h4>{r.risk_type}</h4><p>{r.description}</p><small>核查建议：{r.suggested_review}</small><SourceLinks sources={r.sources} /></article>)}</div></section>
    {scenarioOpen && <div className="modal-backdrop"><form className="modal scenario-modal" onSubmit={async event => { event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget)); const parameters = Object.fromEntries(Object.entries(values).filter(([, value]) => value !== '').map(([key, value]) => [key, Number(value)])); setScenario(await api.compensationScenario(data.case.id, parameters)); }}><div className="modal-head"><div><p className="eyebrow">SCENARIO ONLY</p><h2>赔偿参数情景测算</h2></div><button type="button" className="ghost" onClick={() => { setScenarioOpen(false); setScenario(null) }}>关闭</button></div><p className="boundary">只做律师录入参数的算术汇总，不自动适用地区标准、责任比例或保险限额。</p><div className="scenario-grid"><label>医疗费<input name="medical_expense" type="number" step="0.01" defaultValue={data.medical_expenses.reduce((sum, item) => sum + item.amount, 0)} /></label><label>误工天数<input name="lost_work_days" type="number" /></label><label>误工日标准<input name="lost_work_daily_rate" type="number" step="0.01" /></label><label>护理天数<input name="nursing_days" type="number" /></label><label>护理日标准<input name="nursing_daily_rate" type="number" step="0.01" /></label><label>住院天数<input name="hospital_days" type="number" /></label><label>伙食补助日标准<input name="hospital_daily_rate" type="number" step="0.01" /></label><label>交通费<input name="transportation_expense" type="number" step="0.01" /></label></div><button className="primary full">执行情景测算</button>{scenario && <div className="scenario-result"><strong>情景合计：¥ {scenario.total.toLocaleString('zh-CN')}</strong>{scenario.items.map((item: Record<string, any>) => <p key={item.name}>{item.name}<span>¥ {item.amount.toLocaleString('zh-CN')}</span></p>)}{scenario.warnings.map((warning: string) => <small key={warning}>{warning}</small>)}</div>}</form></div>}
  </>
}

function AgentRuns({ detail, runs, rerun }: { detail: Record<string, any> | null; runs: Array<Record<string, any>>; rerun: (node: string) => Promise<void> }) {
  return <><SectionTitle eyebrow="WORKFLOW OBSERVABILITY" title="Agent 执行过程" description="查看每个结构化节点的输入、输出、警告和重跑记录。" />
    <div className="run-summary"><div><span>最近运行</span><strong>{detail?.id?.slice(0, 8) || '—'}</strong></div><div><span>状态</span><Badge tone={detail?.status === 'failed' ? 'danger' : 'warning'}>{detail?.status || '无运行'}</Badge></div><div><span>Provider</span><strong>{detail?.provider || '—'}</strong></div><div><span>历史运行</span><strong>{runs.length}</strong></div></div>
    <section className="panel workflow-list">{detail?.nodes?.map((node: Record<string, any>, index: number) => <article key={node.id}><div className={`node-index ${node.status}`}>{node.status === 'completed' ? '✓' : node.status === 'skipped' ? '—' : index + 1}</div><div><strong>{node.node_name}</strong><p>生成 {node.output_summary?.generated_records || 0} 条结构化记录</p>{node.warnings?.map((w: string) => <small className="warning-text" key={w}>{w}</small>)}</div><Badge tone={node.status === 'completed' ? 'success' : 'neutral'}>{node.status}</Badge>{node.status !== 'skipped' && <button className="ghost small" onClick={() => rerun(node.node_name)}>重新执行</button>}</article>) || <Empty>尚无工作流运行记录</Empty>}</section></>
}

function ReviewCenter({ data, review, reload, caseId }: { data: Workspace; review: (type: string, item: Reviewable, action: 'accepted' | 'modified' | 'rejected', revised?: Record<string, string>) => void; reload: () => Promise<void> | void; caseId: string }) {
  const [selected, setSelected] = useState<string[]>([])
  const [editing, setEditing] = useState<{ type: string; item: Reviewable; field: string; value: string; title: string } | null>(null)
  const [history, setHistory] = useState<{ current: Record<string, unknown>; history: Array<Record<string, any>> } | null>(null)
  const queue: Array<{ type: string; title: string; description: string; item: Reviewable; editField: string; mandatory?: boolean }> = [
    ...data.facts.map(item => ({ type: 'fact', title: '事实 · ' + item.fact_type, description: item.content, editField: 'content', item })),
    ...data.missing_materials.map(item => ({ type: 'missing_material', title: '缺失材料 · ' + item.name, description: item.reason, editField: 'reason', item })),
    ...data.traffic_risks.map(item => ({ type: 'traffic_risk', title: '专业风险 · ' + item.risk_type, description: item.description, editField: 'description', item, mandatory: true })),
    ...data.reports.map(item => ({ type: 'report', title: '报告 · ' + item.title, description: item.content, editField: 'content', item, mandatory: true })),
  ]
  const pendingRows = queue.filter(row => row.item.review_status === 'unreviewed')
  async function batch(action: 'accepted' | 'rejected') {
    const items = queue.filter(row => selected.includes(`${row.type}:${row.item.id}`)).map(row => ({ target_type: row.type, target_id: row.item.id }))
    if (!items.length) return
    await api.batchReview({ case_id: caseId, action, items, comment: action === 'accepted' ? '律师批量核对后确认' : '律师批量驳回' })
    setSelected([]); await reload()
  }
  return <><SectionTitle eyebrow="HUMAN REVIEW" title="律师复核中心" description="逐项或批量处理 AI 结果；修改前后内容、人员和时间均保留审计记录。" />
    <div className="review-filter"><Badge tone="warning">待复核 {pendingRows.length}</Badge><Badge tone="success">已处理 {queue.length - pendingRows.length}</Badge><button className="ghost small" onClick={() => setSelected(pendingRows.map(row => `${row.type}:${row.item.id}`))}>选择全部待复核</button><button className="accept" disabled={!selected.length} onClick={() => batch('accepted')}>批量接受 ({selected.length})</button><button className="reject" disabled={!selected.length} onClick={() => batch('rejected')}>批量驳回</button></div>
    <section className="panel review-list">{queue.map(row => { const key = `${row.type}:${row.item.id}`; return <article key={key}><input className="review-check" type="checkbox" disabled={row.item.review_status !== 'unreviewed'} checked={selected.includes(key)} onChange={e => setSelected(e.target.checked ? [...selected, key] : selected.filter(value => value !== key))} /><div className="review-main"><div>{row.mandatory && <Badge tone="danger">强制复核</Badge>}<Badge tone={statusTone(row.item.review_status)}>{reviewLabel(row.item.review_status)}</Badge>{row.item.version && <Badge tone="neutral">v{row.item.version}</Badge>}</div><h3>{row.title}</h3><p>{row.description}</p><SourceLinks sources={row.item.sources} /><button className="link-button" onClick={() => api.reviewHistory(row.type, row.item.id).then(setHistory)}>查看修改历史</button></div>{row.item.review_status === 'unreviewed' && <div className="review-actions"><button className="accept" onClick={() => review(row.type, row.item, 'accepted')}>接受并确认</button><button className="modify" onClick={() => setEditing({ type: row.type, item: row.item, field: row.editField, value: row.description, title: row.title })}>修改后确认</button><button className="reject" onClick={() => review(row.type, row.item, 'rejected')}>驳回</button></div>}</article> })}</section>
    {editing && <div className="modal-backdrop"><div className="modal review-editor"><div className="modal-head"><div><p className="eyebrow">LAWYER EDIT</p><h2>{editing.title}</h2></div><button className="ghost" onClick={() => setEditing(null)}>关闭</button></div><label>修改内容<textarea value={editing.value} onChange={e => setEditing({ ...editing, value: e.target.value })} /></label><div className="diff-preview"><div><strong>AI 原始结果</strong><p>{queue.find(row => row.item.id === editing.item.id)?.description}</p></div><div><strong>律师修改结果</strong><p>{editing.value}</p></div></div><button className="primary full" onClick={async () => { await review(editing.type, editing.item, 'modified', { [editing.field]: editing.value }); setEditing(null) }}>保存修改并确认</button></div></div>}
    {history && <div className="modal-backdrop"><div className="modal history-modal"><div className="modal-head"><div><p className="eyebrow">VERSION HISTORY</p><h2>复核与修改历史</h2></div><button className="ghost" onClick={() => setHistory(null)}>关闭</button></div>{history.history.length ? history.history.map(item => <article className="history-item" key={item.id}><div><Badge tone={statusTone(item.action)}>{reviewLabel(item.action)}</Badge><span>{item.reviewer} · {new Date(item.created_at).toLocaleString('zh-CN')}</span></div><p>{item.comment || '未填写说明'}</p>{Object.keys(item.revised_value || {}).length > 0 && <pre>{JSON.stringify(item.revised_value, null, 2)}</pre>}</article>) : <Empty>暂无复核历史</Empty>}</div></div>}
  </>
}

function Reports({ data, caseId }: { data: Workspace; caseId: string }) {
  const [citations, setCitations] = useState<Array<Record<string, any>> | null>(null)
  return <><SectionTitle eyebrow="REPORT CENTER" title="报告及文书中心" description="生成可编辑辅助草稿，不输出可直接提交的正式法律文书。" />
    {data.reports.length ? data.reports.map(report => <section className="panel report" key={report.id}><div className="panel-head"><div><Badge tone="warning">AI 草稿</Badge><h3>{report.title}</h3></div><div className="report-actions"><Badge tone={report.citation_complete ? 'success' : 'danger'}>{report.citation_complete ? '已关联事实来源' : '引用待补充'}</Badge><button className="ghost small" onClick={() => api.reportCitations(caseId, report.id).then(setCitations)}>材料引用目录</button><button className="ghost small" onClick={() => api.downloadReport(caseId, report.id, 'docx')}>导出 DOCX</button><button className="ghost small" onClick={() => api.downloadReport(caseId, report.id, 'md')}>导出 Markdown</button></div></div><pre>{report.content}</pre>{citations && <div className="report-citations"><h4>材料引用目录</h4>{citations.map(item => <button key={item.index} onClick={() => window.dispatchEvent(new CustomEvent('lcc:source-preview', { detail: item }))}>[{item.index}] {item.filename} · 第 {item.page_number} 页：{item.quote}</button>)}</div>}<footer>{report.disclaimer}</footer></section>) : <Empty>运行案件分析后生成辅助报告</Empty>}</>
}

function SourcePreview({ preview, busy, close, changePage }: { preview: DocumentPreview | null; busy: boolean; close: () => void; changePage: (page: number) => void }) {
  const before = preview && preview.highlight_start >= 0 ? preview.text.slice(0, preview.highlight_start) : preview?.text
  const marked = preview && preview.highlight_start >= 0 ? preview.text.slice(preview.highlight_start, preview.highlight_end) : ''
  const after = preview && preview.highlight_start >= 0 ? preview.text.slice(preview.highlight_end) : ''
  return <div className="source-drawer-backdrop" onMouseDown={close}><aside className="source-drawer" onMouseDown={event => event.stopPropagation()}><header><div><p className="eyebrow">SOURCE TRACE</p><h2>{preview?.filename || '材料原文'}</h2></div><button className="ghost" onClick={close}>关闭</button></header>{busy || !preview ? <div className="loading-preview">正在定位材料原文…</div> : <><div className="preview-toolbar"><button disabled={preview.page_number <= 1} onClick={() => changePage(preview.page_number - 1)}>上一页</button><span>第 {preview.page_number} / {preview.page_count} 页</span><button disabled={preview.page_number >= preview.page_count} onClick={() => changePage(preview.page_number + 1)}>下一页</button>{preview.has_original && <button onClick={() => api.openDocument(preview.id)}>打开原始文件</button>}</div>{preview.parse_warning && <div className="alert-inline">{preview.parse_warning}</div>}<div className="source-paper">{preview.text ? <pre>{before}{marked && <mark>{marked}</mark>}{after}</pre> : <Empty>该页没有可显示文本，请人工查看原始材料</Empty>}</div><div className="boundary"><strong>引用核对提示</strong><span>{marked && preview.highlight_exact ? '已定位并高亮完全一致的引用片段。' : marked ? '引用表述与原文不完全一致，已高亮最接近片段，必须人工核对。' : preview.requested_highlight ? '未找到可靠匹配片段，请人工核对整页。' : '当前为材料文本预览。'}</span></div></>}</aside></div>
}

function Relationships({ data }: { data: Workspace }) {
  const partyName = (id: string) => data.parties.find(item => item.id === id)?.name || '未知主体'
  return <><SectionTitle eyebrow="PARTY RELATIONSHIP" title="案件主体与关系" description="展示案件主体和已经提取的关系；关系性质仍须律师确认。" /><section className="panel relationship-board"><div className="party-nodes">{data.parties.map((party, index) => <article key={party.id} className={`party-node party-${index % 4}`}><span>{party.party_type === 'person' ? '人' : '机构'}</span><strong>{party.name}</strong><small>{party.role}</small></article>)}</div>{data.relationships.length ? <div className="relationship-list">{data.relationships.map(item => <article key={item.id}><strong>{partyName(item.from_party_id)}</strong><span>— {item.relationship_type} →</span><strong>{partyName(item.to_party_id)}</strong><p>{item.description}</p><Badge tone={statusTone(item.review_status)}>{reviewLabel(item.review_status)}</Badge></article>)}</div> : <div className="boundary"><strong>关系待补充</strong><span>当前材料只识别到主体，尚未形成可核验的结构化法律关系；系统不作推定。</span></div>}</section></>
}

function Tasks({ data, reload }: { data: Workspace; reload: () => Promise<void> | void }) {
  const groups = ['todo', 'in_progress', 'done'] as const
  const labels = { todo: '待处理', in_progress: '处理中', done: '已完成' }
  async function update(id: string, status: string) { await api.updateTask(id, { status }); await reload() }
  return <><SectionTitle eyebrow="CASE TASKS" title="办案任务" description="根据案件阶段和信息缺口生成任务，可由团队更新处理状态。" /><div className="task-board">{groups.map(group => <section className="task-column" key={group}><header><h3>{labels[group]}</h3><Badge tone={group === 'done' ? 'success' : group === 'in_progress' ? 'info' : 'warning'}>{data.tasks.filter(task => task.status === group).length}</Badge></header>{data.tasks.filter(task => task.status === group).map(task => <article key={task.id}><div><Badge tone={task.priority === 'high' ? 'danger' : 'warning'}>{task.priority === 'high' ? '高优先级' : '普通'}</Badge></div><h4>{task.name}</h4><p>{task.trigger_reason}</p><small>负责人：{(task as any).assignee || '案件负责律师'}</small><select value={task.status} onChange={event => update(task.id, event.target.value)}><option value="todo">待处理</option><option value="in_progress">处理中</option><option value="done">已完成</option><option value="cancelled">已取消</option></select></article>)}</section>)}</div></>
}

function QualityView({ data, quality }: { data: Workspace; quality: QualityReport | null }) {
  if (!quality) return <Empty>正在计算案件质量指标…</Empty>
  const metrics = [
    ['材料解析率', quality.document_parse_rate], ['文本质量', quality.document_quality_score],
    ['事实来源覆盖', quality.fact_source_coverage], ['事实复核完成', quality.fact_review_completion],
    ['强制风险复核', quality.mandatory_risk_review_completion],
  ] as const
  return <><SectionTitle eyebrow="QUALITY & SAFETY" title="质量与安全" description="量化材料质量、来源覆盖和人工复核完成度；分数不代表案件胜诉概率。" />
    <section className="quality-hero"><div><span>案件质量分</span><strong>{Math.round(quality.overall_score * 100)}</strong><small>/ 100</small></div><p>该分数只衡量系统处理完整性和可追溯性，不评价法律结论或案件结果。</p></section>
    <div className="quality-grid">{metrics.map(([label, value]) => <article key={label}><header><span>{label}</span><strong>{Math.round(value * 100)}%</strong></header><div><i style={{ width: `${value * 100}%` }} /></div></article>)}</div>
    <div className="two-column"><section className="panel"><div className="panel-head"><h3>质量警告</h3><Badge tone={quality.warnings.length ? 'warning' : 'success'}>{quality.warnings.length} 项</Badge></div><div className="stack-list">{quality.warnings.map(warning => <div className="list-row" key={warning}><span className="dot"/><div><strong>{warning}</strong></div></div>)}</div></section>
      <section className="panel"><div className="panel-head"><h3>文档安全检查</h3><span>{data.document_quality.length} 份</span></div>{data.document_quality.map(item => <article className="quality-doc" key={item.id}><div><strong>{data.documents.find(doc => doc.id === item.document_id)?.filename || item.document_id}</strong><Badge tone={item.requires_human_review ? 'warning' : 'success'}>{item.requires_human_review ? '需检查' : '通过'}</Badge></div><p>文本质量 {Math.round(item.text_quality_score * 100)}% · OCR {item.ocr_provider}</p>{item.injection_risk && <small>检测到疑似 Prompt Injection，已按不可信材料处理。</small>}</article>)}</section></div>
    <section className="panel table-panel"><div className="panel-head"><h3>法律知识引用</h3><Badge tone={data.legal_citations.length ? 'info' : 'warning'}>{data.legal_citations.length} 条</Badge></div>{data.legal_citations.length ? <table><thead><tr><th>来源</th><th>更新时间</th><th>地区及范围</th><th>过期风险</th></tr></thead><tbody>{data.legal_citations.map(item => <tr key={item.id}><td><strong>{item.title}</strong><small>{item.source_name}</small></td><td>{item.published_or_updated_at || '待核验'}</td><td>{item.jurisdiction} · {item.scope}</td><td><Badge tone={item.stale_risk ? 'warning' : 'success'}>{item.stale_risk ? '需核验' : '已标记有效'}</Badge></td></tr>)}</tbody></table> : <Empty>尚未导入经核验的知识资料，因此系统不生成法律引用</Empty>}</section>
  </>
}
