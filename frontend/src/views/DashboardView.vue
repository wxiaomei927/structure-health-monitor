<template>
  <div class="data-platform">
    <!-- 1. 引导区：只放异常概览，正常状态不占篇幅 -->
    <n-card class="intro-card" :bordered="false">
      <div class="intro-content">
        <div class="intro-left">
          <div class="title-group">
            <div class="icon-wrapper">
              <n-icon size="32" color="#165DFF">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M3 13h2v8H3zm4 0h2v8H7zm4 0h2v8h-2zm4 0h2v8h-2zm4 0h2v8h-2zM3 3h18v8H3z"/></svg>
              </n-icon>
            </div>
            <div>
              <h1 class="page-title">监测总览</h1>
            </div>
          </div>
        </div>
        <div class="intro-right">
          <div class="hero-stat-card" :class="{ 'stat-danger': zoneAlertLevel.critical > 0 }">
            <span class="hero-stat-label">严重异常部位</span>
            <strong>{{ zoneAlertLevel.critical }}</strong>
          </div>
          <div class="hero-stat-card" :class="{ 'stat-warn': zoneAlertLevel.warning > 0 }">
            <span class="hero-stat-label">预警部位</span>
            <strong>{{ zoneAlertLevel.warning }}</strong>
          </div>
          <div class="hero-stat-card">
            <span class="hero-stat-label">正常部位</span>
            <strong>{{ zoneAlertLevel.normal }} / {{ zoneAlertLevel.total }}</strong>
          </div>
          <div class="hero-stat-card">
            <span class="hero-stat-label">在线终端</span>
            <strong>{{ onlineCount }} / {{ devices.length }}</strong>
          </div>
        </div>
      </div>
    </n-card>

    <!-- 2. 异常部位清单：异常排前面，点进区域监测 -->
    <n-card title="监测对象" :bordered="false" class="main-table-card">
      <template #header-extra>
        <n-space :size="10" align="center">
          <n-tag v-for="item in kindSummary" :key="item.kind" size="small" :bordered="false">
            {{ item.kind }} {{ item.count }}
          </n-tag>
          <n-button size="medium" secondary @click="$router.push('/zone')">
            <template #icon><n-icon><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg></n-icon></template>
            进入区域监测
          </n-button>
        </n-space>
      </template>
      <n-data-table
        :columns="zoneColumns"
        :data="zoneRows"
        :loading="loading"
        :bordered="false"
        size="large"
        :row-key="(row) => row.zoneCode"
        :row-props="rowProps"
        class="zones-table"
      />
    </n-card>

    <!-- 3. 最近告警 -->
    <n-card title="最近告警" :bordered="false" class="main-table-card">
      <template #header-extra>
        <n-button size="medium" secondary @click="$router.push('/alerts')">
          <template #icon><n-icon><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg></n-icon></template>
          全部告警
        </n-button>
      </template>
      <n-data-table
        :columns="alertColumns"
        :data="alertRows"
        :loading="loading"
        :bordered="false"
        size="large"
        :row-key="(row) => row.id"
        :max-height="300"
      />
    </n-card>
  </div>
</template>

<script setup>
import { computed, h, onMounted, ref } from 'vue'
import { NIcon, NTag } from 'naive-ui'
import { alertApi, deviceApi, measurementApi, structureApi } from '../api'
import { formatShort } from '../utils/chart'

const loading = ref(true)
const structures = ref([])
const zones = ref([])
const devices = ref([])
const alerts = ref([])
const zoneStats = ref([])

const zoneColumns = [
  { title: '所属工程', key: 'structureName', width: 160 },
  { title: '类型', key: 'kind', width: 110 },
  { title: '监测部位', key: 'zoneName', width: 190 },
  { title: '网格规模', key: 'gridSize', width: 100 },
  { title: '终端数', key: 'deviceCount', width: 80 },
  { title: '电阻均值 (Ω)', key: 'resistanceAvg', width: 130 },
  { title: '应变均值 (με)', key: 'strainAvg', width: 120 },
  {
    title: '状态',
    key: 'alertState',
    width: 110,
    render: (row) =>
      h(
        NTag,
        { type: row.tagType, size: 'small', round: true },
        { default: () => row.alertText }
      )
  }
]

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
  { title: '部位编号', key: 'zoneCode', width: 130 },
  { title: '触发时间', key: 'triggered_at', width: 140 }
]

const onlineCount = computed(() => devices.value.filter((item) => item.status !== 'offline').length)

// 按监测部位统计异常分布，四张卡的数字口径一致、可相互核对
const zoneAlertLevel = computed(() => {
  const level = new Map()
  alerts.value
    .filter((item) => !item.acknowledged_at)
    .forEach((item) => {
      const current = level.get(item.zone_id)
      if (!current || item.severity === 'critical') {
        level.set(item.zone_id, item.severity)
      }
    })
  let critical = 0
  let warning = 0
  level.forEach((severity) => {
    if (severity === 'critical') critical += 1
    else warning += 1
  })
  const normal = zones.value.filter((zone) => !level.has(zone.id)).length
  return { critical, warning, normal, total: zones.value.length }
})

