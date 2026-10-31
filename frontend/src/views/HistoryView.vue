<template>
  <div class="history-page">
    <!-- 1. 引导区 -->
    <n-card class="intro-card" :bordered="false">
      <div class="intro-content">
        <div class="intro-left">
          <div class="title-group">
            <div class="icon-wrapper">
              <n-icon size="32" color="#165DFF">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M12 2a10 10 0 100 20 10 10 0 000-20zm0 18a8 8 0 110-16 8 8 0 010 16zm.5-13H11v6l5.2 3.1.8-1.3-4.5-2.7z"/></svg>
              </n-icon>
            </div>
            <div>
              <h1 class="page-title">历史数据</h1>
            </div>
          </div>
        </div>
        <div class="intro-right">
          <n-select
            v-model:value="query.device_id"
            :options="deviceOptions"
            placeholder="全部终端"
            clearable
            style="width: 190px"
          />
          <n-date-picker
            v-model:value="query.range"
            type="datetimerange"
            clearable
            :locale="dateZhCN"
            start-placeholder="开始"
            end-placeholder="结束"
            style="width: 320px"
          />
          <n-button type="primary" size="medium" :loading="loading" @click="handleQuery">检索</n-button>
          <n-button v-if="!isGuest" size="medium" secondary @click="handleExport('xlsx')">导出 Excel</n-button>
          <n-button v-if="!isGuest" size="medium" quaternary @click="handleExport('csv')">导出 CSV</n-button>
        </div>
      </div>
    </n-card>

    <!-- 2. 趋势图表 -->
    <div class="charts-section">
      <n-grid :x-gap="24" :y-gap="24" cols="1 800:2" class="charts-grid">
        <n-grid-item>
          <n-card title="电阻与阻抗幅值趋势" :bordered="false" class="chart-card hover-effect">
            <template #header-extra>
              <n-tag type="primary" size="small" round>Ω</n-tag>
            </template>
            <div class="chart-summary-grid">
              <div class="summary-chip">
                <span>记录数</span>
                <strong>{{ rows.length }}</strong>
              </div>
              <div class="summary-chip">
                <span>电阻区间</span>
                <strong>{{ rangeText.resistance }}</strong>
              </div>
              <div class="summary-chip">
                <span>均值</span>
                <strong>{{ rangeText.avg }}</strong>
              </div>
            </div>
            <div ref="trendChartRef" class="chart-container"></div>
          </n-card>
        </n-grid-item>

        <n-grid-item>
          <n-card title="相位角趋势" :bordered="false" class="chart-card hover-effect">
            <template #header-extra>
              <n-tag type="warning" size="small" round>°</n-tag>
            </template>
            <div class="chart-summary-grid">
              <div class="summary-chip">
                <span>相位均值</span>
                <strong>{{ rangeText.phase }}</strong>
              </div>
              <div class="summary-chip">
                <span>相位区间</span>
                <strong>{{ rangeText.phaseRange }}</strong>
              </div>
              <div class="summary-chip">
                <span>时间跨度</span>
                <strong>{{ rangeText.span }}</strong>
              </div>
            </div>
            <div ref="phaseChartRef" class="chart-container"></div>
          </n-card>
        </n-grid-item>
      </n-grid>
    </div>

    <!-- 3. 记录明细 -->
    <n-card title="采集记录明细" :bordered="false" class="main-table-card">
      <n-data-table
        :columns="columns"
        :data="tableRows"
        :loading="loading"
        :bordered="false"
        size="large"
        :row-key="(row) => row.id"
        :max-height="520"
      />
    </n-card>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { NIcon, useMessage } from 'naive-ui'
import { dateZhCN } from 'naive-ui'
import { buildLineOption, echarts, formatClock, formatShort, seriesColors } from '../utils/chart'
import { deviceApi, downloadFile, measurementApi } from '../api'
import { isGuest } from '../utils/session'

const message = useMessage()
const query = reactive({ device_id: null, range: null })
const rows = ref([])
const loading = ref(false)
const trendChartRef = ref(null)
const phaseChartRef = ref(null)
let trendChart = null
let phaseChart = null

const deviceOptions = ref([])

const columns = [
  { title: '序号', key: 'id', width: 80 },
  { title: '终端', key: 'device_id', width: 100 },
  { title: '电阻 (Ω)', key: 'resistance_ohm', width: 110 },
  { title: '阻抗幅值 (Ω)', key: 'impedance_magnitude_ohm', width: 130 },
  { title: '相位角 (°)', key: 'phase_deg', width: 110 },
  { title: '应变 (με)', key: 'strain_ue', width: 110 },
  { title: '频率 (Hz)', key: 'frequency_hz', width: 100 },
  { title: '测量时间', key: 'measured_at', width: 160 }
]

