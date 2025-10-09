<template>
  <n-card class="stock-card mobile-card mobile-shadow mobile-stock-card" :bordered="false" :class="{ 'is-analyzing': isAnalyzing }" :data-stock-code="stock.code">
    <div class="card-header mobile-card-header">
      <div class="header-main">
        <div class="header-left">
          <div class="stock-info">
            <div class="stock-code">{{ stock.code }}</div>
            <div class="stock-name" v-if="stock.name">{{ stock.name }}</div>
          </div>
          <div class="stock-price-info" v-if="stock.price !== undefined">
            <div class="stock-price">
              <span class="label">当前价格:</span>
              <span class="value">{{ stock.price.toFixed(2) }}</span>
            </div>
            <div class="stock-change" :class="{ 
              'up': calculatedChangePercent && calculatedChangePercent > 0,
              'down': calculatedChangePercent && calculatedChangePercent < 0
            }">
              <span class="label">涨跌幅:</span>
              <span class="value">{{ formatChangePercent(calculatedChangePercent) }}</span>
            </div>
          </div>
        </div>
        <div class="header-right">
          <n-button 
            size="small" 
            v-if="stock.analysisStatus === 'completed'"
            @click="copyStockAnalysis"
            class="copy-button"
            type="primary"
            secondary
            round
          >
            <template #icon>
              <n-icon><CopyOutline /></n-icon>
            </template>
            复制结果
          </n-button>
        </div>
      </div>
      <div class="analysis-status" v-if="stock.analysisStatus !== 'completed'">
        <n-tag 
          :type="getStatusType" 
          size="small"
          round
          :bordered="false"
        >
          <template #icon>
            <n-icon>
              <component :is="getStatusIcon" />
            </n-icon>
          </template>
          {{ getStatusText }}
        </n-tag>
      </div>
      
      <!-- 操作按钮区域 - 仅在分析完成时显示 -->
      <div class="action-buttons" v-if="stock.analysisStatus === 'completed'">
        <n-space align="center" justify="space-between">
          <n-space>
            <n-button 
              size="small" 
              type="primary" 
              secondary 
              @click="handleFavorite"
              :loading="favoriting"
            >
              <template #icon>
                <n-icon><HeartOutline /></n-icon>
              </template>
              {{ isFavorite ? '取消收藏' : '收藏' }}
            </n-button>
            <n-button 
              size="small" 
              type="info" 
              secondary 
              @click="handleShare"
              :loading="sharing"
            >
              <template #icon>
                <n-icon><ShareOutline /></n-icon>
              </template>
              分享
            </n-button>
            <n-button 
              size="small" 
              type="warning" 
              secondary 
              @click="handleExportImage"
              :loading="exporting"
            >
              <template #icon>
                <n-icon><ImageOutline /></n-icon>
              </template>
              保存图片
            </n-button>
            <n-button 
              size="small" 
              type="success" 
              secondary 
              @click="handleStartConversation"
            >
              <template #icon>
                <n-icon><ChatbubbleEllipsesOutline /></n-icon>
              </template>
              对话
            </n-button>
          </n-space>
        </n-space>
      </div>
    </div>
    
    <div class="stock-summary" v-if="stock.score !== undefined || stock.recommendation">
      <div class="summary-item score-item" v-if="stock.score !== undefined">
        <div class="summary-value" :class="getScoreClass(stock.score)">{{ stock.score }}</div>
        <div class="summary-label">评分</div>
      </div>
      <div class="summary-item recommendation-item" v-if="stock.recommendation">
        <div class="summary-value recommendation">{{ stock.recommendation }}</div>
        <div class="summary-label">推荐</div>
      </div>
    </div>
    
    <div class="analysis-date" v-if="stock.analysis_date">
      <n-tag type="info" size="small">
        <template #icon>
          <n-icon><CalendarOutline /></n-icon>
        </template>
        分析日期: {{ formatDate(stock.analysis_date) }}
      </n-tag>
    </div>
    
    <div class="technical-indicators" v-if="hasAnyTechnicalIndicator">
      <n-divider dashed style="margin: 12px 0 8px 0">技术指标</n-divider>
      
      <div class="indicators-grid">
        <div class="indicator-item" v-if="stock.rsi !== undefined">
          <div class="indicator-value" :class="getRsiClass(stock.rsi)">{{ stock.rsi.toFixed(2) }}</div>
          <div class="indicator-label">RSI</div>
        </div>
        
        <div class="indicator-item" v-if="stock.price_change !== undefined">
          <div class="indicator-value" :class="{ 
            'up': stock.price_change > 0,
            'down': stock.price_change < 0
          }">{{ formatPriceChange(stock.price_change) }}</div>
          <div class="indicator-label">涨跌额</div>
        </div>
        
        <div class="indicator-item" v-if="stock.ma_trend">
          <div class="indicator-value" :class="getTrendClass(stock.ma_trend)">
            {{ getChineseTrend(stock.ma_trend) }}
          </div>
          <div class="indicator-label">均线趋势</div>
        </div>
        
        <div class="indicator-item" v-if="stock.macd_signal">
          <div class="indicator-value" :class="getSignalClass(stock.macd_signal)">
            {{ getChineseSignal(stock.macd_signal) }}
          </div>
          <div class="indicator-label">MACD信号</div>
        </div>
        
        <div class="indicator-item" v-if="stock.volume_status">
          <div class="indicator-value" :class="getVolumeStatusClass(stock.volume_status)">
            {{ getChineseVolumeStatus(stock.volume_status) }}
          </div>
          <div class="indicator-label">成交量</div>
        </div>
      </div>
    </div>
    
    <!-- 图表放在AI分析上面 -->
    <div
      v-if="stock.chart_data && stock.chart_data.length"
      class="chart-container"
      :data-chart-option="JSON.stringify(chartOption)"
    >
      <div class="chart-header">
        <n-divider dashed style="margin: 12px 0 8px 0">K线图</n-divider>
        <div class="chart-controls">
          <n-switch
            v-model:value="showBollinger"
            size="small"
          >
            <template #checked>
              BOLL
            </template>
            <template #unchecked>
              BOLL
            </template>
          </n-switch>
        </div>
      </div>
      <div ref="chartContainer" class="chart">
        <VChart
          ref="chartRef"
          :option="chartOption"
          :autoresize="true"
          style="height: 100%; width: 100%;"
        />
      </div>
    </div>

    <n-divider />
    
    <div class="card-content">
      <template v-if="stock.analysisStatus === 'error'">
        <div class="error-status">
          <n-icon :component="AlertCircleIcon" class="error-icon" />
          <span>{{ stock.error || '未知错误' }}</span>
        </div>
      </template>
      
      <template v-else-if="stock.analysisStatus === 'analyzing'">
        <div class="analysis-result analysis-streaming" ref="analysisResultRef">
          <template v-for="block in parsedAnalysisBlocks" :key="block.key">
            <!-- 已完成的角色：可折叠 -->
            <details 
              v-if="block.type === 'role-completed'"
              class="analysis-fold"
              :open="block.isOpen"
              @toggle="toggleRoleOpen(block.roleName!)"
            >
              <summary>角色 - {{ block.roleName }}</summary>
              <div v-html="getHighlightedContent(block)"></div>
            </details>
            
            <!-- 正在分析的角色：5行滚动预览 -->
            <div 
              v-else-if="block.type === 'role-analyzing'"
              class="analysis-preview-box"
              :data-role="block.roleName"
            >
              <div class="preview-box-header">角色 - {{ block.roleName }}</div>
              <div class="preview-box-content" v-html="getHighlightedContent(block)"></div>
            </div>
            
            <!-- 综合决策 -->
            <div v-else-if="block.type === 'final'" v-html="getHighlightedContent(block)"></div>
            
            <!-- 其他内容 -->
            <div v-else v-html="getHighlightedContent(block)"></div>
          </template>
        </div>
      </template>
      
      <template v-else-if="stock.analysisStatus === 'completed'">
        <div class="analysis-result analysis-completed">
          <template v-for="block in parsedAnalysisBlocks" :key="block.key">
            <!-- 已完成的角色：可折叠 -->
            <details 
              v-if="block.type === 'role-completed'"
              class="analysis-fold"
              :open="block.isOpen"
              @toggle="toggleRoleOpen(block.roleName!)"
            >
              <summary>角色 - {{ block.roleName }}</summary>
              <div v-html="getHighlightedContent(block)"></div>
            </details>
            
            <!-- 综合决策 -->
            <div v-else-if="block.type === 'final'" v-html="getHighlightedContent(block)"></div>
            
            <!-- 其他内容 -->
            <div v-else v-html="getHighlightedContent(block)"></div>
          </template>
        </div>
      </template>
    </div>

  </n-card>
</template>

<script setup lang="ts">
import { computed, watch, ref, nextTick, onMounted, onBeforeUnmount } from 'vue';
import { NCard, NDivider, NIcon, NTag, NButton, NSwitch, useMessage } from 'naive-ui';
import { 
  AlertCircleOutline as AlertCircleIcon,
  CalendarOutline,
  CopyOutline,
  HourglassOutline,
  ReloadOutline,
  HeartOutline,
  ShareOutline,
  ChatbubbleEllipsesOutline,
  ImageOutline
} from '@vicons/ionicons5';
import html2canvas from 'html2canvas';
import { parseMarkdown } from '@/utils';
import type { StockInfo } from '@/types';
// 导入原生ECharts
import * as echarts from 'echarts';
import { useResizeObserver } from '@vueuse/core';
import VChart from 'vue-echarts';

