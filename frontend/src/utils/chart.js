import * as echarts from 'echarts'

// 全站统一的图表基调：网格线浅淡，坐标轴纤细，框架退后让数据成为主角
export const chartTheme = {
  textStyle: {
    fontFamily: 'Inter, "PingFang SC", "Microsoft YaHei", sans-serif',
    color: '#4e5969'
  },
  gridLine: {
    color: '#f2f3f5',
    width: 1
  },
  axisLabel: {
    color: '#86909c',
    fontSize: 13
  },
  axisLine: {
    lineStyle: { color: '#e5e6eb' }
  },
  splitLine: {
    lineStyle: { color: '#f2f3f5', type: 'solid' }
  },
  tooltip: {
    backgroundColor: 'rgba(15, 23, 42, 0.92)',
    borderWidth: 0,
    textStyle: { color: '#f2f3f5', fontSize: 13 },
    axisPointer: {
      lineStyle: { color: '#86909c', width: 1, type: 'dashed' }
    }
  }
}

// 序列色与 CSS 变量里的 --series-* 保持一致
export const seriesColors = {
  resistance: '#165dff',
  impedance: '#00b42a',
  phase: '#ff7d00',
  strain: '#7c3aed',
  auxiliary: '#ff9a2e'
}

// 时间序列折线配置，阈值线用虚线画出
export function buildLineOption({
  times = [],
  series = [],
  yName = '',
  thresholds = [],
  smooth = true
}) {
  const chartSeries = series.map((item, index) => ({
    name: item.name,
    type: 'line',
    smooth,
    showSymbol: false,
    data: item.data,
    lineStyle: { width: 1.8, color: item.color || seriesColors[index] },
    // 图例图标会取这里的颜色，不设的话 ECharts 用默认调色板，跟线对不上
    itemStyle: { color: item.color || seriesColors[index] },
    areaStyle: item.area
      ? { color: hexToRgba(item.color || seriesColors[index], 0.08) }
      : undefined,
    emphasis: { focus: 'series' }
  }))

  thresholds.forEach((item) => {
    chartSeries.push({
      name: item.name,
      type: 'line',
      data: times.map(() => item.value),
      lineStyle: { width: 1, type: 'dashed', color: item.color || '#f53f3f' },
      itemStyle: { color: item.color || '#f53f3f' },
      silent: true,
      tooltip: { show: false },
      markLine: {
        silent: true,
        symbol: 'none',
        label: {
          formatter: item.name,
          color: item.color || '#f53f3f',
          fontSize: 10,
          position: 'insideEndTop'
        },
        lineStyle: { color: item.color || '#f53f3f', type: 'dashed', width: 1 },
        data: [{ yAxis: item.value }]
      }
    })
  })

  return {
    textStyle: chartTheme.textStyle,
    tooltip: {
      ...chartTheme.tooltip,
      trigger: 'axis',
      axisPointer: { type: 'line', ...chartTheme.tooltip.axisPointer }
    },
    legend: {
      top: 0,
      right: 0,
      icon: 'roundRect',
      itemWidth: 10,
      itemHeight: 3,
      itemGap: 16,
      textStyle: { color: '#86909c', fontSize: 12 }
    },
    grid: { left: 52, right: 18, top: 28, bottom: 26, containLabel: false },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: times,
      axisLine: chartTheme.axisLine,
      axisTick: { show: false },
      axisLabel: chartTheme.axisLabel
    },
    yAxis: {
      type: 'value',
      name: yName,
      nameTextStyle: { color: '#86909c', fontSize: 12, align: 'right' },
      scale: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: chartTheme.axisLabel,
      splitLine: chartTheme.splitLine
    },
    series: chartSeries
  }
}

