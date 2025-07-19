<template>
  <div class="analysis-panel-container">
    <!-- 分析信息和控制栏 -->
    <n-card class="analysis-info-card" size="small">
      <n-space align="center" justify="space-between">
        <n-space align="center">
          <n-tag :type="isAnalyzing ? 'warning' : 'success'">
            {{ isAnalyzing ? '分析中...' : '分析完成' }}
          </n-tag>
          <n-text depth="3">
            {{ initialConfig.stockCodes.length }} 只股票 | {{ initialConfig.marketType }} | {{ initialConfig.analysisDays }}天
          </n-text>
        </n-space>
        
        <n-space>
          <n-button 
            size="small" 
            @click="handleRestartAnalysis"
            :loading="isAnalyzing"
          >
            重新分析
          </n-button>
          <n-button 
            size="small" 
            :disabled="analyzedStocks.length === 0"
            @click="copyAnalysisResults"
          >
            复制结果
          </n-button>
          <n-dropdown 
            trigger="click" 
            :disabled="analyzedStocks.length === 0"
            :options="exportOptions"
            @select="handleExportSelect"
          >
            <n-button size="small" :disabled="analyzedStocks.length === 0">
              导出
              <template #icon>
                <n-icon>
                  <DownloadIcon />
                </n-icon>
              </template>
            </n-button>
          </n-dropdown>
        </n-space>
      </n-space>
    </n-card>
    
    <!-- 结果显示区域 -->
    <n-card class="results-container">
      <div class="results-header">
        <n-space align="center" justify="space-between">
          <n-text>分析结果 ({{ analyzedStocks.length }})</n-text>
          <n-space>
            <n-select 
              v-model:value="displayMode" 
              size="small" 
              style="width: 120px"
              :options="[
                { label: '卡片视图', value: 'card' },
                { label: '表格视图', value: 'table' }
              ]"
            />
          </n-space>
        </n-space>
      </div>
      
      <template v-if="analyzedStocks.length === 0 && !isAnalyzing">
        <n-empty description="尚未开始分析" size="large">
          <template #icon>
            <n-icon :component="DocumentTextIcon" />
          </template>
        </n-empty>
      </template>
      
      <template v-else-if="displayMode === 'card'">
        <n-grid cols="1" :x-gap="8" :y-gap="8" responsive="screen">
          <n-grid-item v-for="stock in analyzedStocks" :key="stock.code">
            <StockCard 
              :stock="stock" 
              @start-conversation="handleStartConversation"
            />
          </n-grid-item>
        </n-grid>
      </template>
      
      <template v-else>
        <div class="table-container">
          <n-data-table
            :columns="stockTableColumns"
            :data="analyzedStocks"
            :pagination="{ pageSize: 10 }"
            :row-key="(row: StockInfo) => row.code"
            :bordered="false"
            :single-line="false"
            striped
            :scroll-x="1200"
          />
        </div>
      </template>
    </n-card>

    <!-- 对话对话框 -->
    <ConversationDialog
      v-model:show="showConversationDialog"
      :stock-info="currentStockForConversation"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue';
import { 
  NCard, 
  NIcon, 
  NGrid, 
  NGridItem, 
  NButton,
  NEmpty,
  useMessage,
  NSpace,
  NText,
  NDataTable,
  NTag,
  NSelect,
  type DataTableColumns
} from 'naive-ui';
import { useClipboard } from '@vueuse/core'
import { 
  DocumentTextOutline as DocumentTextIcon,
  DownloadOutline as DownloadIcon,
  ImageOutline as ImageIcon,
  DocumentOutline as PdfIcon,
  GridOutline as ExcelIcon
} from '@vicons/ionicons5';
import html2canvas from 'html2canvas';

import StockCard from './StockCard.vue';
import ConversationDialog from './ConversationDialog.vue';

import type { StockInfo, ApiConfig } from '@/types';

// Props
interface Props {
  tabId: string;
  initialConfig: {
    stockCodes: string[];
    marketType: string;
    analysisDays: number;
  };
  apiConfig: ApiConfig;
  tabData: {
    hasStartedAnalysis: boolean;
    isAnalyzing: boolean;
    analyzedStocks: StockInfo[];
    analysisCompleted: boolean;
  };
}