const props = defineProps<{
  stock: StockInfo;
}>();

const emit = defineEmits<{
  'start-conversation': [stock: StockInfo];
}>();





// 状态变量
const favoriting = ref(false);
const sharing = ref(false);
const exporting = ref(false);
const isFavorite = ref(false);

// 图表相关变量
const chartContainer = ref<HTMLElement | null>(null);
const chartInstance = ref<echarts.ECharts | null>(null);
const chartOption = ref<echarts.EChartsOption>({});
const showBollinger = ref(false);
const chartInitialized = ref(false);
const lastConfigHash = ref('');
const chartRef = ref<InstanceType<typeof VChart> | null>(null);

const isAnalyzing = computed(() => {
  return props.stock.analysisStatus === 'analyzing';
});

const generateChartOption = () => {
  const chartData: any[] = props.stock.chart_data || [];
  if (chartData.length === 0) return {};
  
  // 验证数据完整性
  if (chartData.length < 2) {
    console.warn('[StockCard] Insufficient data points for chart:', chartData.length);
    return {};
  }
  
  // 验证数据格式
  const isValidData = chartData.every(item => 
    item && 
    typeof item === 'object' && 
    (item.date || item.Date) &&
    (item.open !== undefined || item.Open !== undefined) &&
    (item.close !== undefined || item.Close !== undefined) &&
    (item.high !== undefined || item.High !== undefined) &&
    (item.low !== undefined || item.Low !== undefined)
  );
  
  if (!isValidData) {
    console.warn('Invalid chart data format detected');
    return {};
  }
  
  // The data is an array of objects, e.g., {date: '...', open: ..., close: ...}
  const dates = chartData.map(item => item.date);
  const klineData = chartData.map(item => [
    item.Open || item.open, 
    item.Close || item.close, 
    item.Low || item.low, 
    item.High || item.high
  ]);
  const volumes = chartData.map((item, index) => [
    index, 
    item.Volume || item.volume, 
    (item.Close || item.close) > (item.Open || item.open) ? 1 : -1
  ]);

  const calculateMA = (dayCount: number) => {
    const result = [];
    const closePrices = klineData.map(d => d[1] ?? 0); // Close price is at index 1, default to 0 if undefined

    for (let i = 0, len = closePrices.length; i < len; i++) {
      if (i < dayCount - 1) {
        result.push(null);
        continue;
      }
      let sum = 0;
      let validCount = 0;
      for (let j = 0; j < dayCount; j++) {
        const price = closePrices[i - j];
        if (price !== null && !isNaN(price)) {
          sum += price;
          validCount++;
        }
      }
      if (validCount > 0) {
        result.push(parseFloat((sum / validCount).toFixed(2)));
      } else {
        result.push(null);
      }
    }
    return result;
  };

  const ma5 = calculateMA(5);
  const ma10 = calculateMA(10);
  const ma20 = calculateMA(20);

  // 提取布林带数据
  const bollMiddle = chartData.map(item => item.BB_Middle || null);
  const bollUpper = chartData.map(item => item.BB_Upper || null);
  const bollLower = chartData.map(item => item.BB_Lower || null);

  // 验证关键数据数组长度一致性
  const expectedLength = chartData.length;
  const dataArrays = [dates, klineData, ma5, ma10, ma20, volumes];
  const invalidArrays = dataArrays.filter(arr => arr.length !== expectedLength);
  
  if (invalidArrays.length > 0) {
    console.warn('[StockCard] Data length mismatch detected:', {
      expected: expectedLength,
      dates: dates.length,
      kline: klineData.length,
      ma5: ma5.length,
      ma10: ma10.length,
      ma20: ma20.length,
      volumes: volumes.length
    });
  }

  // 基础图例数据
  const legendData = ['日K', 'MA5', 'MA10', 'MA20'];
  if (showBollinger.value) {
    legendData.push('BOLL中轨', 'BOLL上轨', 'BOLL下轨');
  }

  // 基础系列数据
  const series: any[] = [
    {
      name: '日K',
      type: 'candlestick',
      data: klineData,
      xAxisIndex: 0,
      yAxisIndex: 0,
      itemStyle: {
          color: '#ec0000',
          color0: '#00da3c',
          borderColor: '#8A0000',
          borderColor0: '#008F28'
      },
      markPoint: {
        label: {
          formatter: function (param: any) {
            return param != null ? Math.round(param.value) + '' : '';
          }
        },
        data: [
          {
            name: 'max',
            type: 'max',
            valueDim: 'highest'
          },
          {
            name: 'min',
            type: 'min',
            valueDim: 'lowest'
          }
        ]
      }
    },
    {
      name: 'MA5',
      type: 'line',
      data: ma5,
      xAxisIndex: 0,
      yAxisIndex: 0,
      coordinateSystem: 'cartesian2d',
      smooth: true,
      lineStyle: {
        opacity: 0.5
      }
    },
    {
      name: 'MA10',
      type: 'line',
      data: ma10,
      xAxisIndex: 0,
      yAxisIndex: 0,
      coordinateSystem: 'cartesian2d',
      smooth: true,
      lineStyle: {
        opacity: 0.5
      }
    },
    {
      name: 'MA20',
      type: 'line',
      data: ma20,
      xAxisIndex: 0,
      yAxisIndex: 0,
      coordinateSystem: 'cartesian2d',
      smooth: true,
      lineStyle: {
        opacity: 0.5
      }
    },
    {
      name: 'Volume',
      type: 'bar',
      xAxisIndex: 1,
      yAxisIndex: 1,
      coordinateSystem: 'cartesian2d',
      data: volumes.map(item => item[1]),
      itemStyle: {
        color: ({ dataIndex }: { dataIndex: number }) => (volumes[dataIndex][2] === 1 ? '#ec0000' : '#00da3c')
      }
    }
  ];

  // 如果显示布林带，添加布林带系列
  if (showBollinger.value) {
    series.push(
      {
        name: 'BOLL中轨',
        type: 'line',
        data: bollMiddle,
        xAxisIndex: 0,
        yAxisIndex: 0,
        coordinateSystem: 'cartesian2d',
        smooth: true,
        lineStyle: {
          color: '#FFA500',
          width: 1,
          opacity: 0.8
        }
      },
      {
        name: 'BOLL上轨',
        type: 'line',
        data: bollUpper,
        xAxisIndex: 0,
        yAxisIndex: 0,
        coordinateSystem: 'cartesian2d',
        smooth: true,
        lineStyle: {
          color: '#FF6B6B',
          width: 1,
          opacity: 0.6
        }
      },
      {
        name: 'BOLL下轨',
        type: 'line',
        data: bollLower,
        xAxisIndex: 0,
        yAxisIndex: 0,
        coordinateSystem: 'cartesian2d',
        smooth: true,
        lineStyle: {
          color: '#4ECDC4',
          width: 1,
          opacity: 0.6
        }
      }
    );
  }

  return {
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: legendData
    },
    grid: [
      {
        left: '10%',
        right: '8%',
        height: '50%'
      },
      {
        left: '10%',
        right: '8%',
        top: '65%',
        height: '16%'
      }
    ],
    xAxis: [
      {
        type: 'category' as const,
        data: dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        gridIndex: 0
      },
      {
        type: 'category' as const,
        gridIndex: 1,
        data: dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false }
      }
    ],
    yAxis: [
      {
        type: 'value' as const,
        scale: true,
        gridIndex: 0,
        splitArea: {
          show: true
        }
      },
      {
        type: 'value' as const,
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false }
      }
    ],
    dataZoom: [
      {
        type: 'slider' as const,
        show: true,
        xAxisIndex: [0, 1],
        start: 0,
        end: 100,
        top: '85%',
        height: 20,
        throttle: 300
      }
    ],
    series: series
  } as echarts.EChartsOption;
};

// 生成简单的配置哈希来判断是否需要更新
const getConfigHash = () => {
  const data = props.stock.chart_data;
  if (!data || data.length === 0) return '';
  return `${data.length}-${showBollinger.value}`;
};

// 更新图表
const updateChart = async () => {
  if (!props.stock.chart_data || props.stock.chart_data.length === 0) return;
  
  const currentHash = getConfigHash();
  
  // 只有在配置真正改变时才重新生成图表
  if (currentHash !== lastConfigHash.value) {
    // 生成新配置
    const newOption = generateChartOption();
    if (!newOption || Object.keys(newOption).length === 0) {
      console.warn('Failed to generate chart option');
      return;
    }
    
    chartOption.value = newOption;
    lastConfigHash.value = currentHash;
  }
};

// 监听图表数据变化
watch(() => props.stock.chart_data, (newChartData) => {
  if (newChartData && newChartData.length > 0) {
    // 如果图表未初始化，则表示这是第一次获取数据。
    const needsInit = !chartInitialized.value;
    updateChart();
    if (needsInit) {
      chartInitialized.value = true;
    }
  }
}, { deep: false });

// 监听布林带显示状态变化
watch(() => showBollinger.value, () => {
  if (props.stock.chart_data && props.stock.chart_data.length > 0) {
    updateChart();
  }
});