// 柱状对比配置，用于并列关系的数据
export function buildBarOption({
  labels = [],
  series = [],
  yName = '',
  horizontal = false
}) {
  const categoryAxis = {
    type: 'category',
    data: labels,
    axisLine: chartTheme.axisLine,
    axisTick: { show: false },
    axisLabel: chartTheme.axisLabel
  }
  const valueAxis = {
    type: 'value',
    name: yName,
    nameTextStyle: { color: '#86909c', fontSize: 12 },
    // 柱子要能从 0 起算，不然小数值那根柱子是零长度，看着像没数据
    min: 0,
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: chartTheme.axisLabel,
    splitLine: chartTheme.splitLine
  }

  return {
    textStyle: chartTheme.textStyle,
    tooltip: {
      ...chartTheme.tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow', ...chartTheme.tooltip.axisPointer }
    },
    legend: {
      top: 0,
      right: 0,
      icon: 'roundRect',
      itemWidth: 10,
      itemHeight: 3,
      itemGap: 16,
      textStyle: { color: '#86909c', fontSize: 12 }
    },
    grid: horizontal
      ? { left: 8, right: 44, top: 28, bottom: 24, containLabel: true }
      : { left: 56, right: 18, top: 28, bottom: 24, containLabel: false },
    xAxis: horizontal ? valueAxis : categoryAxis,
    yAxis: horizontal ? categoryAxis : valueAxis,
    series: series.map((item, index) => ({
      name: item.name,
      type: 'bar',
      barMaxWidth: 22,
      data: item.data,
      itemStyle: { color: item.color || seriesColors[index], borderRadius: horizontal ? [0, 3, 3, 0] : [3, 3, 0, 0] },
      label: {
        show: true,
        position: horizontal ? 'right' : 'top',
        color: '#86909c',
        fontSize: 12
      }
    }))
  }
}

// 电阻率热力图配置，异常区域靠色带凸显
export function buildHeatmapOption(matrix, colorScale) {
  const data = []
  let min = Infinity
  let max = -Infinity
  matrix.forEach((row, y) => {
    row.forEach((value, x) => {
      data.push([x, y, value])
      if (value < min) min = value
      if (value > max) max = value
    })
  })

  return {
    textStyle: chartTheme.textStyle,
    tooltip: {
      ...chartTheme.tooltip,
      formatter: (params) => {
        const [x, y, value] = params.data
        return `位置 (${x}, ${y})<br/>电阻率 ${value.toFixed(2)} Ω·m`
      }
    },
    grid: { left: 46, right: 58, top: 12, bottom: 40 },
    xAxis: {
      type: 'category',
      data: matrix[0].map((_, i) => i),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
      splitArea: { show: false }
    },
    yAxis: {
      type: 'category',
      data: matrix.map((_, i) => i),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
      splitArea: { show: false }
    },
    visualMap: {
      min: min,
      max: max,
      calculable: true,
      orient: 'vertical',
      right: 8,
      top: 'center',
      itemHeight: 140,
      itemWidth: 10,
      text: ['高', '低'],
      textStyle: { color: '#86909c', fontSize: 12 },
      inRange: { color: colorScale || ['#e8f3ff', '#93c5fd', '#3b82f6', '#1e40af', '#ff7d00', '#f53f3f'] }
    },
    series: [
      {
        name: '电阻率',
        type: 'heatmap',
        data,
        progressive: 2000,
        emphasis: {
          itemStyle: {
            borderColor: '#1d2129',
            borderWidth: 1
          }
        }
      }
    ]
  }
}

// 十六进制颜色转带透明度的 rgba
export function hexToRgba(hex, alpha) {
  const value = hex.replace('#', '')
  const num = parseInt(value, 16)
  const r = (num >> 16) & 255
  const g = (num >> 8) & 255
  const b = num & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

// ISO 时间串压成时分秒
export function formatClock(value) {
  if (!value) return ''
  return value.replace('T', ' ').slice(5, 19)
}

// ISO 时间串压成月日时分
export function formatShort(value) {
  if (!value) return ''
  return value.replace('T', ' ').slice(5, 16)
}

export { echarts }
