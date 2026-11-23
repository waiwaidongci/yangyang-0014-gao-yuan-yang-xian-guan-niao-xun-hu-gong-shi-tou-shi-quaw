export const roles = Object.freeze({operator: '录入员', reviewer: '复核员', viewer: '查阅员'})
export const jobStates = Object.freeze({queued: '排队', running: '运行中', done: '完成', failed: '失败'})
let session
try { session = JSON.parse(sessionStorage.getItem('yangyang-session')) } catch { session = null }

export function h(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]))
}

export async function api(path, method = 'GET', body) {
  const headers = {}
  if (session?.access_token) headers.Authorization = `Bearer ${session.access_token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const response = await fetch(path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body)})
  const type = response.headers.get('Content-Type') ?? ''
  const data = type.includes('application/json') ? await response.json() : await response.text()
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : (response.status === 422 ? '请检查输入字段或取值范围。' : '请求失败，请重试。')
    throw Object.assign(new Error(detail), {status: response.status, detail: data.detail})
  }
  return data
}

export const badge = (text, state = '') => `<span class="status-chip ${h(state)}">${h(text)}</span>`
export const empty = message => `<p class="empty-state">${h(message)}</p>`
export function notice(element, message, failure = false) {
  element.textContent = message
  element.dataset.type = failure ? 'error' : 'success'
}
export async function waitJob(id, maxWait = 12000) {
  const deadline = Date.now() + maxWait
  do {
    const job = await api(`/api/jobs/${id}`)
    if (job.status === 'done') return job.result
    if (job.status === 'failed') throw new Error(job.error)
    await new Promise(resolve => setTimeout(resolve, 350))
  } while (Date.now() < deadline)
  throw new Error('后台任务仍在排队，可稍后刷新查看。')
}

export function mount({title, kicker, pages, render}) {
  const root = document.getElementById('app') ?? document.body.appendChild(document.createElement('div'))
  const first = Object.keys(pages)[0]
  const active = () => Object.hasOwn(pages, location.hash.slice(1)) ? location.hash.slice(1) : first
  let version = 0

  function login() {
    root.innerHTML = `<main class="signin"><div class="signin-heading"><p class="kicker">${h(kicker)}</p><h1>${h(title)}</h1></div>
      <form class="signin-form"><h2>登录工作台</h2><label>演示账号 <select name="role">${Object.entries(roles).map(([key, value]) => `<option value="${h(key)}">${h(value)}</option>`).join('')}</select></label>
      <label>密码 <input name="password" type="password" value="Demo2026!" required autocomplete="current-password"></label>
      <button type="submit">进入工作台</button><p role="status"></p></form></main>`
    root.querySelector('form').onsubmit = async event => {
      event.preventDefault()
      const form = event.currentTarget
      const data = new FormData(form)
      const button = form.querySelector('button')
      button.disabled = true
      try {
        session = await api('/api/auth/login', 'POST', {email: `${data.get('role')}@demo.local`, password: data.get('password')})
        sessionStorage.setItem('yangyang-session', JSON.stringify(session))
        show()
      } catch (error) {
        notice(form.querySelector('[role=status]'), error.message, true)
        button.disabled = false
      }
    }
  }

  function clear() {
    ++version
    session = null
    sessionStorage.removeItem('yangyang-session')
    login()
  }

  async function show() {
    if (!session) return login()
    const slug = active()
    const current = ++version
    const label = typeof pages[slug] === 'string' ? pages[slug] : pages[slug].label
    document.title = `${label} · ${title}`
    root.innerHTML = `<div class="workbench"><header class="masthead"><div class="masthead-title"><p class="kicker">${h(kicker)}</p><strong>${h(title)}</strong></div>
      <div class="session"><span>${h(roles[session.role])}</span><button type="button" class="quiet" data-signout>退出</button></div></header>
      <nav class="workbench-nav" aria-label="业务模块">${Object.entries(pages).map(([key, value]) => `<a href="#${h(key)}" ${key === slug ? 'aria-current="page"' : ''}>${h(typeof value === 'string' ? value : value.label)}</a>`).join('')}</nav>
      <main id="outlet" class="outlet" aria-label="${h(label)}" aria-busy="true"></main></div>`
    root.querySelector('[data-signout]').onclick = clear
    const outlet = root.querySelector('#outlet')
    try {
      await render(slug, outlet, session)
    } catch (error) {
      if (current !== version) return
      if (error.status === 401) return clear()
      outlet.innerHTML = `<section class="error-state" role="alert"><h1>页面暂时无法加载</h1><p>${h(error.message)}</p><button type="button">重新加载</button></section>`
      outlet.querySelector('button').onclick = show
      console.error(error)
    } finally {
      outlet.setAttribute('aria-busy', 'false')
    }
  }

  addEventListener('hashchange', show)
  show()
}
