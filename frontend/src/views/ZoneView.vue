<template>
  <div class="zone-page">
    <!-- 1. 引导区：选部位 + 部位概况 -->
    <n-card class="intro-card" :bordered="false">
      <div class="intro-content">
        <div class="intro-left">
          <div class="title-group">
            <div class="icon-wrapper">
              <n-icon size="32" color="#165DFF">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M3 3h8v8H3zm10 0h8v8h-8zM3 13h8v8H3zm10 0h8v8h-8z"/></svg>
              </n-icon>
            </div>
            <div>
              <h1 class="page-title">区域监测</h1>
            </div>
          </div>
        </div>
        <div class="intro-right">
          <n-select
            v-model:value="selectedZone"
            :options="zoneOptions"
            placeholder="选择部位"
            style="width: 260px"
            @update:value="handleZoneChange"
          />
          <n-button size="medium" secondary :loading="loading" @click="loadZoneData(selectedZone)">刷新</n-button>
        </div>
      </div>
    </n-card>

    <n-empty v-if="!selectedZone" description="请选择要监测的部位" class="empty-block" />

    <template v-else>
      <!-- 2. 部位概况 + 当前读数 -->
      <div class="charts-section">
        <n-grid :x-gap="24" :y-gap="24" cols="1 900:3" class="charts-grid">
          <n-grid-item>
            <n-card title="当前读数" :bordered="false" class="chart-card">
              <template #header-extra>
                <n-tag :type="zoneStatus.type" size="small" round>{{ zoneStatus.text }}</n-tag>
              </template>
              <div class="readout-grid">
                <div v-for="item in readouts" :key="item.label" class="readout-item">
                  <span class="readout-label">{{ item.label }}</span>
                  <strong class="readout-value mono">{{ item.value }}</strong>
                  <span class="readout-unit">{{ item.unit }}</span>
                </div>
              </div>
            </n-card>
          </n-grid-item>

          <n-grid-item :span="2">
            <n-card title="部位概况" :bordered="false" class="chart-card">
              <template #header-extra>
                <n-tag type="info" size="small" round>{{ zone?.code }}</n-tag>
              </template>
              <div class="profile-grid">
                <div class="profile-item">
                  <span>所属工程</span>
                  <strong>{{ structureName }}</strong>
                </div>
                <div class="profile-item">
                  <span>工程类型</span>
                  <strong>{{ structureKind }}</strong>
                </div>
                <div class="profile-item">
                  <span>布设面积</span>
                  <strong class="mono">{{ zone?.area_sqm ?? '—' }} m²</strong>
                </div>
                <div class="profile-item">
                  <span>涂层厚度</span>
                  <strong class="mono">{{ zone?.coating_thickness_mm ?? '—' }} mm</strong>
                </div>
                <div class="profile-item">
                  <span>成像网格</span>
                  <strong class="mono">{{ zone?.grid_size ?? '—' }} × {{ zone?.grid_size ?? '—' }}</strong>
                </div>
                <div class="profile-item">
                  <span>采集终端</span>
                  <strong class="mono">{{ zoneDeviceCount }} 台</strong>
                </div>
                <div class="profile-item">
                  <span>未处理告警</span>
                  <strong class="mono" :class="zoneAlertCount ? 'text-danger' : ''">{{ zoneAlertCount }} 条</strong>
                </div>
                <div class="profile-item">
                  <span>最近上报</span>
                  <strong class="mono">{{ lastSeenText }}</strong>
                </div>
              </div>
            </n-card>
          </n-grid-item>
        </n-grid>
      </div>

      <!-- 3. 电阻率成像 + 时序曲线 -->
      <div class="charts-section">
        <n-grid :x-gap="24" :y-gap="24" cols="1 900:2" class="charts-grid">
          <n-grid-item>
            <n-card title="电阻率分布" :bordered="false" class="chart-card">
              <template #header-extra>
                <n-tag
                  v-if="imagingData"
                  :type="imagingData.anomaly_count > 0 ? 'error' : 'success'"
                  size="small"
                  round
                >
                  {{ imagingData.anomaly_count > 0 ? `${imagingData.anomaly_count} 个异常点` : '分布均匀' }}
                </n-tag>
              </template>
              <div class="chart-summary-grid">
                <div class="summary-chip">
                  <span>网格规模</span>
                  <strong>{{ imagingData?.grid_size ?? '—' }}²</strong>
                </div>
                <div class="summary-chip">
                  <span>扫描耗时</span>
                  <strong>{{ imagingData?.scan_cost_ms ?? '—' }} ms</strong>
                </div>
                <div class="summary-chip">
                  <span>解算时间</span>
                  <strong>{{ imagingData ? formatShort(imagingData.created_at) : '—' }}</strong>
                </div>
              </div>
              <div v-if="loading" class="skeleton heatmap-skeleton"></div>
              <n-empty v-else-if="!imagingData" description="该部位尚无成像数据" />
              <div v-else class="imaging-canvas-wrap">
                <div ref="heatmapRef" class="heatmap-box"></div>
              </div>
            </n-card>
          </n-grid-item>

          <n-grid-item>
            <n-card title="电学量趋势" :bordered="false" class="chart-card">
              <template #header-extra>
                <n-tag type="primary" size="small" round>Ω</n-tag>
              </template>
              <div class="chart-summary-grid">
                <div class="summary-chip">
                  <span>电阻均值</span>
                  <strong>{{ chipStats.resistanceAvg }}</strong>
                </div>
                <div class="summary-chip">
                  <span>阻抗均值</span>
                  <strong>{{ chipStats.impedanceAvg }}</strong>
                </div>
                <div class="summary-chip">
                  <span>采样条数</span>
                  <strong>{{ records.length }}</strong>
                </div>
              </div>
              <div ref="trendChartRef" class="chart-container"></div>
            </n-card>
          </n-grid-item>
        </n-grid>
      </div>

      <!-- 4. 该部位的告警与采集记录 -->
      <div class="charts-section">
        <n-grid :x-gap="24" :y-gap="24" cols="1 900:2" class="charts-grid">
          <n-grid-item>
            <n-card title="该部位告警" :bordered="false" class="chart-card">
              <template #header-extra>
                <n-tag :type="zoneAlerts.length ? 'warning' : 'success'" size="small" round>
                  {{ zoneAlerts.length }} 条
                </n-tag>
              </template>
              <n-data-table
                :columns="alertColumns"
                :data="zoneAlertRows"
                :bordered="false"
                :row-key="(row) => row.id"
                :max-height="260"
              />
            </n-card>
          </n-grid-item>

          <n-grid-item>
            <n-card title="采集记录" :bordered="false" class="chart-card">
              <template #header-extra>
                <n-button size="small" secondary @click="$router.push('/history')">查看全部</n-button>
              </template>
              <n-data-table
                :columns="recordColumns"
                :data="recentRows"
                :bordered="false"
                :row-key="(row) => row.id"
                :max-height="260"
              />
            </n-card>
          </n-grid-item>
        </n-grid>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, h, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { NIcon, NTag } from 'naive-ui'
