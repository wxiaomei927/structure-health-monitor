<template>
  <div class="alerts-page">
    <!-- 1. 引导区 -->
    <n-card class="intro-card" :bordered="false">
      <div class="intro-content">
        <div class="intro-left">
          <div class="title-group">
            <div class="icon-wrapper">
              <n-icon size="32" color="#FF7D00">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>
              </n-icon>
            </div>
            <div>
              <h1 class="page-title">异常告警</h1>
            </div>
          </div>
        </div>
        <div class="intro-right">
          <n-radio-group v-model:value="filterMode" @update:value="loadRecords">
            <n-radio-button value="all">全部</n-radio-button>
            <n-radio-button value="open">未处理</n-radio-button>
              <n-radio-button value="done">已处理</n-radio-button>
          </n-radio-group>
          <n-button v-if="!isGuest" type="primary" size="medium" @click="openRuleModal">新建规则</n-button>
        </div>
      </div>
    </n-card>

    <!-- 2. 告警概览 -->
    <div class="charts-section">
      <n-grid :x-gap="24" :y-gap="24" cols="1 800:2" class="charts-grid">
        <n-grid-item>
          <n-card title="告警记录" :bordered="false" class="chart-card">
            <template #header-extra>
              <n-tag :type="summary.open ? 'warning' : 'success'" size="small" round>
                待处理 {{ summary.open ?? 0 }} 条
              </n-tag>
            </template>
            <div class="flow-note">
              读数越出正常范围时自动生成一条记录，现场核查后标记为已处理；处理错了可以撤销。
              <template v-if="isGuest">游客模式下只能查看，不能标记处理状态。</template>
            </div>
            <div class="chart-summary-grid">
              <div class="summary-chip">
                <span>严重告警</span>
                <strong class="text-danger">{{ summary.critical ?? 0 }}</strong>
              </div>
              <div class="summary-chip">
                <span>一般预警</span>
                <strong class="text-warn">{{ summary.warning ?? 0 }}</strong>
              </div>
              <div class="summary-chip">
                <span>已处理</span>
                <strong>{{ summary.acknowledged ?? 0 }}</strong>
              </div>
            </div>
            <n-data-table
              :columns="recordColumns"
              :data="recordRows"
              :loading="loading"
              :bordered="false"
              :row-key="(row) => row.id"
              :max-height="300"
            />
          </n-card>
        </n-grid-item>

        <n-grid-item>
          <n-card title="告警规则" :bordered="false" class="chart-card">
            <template #header-extra>
              <n-tag type="info" size="small" round> {{ rules.length }} 条规则</n-tag>
            </template>
            <div class="flow-note">
              每条规则规定一个监测量的正常范围，连续若干次越界才生成告警，避免单次波动误报。
            </div>
            <div class="chart-summary-grid">
              <div class="summary-chip">
                <span>生效规则</span>
                <strong>{{ enabledCount }}</strong>
              </div>
              <div class="summary-chip">
                <span>严重级别</span>
                <strong>{{ criticalRuleCount }}</strong>
              </div>
              <div class="summary-chip">
                <span>覆盖部位</span>
                <strong>{{ ruleZoneCount }}</strong>
              </div>
            </div>
            <n-data-table
              :columns="ruleColumns"
              :data="ruleRows"
              :bordered="false"
              :row-key="(row) => row.id"
              :max-height="300"
            />
          </n-card>
        </n-grid-item>
      </n-grid>
    </div>

    <!-- 3. 告警分布与处理情况 -->
    <div class="charts-section">
      <n-grid :x-gap="24" :y-gap="24" cols="1 800:2" class="charts-grid">
        <n-grid-item>
          <n-card title="各部位告警分布" :bordered="false" class="chart-card hover-effect">
            <template #header-extra>
              <n-tag type="warning" size="small" round> 条</n-tag>
            </template>
            <div class="chart-summary-grid">
              <div class="summary-chip">
                <span>涉及部位</span>
                <strong>{{ zoneAlertCount }}</strong>
              </div>
              <div class="summary-chip">
                <span>告警总数</span>
                <strong>{{ records.length }}</strong>
              </div>
              <div class="summary-chip">
                <span>处理率</span>
                <strong>{{ confirmRate }}</strong>
              </div>
            </div>
            <div ref="zoneAlertChartRef" class="chart-container"></div>
          </n-card>
        </n-grid-item>

        <n-grid-item>
          <n-card title="按监测量分布" :bordered="false" class="chart-card hover-effect">
            <template #header-extra>
              <n-tag type="info" size="small" round> 条</n-tag>
            </template>
            <div class="chart-summary-grid">
              <div class="summary-chip">
                <span>最常越界</span>
                <strong>{{ topMetric.label }}</strong>
              </div>
              <div class="summary-chip">
                <span>该指标占比</span>
                <strong>{{ topMetric.ratio }}</strong>
              </div>
              <div class="summary-chip">
                <span>已处理</span>
                <strong>{{ summary.acknowledged ?? 0 }}</strong>
            </div>
            </div>
            <div ref="severityChartRef" class="chart-container"></div>
          </n-card>
        </n-grid-item>
      </n-grid>
    </div>

    <!-- 新建规则 -->
    <n-modal v-model:show="showRuleModal" preset="card" title="新建告警规则" style="width: 460px">
      <n-form :model="ruleForm" label-placement="left" label-width="88">
        <n-form-item label="规则名称">
          <n-input v-model:value="ruleForm.name" placeholder="例如 电阻越上限" />
        </n-form-item>
        <n-form-item label="监测部位">
          <n-select v-model:value="ruleForm.zone_id" :options="zoneOptions" placeholder="选择部位" />
        </n-form-item>
        <n-form-item label="监测量">
          <n-select v-model:value="ruleForm.metric" :options="metricOptions" />
        </n-form-item>
        <n-form-item label="下限">
          <n-input-number v-model:value="ruleForm.lower_limit" :placeholder="'不限'" style="width: 100%" />
        </n-form-item>
        <n-form-item label="上限">
          <n-input-number v-model:value="ruleForm.upper_limit" :placeholder="'不限'" style="width: 100%" />
        </n-form-item>
        <n-form-item label="连续点数">
          <n-input-number v-model:value="ruleForm.trigger_count" :min="1" :max="50" style="width: 100%" />
        </n-form-item>
        <n-form-item label="级别">
          <n-radio-group v-model:value="ruleForm.severity">
            <n-radio-button value="warning">预警</n-radio-button>
            <n-radio-button value="critical">严重</n-radio-button>
          </n-radio-group>
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showRuleModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="handleSaveRule">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { computed, h, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { NButton, NIcon, NSpace, NTag, useMessage } from 'naive-ui'
import { alertApi, structureApi } from '../api'
import { buildBarOption, echarts, formatShort } from '../utils/chart'
import { isGuest } from '../utils/session'

const message = useMessage()
const loading = ref(true)
const saving = ref(false)
const records = ref([])
const rules = ref([])
const zones = ref([])
const summary = ref({})
const filterMode = ref('all')
const showRuleModal = ref(false)
const zoneAlertChartRef = ref(null)
const severityChartRef = ref(null)
let zoneAlertChart = null
let severityChart = null

const ruleForm = reactive({
  name: '',
  zone_id: null,
  metric: 'resistance_ohm',
  lower_limit: null,
  upper_limit: null,
  trigger_count: 3,
  severity: 'warning'
})

const metricOptions = [
  { label: '电阻 (Ω)', value: 'resistance_ohm' },
  { label: '相位角 (°)', value: 'phase_deg' },
  { label: '阻抗幅值 (Ω)', value: 'impedance_magnitude_ohm' },
  { label: '应变 (με)', value: 'strain_ue' }
]

const recordColumns = computed(() => {
  const columns = [
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
    { title: '终端', key: 'device_id', width: 90 },
    {
      title: '状态',
      key: 'state',
      width: 150,
      render: (row) =>
        row.acknowledged_at
          ? h('div', { style: 'display:flex;flex-direction:column;gap:2px' }, [
              h(NTag, { type: 'default', size: 'small', round: true }, { default: () => '已处理' }),
              h('span', { style: 'font-size:13px;color:#86909C' },
                { default: () => `${row.acknowledged_by || 'admin'} 于 ${formatShort(row.acknowledged_at)}` })
            ])
          : h(NTag, { type: 'warning', size: 'small', round: true }, { default: () => '待处理' })
    }
  ]
  if (isGuest.value) return columns
  columns.push({
    title: '操作',
    key: 'action',
    width: 175,
    render: (row) =>
      h(NSpace, { size: 6 }, {
        default: () => [
          row.acknowledged_at
            ? h(
                NButton,
                { size: 'small', secondary: true, onClick: () => handleReopen(row) },
                { default: () => '撤销处理' }
              )
            : h(
                NButton,
                { size: 'small', type: 'primary', onClick: () => handleAck(row) },
                { default: () => '标记已处理' }
              ),
          h(
            NButton,
            { size: 'small', quaternary: true, onClick: () => gotoZone(row) },
            { default: () => '查看现场' }
          )
        ]
      })
  })
  return columns
})

const ruleColumns = [
  { title: '规则名称', key: 'name', width: 120 },
  { title: '监测量', key: 'metric', width: 90 },
  { title: '越界条件', key: 'range', width: 130 },
  { title: '连续几次越界才报', key: 'trigger_count', width: 140 },
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
  }
]