const tableRows = computed(() =>
  rows.value.map((item) => ({
    ...item,
    resistance_ohm: fmt(item.resistance_ohm, 2),
    impedance_magnitude_ohm: fmt(item.impedance_magnitude_ohm, 2),
    phase_deg: fmt(item.phase_deg, 3),
    strain_ue: fmt(item.strain_ue, 1),
    frequency_hz: item.frequency_hz ?? '—',
    measured_at: formatShort(item.measured_at)
  }))
)

const rangeText = computed(() => {
  const pick = (key) =>
    rows.value.map((item) => item[key]).filter((value) => value !== null && value !== undefined)
  const resistance = pick('resistance_ohm')
  const phase = pick('phase_deg')
  if (!resistance.length) {
    return { resistance: '—', avg: '—', phase: '—', phaseRange: '—', span: '—' }
  }
  const min = Math.min(...resistance)
  const max = Math.max(...resistance)
  const avg = resistance.reduce((sum, value) => sum + value, 0) / resistance.length
  const phaseMin = Math.min(...phase)
  const phaseMax = Math.max(...phase)
  const phaseAvg = phase.reduce((sum, value) => sum + value, 0) / phase.length

  const first = rows.value[0]?.measured_at
  const last = rows.value[rows.value.length - 1]?.measured_at
  let span = '—'
  if (first && last) {
    const minutes = Math.round((new Date(last) - new Date(first)) / 60000)
    span = minutes >= 60 ? `${(minutes / 60).toFixed(1)} 小时` : `${minutes} 分钟`
  }

  return {
    resistance: `${min.toFixed(1)}~${max.toFixed(1)}`,
    avg: avg.toFixed(2),
    phase: phaseAvg.toFixed(3),
    phaseRange: `${phaseMin.toFixed(2)}~${phaseMax.toFixed(2)}`,
    span
  }
})

function fmt(value, digits) {
  if (value === null || value === undefined) return '—'
  return Number(value).toFixed(digits)
}

async function loadDevices() {
  const list = await deviceApi.list()
  deviceOptions.value = list.map((item) => ({ label: item.device_id, value: item.device_id }))
  // 默认只看第一台终端，多台混在一张图上曲线会互相穿插
  if (list.length && !query.device_id) {
    query.device_id = list[0].device_id
  }
}

function buildParams() {
  const params = { limit: query.device_id ? 300 : 800, order: 'asc' }
  if (query.device_id) params.device_id = query.device_id
  const range = query.range
  if (range && range.length === 2) {
    params.start = formatParam(range[0])
    params.end = formatParam(range[1])
  }
  return params
}

function formatParam(value) {
  const d = new Date(value)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function handleQuery() {
  loading.value = true
  try {
    rows.value = await measurementApi.list(buildParams())
  } catch (err) {
    console.error('历史查询失败', err)
    message.error('查询失败')
  } finally {
    loading.value = false
  }
  await nextTick()
  renderCharts()
}

function handleExport(format) {
  if (!rows.value.length) {
    message.warning('当前没有可导出的数据')
    return
  }
  downloadFile(`/export/measurements.${format}`, {
    device_id: query.device_id || undefined,
    start: query.range ? formatParam(query.range[0]) : undefined,
    end: query.range ? formatParam(query.range[1]) : undefined
  })
}

function renderCharts() {
  // 图表容器在 v-else 分支里，数据没到时不渲染，实例不能提前建
  if (!trendChartRef.value || !phaseChartRef.value) return
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)
  if (!phaseChart) phaseChart = echarts.init(phaseChartRef.value)

  const times = rows.value.map((item) => formatClock(item.measured_at))

  trendChart?.setOption(
    buildLineOption({
      times,
      yName: 'Ω',
      series: [
        { name: '电阻', data: rows.value.map((item) => item.resistance_ohm), color: seriesColors.resistance, area: true },
        { name: '阻抗幅值', data: rows.value.map((item) => item.impedance_magnitude_ohm), color: seriesColors.impedance }
      ]
    })
  )

  phaseChart?.setOption(
    buildLineOption({
      times,
      yName: '°',
      series: [
        { name: '相位角', data: rows.value.map((item) => item.phase_deg), color: seriesColors.phase, area: true }
      ]
    })
  )
}

function handleResize() {
  trendChart?.resize()
  phaseChart?.resize()
}

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  await loadDevices()
  await handleQuery()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  phaseChart?.dispose()
})
</script>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.charts-grid {
  justify-content: center;
  max-width: 1400px;
  margin: 0 auto;
}
</style>