import { useRoute } from 'vue-router'
import {
  buildHeatmapOption,
  buildLineOption,
  echarts,
  formatClock,
  formatShort,
  seriesColors
} from '../utils/chart'
import { alertApi, deviceApi, imagingApi, measurementApi, structureApi } from '../api'

const zones = ref([])
const structures = ref([])
const devices = ref([])
const selectedZone = ref(null)
const imagingData = ref(null)
const records = ref([])
const allAlerts = ref([])
const loading = ref(false)
const heatmapRef = ref(null)
const trendChartRef = ref(null)
let heatmap = null
let trendChart = null

const route = useRoute()

const alertColumns = [
  {
    title: '级别',
    key: 'severity',
    width: 80,
    render: (row) =>
      h(
        NTag,
        { type: row.severity === 'critical' ? 'error' : 'warning', size: 'small', round: true },
        { default: () => (row.severity === 'critical' ? '严重' : '预警') }
      )
  },
  { title: '告警内容', key: 'message' },
  { title: '时间', key: 'triggered_at', width: 130 }
]

const recordColumns = [
  { title: '电阻 (Ω)', key: 'resistance_ohm', width: 100 },
  { title: '阻抗 (Ω)', key: 'impedance_magnitude_ohm', width: 100 },
  { title: '相位 (°)', key: 'phase_deg', width: 90 },
  { title: '应变 (με)', key: 'strain_ue', width: 90 },
  { title: '测量时间', key: 'measured_at', width: 140 }
]

