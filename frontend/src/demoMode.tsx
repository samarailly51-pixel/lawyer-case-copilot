import { createContext, ReactNode, useContext } from 'react'

export type AuthStatus = {
  mode: string
  login_required: boolean
  bootstrap_required: boolean
  public_demo: boolean
  read_only: boolean
}

const DemoModeContext = createContext({ publicDemo: false, readOnly: false })

export function DemoModeProvider({ status, children }: { status: AuthStatus; children: ReactNode }) {
  const value = { publicDemo: status.public_demo, readOnly: status.read_only }
  return <DemoModeContext.Provider value={value}>
    <div className={value.readOnly ? 'public-demo-root' : ''}>
      {value.readOnly && <div className="public-demo-banner">
        <strong>公开只读 Demo</strong>
        <span>所有人物、机构和案情均为虚构；创建、上传和修改功能已关闭。</span>
      </div>}
      {children}
    </div>
  </DemoModeContext.Provider>
}

export const useDemoMode = () => useContext(DemoModeContext)
