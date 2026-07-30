import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api } from '../api'
import { Badge } from '../components'
import type { EvaluationReport } from '../types'

type RuleCatalog = {
  filename: string
  file_sha256: string
  version: string
  description: string
  rule_count: number
  enabled_rule_count: number
  valid: boolean
  validation_errors: string[]
  validation_warnings: string[]
  rules: Array<Record<string, unknown>>
}

const pct = (value = 0) => `${Math.round(value * 100)}%`

export default function EvaluationPage() {
  const [report, setReport] = useState<EvaluationReport | null>(null)
  const [rules, setRules] = useState<RuleCatalog[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.latestEvaluation(), api.trafficRules()])
      .then(([nextReport, nextRules]) => {
        setReport(nextReport)
        setRules(nextRules as RuleCatalog[])
      })
      .catch(event => setError((event as Error).message))
  }, [])

  const summary = report?.summary
  return <div className="case-list-shell">
    <header className="topbar">
      <Link to="/" className="brand"><span className="brand-mark">L</span><div><strong>Lawyer Case Copilot</strong><small>返回案件工作台</small></div></Link>
      <div className="top-actions"><Badge tone="info">SYNTHETIC EVAL</Badge><Link to="/knowledge" className="ghost">知识资料库</Link><Link to="/settings" className="ghost">律所设置</Link></div>
    </header>
    <main className="case-list-main evaluation-page">
      <section className="page-intro">
        <div><p className="eyebrow">EVALUATION & RULE GOVERNANCE</p><h1>评测与规则中心</h1><p>区分“系统流程通过”与“真实业务准确”，让能力声明有证据、有边界。</p></div>
        <a className="ghost" href="https://github.com/samarailly51-pixel/lawyer-case-copilot/blob/main/docs/evaluation-report.md" target="_blank" rel="noreferrer">查看评测报告</a>
      </section>
      {error && <div className="alert">{error}</div>}
      <section className="summary-row evaluation-summary">
        <div><span>合成场景</span><strong>{summary?.total_scenarios ?? '—'}</strong><small>Demo + 非 Demo 路径</small></div>
        <div><span>断言通过</span><strong>{summary ? `${summary.passed_scenarios}/${summary.total_scenarios}` : '—'}</strong><small>结构化回归检查</small></div>
        <div><span>通过率</span><strong>{summary ? pct(summary.pass_rate) : '—'}</strong><small>不等于真实准确率</small></div>
        <div><span>事实来源覆盖</span><strong>{summary ? pct(summary.average_fact_source_coverage) : '—'}</strong><small>材料引用完整性</small></div>
      </section>

      <section className="panel eval-boundary">
        <div><p className="eyebrow">INTERPRETATION BOUNDARY</p><h3>这组数字能够证明什么？</h3><p>{summary?.scope_note || '正在载入评测边界…'}</p></div>
        <ul>{report?.limitations.map(item => <li key={item}>{item}</li>)}</ul>
      </section>

      <section className="panel table-panel">
        <div className="panel-head"><div><h3>回归场景</h3><small>{summary?.dataset_label || '完全虚构回归集'}</small></div><Badge tone={summary?.pass_rate === 1 ? 'success' : 'warning'}>{summary ? pct(summary.pass_rate) : 'LOADING'}</Badge></div>
        <table className="evaluation-table">
          <thead><tr><th>场景</th><th>数据路径</th><th>状态</th><th>事实来源</th><th>专业字段来源</th><th>失败原因</th></tr></thead>
          <tbody>{report?.results.map(item => <tr key={item.id}>
            <td><code>{item.id}</code></td><td>{item.fixture}</td>
            <td><Badge tone={item.passed ? 'success' : 'danger'}>{item.passed ? '通过' : '失败'}</Badge></td>
            <td>{pct(item.quality?.fact_source_coverage)}</td><td>{pct(item.specialist_source_coverage ?? 1)}</td>
            <td>{item.failures.length ? item.failures.join('；') : '—'}</td>
          </tr>)}</tbody>
        </table>
      </section>

      <section className="rules-heading">
        <div><p className="eyebrow">CONFIGURABLE DOMAIN RULES</p><h2>交通事故规则治理</h2><p>规则文件独立于 Prompt，加载前进行 Schema、来源和高风险人工复核校验。</p></div>
      </section>
      <section className="rule-grid">{rules.map(file => <article className="rule-card" key={file.filename}>
        <header><div><code>{file.filename}</code><h3>{file.description}</h3></div><Badge tone={file.valid ? 'success' : 'danger'}>{file.valid ? 'VALID' : 'INVALID'}</Badge></header>
        <div className="rule-meta"><span>版本 <strong>{file.version}</strong></span><span>规则 <strong>{file.rule_count}</strong></span><span>已启用 <strong>{file.enabled_rule_count}</strong></span></div>
        <p className="rule-checksum">SHA-256：<code>{file.file_sha256}</code></p>
        {file.rules.length > 0
          ? <ul>{file.rules.slice(0, 6).map((rule, index) => <li key={String(rule.id || index)}><code>{String(rule.id || 'unnamed')}</code><span>{String(rule.description || '')}</span><Badge tone={rule.enabled === false ? 'neutral' : rule.severity === 'high' ? 'danger' : 'warning'}>{rule.enabled === false ? 'disabled' : String(rule.severity || 'medium')}</Badge></li>)}</ul>
          : <div className="rule-placeholder"><strong>等待项目所有者补充</strong><p>此处只保留经过脱敏、核验并标明适用边界的个人经验规则，不自动虚构。</p></div>}
        {[...file.validation_errors, ...file.validation_warnings].map(message => <small className="warning-text" key={message}>{message}</small>)}
      </article>)}</section>
    </main>
  </div>
}
