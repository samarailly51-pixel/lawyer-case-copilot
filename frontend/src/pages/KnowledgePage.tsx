import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api } from '../api'
import { Badge, Icon } from '../components'
import type { KnowledgeSource } from '../types'

export default function KnowledgePage() {
  const [items, setItems] = useState<KnowledgeSource[]>([])
  const [error, setError] = useState('')
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [verifiedOnly, setVerifiedOnly] = useState(true)
  const [searching, setSearching] = useState(false)

  const load = () => api.knowledge().then(setItems).catch(event => setError(event.message))
  useEffect(() => { void load() }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>
    try {
      await api.addKnowledge({ ...form, stale_risk: form.stale_risk === 'true', metadata_json: {} })
      setOpen(false)
      await load()
    } catch (event) {
      setError((event as Error).message)
    }
  }

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!query.trim()) {
      await load()
      return
    }
    setSearching(true)
    setError('')
    try {
      setItems(await api.searchKnowledge({
        query,
        scopes: ['general', 'traffic_injury', 'internal', 'personal_experience'],
        limit: 20,
        verified_only: verifiedOnly,
        exclude_historical: true,
      }))
    } catch (event) {
      setError((event as Error).message)
    } finally {
      setSearching(false)
    }
  }

  return <div className="case-list-shell">
    <header className="topbar">
      <Link to="/" className="brand"><span className="brand-mark">L</span><div><strong>Lawyer Case Copilot</strong><small>律师案件智能助理</small></div></Link>
      <div className="top-actions"><Link to="/evaluation" className="ghost">评测与规则</Link><Link className="ghost" to="/">返回案件工作台</Link></div>
    </header>
    <main className="case-list-main">
      <section className="page-intro">
        <div><p className="eyebrow">VERIFIED KNOWLEDGE</p><h1>知识资料库</h1><p>只导入可说明来源、时间、地区、适用范围和核验人的资料。</p></div>
        <button className="primary" onClick={() => setOpen(true)}><Icon name="plus" />导入资料</button>
      </section>
      <form className="knowledge-search" onSubmit={search}>
        <input value={query} onChange={event => setQuery(event.target.value)} placeholder="检索标题、引用内容、地区或适用范围" />
        <label><input type="checkbox" checked={verifiedOnly} onChange={event => setVerifiedOnly(event.target.checked)} />仅显示已核验且无过期风险</label>
        <button className="primary" disabled={searching}>{searching ? '检索中…' : '检索'}</button>
        <button className="ghost" type="button" onClick={() => { setQuery(''); void load() }}>重置</button>
      </form>
      {error && <div className="alert-inline">{error}</div>}
      <section className="panel table-panel knowledge-table">
        <table><thead><tr><th>资料</th><th>范围</th><th>时间及地区</th><th>核验状态</th></tr></thead><tbody>{items.map(item => <tr key={item.id}>
          <td><strong>{item.title}</strong><small>{item.source_name}</small><p>{item.excerpt.slice(0, 100)}{item.excerpt.length > 100 ? '…' : ''}</p></td>
          <td>{item.scope}<small>{item.applicability_scope}</small></td>
          <td>{item.published_or_updated_at}<small>{item.jurisdiction}</small></td>
          <td><Badge tone={item.effective_status === 'verified_effective' && !item.stale_risk ? 'success' : 'warning'}>{item.effective_status}</Badge><small>{item.stale_risk ? '存在过期风险 · ' : ''}核验人：{item.verified_by}</small></td>
        </tr>)}</tbody></table>
        {items.length === 0 && <div className="empty"><p>没有符合当前核验条件的资料。</p></div>}
      </section>
    </main>
    {open && <div className="modal-backdrop" onMouseDown={() => setOpen(false)}>
      <form className="modal knowledge-form" onSubmit={submit} onMouseDown={event => event.stopPropagation()}>
        <div className="modal-head"><div><p className="eyebrow">IMPORT SOURCE</p><h2>导入知识资料</h2></div><button type="button" className="ghost" onClick={() => setOpen(false)}>关闭</button></div>
        <div className="form-row"><label>资料标题<input name="title" required /></label><label>知识范围<select name="scope"><option value="general">通用法律知识</option><option value="traffic_injury">交通事故人伤</option><option value="internal">律所内部知识</option><option value="personal_experience">个人经验</option></select></label></div>
        <label>引用内容<textarea name="excerpt" minLength={10} required /></label>
        <div className="form-row"><label>来源名称<input name="source_name" required /></label><label>来源地址或内部 ID<input name="source_url" required /></label></div>
        <div className="form-row"><label>发布或更新时间<input name="published_or_updated_at" type="date" required /></label><label>适用地区<input name="jurisdiction" required /></label></div>
        <label>适用范围<input name="applicability_scope" required /></label>
        <div className="form-row"><label>有效性状态<select name="effective_status"><option value="verification_required">待进一步核验</option><option value="verified_effective">已核验有效</option><option value="historical">历史资料</option></select></label><label>核验人<input name="verified_by" required /></label></div>
        <input type="hidden" name="stale_risk" value="true" />
        <button className="primary full">保存知识资料</button>
      </form>
    </div>}
  </div>
}
