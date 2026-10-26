<template>
  <div class="device-page">
    <!-- 1. 引导区 -->
    <n-card class="intro-card" :bordered="false">
      <div class="intro-content">
        <div class="intro-left">
          <div class="title-group">
            <div class="icon-wrapper">
              <n-icon size="32" color="#165DFF">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M15 7H9v2h6zm-2 4H9v2h4zm6-7H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V6a2 2 0 00-2-2zm0 16H5V6h14zM7 15h2v2H7zm0-4h2v2H7zm0-4h2v2H7zm4 8h2v2h-2zm0-4h2v2h-2zm0-4h2v2h-2zm4 8h2v2h-2zm0-4h2v2h-2zm0-4h2v2h-2z"/></svg>
              </n-icon>
            </div>
            <div>
              <h1 class="page-title">设备管理</h1>
            </div>
          </div>
        </div>
        <div class="intro-right">
          <n-button type="primary" size="medium" @click="openCreateModal">登记终端</n-button>
        </div>
      </div>
    </n-card>

    <!-- 2. 终端列表 + 结构树 -->
    <div class="charts-section">
      <n-grid :x-gap="24" :y-gap="24" cols="1 900:3" class="charts-grid">
        <n-grid-item :span="2">
          <n-card title="采集终端" :bordered="false" class="chart-card">
            <template #header-extra>
              <n-space :size="10" align="center">
                <n-tag type="success" size="small" round>在线 {{ onlineCount }}</n-tag>
                <n-tag type="default" size="small" round>共 {{ rows.length }} 台</n-tag>
              </n-space>
            </template>
            <n-data-table
              :columns="deviceColumns"
              :data="tableRows"
              :loading="loading"
              :bordered="false"
              size="large"
              :row-key="(row) => row.id"
              :max-height="440"
            />
          </n-card>
        </n-grid-item>

        <n-grid-item>
          <n-card title="工程与监测部位" :bordered="false" class="chart-card">
            <template #header-extra>
              <n-space :size="8" align="center">
                <n-tag type="info" size="small" round> {{ structures.length }} 个工程</n-tag>
                <n-button size="small" secondary @click="openStructureModal">新增工程</n-button>
              </n-space>
            </template>
            <div class="tree">
              <div v-for="structure in structures" :key="structure.id" class="tree-group">
                <div class="tree-node structure">
                  <span class="tree-dot"></span>
                  <div>
                    <div class="tree-name">{{ structure.name }}</div>
                    <div class="tree-meta">{{ structure.code }} · {{ structure.kind || '未分类' }}</div>
                  </div>
                  <n-space :size="4" class="tree-actions">
                    <n-button size="small" quaternary @click="openZoneModal(null, structure.id)">加部位</n-button>
                    <n-button size="small" quaternary @click="openStructureModal(structure)">编辑</n-button>
                  </n-space>
                </div>
                <div v-for="zone in zonesOf(structure.id)" :key="zone.id" class="tree-node zone">
                  <span class="tree-dot"></span>
                  <div>
                    <div class="tree-name">{{ zone.name }}</div>
                    <div class="tree-meta">
                      {{ zone.code }} · {{ zone.grid_size }}² 网格
                      <template v-if="zone.coating_thickness_mm">
                        · 涂层 {{ zone.coating_thickness_mm }}mm
                      </template>
                    </div>
                  </div>
                  <n-space :size="4" class="tree-actions">
                    <span class="tree-count">{{ deviceCount(zone.id) }} 个终端</span>
                    <n-button size="small" quaternary @click="openZoneModal(zone)">编辑</n-button>
                  </n-space>
                </div>
              </div>
              <n-empty v-if="!structures.length" description="还没有登记工程" />
            </div>
          </n-card>
        </n-grid-item>
      </n-grid>
    </div>

    <!-- 登记终端 -->
    <n-modal v-model:show="showModal" preset="card" :title="editingId ? '编辑终端' : '登记终端'" style="width: 460px">
      <n-form ref="formRef" :model="form" :rules="rules">
        <n-form-item path="device_id" label="终端编号">
          <n-input v-model:value="form.device_id" placeholder="例如 WSD-01" :disabled="!!editingId" />
        </n-form-item>
        <n-form-item path="name" label="名称">
          <n-input v-model:value="form.name" placeholder="例如 采集终端 01" />
        </n-form-item>
        <n-form-item path="zone_id" label="所属部位">
          <n-select v-model:value="form.zone_id" :options="zoneOptions" placeholder="选择部位" clearable />
        </n-form-item>
        <n-form-item path="model" label="型号">
          <n-input v-model:value="form.model" placeholder="例如 ESP32" />
        </n-form-item>
        <n-form-item path="location" label="位置描述">
          <n-input v-model:value="form.location" placeholder="例如 隧道右幅 K12+300 段" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="handleSave">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 登记工程 -->
    <n-modal
      v-model:show="showStructureModal"
      preset="card"
      :title="structureForm.id ? '编辑工程' : '登记工程'"
      style="width: 460px"
    >
      <n-form ref="structureFormRef" :model="structureForm" :rules="structureRules">
        <n-form-item path="code" label="工程编号">
          <n-input
            v-model:value="structureForm.code"
            placeholder="例如 GL-001"
            :disabled="!!structureForm.id"
          />
        </n-form-item>
        <n-form-item path="name" label="工程名称">
          <n-input v-model:value="structureForm.name" placeholder="例如 胶州湾海底隧道" />
        </n-form-item>
        <n-form-item path="kind" label="工程类型">
          <n-input v-model:value="structureForm.kind" placeholder="例如 海底隧道、斜拉桥、地铁车站" />
        </n-form-item>
        <n-form-item path="location" label="位置描述">
          <n-input v-model:value="structureForm.location" placeholder="例如 青岛市黄岛区" />
        </n-form-item>
        <n-form-item path="note" label="备注">
          <n-input
            v-model:value="structureForm.note"
            type="textarea"
            placeholder="例如 2026 年 10 月完成涂层布设"
            :rows="2"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showStructureModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="handleStructureSave">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 登记监测部位 -->
    <n-modal
      v-model:show="showZoneModal"
      preset="card"
      :title="zoneForm.code ? '编辑监测部位' : '登记监测部位'"
      style="width: 480px"
    >
      <n-form ref="zoneFormRef" :model="zoneForm" :rules="zoneRules">
        <n-form-item path="code" label="部位编号">
          <n-input
            v-model:value="zoneForm.code"
            placeholder="例如 GL-001-Z1"
            :disabled="!!zoneForm.code"
          />
        </n-form-item>
        <n-form-item path="name" label="部位名称">
          <n-input v-model:value="zoneForm.name" placeholder="例如 隧道右幅 K12+300 段" />
        </n-form-item>
        <n-form-item path="structure_id" label="所属工程">
          <n-select v-model:value="zoneForm.structure_id" :options="structureOptions" placeholder="选择工程" />
        </n-form-item>
        <n-form-item path="grid_size" label="成像网格规模">
          <n-input-number v-model:value="zoneForm.grid_size" :min="16" :max="256" :step="16" style="width: 100%" />
        </n-form-item>
        <n-form-item path="area_sqm" label="布设面积（m²）">
          <n-input-number v-model:value="zoneForm.area_sqm" :min="0" :step="0.5" style="width: 100%" />
        </n-form-item>
        <n-form-item path="coating_thickness_mm" label="涂层厚度（mm）">
          <n-input-number
            v-model:value="zoneForm.coating_thickness_mm"
            :min="0"
            :step="0.1"
            style="width: 100%"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showZoneModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="handleZoneSave">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { computed, h, onMounted, reactive, ref } from 'vue'
