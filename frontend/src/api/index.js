import axios from 'axios'
import { clearSession } from '../utils/session'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 15000
})

// 统一带上登录令牌
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 令牌失效时退回登录页
http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    if (status === 401) {
      clearSession()
      if (window.location.hash !== '#/login') {
        window.location.hash = '#/login'
      }
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  login: (payload) => http.post('/auth/login', payload),
  register: (payload) => http.post('/auth/register', payload),
  guest: () => http.post('/auth/guest'),
  me: () => http.get('/auth/me')
}

export const structureApi = {
  list: () => http.get('/structures'),
  create: (payload) => http.post('/structures', payload),
  update: (code, payload) => http.put(`/structures/${code}`, payload),
  listZones: (params) => http.get('/structures/zones', { params }),
  createZone: (payload) => http.post('/structures/zones', payload),
  updateZone: (code, payload) => http.put(`/structures/zones/${code}`, payload),
  getZone: (code) => http.get(`/structures/zones/${code}`)
}

export const deviceApi = {
  list: () => http.get('/devices'),
  create: (payload) => http.post('/devices', payload),
  update: (deviceId, payload) => http.put(`/devices/${deviceId}`, payload),
  remove: (deviceId) => http.delete(`/devices/${deviceId}`)
}

export const measurementApi = {
  receive: (payload) => http.post('/measurements', payload),
  list: (params) => http.get('/measurements', { params }),
  latest: (params) => http.get('/measurements/latest', { params }),
  count: (params) => http.get('/measurements/count', { params }),
  stats: (params) => http.get('/measurements/stats', { params })
}

export const alertApi = {
  records: (params) => http.get('/alerts/records', { params }),
  summary: () => http.get('/alerts/summary'),
  acknowledge: (id) => http.post(`/alerts/records/${id}/acknowledge`, null, { params: { operator: 'admin' } }),
  reopen: (id) => http.post(`/alerts/records/${id}/reopen`),
  rules: (params) => http.get('/alerts/rules', { params }),
  createRule: (payload) => http.post('/alerts/rules', payload),
  removeRule: (id) => http.delete(`/alerts/rules/${id}`)
}

export const imagingApi = {
  latest: (params) => http.get('/imaging/latest', { params }),
  history: (params) => http.get('/imaging/history', { params }),
  upload: (payload) => http.post('/imaging', payload)
}

export const overviewApi = {
  summary: () => http.get('/overview')
}

// 导出走浏览器直接下载，不走 axios 响应拦截，避免二进制被当成 JSON 解析
export function downloadFile(path, params) {
  const query = new URLSearchParams()
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      query.append(key, value)
    }
  })
  const token = localStorage.getItem('access_token')
  const url = `/api/v1${path}${query.toString() ? `?${query}` : ''}`
  const link = document.createElement('a')
  link.href = url
  link.download = ''
  if (token) {
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((resp) => {
        // 文件名从响应头里取，服务端按类型给了不同后缀
        const disposition = resp.headers.get('Content-Disposition') || ''
        const matched = disposition.match(/filename="?([^"]+)"?/)
        const filename = matched ? matched[1] : ''
        return resp.blob().then((blob) => ({ blob, filename }))
      })
      .then(({ blob, filename }) => {
        const objectUrl = URL.createObjectURL(blob)
        link.href = objectUrl
        if (filename) link.download = filename
        link.click()
        URL.revokeObjectURL(objectUrl)
      })
    return
  }
  link.click()
}

export default http