// 添加组件挂载后的图表初始化
onMounted(async () => {
  await nextTick();
  // 如果组件挂载时数据已存在，则绘制图表
  if (props.stock.chart_data && props.stock.chart_data.length > 0) {
    updateChart();
  }
  
  // 添加窗口resize监听（可选，因为autoresize已启用）
  useResizeObserver(chartContainer, () => {
    if (chartRef.value) {
      chartRef.value.resize();
    }
  });
});

// 清理
onBeforeUnmount(() => {
  // 无需手动dispose，vue-echarts会处理
});

const lastAnalysisLength = ref(0);
const lastAnalysisText = ref('');

// 定义分析块类型
interface AnalysisBlock {
  type: 'role-completed' | 'role-analyzing' | 'final' | 'other';
  roleName?: string;
  content: string;
  key: string;
  isOpen?: boolean; // 用于 details 的状态
}

// 维护每个role的折叠状态（使用Map，key是roleName）
const roleOpenStates = ref<Map<string, boolean>>(new Map());

// 监听分析内容变化并自动滚动
watch(() => props.stock.analysis, (newVal, oldVal) => {
  if (newVal && props.stock.analysisStatus === 'analyzing') {
    lastAnalysisLength.value = newVal.length;
    lastAnalysisText.value = newVal;
    
    // 如果内容增加了，自动滚动预览框到底部
    if (oldVal && newVal.length > oldVal.length) {
      nextTick(() => {
        // 找到当前正在分析的预览框并滚动到底部
        const previewBoxes = document.querySelectorAll('.analysis-preview-box .preview-box-content');
        if (previewBoxes.length > 0) {
          const lastBox = previewBoxes[previewBoxes.length - 1] as HTMLElement;
          lastBox.scrollTop = lastBox.scrollHeight;
        }
      });
    }
  }
}, { immediate: true });

// 分析内容的解析 - 返回结构化数据
const parsedAnalysisBlocks = computed<AnalysisBlock[]>(() => {
  if (!props.stock.analysis) return [];
  
  const content = props.stock.analysis;
  const blocks: AnalysisBlock[] = [];
  let lastIndex = 0;
  
  // 正则：匹配完整的 <analysis>...</analysis> 块
  const completeAnalysisRegex = /<analysis>(.*?)<\/analysis>/gs;
  
  // 处理所有完整的 analysis 块（已完成的角色）
  const matches = [...content.matchAll(completeAnalysisRegex)];
  
  for (const match of matches) {
    // 添加匹配前的内容
    const beforeContent = content.substring(lastIndex, match.index);
    if (beforeContent.trim()) {
      blocks.push({
        type: 'other',
        content: parseMarkdown(beforeContent),
        key: `other-${blocks.length}`
      });
    }
    
    const analysisContent = match[1];
    // 提取角色名
    const roleMatch = analysisContent.match(/^[\s\n]*###\s*([^\n]+)/);
    const roleName = roleMatch ? roleMatch[1].trim() : '分析过程';
    
    // 检查该role是否已有保存的状态，如果没有则默认折叠
    if (!roleOpenStates.value.has(roleName)) {
      roleOpenStates.value.set(roleName, false);
    }
    
    // 已完成的角色
    blocks.push({
      type: 'role-completed',
      roleName,
      content: parseMarkdown(analysisContent),
      key: `role-${roleName}`,
      isOpen: roleOpenStates.value.get(roleName)
    });
    
    lastIndex = match.index! + match[0].length;
  }
  
  // 处理剩余内容（可能包含未完成的analysis块）
  const remaining = content.substring(lastIndex);
  
  // 检查剩余内容中是否有未闭合的 <analysis> 标签
  const lastAnalysisIndex = remaining.lastIndexOf('<analysis>');
  const lastAnalysisCloseIndex = remaining.lastIndexOf('</analysis>');
  
  // 如果最后一个<analysis>在最后一个</analysis>之后，说明有未闭合的块
  if (lastAnalysisIndex !== -1 && lastAnalysisIndex > lastAnalysisCloseIndex) {
    // 添加 <analysis> 标签前的所有内容
    const beforeAnalysis = remaining.substring(0, lastAnalysisIndex);
    if (beforeAnalysis.trim()) {
      blocks.push({
        type: 'other',
        content: parseMarkdown(beforeAnalysis),
        key: `other-${blocks.length}`
      });
    }
    
    // 提取未闭合的analysis内容
    const analysisContent = remaining.substring(lastAnalysisIndex + '<analysis>'.length);
    
    // 提取角色名
    const roleMatch = analysisContent.match(/^[\s\n]*###\s*([^\n]+)/);
    const roleName = roleMatch ? roleMatch[1].trim() : '分析中...';
    
    // 正在分析的角色 - 也解析 Markdown
    blocks.push({
      type: 'role-analyzing',
      roleName,
      content: parseMarkdown(analysisContent),
      key: `analyzing-${roleName}`
    });
  } else {
    // 没有未闭合的analysis，处理剩余内容
    // 检查是否有 final 块
    const finalRegex = /<final>(.*?)<\/final>/gs;
    const finalMatch = remaining.match(finalRegex);
    
    if (finalMatch) {
      let remainingContent = remaining;
      const finalMatches = [...remaining.matchAll(finalRegex)];
      let finalLastIndex = 0;
      
      for (const fMatch of finalMatches) {
        const beforeFinal = remainingContent.substring(finalLastIndex, fMatch.index);
        if (beforeFinal.trim()) {
          blocks.push({
            type: 'other',
            content: parseMarkdown(beforeFinal),
            key: `other-${blocks.length}`
          });
        }
        
        blocks.push({
          type: 'final',
          content: parseMarkdown(fMatch[1]),
          key: `final-${blocks.length}`
        });
        
        finalLastIndex = fMatch.index! + fMatch[0].length;
      }
      
      const afterFinal = remainingContent.substring(finalLastIndex);
      if (afterFinal.trim()) {
        blocks.push({
          type: 'other',
          content: parseMarkdown(afterFinal),
          key: `other-${blocks.length}`
        });
      }
    } else if (remaining.trim()) {
      blocks.push({
        type: 'other',
        content: parseMarkdown(remaining),
        key: `other-${blocks.length}`
      });
    }
  }
  
  // 如果没有任何块，且内容不包含特殊标签，作为普通内容处理
  if (blocks.length === 0 && content.trim()) {
    blocks.push({
      type: 'other',
      content: parseMarkdown(content),
      key: 'content-main'
    });
  }
  
  return blocks;
});

// 处理role折叠状态切换
const toggleRoleOpen = (roleName: string) => {
  const currentState = roleOpenStates.value.get(roleName) || false;
  roleOpenStates.value.set(roleName, !currentState);
};

// 对每个block的内容应用高亮
const getHighlightedContent = (block: AnalysisBlock): string => {
  return highlightKeywords(block.content);
};

// 关键词高亮处理函数
function highlightKeywords(html: string): string {
  // 买入/卖出/持有信号
  html = html.replace(/(<strong>)(买入|卖出|持有)(<\/strong>)/g, '$1<span class="buy">$2</span>$3');
  
  // 上涨/增长相关词
  html = html.replace(/(<strong>)(上涨|看涨|增长|增加|上升)(<\/strong>)/g, '$1<span class="up">$2</span>$3');
  
  // 下跌/减少相关词
  html = html.replace(/(<strong>)(下跌|看跌|减少|降低|下降)(<\/strong>)/g, '$1<span class="down">$2</span>$3');
  
  // 技术指标相关词
  html = html.replace(/(<strong>)(RSI|MACD|MA|KDJ|均线|成交量|布林带|Bollinger|移动平均|相对强弱|背离)(<\/strong>)/g, 
                      '$1<span class="indicator">$2</span>$3');
  
  // 高亮重要的百分比数字 (如 +12.34%, -12.34%)
  html = html.replace(/([+-]?\d+\.?\d*\s*%)/g, '<span class="number">$1</span>');
  
  // 高亮重要的数值 (如带小数位的数字)
  html = html.replace(/(\s|>)(\d+\.\d+)(\s|<)/g, '$1<span class="number">$2</span>$3');
  
  return html;
}

// 获取涨跌幅
const calculatedChangePercent = computed(() => {
  if (props.stock.changePercent !== undefined) {
    return props.stock.changePercent;
  }
  return undefined;
});

const hasAnyTechnicalIndicator = computed(() => {
  return props.stock.rsi !== undefined || 
         props.stock.price_change !== undefined || 
         props.stock.ma_trend !== undefined || 
         props.stock.macd_signal !== undefined || 
         props.stock.volume_status !== undefined;
});

function formatChangePercent(percent: number | undefined): string {
  if (percent === undefined) return '--';
  
  const sign = percent > 0 ? '+' : '';
  return `${sign}${percent.toFixed(2)}%`;
}

function formatPriceChange(change: number | undefined | null): string {
  if (change === undefined || change === null) return '--';
  const sign = change > 0 ? '+' : '';
  return `${sign}${change.toFixed(2)}`;
}

function formatDate(dateStr: string | undefined | null): string {
  if (!dateStr) return '--';
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) {
      return dateStr;
    }
    return date.toISOString().split('T')[0];
  } catch (e) {
    return dateStr;
  }
}

function getScoreClass(score: number): string {
  if (score >= 80) return 'score-high';
  if (score >= 70) return 'score-medium-high';
  if (score >= 60) return 'score-medium';
  if (score >= 40) return 'score-medium-low';
  return 'score-low';
}