const zoneOptions = computed(() =>
  zones.value.map((item) => ({ label: `${item.code} ${item.name}`, value: item.id }))
)

const metricNames = {
  resistance_ohm: '电阻',
  phase_deg: '相位角',
  impedance_magnitude_ohm: '阻抗幅值',
  strain_ue: '应变'
}

const enabledCount = computed(() => rules.value.filter((item) => item.enabled).length)
const criticalRuleCount = computed(() => rules.value.filter((item) => item.severity === 'critical').length)
const ruleZoneCount = computed(() => new Set(rules.value.map((item) => item.zone_id).filter(Boolean)).size)

const zoneAlertCount = computed(() => new Set(records.value.map((item) => item.zone_id).filter(Boolean)).size)

// 越界次数最多的监测量
const topMetric = computed(() => {
  const counter = {}
  records.value.forEach((item) => {
    counter[item.metric] = (counter[item.metric] || 0) + 1
  })
  const entries = Object.entries(counter).sort((a, b) => b[1] - a[1])
  if (!entries.length) return { label: '—', ratio: '—' }
  const [metric, count] = entries[0]
  const total = records.value.length || 1
  return {
    label: metricNames[metric] || metric,
    ratio: `${((count / total) * 100).toFixed(0)}%`
  }
})

const confirmRate = computed(() => {
  const total = summary.value.total || 0
  if (!total) return '—'
  return `${((summary.value.acknowledged || 0) / total * 100).toFixed(0)}%`
})

