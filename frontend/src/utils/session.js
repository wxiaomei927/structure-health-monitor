import { computed, reactive } from 'vue'

// 登录态放在这里统一管理，游客和正式账号都走同一套入口
export const state = reactive({
  token: localStorage.getItem('access_token') || '',
  username: localStorage.getItem('username') || '',
  displayName: localStorage.getItem('display_name') || '',
  role: localStorage.getItem('role') || ''
})

export const isGuest = computed(() => state.role === 'guest')

export function setSession(payload) {
  state.token = payload.access_token
  state.username = payload.username
  state.displayName = payload.display_name || payload.username
  state.role = payload.role || ''
  localStorage.setItem('access_token', state.token)
  localStorage.setItem('username', state.username)
  localStorage.setItem('display_name', state.displayName)
  localStorage.setItem('role', state.role)
}

export function clearSession() {
  state.token = ''
  state.username = ''
  state.displayName = ''
  state.role = ''
  localStorage.removeItem('access_token')
  localStorage.removeItem('username')
  localStorage.removeItem('display_name')
  localStorage.removeItem('role')
}