function getRsiClass(rsi: number): string {
  if (rsi >= 70) return 'rsi-overbought';
  if (rsi <= 30) return 'rsi-oversold';
  return '';
}

function getTrendClass(trend: string): string {
  if (trend === 'UP') return 'trend-up';
  if (trend === 'DOWN') return 'trend-down';
  return 'trend-neutral';
}

function getSignalClass(signal: string): string {
  if (signal === 'BUY') return 'signal-buy';
  if (signal === 'SELL') return 'signal-sell';
  return 'signal-neutral';
}

function getVolumeStatusClass(status: string): string {
  if (status === 'HIGH') return 'volume-high';
  if (status === 'LOW') return 'volume-low';
  return 'volume-normal';
}

function getChineseTrend(trend: string): string {
  const trendMap: Record<string, string> = {
    'UP': '上升',
    'DOWN': '下降',
    'NEUTRAL': '平稳'
  };
  
  return trendMap[trend] || trend;
}

function getChineseSignal(signal: string): string {
  const signalMap: Record<string, string> = {
    'BUY': '买入',
    'SELL': '卖出',
    'HOLD': '持有',
    'NEUTRAL': '中性'
  };
  
  return signalMap[signal] || signal;
}

function getChineseVolumeStatus(status: string): string {
  const statusMap: Record<string, string> = {
    'HIGH': '放量',
    'LOW': '缩量',
    'NORMAL': '正常'
  };
  
  return statusMap[status] || status;
}

const message = useMessage();

// 添加复制功能
async function copyStockAnalysis() {
  if (!props.stock.analysis) {
    message.warning('暂无分析结果可复制');
    return;
  }

  try {
    let result = `【${props.stock.code} ${props.stock.name || ''}】\n`;
    
    // 添加分析日期
    if (props.stock.analysis_date) {
      result += `分析日期: ${formatDate(props.stock.analysis_date)}\n`;
    }
    
    // 添加评分和推荐信息
    if (props.stock.score !== undefined) {
      result += `评分: ${props.stock.score}\n`;
    }
    
    if (props.stock.recommendation) {
      result += `推荐: ${props.stock.recommendation}\n`;
    }
    
    // 添加技术指标信息
    if (props.stock.rsi !== undefined) {
      result += `RSI: ${props.stock.rsi.toFixed(2)}\n`;
    }
    
    if (props.stock.price_change !== undefined) {
      const sign = props.stock.price_change > 0 ? '+' : '';
      result += `涨跌额: ${sign}${props.stock.price_change.toFixed(2)}\n`;
    }
    
    if (props.stock.ma_trend) {
      result += `均线趋势: ${getChineseTrend(props.stock.ma_trend)}\n`;
    }
    
    if (props.stock.macd_signal) {
      result += `MACD信号: ${getChineseSignal(props.stock.macd_signal)}\n`;
    }
    
    if (props.stock.volume_status) {
      result += `成交量: ${getChineseVolumeStatus(props.stock.volume_status)}\n`;
    }
    
    // 添加分析结果
    result += `\n${props.stock.analysis}\n`;
    
    await navigator.clipboard.writeText(result);
    message.success('已复制分析结果到剪贴板');
  } catch (error) {
    message.error('复制失败，请手动复制');
    console.error('复制分析结果时出错:', error);
  }
}

// 添加状态相关的计算属性
const getStatusType = computed(() => {
  switch (props.stock.analysisStatus) {
    case 'waiting':
      return 'default';
    case 'analyzing':
      return 'info';
    case 'error':
      return 'error';
    default:
      return 'default';
  }
});

const getStatusIcon = computed(() => {
  switch (props.stock.analysisStatus) {
    case 'waiting':
      return HourglassOutline;
    case 'analyzing':
      return ReloadOutline;
    case 'error':
      return AlertCircleIcon;
    default:
      return HourglassOutline;
  }
});

const getStatusText = computed(() => {
  switch (props.stock.analysisStatus) {
    case 'waiting':
      return '等待分析';
    case 'analyzing':
      return '正在分析';
    case 'error':
      return '分析出错';
    default:
      return '';
  }
});

// 添加滚动控制相关变量
const analysisResultRef = ref<HTMLElement | null>(null);
const userScrolling = ref(false);
const scrollPosition = ref(0);
const scrollThreshold = 30; // 底部阈值，小于这个值认为用户已滚动到底部

// 检测用户滚动行为
function handleScroll() {
  if (!analysisResultRef.value) return;
  
  const element = analysisResultRef.value;
  const atBottom = element.scrollHeight - element.scrollTop - element.clientHeight < scrollThreshold;
  
  // 记录当前滚动位置
  scrollPosition.value = element.scrollTop;
  
  // 判断用户是否正在主动滚动
  if (atBottom) {
    // 用户滚动到底部，标记为非主动滚动状态
    userScrolling.value = false;
  } else {
    // 用户未在底部，标记为主动滚动状态
    userScrolling.value = true;
  }
}

// 监听滚动事件
onMounted(() => {
  if (analysisResultRef.value) {
    // 初始滚动到底部
    analysisResultRef.value.scrollTop = analysisResultRef.value.scrollHeight;
    analysisResultRef.value.addEventListener('scroll', handleScroll);
  }
});

// 清理事件监听
onBeforeUnmount(() => {
  if (analysisResultRef.value) {
    analysisResultRef.value.removeEventListener('scroll', handleScroll);
  }
});

// 改进流式更新监听，更保守地控制滚动行为
let isProcessingUpdate = false; // 防止重复处理更新
watch(() => props.stock.analysis, (newVal, oldVal) => {
  // 只在分析中且内容增加时处理
  if (newVal && oldVal && newVal.length > oldVal.length && 
      props.stock.analysisStatus === 'analyzing' && !isProcessingUpdate) {
    
    isProcessingUpdate = true; // 标记正在处理更新
    
    // 检查是否应该自动滚动
    let shouldAutoScroll = false;
    if (analysisResultRef.value) {
      const element = analysisResultRef.value;
      // 仅当滚动接近底部或用户尚未开始滚动时自动滚动
      const atBottom = element.scrollHeight - element.scrollTop - element.clientHeight < scrollThreshold;
      shouldAutoScroll = atBottom || !userScrolling.value;
    }
    
    // 使用nextTick确保DOM已更新
    nextTick(() => {
      if (analysisResultRef.value && shouldAutoScroll) {
        // 使用smoothScroll而非直接设置scrollTop，减少视觉跳动
        smoothScrollToBottom(analysisResultRef.value);
      }
      
      // 重置处理标记
      setTimeout(() => {
        isProcessingUpdate = false;
      }, 50); // 短暂延迟，防止过快连续处理
    });
  }
}, { immediate: false });

// 平滑滚动到底部的辅助函数
function smoothScrollToBottom(element: HTMLElement) {
  const targetPosition = element.scrollHeight;
  
  // 如果已经很接近底部，直接跳转避免不必要的动画
  const currentGap = targetPosition - element.scrollTop - element.clientHeight;
  if (currentGap < 100) {
    element.scrollTop = targetPosition;
    return;
  }
  
  // 否则使用平滑滚动
  element.scrollTo({
    top: targetPosition,
    behavior: 'smooth'
  });
}

// 获取图表数据URL
const getChartDataURL = () => {
  if (chartInstance.value) {
    // 使用 ECharts 的 API 生成图片
    // 缩放操作由 html2canvas 统一处理，避免双重缩放。
    return chartInstance.value.getDataURL({
      type: 'png',
      pixelRatio: 1, 
      backgroundColor: '#f0f2f5' // 匹配截图背景色
    });
  }
  return null;
};

// 处理收藏功能
const handleFavorite = async () => {
  try {
    favoriting.value = true;
    // TODO: 实现收藏功能
    message.success('收藏功能待实现');
  } catch (error) {
    message.error('收藏失败');
  } finally {
    favoriting.value = false;
  }
};

// 处理分享功能
const handleShare = async () => {
  try {
    sharing.value = true;
    // TODO: 实现分享功能
    message.success('分享功能待实现');
  } catch (error) {
    message.error('分享失败');
  } finally {
    sharing.value = false;
  }
};