// 各部位的告警条数
const zoneAlertRows = computed(() => {
  const counter = {}
  records.value.forEach((item) => {
    if (!item.zone_id) return
    counter[item.zone_id] = (counter[item.zone_id] || 0) + 1
  })
  return Object.entries(counter)
    .map(([zoneId, count]) => {
      // 对象键取出来是字符串，跟数字 id 比较前要转一下
      const zone = zones.value.find((item) => item.id === Number(zoneId))
      return { code: zone?.code || `未知部位`, name: zone?.name || '', count }
    })
    .sort((a, b) => b.count - a.count)
})

const recordRows = computed(() =>
  records.value.map((item) => ({
    ...item,
    device_id: item.device_id || '—',
    triggered_at: formatShort(item.triggered_at)
  }))
)

const ruleRows = computed(() =>
  rules.value.map((item) => ({
    ...item,
    metric: metricNames[item.metric] || item.metric,
    range: describeRange(item)
  }))
)

// 规则只设了单边时，写清楚是"超过上限"还是"低于下限"，不用无穷大符号
function describeRange(rule) {
  const hasLower = rule.lower_limit !== null && rule.lower_limit !== undefined
  const hasUpper = rule.upper_limit !== null && rule.upper_limit !== undefined
  if (hasLower && hasUpper) return `${rule.lower_limit} ~ ${rule.upper_limit}`
  if (hasUpper) return `高于 ${rule.upper_limit}`
  if (hasLower) return `低于 ${rule.lower_limit}`
  return '不限'
}