const props = defineProps<Props>();

// Emits
const emit = defineEmits<{
  'update-title': [tabId: string, title: string];
  'restart-analysis': [tabId: string];
}>();

// 使用Naive UI的组件API
const message = useMessage();
const { copy } = useClipboard();

// 本地显示状态
const displayMode = ref<'card' | 'table'>('card');

// 使用计算属性来访问分析状态
const isAnalyzing = computed(() => props.tabData.isAnalyzing);
const analyzedStocks = computed(() => props.tabData.analyzedStocks);

// 导出选项
const exportOptions = computed(() => [
  {
    label: '导出为图片 (JPG)',
    key: 'jpg',
    icon: () => h(NIcon, null, { default: () => h(ImageIcon) })
  },
  {
    label: '导出为CSV',
    key: 'csv',
    icon: () => h(NIcon, null, { default: () => h(DownloadIcon) })
  },
  {
    label: '导出为Excel',
    key: 'excel',
    icon: () => h(NIcon, null, { default: () => h(ExcelIcon) })
  },
  {
    label: '导出为PDF',
    key: 'pdf',
    icon: () => h(NIcon, null, { default: () => h(PdfIcon) })
  }
]);

// 对话相关状态
const showConversationDialog = ref(false);
const currentStockForConversation = ref<StockInfo>({
  code: '',
  name: '',
  marketType: 'A',
  analysisStatus: 'waiting'
});

// 表格列定义
const stockTableColumns = ref<DataTableColumns<StockInfo>>([
  {
    title: '代码',
    key: 'code',
    width: 100,
    fixed: 'left'
  },
  {
    title: '状态',
    key: 'analysisStatus',
    width: 100,
    render(row: StockInfo) {
      const statusMap = {
        'waiting': '等待分析',
        'analyzing': '分析中',
        'completed': '已完成',
        'error': '出错'
      };
      return statusMap[row.analysisStatus] || row.analysisStatus;
    }
  },
  {
    title: '价格',
    key: 'price',
    width: 100,
    render(row: StockInfo) {
      return row.price !== undefined ? row.price.toFixed(2) : '--';
    }
  },
  {
    title: '涨跌幅',
    key: 'changePercent',
    width: 100,
    render(row: StockInfo) {
      if (row.changePercent === undefined) {
        if (row.price_change !== undefined && row.price !== undefined) {
          const basePrice = row.price - row.price_change;
          if (basePrice !== 0) {
            const calculatedPercent = (row.price_change / basePrice) * 100;
            const sign = calculatedPercent > 0 ? '+' : '';
            return `${sign}${calculatedPercent.toFixed(2)}%`;
          }
        }
        return '--';
      }
      const sign = row.changePercent > 0 ? '+' : '';
      return `${sign}${row.changePercent.toFixed(2)}%`;
    }
  },
  {
    title: 'RSI',
    key: 'rsi',
    width: 80,
    render(row: StockInfo) {
      return row.rsi !== undefined ? row.rsi.toFixed(2) : '--';
    }
  },
  {
    title: '评分',
    key: 'score',
    width: 80,
    render(row: StockInfo) {
      return row.score !== undefined ? row.score : '--';
    }
  },
  {
    title: '推荐',
    key: 'recommendation',
    width: 100
  }
]);

// 重新分析
const handleRestartAnalysis = () => {
  emit('restart-analysis', props.tabId);
};

// 复制分析结果
async function copyAnalysisResults() {
  if (analyzedStocks.value.length === 0) {
    message.warning('没有可复制的分析结果');
    return;
  }
  
  try {
    const formattedResults = analyzedStocks.value
      .filter((stock: StockInfo) => stock.analysisStatus === 'completed')
      .map((stock: StockInfo) => {
        let result = `【${stock.code} ${stock.name || ''}】\n`;
        
        if (stock.score !== undefined) {
          result += `评分: ${stock.score}\n`;
        }
        
        if (stock.recommendation) {
          result += `推荐: ${stock.recommendation}\n`;
        }
        
        result += `\n${stock.analysis || '无分析结果'}\n`;
        
        return result;
      })
      .join('\n');
    
    if (!formattedResults) {
      message.warning('没有已完成的分析结果可复制');
      return;
    }
    
    await copy(formattedResults);
    message.success('已复制分析结果到剪贴板');
  } catch (error) {
    message.error('复制失败，请手动复制');
    console.error('复制分析结果时出错:', error);
  }
}