const zoneOptions = computed(() =>
  zones.value.map((item) => ({ label: `${item.code} ${item.name}`, value: item.code }))
)

const zone = computed(() => zones.value.find((item) => item.code === selectedZone.value))

const structure = computed(() =>
  structures.value.find((item) => item.id === zone.value?.structure_id)
)

const structureName = computed(() => structure.value?.name || '—')
const structureKind = computed(() => structure.value?.kind || '—')

const zoneDeviceCount = computed(() => {
  if (!zone.value) return 0
  return devices.value.filter((item) => item.zone_id === zone.value.id).length
})

const zoneAlerts = computed(() =>
  allAlerts.value.filter((item) => item.zone_id === zone.value?.id)
)

const zoneAlertCount = computed(
  () => allAlerts.value.filter((item) => item.zone_id === zone.value?.id && !item.acknowledged_at).length
)

const lastSeenText = computed(() => {
  const times = devices.value
    .filter((item) => item.zone_id === zone.value?.id)
    .map((item) => item.last_seen_at)
    .filter(Boolean)
    .sort()
  if (!times.length) return '—'
  return formatShort(times[times.length - 1])
})

const zoneStatus = computed(() => {
  if (zoneAlertCount.value > 0) return { type: 'error', text: '存在异常' }
  if (!records.value.length) return { type: 'default', text: '无数据' }
  return { type: 'success', text: '运行正常' }
})

const readouts = computed(() => {
  const last = records.value[records.value.length - 1]
  if (!last) {
    return [
      { label: '电阻', value: '—', unit: 'Ω' },
      { label: '阻抗幅值', value: '—', unit: 'Ω' },
      { label: '相位角', value: '—', unit: '°' },
      { label: '应变', value: '—', unit: 'με' }
    ]
  }
  return [
    { label: '电阻', value: fmt(last.resistance_ohm, 2), unit: 'Ω' },
    { label: '阻抗幅值', value: fmt(last.impedance_magnitude_ohm, 2), unit: 'Ω' },
    { label: '相位角', value: fmt(last.phase_deg, 3), unit: '°' },
    { label: '应变', value: fmt(last.strain_ue, 1), unit: 'με' }
  ]
})

const recentRows = computed(() =>
  records.value
    .slice(-8)
    .reverse()
    .map((item) => ({
      ...item,
      resistance_ohm: fmt(item.resistance_ohm, 2),
      impedance_magnitude_ohm: fmt(item.impedance_magnitude_ohm, 2),
      phase_deg: fmt(item.phase_deg, 3),
      strain_ue: fmt(item.strain_ue, 1),
      measured_at: formatShort(item.measured_at)
    }))
)

const zoneAlertRows = computed(() =>
  zoneAlerts.value.map((item) => ({
    ...item,
    triggered_at: formatShort(item.triggered_at)
  }))
)

const chipStats = computed(() => {
  const pick = (key) =>
    records.value.map((item) => item[key]).filter((value) => value !== null && value !== undefined)
  const avg = (list) => (list.length ? (list.reduce((s, v) => s + v, 0) / list.length).toFixed(2) : '—')
  return {
    resistanceAvg: avg(pick('resistance_ohm')),
    impedanceAvg: avg(pick('impedance_magnitude_ohm'))
  }
})

function fmt(value, digits) {
  if (value === null || value === undefined) return '—'
  return Number(value).toFixed(digits)
}