async function loadRecords() {
  loading.value = true
  try {
    const [recordList, sum] = await Promise.all([
      alertApi.records({
        only_open: filterMode.value === 'open',
        only_done: filterMode.value === 'done',
        limit: 200
      }),
      alertApi.summary()
    ])
    records.value = recordList
    summary.value = sum
  } catch (err) {
    console.error('告警加载失败', err)
  } finally {
    loading.value = false
  }
  await nextTick()
  renderCharts()
}

function renderCharts() {
  if (!zoneAlertChartRef.value || !severityChartRef.value) return
  if (!zoneAlertChart) zoneAlertChart = echarts.init(zoneAlertChartRef.value)
  if (!severityChart) severityChart = echarts.init(severityChartRef.value)

  const rows = zoneAlertRows.value
  if (rows.length) {
    zoneAlertChart.setOption(
      buildBarOption({
        // 编号太长会挤掉轴标签，这里用部位名称，跟表格里的说法一致
        labels: rows.map((item) => item.name || item.code),
        series: [{ name: '告警条数', data: rows.map((item) => item.count), color: '#FF7D00' }],
        yName: '条',
        horizontal: true
      })
    )
  }

  const critical = summary.value.critical || 0
  const warning = summary.value.warning || 0
  const acknowledged = summary.value.acknowledged || 0

  const metricCounter = {}
  records.value.forEach((item) => {
    metricCounter[item.metric] = (metricCounter[item.metric] || 0) + 1
  })
  const metricRows = Object.entries(metricCounter)
    .map(([metric, count]) => ({ label: metricNames[metric] || metric, count }))
    .sort((a, b) => b.count - a.count)

  severityChart.setOption(
    buildBarOption({
      labels: metricRows.length ? metricRows.map((item) => item.label) : ['暂无'],
      series: [
        {
          name: '告警条数',
          data: metricRows.length ? metricRows.map((item) => item.count) : [0],
          color: '#FF7D00'
        }
      ],
      yName: '条',
      horizontal: true
    })
  )
}

function handleResize() {
  zoneAlertChart?.resize()
  severityChart?.resize()
}

async function loadRules() {
  rules.value = await alertApi.rules()
}

async function handleAck(item) {
  try {
    await alertApi.acknowledge(item.id)
    message.success('已标记为处理完毕，该条不再计入未处理')
    await loadRecords()
  } catch (err) {
    message.error('操作失败')
  }
}

async function handleReopen(item) {
  try {
    await alertApi.reopen(item.id)
    message.success('已撤销处理，这条重新计入未处理')
    await loadRecords()
  } catch (err) {
    message.error('撤销失败')
  }
}

function gotoZone(item) {
  const zone = zones.value.find((entry) => entry.id === item.zone_id)
  if (!zone) {
    message.warning('该告警未关联监测部位')
    return
  }
  window.location.hash = `#/zone?code=${zone.code}`
}

function openRuleModal() {
  ruleForm.name = ''
  ruleForm.zone_id = zones.value.length ? zones.value[0].id : null
  ruleForm.metric = 'resistance_ohm'
  ruleForm.lower_limit = null
  ruleForm.upper_limit = null
  ruleForm.trigger_count = 3
  ruleForm.severity = 'warning'
  showRuleModal.value = true
}

async function handleSaveRule() {
  if (!ruleForm.name) {
    message.warning('请填写规则名称')
    return
  }
  if (ruleForm.lower_limit === null && ruleForm.upper_limit === null) {
    message.warning('上下限至少要填一个')
    return
  }
  saving.value = true
  try {
    await alertApi.createRule({ ...ruleForm })
    message.success('规则已创建')
    showRuleModal.value = false
    await loadRules()
  } catch (err) {
    message.error(err?.response?.data?.detail || '创建失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  zones.value = await structureApi.listZones()
  await loadRecords()
  await loadRules()
  await nextTick()
  renderCharts()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  zoneAlertChart?.dispose()
  severityChart?.dispose()
})
</script>

<style scoped>
.alerts-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.charts-grid {
  justify-content: center;
  max-width: 1400px;
  margin: 0 auto;
}

.text-danger {
  color: #f53f3f;
}

.text-warn {
  color: #ff7d00;
}
</style>
