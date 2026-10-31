<template>
  <div class="login-page">
    <div class="login-card">
      <div class="brand-block">
        <div class="brand-mark">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22">
            <path fill="currentColor" d="M2 13.5l3.2-4.4 3 3.4 3.6-5.6 3.4 5 2.4-2.6L22 13H2z"/>
            <path fill="currentColor" d="M2 16h20v2H2z"/>
          </svg>
        </div>
        <span class="brand-name">结构健康监测平台</span>
      </div>

      <h1 class="page-title">{{ isRegister ? '创建账号' : '欢迎登录' }}</h1>

      <n-form ref="formRef" :model="form" :rules="rules" @keyup.enter="handleSubmit">
        <n-form-item path="username" label="用户名">
          <n-input v-model:value="form.username" placeholder="请输入用户名" autocomplete="username" />
        </n-form-item>

        <template v-if="isRegister">
          <n-form-item path="email" label="邮箱">
            <n-input v-model:value="form.email" placeholder="example@mail.com" />
          </n-form-item>
          <n-form-item path="display_name" label="显示名称">
            <n-input v-model:value="form.display_name" placeholder="选填，默认与用户名相同" />
          </n-form-item>
        </template>

        <n-form-item path="password" label="密码">
          <n-input
            v-model:value="form.password"
            type="password"
            :placeholder="isRegister ? '至少 6 位' : '请输入密码'"
            :show-password-on="isRegister ? 'click' : undefined"
            show-password-on="click"
            :autocomplete="isRegister ? 'new-password' : 'current-password'"
          />
        </n-form-item>

      <n-form-item v-if="isRegister" path="password2" label="确认密码">
        <n-input
          v-model:value="form.password2"
          type="password"
          placeholder="再次输入密码"
          show-password-on="click"
          autocomplete="new-password"
        />
      </n-form-item>

        <n-button type="primary" block :loading="loading" @click="handleSubmit">
          {{ isRegister ? '注 册' : '登 录' }}
        </n-button>
      </n-form>

      <div class="guest-entry">
        <div class="guest-divider">
          <span>或</span>
        </div>
        <n-button
          block
          secondary
          class="guest-button"
          :loading="guestLoading"
          @click="handleGuest"
        >
          以游客身份浏览
        </n-button>
        <p class="guest-hint">游客可以查看平台全部展示数据，不能修改任何内容</p>
      </div>

      <div class="auth-switch">
        <template v-if="isRegister">
          已有账号？<router-link to="/login">前往登录</router-link>
        </template>
        <template v-else>
          还没有账号？<router-link to="/register">立即注册</router-link>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { authApi } from '../api'
import { setSession } from '../utils/session'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const formRef = ref(null)
const loading = ref(false)
const guestLoading = ref(false)

const isRegister = computed(() => route.name === 'Register')

const form = reactive({
  username: '',
  email: '',
  display_name: '',
  password: '',
  password2: ''
})

const rules = {
  username: { required: true, message: '请输入用户名', trigger: ['blur', 'input'] },
  password: { required: true, message: '请输入密码', trigger: ['blur', 'input'] },
  email: { required: true, message: '请输入邮箱', trigger: ['blur', 'input'] },
  password2: { required: true, message: '请再次输入密码', trigger: ['blur', 'input'] }
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch (err) {
    return
  }

  if (isRegister.value) {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      message.error('邮箱格式不正确')
      return
    }
    if (form.password.length < 6) {
      message.error('密码至少 6 位')
      return
    }
    if (form.password !== form.password2) {
      message.error('两次输入的密码不一致')
      return
    }
  }

  loading.value = true
  try {
    if (isRegister.value) {
      await authApi.register({
        username: form.username,
        email: form.email,
        display_name: form.display_name || form.username,
        password: form.password
      })
      message.success('注册成功，请登录')
      router.push({ name: 'Login' })
      return
    }

    const data = await authApi.login({ username: form.username, password: form.password })
    setSession(data)
    message.success('登录成功')
    router.push({ name: 'Dashboard' })
  } catch (err) {
    const detail = err?.response?.data?.detail || '操作失败，请稍后重试'
    message.error(detail)
  } finally {
    loading.value = false
  }
}

async function handleGuest() {
  guestLoading.value = true
  try {
    const data = await authApi.guest()
    setSession(data)
    message.success('已进入游客模式')
    router.push({ name: 'Dashboard' })
  } catch (err) {
    const detail = err?.response?.data?.detail || '进入失败，请稍后重试'
    message.error(detail)
  } finally {
    guestLoading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 45%, #0ea5a4 100%);
  position: relative;
  overflow: hidden;
}

/* 两团光晕，让纯色渐变不显得死板 */
.login-page::after {
  content: "";
  position: absolute;
  width: 520px;
  height: 520px;
  right: -160px;
  top: -160px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.16), transparent 70%);
}

.login-page::before {
  content: "";
  position: absolute;
  width: 420px;
  height: 420px;
  left: -140px;
  bottom: -140px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.12), transparent 70%);
}

.login-card {
  position: relative;
  z-index: 1;
  width: 400px;
  max-width: 100%;
  background: #fff;
  border-radius: 16px;
  padding: 36px 36px 28px;
  box-shadow: 0 20px 60px rgba(10, 25, 60, 0.25);
}

.brand-block {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 6px;
}

.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: var(--accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-name {
  font-size: 19px;
  font-weight: 700;
  color: var(--ink-900);
  letter-spacing: 0.5px;
}

.page-title {
  text-align: center;
  font-size: 22px;
  font-weight: 600;
  color: var(--ink-900);
  margin: 14px 0 22px;
}

.guest-entry {
  margin-top: 18px;
}

/* 游客入口要一眼能看见，用描边主色而不是灰底次级 */
.guest-button {
  color: #0e42d2 !important;
  border: 1px solid #165dff !important;
  background-color: #ffffff !important;
}

.guest-button:hover {
  color: #0e42d2 !important;
  border-color: #0e42d2 !important;
  background-color: #f2f6ff !important;
}

.guest-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  color: var(--ink-400);
  font-size: var(--text-sm);
}

.guest-divider::before,
.guest-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--ink-100);
}

.guest-hint {
  margin: 10px 0 0;
  text-align: center;
  font-size: var(--text-xs);
  color: var(--ink-400);
  line-height: 1.6;
}

.auth-switch {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--ink-100);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--ink-500);
}

.auth-switch a {
  color: var(--accent);
  text-decoration: none;
  margin-left: 4px;
}

.auth-switch a:hover {
  text-decoration: underline;
}
</style>