async function loadBaseData() {
  const [zoneList, structureList, deviceList, alertList] = await Promise.all([
    structureApi.listZones(),
    structureApi.list(),
    deviceApi.list(),
    alertApi.records({ limit: 300 })
  ])
  zones.value = zoneList
  structures.value = structureList
  devices.value = deviceList
  allAlerts.value = alertList
  // 地址栏带的测区编号优先，从总览或告警页跳进来能直接落到目标测区
  const code = route.query.code
  if (code && zoneList.some((item) => item.code === code)) {
    selectedZone.value = code
  } else if (zoneList.length && !selectedZone.value) {
    selectedZone.value = zoneList[0].code
  }
}

async function loadZoneData(zoneCode) {
  const code = zoneCode || selectedZone.value
  if (!code) return
  loading.value = true
  try {
    const target = zones.value.find((item) => item.code === code)
    const zoneDevices = devices.value.filter((item) => item.zone_id === target?.id)
    const deviceId = zoneDevices[0]?.device_id

    const [latest, measurementRows] = await Promise.all([
      imagingApi.latest({ zone_code: code }),
      deviceId
        ? measurementApi.latest({ device_id: deviceId, limit: 80 })
        : Promise.resolve([])
    ])
    imagingData.value = latest?.available ? latest : null
    records.value = measurementRows
  } catch (err) {
    console.error('部位数据加载失败', err)
  } finally {
    loading.value = false
  }
  // 等骨架屏撤掉、容器挂载后再画
  await nextTick()
  await nextTick()
  renderHeatmap()
  renderTrend()
}

function renderHeatmap() {
  if (!heatmapRef.value) return
  // 图表容器在 v-else 分支里，加载时会先被骨架屏替换掉，
  // 旧实例绑定的元素已经不是当前这个了，得重新初始化
  if (heatmap && heatmap.getDom() !== heatmapRef.value) {
    heatmap.dispose()
    heatmap = null
  }
  if (!heatmap) heatmap = echarts.init(heatmapRef.value)
  if (!imagingData.value) return
  heatmap.setOption(buildHeatmapOption(imagingData.value.matrix), true)
}

function renderTrend() {
  if (!trendChartRef.value) return
  if (trendChart && trendChart.getDom() !== trendChartRef.value) {
    trendChart.dispose()
    trendChart = null
  }
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)
  const times = records.value.map((item) => formatClock(item.measured_at))
  trendChart.setOption(
    buildLineOption({
      times,
      yName: 'Ω',
      series: [
        {
          name: '电阻',
          data: records.value.map((item) => item.resistance_ohm),
          color: seriesColors.resistance,
          area: true
        },
        {
          name: '阻抗幅值',
          data: records.value.map((item) => item.impedance_magnitude_ohm),
          color: seriesColors.impedance
        }
      ]
    })
  )
}

async function handleZoneChange(code) {
  imagingData.value = null
  records.value = []
  await loadZoneData(code)
}

function handleResize() {
  heatmap?.resize()
  trendChart?.resize()
}

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  await loadBaseData()
  await loadZoneData(selectedZone.value)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  heatmap?.dispose()
  trendChart?.dispose()
})
</script>

<style scoped>
.zone-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.charts-grid {
  justify-content: center;
  max-width: 1400px;
  margin: 0 auto;
}

.empty-block {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
  padding: 60px 0;
}

/* 当前读数 */
.readout-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.readout-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #f7f8fa;
  border: 1px solid #eef0f3;
}

.readout-label {
  font-size: var(--text-sm);
  color: #86909c;
}

.readout-value {
  font-size: 22px;
  color: #1d2129;
  line-height: 1.3;
}

.readout-unit {
  font-size: var(--text-sm);
  color: #86909c;
}

/* 测区档案 */
.profile-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.profile-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f7f8fa;
  border: 1px solid #eef0f3;
}

.profile-item span {
  font-size: var(--text-sm);
  color: #86909c;
}

.profile-item strong {
  font-size: 15px;
  color: #1d2129;
  font-weight: 600;
}

.heatmap-box {
  height: 420px;
  width: 100%;
}

.heatmap-skeleton {
  height: 420px;
}

.imaging-canvas-wrap {
  position: relative;
}

.text-danger {
  color: #f53f3f;
}
</style>