const kindSummary = computed(() => {
  const counter = {}
  structures.value.forEach((item) => {
    const kind = item.kind || '其他'
    counter[kind] = (counter[kind] || 0) + 1
  })
  return Object.entries(counter).map(([kind, count]) => ({ kind, count }))
})

// 异常测区排前面，正常测区按编号排
const zoneRows = computed(() => {
  const statsMap = {}
  zoneStats.value.forEach((item) => {
    statsMap[item.device_id] = item
  })

  const rows = zones.value.map((zone) => {
    const structureItem = structures.value.find((item) => item.id === zone.structure_id)
    const zoneDevices = devices.value.filter((item) => item.zone_id === zone.id)
    const avgOf = (key) => {
      const values = zoneDevices
        .map((item) => statsMap[item.device_id]?.[key])
        .filter((value) => value !== undefined && value !== null)
      if (!values.length) return null
      return values.reduce((sum, value) => sum + value, 0) / values.length
    }

    const openAlerts = alerts.value.filter(
      (item) => item.zone_id === zone.id && !item.acknowledged_at
    )
    const hasCritical = openAlerts.some((item) => item.severity === 'critical')

    return {
      zoneCode: zone.code,
      zoneName: zone.name,
      structureName: structureItem?.name || '—',
      kind: structureItem?.kind || '—',
      gridSize: `${zone.grid_size}×${zone.grid_size}`,
      deviceCount: zoneDevices.length,
      resistanceAvg: formatMetric(avgOf('resistance_avg'), 2),
      strainAvg: formatMetric(avgOf('strain_avg'), 1),
      alertCount: openAlerts.length,
      tagType: hasCritical ? 'error' : openAlerts.length ? 'warning' : 'success',
      alertText: hasCritical
        ? '严重异常'
        : openAlerts.length
          ? `${openAlerts.length} 条预警`
          : '正常'
    }
  })

  return rows.sort((a, b) => {
    const aWeight = a.alertCount > 0 ? 0 : 1
    const bWeight = b.alertCount > 0 ? 0 : 1
    if (aWeight !== bWeight) return aWeight - bWeight
    return a.zoneCode.localeCompare(b.zoneCode)
  })
})

const alertRows = computed(() =>
  alerts.value.slice(0, 8).map((item) => ({
    ...item,
    zoneCode: zones.value.find((zone) => zone.id === item.zone_id)?.code || '—',
    triggered_at: formatShort(item.triggered_at)
  }))
)

function formatMetric(value, digits) {
  if (value === null || value === undefined) return '—'
  return Number(value).toFixed(digits)
}

function rowProps(row) {
  return {
    style: 'cursor: pointer',
    onClick: () => {
      window.location.hash = `#/zone?code=${row.zoneCode}`
    }
  }
}

async function loadAll() {
  loading.value = true
  try {
    const [structureList, zoneList, deviceList, alertList, stats] = await Promise.all([
      structureApi.list(),
      structureApi.listZones(),
      deviceApi.list(),
      alertApi.records({ limit: 100 }),
      measurementApi.stats({})
    ])
    structures.value = structureList
    zones.value = zoneList
    devices.value = deviceList
    alerts.value = alertList
    zoneStats.value = stats
  } catch (err) {
    console.error('总览数据加载失败', err)
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.data-platform {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Intro Card */
.intro-card {
  background: linear-gradient(135deg, #ffffff 0%, #f9f9fb 100%);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
}

.intro-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
}

.title-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

.icon-wrapper {
  width: 48px;
  height: 48px;
  background: #e8f3ff;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #1d2129;
  margin: 0;
}

.intro-right {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-right: 12px;
  flex-wrap: wrap;
}

.hero-stat-card {
  min-width: 132px;
  padding: 12px 14px;
  border-radius: 12px;
  background: linear-gradient(180deg, #ffffff 0%, #f7faff 100%);
  border: 1px solid #eaf2ff;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hero-stat-card strong {
  font-size: 22px;
  color: #1d2129;
}

.hero-stat-label {
  font-size: var(--text-sm);
  color: #86909c;
}

.stat-danger {
  border-color: #f5b8b8;
  background: linear-gradient(180deg, #ffffff 0%, #fff5f5 100%);
}

.stat-danger strong {
  color: #f53f3f;
}

.stat-warn {
  border-color: #ffd3a6;
  background: linear-gradient(180deg, #ffffff 0%, #fff9f0 100%);
}

.stat-warn strong {
  color: #ff7d00;
}

/* Main Table */
.main-table-card {
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
}

.zones-table {
  margin-top: 12px;
}
</style>
