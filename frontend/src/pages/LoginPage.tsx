import { FormEvent, useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function LoginPage() {
  const navigate = useNavigate(); const location = useLocation()
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false); const [bootstrap, setBootstrap] = useState(false)
  useEffect(() => { api.authStatus().then(status => { setBootstrap(status.bootstrap_required); if (!status.login_required) navigate('/') }) }, [navigate])
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    try {
      const result = await api.login(String(form.get('email')), String(form.get('password')))
      localStorage.setItem('lcc_token', result.access_token); localStorage.setItem('lcc_workspace', result.workspace.id)
      navigate((location.state as { from?: string })?.from || '/')
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  return <div className="login-shell"><section className="login-brand"><div className="brand-mark large">L</div><p className="eyebrow">LAWYER CASE COPILOT</p><h1>让案件材料成为<br/>可追溯的工作空间</h1><p>事实、证据、风险与知识引用都保留来源，重要判断始终回到案件负责律师。</p><div className="login-boundary">系统提供办案辅助，不构成正式法律意见。</div></section><form className="login-card" onSubmit={submit}><p className="eyebrow">SECURE WORKSPACE</p><h2>登录律所工作空间</h2><p>使用管理员创建的成员账号登录。</p>{bootstrap && <div className="alert-inline">尚未配置管理员，请先在服务器运行 bootstrap_admin 命令。</div>}{error && <div className="alert-inline">{error}</div>}<label>邮箱<input name="email" type="email" required autoComplete="username" placeholder="name@lawfirm.com" /></label><label>密码<input name="password" type="password" minLength={8} required autoComplete="current-password" /></label><button className="primary full" disabled={busy}>{busy ? '正在登录…' : '进入案件工作台'}</button><small>登录凭证仅保存在当前浏览器，服务端密码采用 scrypt 哈希。</small></form></div>
}