// 处理导出图片功能
const handleExportImage = async () => {
  try {
    exporting.value = true;
    message.loading('正在生成图片...', { duration: 0 });
    
    // 使用静态导入的html2canvas
    
    // 获取当前卡片的DOM元素
    const cardElement = document.querySelector(`[data-stock-code="${props.stock.code}"]`) as HTMLElement;
    if (!cardElement) {
      message.error('无法找到要导出的卡片');
      return;
    }
    
    // 确保样式正确应用到导出图片
    const currentWidth = window.innerWidth;
    let technicalIndicators = cardElement.querySelector('.technical-indicators') as HTMLElement;
    let indicatorsGrid = cardElement.querySelector('.indicators-grid') as HTMLElement;
    let indicatorItems = cardElement.querySelectorAll('.indicator-item') as NodeListOf<HTMLElement>;
    let originalTechnicalStyle = '';
    let originalGridStyle = '';
    let originalItemStyles: string[] = [];
    
    if (indicatorsGrid && technicalIndicators) {
      originalTechnicalStyle = technicalIndicators.style.cssText;
      originalGridStyle = indicatorsGrid.style.cssText;
      // 保存所有indicator-item的原始样式
      indicatorItems.forEach((item, index) => {
        originalItemStyles[index] = item.style.cssText;
      });
      
      // 根据当前屏幕宽度应用对应的样式
      if (currentWidth <= 375) {
        technicalIndicators.style.cssText += '; margin: 0.5rem 0.25rem; border-radius: 0.45rem; padding: 0.4rem 0.3rem;';
        indicatorsGrid.style.cssText += '; display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem; padding: 0.2rem;';
        indicatorItems.forEach(item => {
          item.style.cssText += '; border-radius: 0.45rem; padding: 0.5rem 0.25rem; background-color: rgba(255, 255, 255, 0.7); box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03); border: 1px solid rgba(0, 0, 0, 0.08);';
        });
      } else if (currentWidth <= 480) {
        technicalIndicators.style.cssText += '; margin: 0.5rem 0.25rem; border-radius: 0.45rem; padding: 0.4rem 0.3rem;';
        indicatorsGrid.style.cssText += '; display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem; padding: 0.2rem;';
        indicatorItems.forEach(item => {
          item.style.cssText += '; border-radius: 0.45rem; padding: 0.5rem 0.25rem; background-color: rgba(255, 255, 255, 0.7); box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03); border: 1px solid rgba(0, 0, 0, 0.08);';
        });
      } else if (currentWidth <= 768) {
        technicalIndicators.style.cssText += '; margin: 0.75rem 0.5rem; background-color: rgba(240, 240, 245, 0.5); border-radius: 0.5rem; padding: 0.5rem; box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.05);';
        indicatorsGrid.style.cssText += '; display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; padding: 0.25rem;';
        indicatorItems.forEach(item => {
          item.style.cssText += '; border-radius: 0.5rem; padding: 0.625rem 0.5rem; background-color: rgba(255, 255, 255, 0.7); box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);';
        });
      } else {
        indicatorsGrid.style.cssText += '; display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem;';
      }
    }
    
    // 处理折叠的分析内容 - 手动隐藏折叠状态下的内容
    // html2canvas 不尊重 <details> 的 open 属性，需要手动控制
    const detailsElements = cardElement.querySelectorAll('details.analysis-fold') as NodeListOf<HTMLDetailsElement>;
    const hiddenContentElements: Array<{element: HTMLElement, originalDisplay: string}> = [];
    
    detailsElements.forEach((details) => {
      if (!details.open) {
        // 如果 details 是折叠状态，隐藏其内容（除了 summary）
        const children = Array.from(details.children) as HTMLElement[];
        children.forEach((child) => {
          if (child.tagName.toLowerCase() !== 'summary') {
            hiddenContentElements.push({
              element: child,
              originalDisplay: child.style.display
            });
            child.style.display = 'none';
          }
        });
      }
    });
    
    // 生成canvas - 保持当前折叠/展开状态
    const canvas = await html2canvas(cardElement, {
      useCORS: true,
      scale: 2, // 提高清晰度
      backgroundColor: '#ffffff',
      allowTaint: false,
      foreignObjectRendering: false,
      logging: false
    });
    
    // 恢复原始样式
    if (indicatorsGrid && technicalIndicators) {
      technicalIndicators.style.cssText = originalTechnicalStyle;
      indicatorsGrid.style.cssText = originalGridStyle;
      indicatorItems.forEach((item, index) => {
        item.style.cssText = originalItemStyles[index] || '';
      });
    }
    
    // 恢复被隐藏的折叠内容
    hiddenContentElements.forEach(({ element, originalDisplay }) => {
      element.style.display = originalDisplay;
    });
    
    // 转换为图片并下载
    const imageUrl = canvas.toDataURL('image/png');
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = `${props.stock.code}_${props.stock.name || '股票分析'}_${new Date().toISOString().split('T')[0]}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    message.destroyAll();
    message.success('图片已保存');
  } catch (error) {
    message.destroyAll();
    message.error('图片导出失败');
    console.error('导出图片时出错:', error);
  } finally {
    exporting.value = false;
  }
};

// 处理开始对话
const handleStartConversation = () => {
  emit('start-conversation', props.stock);
};

defineExpose({
  getChartDataURL
});
</script>

<style scoped>
.stock-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  width: 100%; /* 确保宽度不会超过容器 */
  max-width: 100%; /* 限制最大宽度 */
}

.stock-card.is-analyzing {
  border-left: 3px solid var(--n-info-color);
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 8px 8px;
  margin-bottom: 1rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.09);
  position: relative;
  background: linear-gradient(to bottom, rgba(240, 240, 245, 0.3), transparent);
  border-radius: 8px 8px 0 0;
  width: 100%; /* 确保宽度不会超过容器 */
}

.header-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  gap: 16px;
  align-items: center;
}

.stock-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 100px;
}

.stock-code {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--n-text-color);
  line-height: 1.2;
  letter-spacing: -0.01em;
}

.stock-name {
  font-size: 0.875rem;
  color: var(--n-text-color-3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
}

.stock-price-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-left: 8px;
  border-left: 1px dashed rgba(0, 0, 0, 0.09);
}

.stock-price, .stock-change {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.stock-price .label,
.stock-change .label {
  font-size: 0.875rem;
  color: var(--n-text-color-3);
}

.stock-price .value {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--n-text-color);
}

.stock-change .value {
  font-size: 1rem;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  background-color: rgba(0, 0, 0, 0.03);
}

.up .value {
  color: var(--n-error-color);
  background-color: rgba(208, 48, 80, 0.08);
}

.down .value {
  color: var(--n-success-color);
  background-color: rgba(24, 160, 88, 0.08);
}

.header-right {
  display: flex;
  align-items: center;
  max-width: 380px;
}

.copy-button {
  transition: all 0.3s ease;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.copy-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.copy-button:active {
  transform: translateY(0);
}

.analysis-status {
  display: flex;
  align-items: center;
  margin-top: 4px;
}

.analysis-status :deep(.n-tag) {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.analysis-status :deep(.n-tag .n-icon) {
  margin-right: 4px;
  animation: spin 2s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.copy-button:active {
  transform: translateY(0);
}

.analysis-status {
  display: flex;
  align-items: center;
}

.analysis-status :deep(.n-tag) {
  display: flex;
  align-items: center;
  gap: 4px;
}

.analysis-status :deep(.n-tag .n-icon) {
  margin-right: 4px;
}

.up .value {
  color: var(--n-error-color);
}

.down .value {
  color: var(--n-success-color);
}

.stock-summary {
  display: flex;
  justify-content: space-around;
  margin: 0.75rem 0;
  padding: 0.5rem;
  background-color: rgba(0, 0, 0, 0.02);
  border-radius: 4px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 0.5rem;
}

.summary-value {
  font-size: 1.25rem;
  font-weight: 700;
}

.summary-label {
  font-size: 0.75rem;
  color: var(--n-text-color-3);
  margin-top: 0.25rem;
}

.analysis-date {
  margin: 0.5rem 0;
  display: flex;
  justify-content: flex-end;
}

.technical-indicators {
  margin-top: 0.5rem;
}

.indicators-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.indicator-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.indicator-value {
  font-size: 0.875rem;
  font-weight: 600;
}

.indicator-label {
  font-size: 0.75rem;
  color: var(--n-text-color-3);
  margin-top: 0.25rem;
}

.score-high {
  color: #18a058;
}

.score-medium-high {
  color: #63e2b7;
}

.score-medium {
  color: #f0a020;
}

.score-medium-low {
  color: #f5a623;
}

.score-low {
  color: #d03050;
}

.rsi-overbought {
  color: #d03050;
}

.rsi-oversold {
  color: #18a058;
}

.trend-up {
  color: #d03050;
}

.trend-down {
  color: #18a058;
}

.trend-neutral {
  color: #f0a020;
}

.signal-buy {
  color: #d03050;
}

.signal-sell {
  color: #18a058;
}

.signal-neutral {
  color: #f0a020;
}

.volume-high {
  color: #d03050;
}

.volume-low {
  color: #18a058;
}

.volume-normal {
  color: #f0a020;
}

.recommendation {
  color: #2080f0;
}

.up {
  color: var(--n-error-color);
}

.down {
  color: var(--n-success-color);
}

.card-content {
  flex: 1;
  min-height: 100px;
  margin-bottom: 0.5rem;
  text-align: left;
  display: flex;
  flex-direction: column;
  width: 100%; /* 确保宽度不会超过容器 */
  overflow-x: hidden; /* 防止内容横向溢出 */
}

.error-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--n-error-color);
  font-size: 0.875rem;
  margin: 0.75rem 1rem;
  padding: 0.5rem;
  background-color: rgba(208, 48, 80, 0.1);
  border-radius: 4px;
}

.error-icon {
  color: var(--n-error-color);
}

.analysis-result {
  font-size: 0.875rem;
  line-height: 1.6;
  text-align: left;
  padding: 0.75rem 1rem;
  border-radius: 4px;
  background-color: rgba(0, 0, 0, 0.01);
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.05);
  /* 移除max-height限制，避免多个滚动条 */
  word-break: break-word;
  hyphens: auto;
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
  display: block; /* 确保显示为块级元素 */
  box-sizing: border-box; /* 确保padding不增加宽度 */
}

/* 隐藏滚动条，因为不再需要 */
.analysis-result::-webkit-scrollbar {
  display: none;
}

.analysis-result {
  scrollbar-width: none; /* Firefox */
}

.analysis-streaming {
  position: relative;
  border-left: 2px solid var(--n-info-color);
  animation: fadePulse 2s infinite;
  /* 防止内容更新时的布局抖动 */
  contain: content;
}

/* 分析预览框样式（正在分析的角色） - 直接应用于模板中的元素 */
.analysis-result .analysis-preview-box {
  margin: 1rem 0;
  padding: 0;
  background-color: rgba(32, 128, 240, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(32, 128, 240, 0.15);
  overflow: hidden;
  animation: fadePulse 2s infinite;
}

.analysis-result .analysis-preview-box .preview-box-header {
  font-weight: 600;
  font-size: 0.95rem;
  color: #2080f0;
  padding: 0.5rem 0.75rem;
  background-color: rgba(32, 128, 240, 0.08);
  border-bottom: 1px solid rgba(32, 128, 240, 0.15);
  display: flex;
  align-items: center;
}

.analysis-result .analysis-preview-box .preview-box-header::after {
  content: '|';
  display: inline-block;
  margin-left: 0.5rem;
  color: var(--n-info-color);
  animation: blink 1s step-end infinite;
  font-weight: bold;
}

.analysis-result .analysis-preview-box .preview-box-content {
  padding: 0.75rem;
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--n-text-color-2);
  word-break: break-word;
  /* 限制最大显示5行 */
  max-height: calc(1.6em * 5);
  overflow-y: auto;
  overflow-x: hidden;
}

/* 预览框滚动条样式 */
.analysis-result .analysis-preview-box .preview-box-content::-webkit-scrollbar {
  width: 6px;
}

.analysis-result .analysis-preview-box .preview-box-content::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 3px;
}

.analysis-result .analysis-preview-box .preview-box-content::-webkit-scrollbar-thumb {
  background: rgba(32, 128, 240, 0.3);
  border-radius: 3px;
}

.analysis-result .analysis-preview-box .preview-box-content::-webkit-scrollbar-thumb:hover {
  background: rgba(32, 128, 240, 0.5);
}

/* 同时保留 :deep() 版本以兼容 v-html 渲染的内容 */
.analysis-result :deep(.analysis-preview-box) {
  margin: 1rem 0;
  padding: 0;
  background-color: rgba(32, 128, 240, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(32, 128, 240, 0.15);
  overflow: hidden;
  animation: fadePulse 2s infinite;
}

.analysis-result :deep(.analysis-preview-box .preview-box-header) {
  font-weight: 600;
  font-size: 0.95rem;
  color: #2080f0;
  padding: 0.5rem 0.75rem;
  background-color: rgba(32, 128, 240, 0.08);
  border-bottom: 1px solid rgba(32, 128, 240, 0.15);
  display: flex;
  align-items: center;
}

.analysis-result :deep(.analysis-preview-box .preview-box-header::after) {
  content: '|';
  display: inline-block;
  margin-left: 0.5rem;
  color: var(--n-info-color);
  animation: blink 1s step-end infinite;
  font-weight: bold;
}

.analysis-result :deep(.analysis-preview-box .preview-box-content) {
  padding: 0.75rem;
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--n-text-color-2);
  word-break: break-word;
  /* 限制最大显示5行 */
  max-height: calc(1.6em * 5);
  overflow-y: auto;
  overflow-x: hidden;
}

/* 预览框滚动条样式 */
.analysis-result :deep(.analysis-preview-box .preview-box-content)::-webkit-scrollbar {
  width: 6px;
}

.analysis-result :deep(.analysis-preview-box .preview-box-content)::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 3px;
}

.analysis-result :deep(.analysis-preview-box .preview-box-content)::-webkit-scrollbar-thumb {
  background: rgba(32, 128, 240, 0.3);
  border-radius: 3px;
}

.analysis-result :deep(.analysis-preview-box .preview-box-content)::-webkit-scrollbar-thumb:hover {
  background: rgba(32, 128, 240, 0.5);
}

/* 改进流式输出的动画效果，消除闪烁 */
.analysis-streaming > :deep(*) {
  animation: none;
}

/* 添加打字机光标效果 */
.analysis-streaming::after {
  content: '|';
  display: inline-block;
  color: var(--n-info-color);
  animation: blink 1s step-end infinite;
  margin-left: 2px;
  font-weight: bold;
  vertical-align: middle;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.analysis-completed {
  border-left: 2px solid var(--n-success-color);
}

@keyframes fadePulse {
  0% { border-left-color: var(--n-info-color); }
  50% { border-left-color: rgba(31, 126, 212, 0.4); }
  100% { border-left-color: var(--n-info-color); }
}

/* 优化标题样式，增加颜色显示 */
.analysis-result :deep(h1), .analysis-result :deep(h2), .analysis-result :deep(h3) {
  margin: 1.25rem 0 0.75rem 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  padding-bottom: 0.4rem;
  font-weight: 600;
}

.analysis-result :deep(h1) {
  font-size: 1.4rem;
  color: #2080f0;
}

.analysis-result :deep(h2) {
  font-size: 1.2rem;
  color: #2080f0;
}

.analysis-result :deep(h3) {
  font-size: 1.1rem;
  color: #2080f0;
}

/* 优化列表样式 */
.analysis-result :deep(ul), .analysis-result :deep(ol) {
  margin: 0.75rem 0;
  padding-left: 1.5rem;
}

.analysis-result :deep(ul) li, .analysis-result :deep(ol) li {
  margin-bottom: 0.3rem;
}

/* 优化段落样式 */
.analysis-result :deep(p) {
  margin: 0.75rem 0;
  text-align: left;
}

/* 优化代码样式 */
.analysis-result :deep(code) {
  background: rgba(0, 0, 0, 0.05);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-family: monospace;
  font-size: 0.85em;
  white-space: pre-wrap; /* 允许代码内容自动换行 */
  word-break: break-word; /* 确保长单词可以换行 */
}

.analysis-result :deep(pre) {
  background: rgba(0, 0, 0, 0.05);
  padding: 0.75rem;
  border-radius: 4px;
  overflow-x: hidden; /* 隐藏水平滚动条 */
  margin: 0.75rem 0;
  border-left: 3px solid #2080f0;
  max-width: 100%;
  width: 100%;
  box-sizing: border-box;
  white-space: pre-wrap; /* 允许代码块自动换行 */
  word-break: break-word; /* 允许长单词换行 */
}

.analysis-result :deep(pre code) {
  background: transparent;
  padding: 0;
  white-space: inherit; /* 继承pre的换行行为 */
}

/* 优化引用样式 */
.analysis-result :deep(blockquote) {
  margin: 0.75rem 0;
  padding: 0.5rem 1rem;
  border-left: 3px solid #f0a020;
  background-color: rgba(240, 160, 32, 0.05);
  color: var(--n-text-color-2);
}

/* 优化表格样式 */
.analysis-result :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.75rem 0;
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  table-layout: fixed; /* 固定表格布局 */
  max-width: 100%;
  display: table; /* 恢复正常表格显示 */
  word-wrap: break-word; /* 允许单词换行 */
}

.analysis-result :deep(th), .analysis-result :deep(td) {
  padding: 0.6rem;
  border: 1px solid rgba(0, 0, 0, 0.1);
  word-break: break-word;
  overflow-wrap: break-word;
  max-width: 100%;
}

.analysis-result :deep(th) {
  background-color: rgba(32, 128, 240, 0.1);
  color: #2080f0;
  font-weight: 600;
  text-align: left;
}

.analysis-result :deep(tr:nth-child(even)) {
  background-color: rgba(0, 0, 0, 0.02);
}

/* 优化文本强调和术语显示 */
.analysis-result :deep(strong) {
  font-weight: 600;
  color: #2080f0;
}

/* 特定指标和信号的样式 */
.analysis-result :deep(.buy), 
.analysis-result :deep(.sell), 
.analysis-result :deep(.hold) {
  color: #d03050;
  background-color: rgba(208, 48, 80, 0.1);
  padding: 0 0.3rem;
  border-radius: 2px;
  font-weight: 600;
}

.analysis-result :deep(.up), 
.analysis-result :deep(.increase) {
  color: #d03050;
  font-weight: 600;
}

.analysis-result :deep(.down), 
.analysis-result :deep(.decrease) {
  color: #18a058;
  font-weight: 600;
}

.analysis-result :deep(.indicator) {
  color: #2080f0;
  background-color: rgba(32, 128, 240, 0.1);
  padding: 0 0.3rem;
  border-radius: 2px;
  font-weight: 600;
}

.analysis-result :deep(.number) {
  font-family: 'Consolas', monospace;
  font-weight: 600;
  color: #f0a020;
}

/* 优化链接样式 */
.analysis-result :deep(a) {
  color: #2080f0;
  text-decoration: none;
  border-bottom: 1px dotted #2080f0;
  transition: all 0.2s ease;
  font-weight: 500;
  word-break: break-word;
  overflow-wrap: break-word;
  display: inline-block;
  max-width: 100%;
}

.analysis-result :deep(a:hover) {
  color: #36ad6a;
  border-bottom: 1px solid #36ad6a;
}

/* 优化图片样式 */
.analysis-result :deep(img) {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0.75rem auto;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  object-fit: contain; /* 保持图片比例 */
}

/* 移动端适配样式 */
@media (max-width: 768px) {
  .stock-card {
    margin-bottom: 0.75rem;
  }
  
  .card-header {
    padding: 0.75rem;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  }
  
  .header-main {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
  }
  
  .header-left {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    width: 100%;
    margin-bottom: 0.5rem;
  }
  
  .stock-info {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 8px;
    min-width: auto;
  }
  
  .stock-code {
    font-size: 1.2rem;
  }
  
  .stock-name {
    font-size: 0.8rem;
    max-width: 100px;
  }
  
  .header-right {
    margin-top: 0.5rem;
    width: 320px;
    display: flex;
    justify-content: flex-end;
  }
  
  .stock-price-info {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: flex-start;
    margin-top: 0.5rem;
    gap: 16px;
    border-left: none;
    border-top: 1px dashed rgba(0, 0, 0, 0.09);
    padding-top: 8px;
    padding-left: 0;
    width: 100%;
  }
  
  .stock-price, .stock-change {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 4px;
    padding: 0;
  }
  
  .stock-price .label,
  .stock-change .label {
    font-size: 0.75rem;
  }
  
  .stock-price .value {
    font-size: 1rem;
  }
  
  .stock-change .value {
    font-size: 0.9rem;
  }
  
  .stock-summary {
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  }
  
  .technical-indicators {
    margin: 0.75rem 0.5rem;
    background-color: rgba(240, 240, 245, 0.5);
    border-radius: 0.5rem;
    padding: 0.5rem;
    box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.05);
  }
  
  .indicators-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
    padding: 0.25rem;
  }
  
  .indicator-item {
    border-radius: 0.5rem;
    padding: 0.625rem 0.5rem;
    background-color: rgba(255, 255, 255, 0.7);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    transition: all 0.2s ease;
  }
  
  .indicator-item:active {
    transform: scale(0.98);
    box-shadow: 0 0 1px rgba(0, 0, 0, 0.1);
  }
  
  .indicator-value {
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 0.25rem;
  }
  
  .indicator-label {
    font-size: 0.7rem;
    color: var(--n-text-color-3);
    margin-top: 0.125rem;
  }
  
  .actions-bar {
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
  }
  
  .action-button {
    width: 100%;
    height: 36px !important;
  }
  
  .card-content {
    padding: 0.5rem 0.3rem;
  }
  
  .analysis-result {
    font-size: 0.85rem;
    line-height: 1.65;
    padding: 0.6rem 0.5rem;
    border-radius: 0.5rem;
    border: 1px solid rgba(0, 0, 0, 0.07);
    margin: 0.4rem 0;
    background-color: rgba(255, 255, 255, 0.7);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    width: 100%; /* 占据全部可用宽度 */
    box-sizing: border-box;
    position: relative;
    overflow-x: hidden !important; /* 强制禁止横向滚动 */
  }
  
  /* 优化表格在移动端的显示 */
  .analysis-result :deep(table) {
    width: 100% !important;
    max-width: 100% !important;
    display: table;
    font-size: 0.8rem;
    border: none;
    border-radius: 0.4rem;
    margin: 0.7rem 0;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.07);
    position: relative;
    word-wrap: break-word;
  }
  
  /* 优化代码块在移动端的显示 */
  .analysis-result :deep(pre) {
    font-size: 0.8rem;
    padding: 0.75rem 0.5rem;
    border-radius: 0.4rem;
    overflow-x: hidden;
    margin: 0.7rem 0;
    background-color: rgba(0, 0, 0, 0.04);
    border-left: 3px solid rgba(32, 128, 240, 0.5);
    width: 100% !important;
    box-sizing: border-box;
    white-space: pre-wrap;
    word-break: break-word;
    position: relative;
  }
  
  /* 改进链接触摸体验 */
  .analysis-result :deep(a) {
    padding: 0.1rem 0;
    margin: 0 0.1rem;
    word-break: break-word;
    overflow-wrap: break-word;
    max-width: 100%;
  }
  
  /* 改进按钮和交互元素触摸体验 */
  .analysis-result :deep(button),
  .analysis-result :deep(.interactive) {
    min-height: 36px; /* 最小触摸高度 */
    min-width: 36px; /* 最小触摸宽度 */
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  
  /* 确保所有内容在移动端都能正确换行和显示 */
  .analysis-result :deep(*) {
    max-width: 100% !important;
    box-sizing: border-box !important;
  }
  
  .analysis-streaming {
    background-color: rgba(32, 128, 240, 0.03);
  }
  
  .analysis-completed {
    background-color: rgba(24, 160, 88, 0.02);
  }
  
  /* 移动端预览框样式 */
  .analysis-result .analysis-preview-box {
    margin: 0.75rem 0;
  }
  
  .analysis-result .analysis-preview-box .preview-box-header {
    font-size: 0.9rem;
    padding: 0.4rem 0.6rem;
  }
  
  .analysis-result .analysis-preview-box .preview-box-content {
    font-size: 0.85rem;
    padding: 0.6rem;
    /* 移动端限制4行 */
    max-height: calc(1.6em * 4);
  }
  
  .analysis-result :deep(.analysis-preview-box) {
    margin: 0.75rem 0;
  }
  
  .analysis-result :deep(.analysis-preview-box .preview-box-header) {
    font-size: 0.9rem;
    padding: 0.4rem 0.6rem;
  }
  
  .analysis-result :deep(.analysis-preview-box .preview-box-content) {
    font-size: 0.85rem;
    padding: 0.6rem;
    /* 移动端限制4行 */
    max-height: calc(1.6em * 4);
  }
  
  /* 优化标题样式 */
  .analysis-result :deep(h1), 
  .analysis-result :deep(h2), 
  .analysis-result :deep(h3) {
    margin: 1rem 0 0.7rem 0;
    line-height: 1.3;
    padding-bottom: 0.4rem;
  }
  
  .analysis-result :deep(h1) {
    font-size: 1.3rem;
  }
  
  .analysis-result :deep(h2) {
    font-size: 1.15rem;
  }
  
  .analysis-result :deep(h3) {
    font-size: 1rem;
  }
  
  /* 优化段落间距 */
  .analysis-result :deep(p) {
    margin: 0.6rem 0;
  }
  
  /* 优化列表样式 */
  .analysis-result :deep(ul), 
  .analysis-result :deep(ol) {
    padding-left: 1.2rem;
    margin: 0.6rem 0;
  }
  
  .analysis-result :deep(li) {
    margin-bottom: 0.35rem;
    padding-left: 0.3rem;
  }
  
  /* 优化引用块 */
  .analysis-result :deep(blockquote) {
    margin: 0.7rem 0;
    padding: 0.6rem 0.75rem;
    border-left: 4px solid #f0a020;
    background-color: rgba(240, 160, 32, 0.07);
    border-radius: 0.25rem;
  }
  
  /* 优化代码块 */
  .analysis-result :deep(pre) {
    font-size: 0.8rem;
    padding: 0.75rem 0.5rem;
    border-radius: 0.4rem;
    overflow-x: hidden;
    margin: 0.7rem 0;
    background-color: rgba(0, 0, 0, 0.04);
    border-left: 3px solid rgba(32, 128, 240, 0.5);
    white-space: pre-wrap;
    word-break: break-word;
  }
  
  .analysis-result :deep(code) {
    font-size: 0.8rem;
    padding: 0.15rem 0.3rem;
    background-color: rgba(0, 0, 0, 0.05);
    border-radius: 0.2rem;
  }
  
  /* 优化表格显示 */
  .analysis-result :deep(table) {
    display: table;
    width: 100%;
    border-radius: 0.4rem;
    margin: 0.7rem 0;
    font-size: 0.8rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.07);
    word-wrap: break-word;
  }
  
  .analysis-result :deep(th), 
  .analysis-result :deep(td) {
    padding: 0.5rem 0.4rem;
  }
  
  /* 优化强调文本 */
  .analysis-result :deep(strong) {
    font-weight: 600;
  }
  
  /* 优化专业术语显示 */
  .analysis-result :deep(.buy), 
  .analysis-result :deep(.sell), 
  .analysis-result :deep(.hold) {
    padding: 0.1rem 0.3rem;
    border-radius: 0.2rem;
  }
  
  .analysis-result :deep(.indicator) {
    padding: 0.1rem 0.3rem;
    border-radius: 0.2rem;
  }
  
  /* 优化图片显示 */
  .analysis-result :deep(img) {
    max-width: 100%;
    height: auto;
    border-radius: 0.4rem;
    margin: 0.7rem auto;
  }
}

/* 小屏幕手机适配 */
@media (max-width: 480px) {
  .stock-card {
    margin-bottom: 0.5rem;
    border-radius: 0.625rem !important;
  }
  
  .stock-info {
    flex-direction: row;
    align-items: center;
    gap: 6px;
  }
  
  .stock-code {
    font-size: 1rem;
  }
  
  .stock-name {
    margin-left: 0;
    margin-top: 0;
    font-size: 0.75rem;
    max-width: 80px;
  }
  
  .stock-price-info {
    gap: 12px;
    padding-top: 6px;
    margin-top: 6px;
    flex-wrap: nowrap;
  }
  
  .stock-price, .stock-change {
    white-space: nowrap;
  }
  
  .stock-price .label,
  .stock-change .label {
    font-size: 0.7rem;
  }
  
  .stock-price .value {
    font-size: 0.85rem;
  }
  
  .stock-change .value {
    font-size: 0.8rem;
    padding: 1px 4px;
  }
  
  .technical-indicators {
    margin: 0.5rem 0.25rem;
    border-radius: 0.45rem;
    padding: 0.4rem 0.3rem;
  }
  
  .indicators-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.5rem;
    padding: 0.2rem;
  }
  
  .indicator-item {
    border-radius: 0.45rem;
    padding: 0.5rem 0.25rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    background-color: rgba(255, 255, 255, 0.7);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  }
  
  .indicator-value {
    font-size: 0.9rem;
    margin-bottom: 0.15rem;
  }
  
  .indicator-label {
    font-size: 0.7rem;
    margin-top: 0;
  }
  
  .card-header {
    padding: 0.625rem;
  }
  
  /* 确保边框在小屏幕上清晰可见 */
  .stock-card, .indicator-item, .analysis-result {
    border: 1px solid rgba(0, 0, 0, 0.08) !important;
  }
  
  /* 为不同类型的指标设置不同的边框颜色 */
  .indicator-item .rsi-overbought {
    border-bottom: 2px solid #d03050;
  }
  
  .indicator-item .rsi-oversold {
    border-bottom: 2px solid #18a058;
  }
  
  .indicator-item .trend-up {
    border-bottom: 2px solid #d03050;
  }
  
  .indicator-item .trend-down {
    border-bottom: 2px solid #18a058;
  }
  
  .indicator-item .signal-buy {
    border-bottom: 2px solid #d03050;
  }
  
  .indicator-item .signal-sell {
    border-bottom: 2px solid #18a058;
  }
  
  /* 分析结果小屏幕样式 */
  .analysis-result {
    font-size: 0.825rem;
    line-height: 1.6;
    padding: 0.5rem 0.4rem;
    margin: 0.2rem 0;
    max-width: none; /* 移除宽度限制 */
    width: 100%; /* 占据全部可用宽度 */
    box-sizing: border-box;
  }
  
  .card-content {
    padding: 0.3rem 0.1rem;
  }
  
  .analysis-result :deep(h1) {
    font-size: 1.2rem;
    margin-top: 0.85rem;
  }
  
  .analysis-result :deep(h2) {
    font-size: 1.1rem;
  }
  
  .analysis-result :deep(h3) {
    font-size: 0.95rem;
  }
  
  .analysis-result :deep(ul), 
  .analysis-result :deep(ol) {
    padding-left: 1rem;
  }
  
  .analysis-result :deep(blockquote) {
    padding: 0.5rem 0.625rem;
  }
  
  .analysis-result :deep(pre) {
    font-size: 0.75rem;
    padding: 0.6rem 0.4rem;
  }
  
  .analysis-result :deep(code) {
    font-size: 0.75rem;
  }
  
  .analysis-result :deep(th), 
  .analysis-result :deep(td) {
    padding: 0.4rem 0.3rem;
  }
}

/* 超小屏幕适配 */
@media (max-width: 375px) {
  .indicators-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.4rem;
  }
  
  .indicator-item {
    padding: 0.4rem 0.2rem;
  }
  
  .indicator-value {
    font-size: 0.85rem;
    margin-bottom: 0.1rem;
  }
  
  .indicator-label {
    font-size: 0.65rem;
  }
  
  /* 分析结果超小屏幕样式 */
  .analysis-result {
    font-size: 0.8rem;
    padding: 0.4rem 0.3rem;
    margin: 0.1rem 0;
    width: 100%; /* 占据全部可用宽度 */
    box-sizing: border-box;
  }
  
  .analysis-result :deep(h1) {
    font-size: 1.15rem;
  }
  
  .analysis-result :deep(h2) {
    font-size: 1.05rem;
  }
  
  .analysis-result :deep(h3) {
    font-size: 0.9rem;
  }
  
  .card-content {
    padding: 0.2rem 0.05rem;
  }
}

/* 添加PC端特定样式，确保纵向布局 */
@media (min-width: 769px) {
  .stock-card {
    max-width: 100%;
    display: flex;
    flex-direction: column;
  }
  
  .card-header {
    flex-direction: column;
  }
  
  .header-main {
    flex-direction: row;
    flex-wrap: nowrap;
  }
  
  .header-left {
    flex-direction: row;
    flex-wrap: nowrap;
  }
  
  .stock-price-info {
    flex-direction: column;
    flex-wrap: nowrap;
  }
  
  .stock-summary {
    flex-direction: row;
    flex-wrap: nowrap;
  }
  
  .card-content {
    width: 100%;
    overflow-x: hidden;
  }
  
  .analysis-result {
    width: 100%;
    max-width: 100%;
    overflow-x: hidden;
  }
  
  /* 优化技术指标在PC端的显示 */
  .indicators-grid {
    grid-template-columns: repeat(5, 1fr);
    gap: 1rem;
  }
}

/* 确保所有嵌套元素不会超出容器 */
.analysis-result :deep(*) {
  max-width: 100%;
  box-sizing: border-box;
}

/* 对于图片特别控制 */
.analysis-result :deep(img) {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0.75rem auto;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  object-fit: contain; /* 保持图片比例 */
}

/* 修复长链接可能导致的溢出 */
.analysis-result :deep(a) {
  word-break: break-word;
  overflow-wrap: break-word;
  display: inline-block;
  max-width: 100%;
}

/* 删除滚动控制面板样式 */
.scroll-controls {
  display: none;
}

/* 折叠组件样式（分析完成后使用） - 直接应用于模板中的元素 */
.analysis-result .analysis-fold {
  margin: 1rem 0;
  padding: 0.75rem;
  background-color: rgba(32, 128, 240, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(32, 128, 240, 0.15);
  transition: all 0.3s ease;
}

.analysis-result .analysis-fold:hover {
  background-color: rgba(32, 128, 240, 0.08);
  border-color: rgba(32, 128, 240, 0.25);
}

.analysis-result .analysis-fold > summary {
  cursor: pointer;
  font-weight: 600;
  font-size: 0.95rem;
  color: #2080f0;
  padding: 0.5rem;
  margin: -0.75rem -0.75rem 0.5rem -0.75rem;
  background-color: rgba(32, 128, 240, 0.08);
  border-radius: 6px 6px 0 0;
  user-select: none;
  display: flex;
  align-items: center;
  transition: all 0.2s ease;
}

.analysis-result .analysis-fold > summary:hover {
  background-color: rgba(32, 128, 240, 0.12);
}

.analysis-result .analysis-fold > summary::before {
  content: '▶';
  display: inline-block;
  margin-right: 0.5rem;
  transition: transform 0.2s ease;
  font-size: 0.8rem;
}

.analysis-result .analysis-fold[open] > summary::before {
  transform: rotate(90deg);
}

.analysis-result .analysis-fold[open] > summary {
  margin-bottom: 0.75rem;
  border-radius: 6px;
}

/* 折叠内容区域 */
.analysis-result .analysis-fold > div {
  padding-left: 0.5rem;
}

/* 同时保留 :deep() 版本以兼容 v-html 渲染的内容 */
.analysis-result :deep(details.analysis-fold) {
  margin: 1rem 0;
  padding: 0.75rem;
  background-color: rgba(32, 128, 240, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(32, 128, 240, 0.15);
  transition: all 0.3s ease;
}

.analysis-result :deep(details.analysis-fold:hover) {
  background-color: rgba(32, 128, 240, 0.08);
  border-color: rgba(32, 128, 240, 0.25);
}

.analysis-result :deep(details.analysis-fold > summary) {
  cursor: pointer;
  font-weight: 600;
  font-size: 0.95rem;
  color: #2080f0;
  padding: 0.5rem;
  margin: -0.75rem -0.75rem 0.5rem -0.75rem;
  background-color: rgba(32, 128, 240, 0.08);
  border-radius: 6px 6px 0 0;
  user-select: none;
  display: flex;
  align-items: center;
  transition: all 0.2s ease;
}

.analysis-result :deep(details.analysis-fold > summary:hover) {
  background-color: rgba(32, 128, 240, 0.12);
}

.analysis-result :deep(details.analysis-fold > summary::before) {
  content: '▶';
  display: inline-block;
  margin-right: 0.5rem;
  transition: transform 0.2s ease;
  font-size: 0.8rem;
}

.analysis-result :deep(details.analysis-fold[open] > summary::before) {
  transform: rotate(90deg);
}

.analysis-result :deep(details.analysis-fold[open] > summary) {
  margin-bottom: 0.75rem;
  border-radius: 6px;
}

/* 折叠内容区域 */
.analysis-result :deep(details.analysis-fold > *:not(summary)) {
  padding-left: 0.5rem;
}

/* 移动端优化折叠组件 */
@media (max-width: 768px) {
  .analysis-result .analysis-fold {
    margin: 0.75rem 0;
    padding: 0.6rem;
  }
  
  .analysis-result .analysis-fold > summary {
    font-size: 0.9rem;
    padding: 0.4rem;
    margin: -0.6rem -0.6rem 0.4rem -0.6rem;
  }
  
  .analysis-result :deep(details.analysis-fold) {
    margin: 0.75rem 0;
    padding: 0.6rem;
  }
  
  .analysis-result :deep(details.analysis-fold > summary) {
    font-size: 0.9rem;
    padding: 0.4rem;
    margin: -0.6rem -0.6rem 0.4rem -0.6rem;
  }
}

.chart-container {
  margin-top: 16px;
  height: 400px; /* 明确图表容器高度 */
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.chart-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.chart {
  height: 100%;
  width: 100%;
}
</style>
