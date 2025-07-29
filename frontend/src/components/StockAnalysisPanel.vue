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

        </n-space>
      </n-space>
    </n-card>
    
    <!-- 结果显示区域 -->
    <n-card class="results-container">
      <div class="results-header">
        <n-space align="center" justify="space-between">
          <n-text>分析结果 ({{ analyzedStocks.length }})</n-text>

        </n-space>
      </div>
      
      <template v-if="analyzedStocks.length === 0 && !isAnalyzing">
        <n-empty description="尚未开始分析" size="large">
          <template #icon>
            <n-icon :component="DocumentTextIcon" />
          </template>
        </n-empty>
      </template>
      
      <n-grid cols="1" :x-gap="8" :y-gap="8" responsive="screen">
        <n-grid-item v-for="stock in analyzedStocks" :key="stock.code">
          <StockCard 
            :stock="stock" 
            @start-conversation="handleStartConversation"
          />
        </n-grid-item>
      </n-grid>
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
  NTag,

} from 'naive-ui';
import { useClipboard } from '@vueuse/core'
import { 
  DocumentTextOutline as DocumentTextIcon
} from '@vicons/ionicons5';

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


// 使用计算属性来访问分析状态
const isAnalyzing = computed(() => props.tabData.isAnalyzing);
const analyzedStocks = computed(() => props.tabData.analyzedStocks);



// 对话相关状态
const showConversationDialog = ref(false);
const currentStockForConversation = ref<StockInfo>({
  code: '',
  name: '',
  marketType: 'A',
  analysisStatus: 'waiting'
});



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