import { NButton, NIcon, NSpace, NTag, useDialog, useMessage } from 'naive-ui'
import { deviceApi, structureApi } from '../api'
import { formatShort } from '../utils/chart'

const message = useMessage()
const dialog = useDialog()

const rows = ref([])
const structures = ref([])
const zones = ref([])
const loading = ref(true)
const saving = ref(false)
const showModal = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const form = reactive({
  device_id: '',
  name: '',
  zone_id: null,
  model: '',
  location: ''
})

const rules = {
  device_id: { required: true, message: '请输入终端编号', trigger: ['blur', 'input'] },
  name: { required: true, message: '请输入名称', trigger: ['blur', 'input'] }
}

const showStructureModal = ref(false)
const structureFormRef = ref(null)
const structureForm = reactive({
  id: null,
  code: '',
  name: '',
  kind: '',
  location: '',
  note: ''
})

const structureRules = {
  code: { required: true, message: '请输入工程编号', trigger: ['blur', 'input'] },
  name: { required: true, message: '请输入工程名称', trigger: ['blur', 'input'] }
}

const showZoneModal = ref(false)
const zoneFormRef = ref(null)
const zoneForm = reactive({
  code: '',
  name: '',
  structure_id: null,
  grid_size: 64,
  area_sqm: null,
  coating_thickness_mm: null
})