// 处理导出选择
function handleExportSelect(key: 'csv' | 'jpg' | 'excel' | 'pdf') {
  switch (key) {
    case 'jpg':
      exportAsImage();
      break;
    case 'csv':
      exportToCsv();
      break;
    case 'excel':
      message.info('Excel导出功能即将推出');
      break;
    case 'pdf':
      message.info('PDF导出功能即将推出');
      break;
  }
}

// 导出为图片
const exportAsImage = async () => {
  if (analyzedStocks.value.length === 0) {
    message.error('没有可导出的内容');
    return;
  }
  
  try {
    message.loading('正在生成图片...', { duration: 0 });
    
    // 使用静态导入的html2canvas
    
    // 获取所有股票卡片
    const stockCards = document.querySelectorAll(`[data-stock-code]`);
    if (stockCards.length === 0) {
      message.error('无法找到要导出的内容');
      return;
    }
    
    // 创建一个容器来放置所有卡片的图片
    const container = document.createElement('div');
    container.style.cssText = `
      background: #f6f6f6;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      width: 800px;
    `;
    
    // 为每个股票卡片生成图片
    for (const card of Array.from(stockCards)) {
      const canvas = await html2canvas(card as HTMLElement, {
        useCORS: true,
        scale: 2,
        backgroundColor: '#ffffff',
        allowTaint: false,
        foreignObjectRendering: false,
        logging: false
      });
      
      const img = document.createElement('img');
      img.src = canvas.toDataURL('image/png');
      img.style.width = '100%';
      container.appendChild(img);
    }
    
    // 对整个容器进行截图
    document.body.appendChild(container);
    const finalCanvas = await html2canvas(container, {
      useCORS: true,
      scale: 1,
      backgroundColor: '#f6f6f6',
      allowTaint: false,
      foreignObjectRendering: false,
      logging: false
    });
    document.body.removeChild(container);
    
    // 下载图片
    const imageUrl = finalCanvas.toDataURL('image/jpeg', 0.9);
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = `股票分析结果_${new Date().toISOString().split('T')[0]}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    message.destroyAll();
    message.success('图片已保存');
  } catch (error) {
    message.destroyAll();
    message.error('图片导出失败');
    console.error('导出图片时出错:', error);
  }
};

// 导出为CSV
const exportToCsv = () => {
  if (analyzedStocks.value.length === 0) {
    message.warning('没有可导出的分析结果');
    return;
  }
  
  try {
    const headers = ['代码', '名称', '价格', '涨跌幅', 'RSI', '评分', '推荐'];
    let csvContent = headers.join(',') + '\n';
    
    analyzedStocks.value.forEach(stock => {
      const row = [
        `"${stock.code}"`,
        `"${stock.name || ''}"`,
        stock.price !== undefined ? stock.price.toFixed(2) : '',
        stock.changePercent !== undefined ? `${stock.changePercent > 0 ? '+' : ''}${stock.changePercent.toFixed(2)}%` : '',
        stock.rsi !== undefined ? stock.rsi.toFixed(2) : '',
        stock.score !== undefined ? stock.score : '',
        `"${stock.recommendation || ''}"`
      ];
      
      csvContent += row.join(',') + '\n';
    });
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `股票分析结果_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    message.success('已导出CSV文件');
  } catch (error) {
    message.error('导出失败');
    console.error('导出CSV时出错:', error);
  }
};

// 处理开始对话
const handleStartConversation = (stock: StockInfo) => {
  currentStockForConversation.value = stock;
  showConversationDialog.value = true;
};
</script>

<style scoped>
.analysis-panel-container {
  padding: 16px;
}

.analysis-info-card {
  margin-bottom: 16px;
}

.results-container {
  margin-bottom: 1rem;
}

.results-header {
  margin-bottom: 1rem;
}

.table-container {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  position: relative;
  border-radius: 0.5rem;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .analysis-panel-container {
    padding: 8px;
  }
  
  .analysis-info-card {
    margin-bottom: 12px;
  }
  
  .table-container {
    margin: 0 -4px;
    padding: 0 4px;
  }
}
</style> 