const zoneRules = {
  code: { required: true, message: '请输入部位编号', trigger: ['blur', 'input'] },
  name: { required: true, message: '请输入部位名称', trigger: ['blur', 'input'] },
  structure_id: { required: true, message: '请选择所属工程', trigger: ['blur', 'change'] }
}

const structureOptions = computed(() =>
  structures.value.map((item) => ({ label: `${item.code} ${item.name}`, value: item.id }))
)

const deviceColumns = [
  { title: '终端编号', key: 'device_id', width: 110 },
  { title: '名称', key: 'name', width: 140 },
  { title: '所属部位', key: 'zone', width: 130 },
  { title: '型号', key: 'model', width: 100 },
  { title: '位置描述', key: 'location' },
  {
    title: '状态',
    key: 'status',
    width: 80,
    render: (row) =>
      h(
        NTag,
        { type: row.offline ? 'error' : 'success', size: 'small', round: true },
        { default: () => (row.offline ? '离线' : '在线') }
      )
  },
  { title: '最后上报', key: 'last_seen', width: 150 },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: (row) =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(NButton, { size: 'small', secondary: true, onClick: () => openEditModal(row) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => confirmRemove(row) }, { default: () => '删除' })
        ]
      })
  }
]

const zoneOptions = computed(() =>
  zones.value.map((item) => ({ label: `${item.code} ${item.name}`, value: item.id }))
)

const onlineCount = computed(() => rows.value.filter((item) => item.status !== 'offline').length)

const tableRows = computed(() =>
  rows.value.map((item) => ({
    ...item,
    zone: zones.value.find((zone) => zone.id === item.zone_id)?.code || '未归属',
    model: item.model || '—',
    location: item.location || '—',
    offline: item.status === 'offline',
    last_seen: item.last_seen_at ? formatShort(item.last_seen_at) : '从未上报'
  }))
)

function zonesOf(structureId) {
  return zones.value.filter((item) => item.structure_id === structureId)
}

function deviceCount(zoneId) {
  return rows.value.filter((item) => item.zone_id === zoneId).length
}

async function loadAll() {
  loading.value = true
  try {
    const [deviceList, structureList, zoneList] = await Promise.all([
      deviceApi.list(),
      structureApi.list(),
      structureApi.listZones()
    ])
    rows.value = deviceList
    structures.value = structureList
    zones.value = zoneList
  } catch (err) {
    message.error('设备列表加载失败')
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  editingId.value = null
  form.device_id = ''
  form.name = ''
  form.zone_id = zones.value.length ? zones.value[0].id : null
  form.model = 'ESP32'
  form.location = ''
  showModal.value = true
}

function openEditModal(item) {
  editingId.value = item.device_id
  form.device_id = item.device_id
  form.name = item.name
  form.zone_id = item.zone_id
  form.model = item.model || ''
  form.location = item.location || ''
  showModal.value = true
}

function openStructureModal(structure) {
  Object.assign(structureForm, {
    id: structure?.id ?? null,
    code: structure?.code ?? '',
    name: structure?.name ?? '',
    kind: structure?.kind ?? '',
    location: structure?.location ?? '',
    note: structure?.note ?? ''
  })
  showStructureModal.value = true
}

function openZoneModal(zone, structureId) {
  Object.assign(zoneForm, {
    code: zone?.code ?? '',
    name: zone?.name ?? '',
    structure_id: zone?.structure_id ?? structureId ?? null,
    grid_size: zone?.grid_size ?? 64,
    area_sqm: zone?.area_sqm ?? null,
    coating_thickness_mm: zone?.coating_thickness_mm ?? null
  })
  showZoneModal.value = true
}

async function handleStructureSave() {
  try {
    await structureFormRef.value?.validate()
  } catch (err) {
    return
  }
  saving.value = true
  try {
    const payload = {
      name: structureForm.name,
      kind: structureForm.kind || null,
      location: structureForm.location || null,
      note: structureForm.note || null
    }
    if (structureForm.id) {
      await structureApi.update(structureForm.code, payload)
      message.success('工程信息已更新')
    } else {
      await structureApi.create({ code: structureForm.code, ...payload })
      message.success('工程已登记')
    }
    showStructureModal.value = false
    await loadAll()
  } catch (err) {
    message.error(err?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleZoneSave() {
  try {
    await zoneFormRef.value?.validate()
  } catch (err) {
    return
  }
  saving.value = true
  try {
    const payload = {
      name: zoneForm.name,
      structure_id: zoneForm.structure_id,
      grid_size: zoneForm.grid_size,
      area_sqm: zoneForm.area_sqm,
      coating_thickness_mm: zoneForm.coating_thickness_mm
    }
    if (zoneForm.code) {
      await structureApi.updateZone(zoneForm.code, payload)
      message.success('部位信息已更新')
    } else {
      await structureApi.createZone({ code: zoneForm.code, ...payload })
      message.success('部位已登记')
    }
    showZoneModal.value = false
    await loadAll()
  } catch (err) {
    message.error(err?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleSave() {
  try {
    await formRef.value?.validate()
  } catch (err) {
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await deviceApi.update(editingId.value, {
        name: form.name,
        zone_id: form.zone_id,
        model: form.model || null,
        location: form.location || null
      })
      message.success('终端信息已更新')
    } else {
      await deviceApi.create({
        device_id: form.device_id,
        name: form.name,
        zone_id: form.zone_id,
        model: form.model || null,
        location: form.location || null
      })
      message.success('终端登记成功')
    }
    showModal.value = false
    await loadAll()
  } catch (err) {
    message.error(err?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function confirmRemove(item) {
  dialog.warning({
    title: '删除终端',
    content: `确认删除 ${item.device_id}？该终端的历史采集记录会一并删除。`,
    positiveText: '确认删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deviceApi.remove(item.device_id)
        message.success('终端已删除')
        await loadAll()
      } catch (err) {
        message.error('删除失败')
      }
    }
  })
}

onMounted(loadAll)
</script>

<style scoped>
.device-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.charts-grid {
  justify-content: center;
  max-width: 1400px;
  margin: 0 auto;
}

/* 结构树：靠缩进和竖线表达层级，不用嵌套卡片 */
.tree {
  padding: 4px 0;
}

.tree-group {
  padding-bottom: 8px;
}

.tree-node {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 0;
  position: relative;
}

.tree-node.zone {
  padding-left: 28px;
}

.tree-node.zone::before {
  content: "";
  position: absolute;
  left: 20px;
  top: 0;
  bottom: 0;
  width: 1px;
  background: #eef0f3;
}

.tree-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #c9cdd4;
  margin-top: 6px;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.tree-node.structure .tree-dot {
  background: #1d2129;
}

.tree-name {
  font-size: 14px;
  color: #1d2129;
  font-weight: 500;
}

.tree-node.zone .tree-name {
  font-weight: 400;
}

.tree-meta {
  font-size: var(--text-sm);
  color: #86909c;
  margin-top: 1px;
}

.tree-count {
  margin-left: auto;
  font-size: var(--text-sm);
  color: #86909c;
  background: #f2f3f5;
  padding: 1px 8px;
  border-radius: 8px;
  white-space: nowrap;
}

/* 树节点右侧的操作区，悬停才显出来，避免平时太杂 */
.tree-actions {
  margin-left: auto;
  align-items: center;
  opacity: 0;
  transition: opacity 150ms ease;
}

.tree-node:hover .tree-actions {
  opacity: 1;
}

.tree-node:hover .tree-count {
  opacity: 0;
}
</style>
