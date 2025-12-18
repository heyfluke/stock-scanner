<template>
  <div class="app-container mobile-bottom-extend">
    <!-- 公告横幅 -->
    <AnnouncementBanner 
      v-if="announcement && showAnnouncementBanner" 
      :content="announcement" 
      :auto-close-time="5"
      @close="handleAnnouncementClose"
    />
    
    <n-layout class="main-layout">
              <n-layout-content class="main-content mobile-content-container">
          
          <!-- 市场时间显示 -->
          <MarketTimeDisplay :is-mobile="isMobile" />
        
        <!-- 用户面板（仅显示已登录用户信息） -->
        <n-card class="user-panel-card mobile-card mobile-card-spacing mobile-shadow" v-if="isLoggedIn">
          <template #header>
            <n-space align="center" justify="space-between">
              <n-space align="center">
                <n-icon :component="PersonIcon" />
                <span>用户中心</span>
              </n-space>
              <n-button 
                text 
                @click="toggleUserPanel"
                :style="{ transform: showUserPanel ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s' }"
              >
                <n-icon :component="ChevronDownIcon" />
              </n-button>
            </n-space>
          </template>
          
          <n-collapse-transition :show="showUserPanel">
            <UserPanel 
            @restore-history="handleRestoreHistory"
            @api-config-changed="handleApiConfigChanged"
          />
          </n-collapse-transition>
        </n-card>
        
        <!-- API配置面板 (仅当选择"个性配置"时显示) -->
        <ApiConfigPanel
          v-if="showApiConfigPanel"
          :default-api-url="defaultApiUrl"
          :default-api-model="defaultApiModel"
          :default-api-timeout="defaultApiTimeout"
          @update:api-config="updateApiConfig"
        />
        
        <!-- 显示当前使用的API配置 -->
        <n-alert v-else type="info" style="margin-bottom: 16px;" :show-icon="false">
          <template #header>
            <n-space align="center">
              <n-icon :component="SettingsIcon" />
              <span>当前API配置</span>
            </n-space>
          </template>
          <n-text>正在使用预配置: <n-text strong>{{ selectedApiConfigName }}</n-text></n-text>
          <n-text depth="3" style="display: block; margin-top: 4px; font-size: 12px;">
            如需更改，请前往"用户中心 > API配置"
          </n-text>
        </n-alert>
        
        <!-- 主要内容 -->
        <n-card class="analysis-container mobile-card mobile-card-spacing mobile-shadow">
          
          <n-grid cols="1 xl:24" :x-gap="16" :y-gap="16" responsive="screen">
            <!-- 左侧配置区域 -->
            <n-grid-item span="1 xl:8">
              <div class="config-section">
                <n-form-item label="选择市场类型">
                  <n-select
                    v-model:value="marketType"
                    :options="marketOptions"
                    @update:value="handleMarketTypeChange"
                  />
                </n-form-item>
                
                <n-form-item :label='marketType === "US" ? "股票搜索" : "基金搜索"' v-if="showSearch">
                  <StockSearch :market-type="marketType" @select="addSelectedStock" />
                </n-form-item>
                
                <n-form-item label="输入代码">
                  <n-input
                    v-model:value="stockCodes"
                    type="textarea"
                    placeholder="输入股票、基金代码，多个代码用逗号、空格或换行分隔"
                    :autosize="{ minRows: 3, maxRows: 6 }"
                  />
                </n-form-item>
                
                <n-form-item label="分析方案">
                  <n-select
                    v-model:value="selectedPresetId"
                    :options="presetOptions"
                    placeholder="标准版"
                  />
                </n-form-item>

                <n-form-item label="分析天数">
                  <n-select
                    v-model:value="analysisDays"
                    :options="analysisDaysOptions"
                  />
                </n-form-item>
                
                <div class="action-buttons">
                  <n-button
                    type="primary"
                    :loading="isAnalyzing"
                    :disabled="!stockCodes.trim()"
                    @click="analyzeStocks"
                  >
                    {{ isAnalyzing ? '分析中...' : '开始分析' }}
                  </n-button>
                  
                  <n-button
                    :disabled="analyzedStocks.length === 0"
                    @click="copyAnalysisResults"
                  >
                    复制结果
                  </n-button>
                </div>
              </div>
            </n-grid-item>
            
            <!-- 右侧结果区域 -->
            <n-grid-item span="1 xl:16">
              <div class="results-section">
                <div class="results-header">
                  <n-space align="center" justify="space-between">
                    <n-text>分析结果 ({{ analyzedStocks.length }})</n-text>
                    <n-space>
                      <n-button 
                        size="small" 
                        :disabled="analyzedStocks.length === 0"
                        @click="copyAnalysisResults"
                      >
                        复制结果
                      </n-button>
                    </n-space>
                  </n-space>
                </div>
                
                <template v-if="analyzedStocks.length === 0 && !isAnalyzing">
                  <n-empty description="尚未分析股票" size="large">
                    <template #icon>
                      <n-icon :component="DocumentTextIcon" />
                    </template>
                  </n-empty>
                </template>
                
                <n-grid cols="1" :x-gap="8" :y-gap="8" responsive="screen">
                  <n-grid-item v-for="(stock, index) in analyzedStocks" :key="stock.code">
                    <StockCard 
                      :stock="stock" 
                      :ref="(el: any) => { if (el) stockCardRefs[index] = el }"
                      @start-conversation="handleStartConversation"
                    />
                  </n-grid-item>
                </n-grid>
              </div>
            </n-grid-item>
          </n-grid>
        </n-card>

        <!-- 隐藏的导出容器，保持原有的双重渲染结构 -->
        <div ref="resultsContainerRef" class="export-container" style="display: none;">
          <template v-if="analyzedStocks.length > 0">
            <n-h2>分析结果</n-h2>
            <n-grid cols="1" :x-gap="8" :y-gap="8" responsive="screen">
              <n-grid-item v-for="stock in analyzedStocks" :key="stock.code">
                <StockCard :stock="stock" @start-conversation="handleStartConversation" />
              </n-grid-item>
            </n-grid>
          </template>
        </div>

        <!-- 对话对话框 -->
        <ConversationDialog
          v-model:show="showConversationDialog"
          :stock-info="currentStockForConversation"
        />
      </n-layout-content>
    </n-layout>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onBeforeUnmount, watch, nextTick } from 'vue';
import { 
  NLayout, 
  NLayoutContent, 
  NCard, 
  NIcon, 
  NGrid, 
  NGridItem, 
  NFormItem, 
  NSelect, 
  NInput, 
  NButton,
  NEmpty,
  useMessage,
  NSpace,
  NText,
  NCollapseTransition,
  NAlert
} from 'naive-ui';
import { useClipboard } from '@vueuse/core'
import { 
  DocumentTextOutline as DocumentTextIcon,
  PersonOutline as PersonIcon,
  ChevronDownOutline as ChevronDownIcon,
  SettingsOutline as SettingsIcon
} from '@vicons/ionicons5';
// removed unused imports
// import { useRoute } from 'vue-router';
// removed unused imports

import MarketTimeDisplay from './MarketTimeDisplay.vue';
import ApiConfigPanel from './ApiConfigPanel.vue';
import StockSearch from './StockSearch.vue';
import StockCard from './StockCard.vue';
import AnnouncementBanner from './AnnouncementBanner.vue';
import UserPanel from './UserPanel.vue';
import ConversationDialog from './ConversationDialog.vue';

import { apiService } from '@/services/api';
import type { StockInfo, ApiConfig, StreamInitMessage, StreamAnalysisUpdate, AgentPreset } from '@/types';
import { loadApiConfig } from '@/utils';
import { validateMultipleStockCodes, MarketType } from '@/utils/stockValidator';

// 使用Naive UI的组件API
const message = useMessage();
const { copy } = useClipboard();
// router not used

// 从环境变量获取的默认配置
const defaultApiUrl = ref('');
const defaultApiModel = ref('');
const defaultApiTimeout = ref('60');
const announcement = ref('');
const showAnnouncementBanner = ref(true);

// 用户面板状态
const showUserPanel = ref(false);
const isLoggedIn = ref(false);
// route currently unused; remove to avoid lints

// 股票分析配置
const marketType = ref('A');
const stockCodes = ref('');
const analysisDays = ref(30); // 默认30天
const selectedPresetId = ref<string | null>(null);
const presets = ref<AgentPreset[]>([]);
const presetOptions = computed(() => {
  const items = presets.value.map(p => ({ label: p.name, value: p.id }));
  return [{ label: '标准版', value: 'standard' }, ...items.filter(i => i.value !== 'standard')];
});
const isAnalyzing = ref(false);
const analyzedStocks = ref<StockInfo[]>([]);

const resultsContainerRef = ref<HTMLElement | null>(null);


// 对话相关状态
const showConversationDialog = ref(false);
const currentStockForConversation = ref<StockInfo>({
  code: '',
  name: '',
  marketType: 'A',
  analysisStatus: 'waiting'
});

// API配置
const apiConfig = ref<ApiConfig>({
  apiUrl: '',
  apiKey: '',
  apiModel: '',
  apiTimeout: '60',
  saveApiConfig: false
});

// 用户选择的API配置名称
const selectedApiConfigName = ref<string>('个性配置');

// 是否显示API配置面板
const showApiConfigPanel = computed(() => {
  return selectedApiConfigName.value === '个性配置';
});

// 加载用户选择的API配置
const loadUserApiConfig = async () => {
  try {
    const settings = await apiService.getUserSettings();
    if (settings && settings.selected_api_config) {
      selectedApiConfigName.value = settings.selected_api_config;
      console.log('🎯 当前使用的API配置:', selectedApiConfigName.value);
    } else {
      selectedApiConfigName.value = '个性配置';
      console.log('🎯 当前使用的API配置: 个性配置（默认）');
    }
  } catch (error) {
    console.error('获取用户API配置失败:', error);
    selectedApiConfigName.value = '个性配置';
  }
};

// 处理API配置变更
const handleApiConfigChanged = async (configName: string) => {
  console.log('🔄 API配置已更改为:', configName);
  selectedApiConfigName.value = configName;
  
  // 如果切换到预配置，清空个性配置的输入框
  if (configName !== '个性配置') {
    apiConfig.value = {
      apiUrl: '',
      apiKey: '',
      apiModel: '',
      apiTimeout: '60',
      saveApiConfig: false
    };
  } else {
    // 切换到"个性配置"时，也清空之前的值，让用户重新填写
    // 这样可以避免发送从其他配置恢复的值
    apiConfig.value = {
      apiUrl: '',
      apiKey: '',
      apiModel: '',
      apiTimeout: '60',
      saveApiConfig: false
    };
  }
};

// 移动端检测
const isMobile = computed(() => {
  return window.innerWidth <= 768;
});



// 监听窗口大小变化
function handleResize() {
  // 窗口大小变化时，isMobile计算属性会自动更新
  // 这里可以添加其他需要在窗口大小变化时执行的逻辑
}

// 显示系统公告
const showAnnouncement = (content: string) => {
  if (!content) return;
  
  // 使用AnnouncementBanner组件显示公告
  announcement.value = content;
  showAnnouncementBanner.value = true;
};

// 切换用户面板显示状态
const toggleUserPanel = () => {
  showUserPanel.value = !showUserPanel.value;
};

// 处理历史记录恢复
const handleRestoreHistory = (history: any) => {
  try {
    console.log('开始恢复历史记录:', history);
    message.info('正在恢复历史分析结果...');
    
    // 清空当前分析结果
    analyzedStocks.value = [];
    
    // 恢复股票分析结果
    if (history.analysis_result && typeof history.analysis_result === 'object') {
      console.log('分析结果数据:', history.analysis_result);
      
      const restoredStocks = Object.entries(history.analysis_result).map(([code, data]: [string, any]) => {
        console.log(`处理股票 ${code}:`, data);
        return {
          code,
          name: data.name || '',
          marketType: history.market_type,
          price: data.price,
          changePercent: data.change_percent || data.price_change,
          marketValue: data.market_value,
          analysis: history.ai_output || data.analysis || '',
          analysisStatus: 'completed' as const,
          score: data.score,
          recommendation: data.recommendation,
          price_change: data.price_change_value || data.price_change,
          rsi: data.rsi,
          ma_trend: data.ma_trend,
          macd_signal: data.macd_signal,
          volume_status: data.volume_status,
          analysis_date: data.analysis_date,
          chart_data: history.chart_data?.[code] || data.chart_data
        };
      });
      
      analyzedStocks.value = restoredStocks;
      console.log('恢复的股票数据:', analyzedStocks.value);
    } else {
      console.warn('没有有效的分析结果数据:', history.analysis_result);
      message.warning('该历史记录没有完整的分析结果数据');
      return;
    }
    
    // 恢复分析参数
    marketType.value = history.market_type;
    analysisDays.value = history.analysis_days;
    
    // 关闭用户面板
    showUserPanel.value = false;
    
    message.success(`已恢复 ${analyzedStocks.value.length} 只股票的历史分析结果`);
    
  } catch (error) {
    console.error('恢复历史记录失败:', error);
    console.error('历史记录数据:', history);
    message.error('恢复历史记录失败');
  }
};

// 市场选项
const marketOptions = [
  { label: 'A股', value: 'A' },
  { label: '港股', value: 'HK' },
  { label: '美股', value: 'US', showSearch: true },
  { label: 'ETF', value: 'ETF', showSearch: true  },
  { label: 'LOF', value: 'LOF', showSearch: true  }
];

// 分析天数选项
const analysisDaysOptions = [
  { label: '7天', value: 7 },
  { label: '14天', value: 14 },
  { label: '30天（推荐）', value: 30 },
  { label: '60天', value: 60 },
  { label: '90天', value: 90 }
];






const showSearch = computed(() => 
  marketOptions.find(option => option.value === marketType.value)?.showSearch
);

// 更新API配置
function updateApiConfig(config: ApiConfig) {
  apiConfig.value = { ...config };
}

// 处理市场类型变更
function handleMarketTypeChange() {
  stockCodes.value = '';
  analyzedStocks.value = [];
}

// 添加选择的股票
function addSelectedStock(symbol: string) {
  // 确保symbol不包含序号或其他不需要的信息
  const cleanSymbol = symbol.trim().replace(/^\d+\.\s*/, '');
  
  if (stockCodes.value) {
    stockCodes.value += ', ' + cleanSymbol;
  } else {
    stockCodes.value = cleanSymbol;
  }
}

// 处理流式响应的数据
function processStreamData(text: string) {
  try {
    // 尝试解析为JSON
    const data = JSON.parse(text);
    
    // 判断是初始消息还是更新消息
    if (data.stream_type === 'single' || data.stream_type === 'batch') {
      // 初始消息
      handleStreamInit(data as StreamInitMessage);
    } else if (data.stock_code) {
      // 更新消息
      handleStreamUpdate(data as StreamAnalysisUpdate);
    } else if (data.scan_completed) {
      // 扫描完成消息
      message.success(`分析完成，共扫描 ${data.total_scanned} 只股票，符合条件 ${data.total_matched} 只`);
      
      // 将所有分析中的股票状态更新为已完成
      analyzedStocks.value = analyzedStocks.value.map(stock => {
        if (stock.analysisStatus === 'analyzing') {
          return { 
            ...stock, 
            analysisStatus: 'completed' as const 
          };
        }
        return stock;
      });
      
      isAnalyzing.value = false;
    }
  } catch (e) {
    console.error('解析流数据出错:', e);
  }
}

// 处理流式初始化消息
function handleStreamInit(data: StreamInitMessage) {
  if (data.stream_type === 'single' && data.stock_code) {
    // 单个股票分析
    analyzedStocks.value = [{
      code: data.stock_code,
      name: '',
      marketType: marketType.value,
      analysisStatus: 'waiting'
    }];
  } else if (data.stream_type === 'batch' && data.stock_codes) {
    // 批量分析
    analyzedStocks.value = data.stock_codes.map(code => ({
      code,
      name: '',
      marketType: marketType.value,
      analysisStatus: 'waiting'
    }));
  }
}

// 处理流式更新消息
function handleStreamUpdate(data: StreamAnalysisUpdate) {
  const stockIndex = analyzedStocks.value.findIndex((s: StockInfo) => s.code === data.stock_code);
  
  if (stockIndex >= 0) {
    const stock = { ...analyzedStocks.value[stockIndex] };
    
    // 确保所有数值类型的字段都有默认值
    stock.price = data.price ?? stock.price ?? undefined;
    stock.price_change = data.price_change_value ?? data.price_change ?? stock.price_change ?? undefined;
    stock.changePercent = data.change_percent ?? stock.changePercent ?? undefined;
    stock.marketValue = data.market_value ?? stock.marketValue ?? undefined;
    stock.score = data.score ?? stock.score ?? undefined;
    stock.rsi = data.rsi ?? stock.rsi ?? undefined;

    // 更新分析状态
    if (data.status) {
      stock.analysisStatus = data.status;
    }
    
    // 如果有分析结果，则更新
    if (data.analysis !== undefined) {
      stock.analysis = data.analysis;
    }
    
    // 处理AI分析片段
    if (data.ai_analysis_chunk !== undefined) {
      stock.analysis = (stock.analysis || '') + data.ai_analysis_chunk;
      stock.analysisStatus = 'analyzing';
    }
    
    // 如果有错误，则更新
    if (data.error !== undefined) {
      stock.error = data.error;
      stock.analysisStatus = 'error';
    }
    
    // 更新其他字段
    if (data.name !== undefined) {
      stock.name = data.name;
    }
    
    if (data.recommendation !== undefined) {
      stock.recommendation = data.recommendation;
    }
    
    if (data.ma_trend !== undefined) {
      stock.ma_trend = data.ma_trend;
    }
    
    if (data.macd_signal !== undefined) {
      stock.macd_signal = data.macd_signal;
    }
    
    if (data.volume_status !== undefined) {
      stock.volume_status = data.volume_status;
    }
    
    if (data.analysis_date) stock.analysis_date = data.analysis_date;

    if (data.chart_data) {
      stock.chart_data = data.chart_data;
      // console.log(`[StockAnalysisApp] Chart data received and set for ${stock.code}`, stock.chart_data);
    }
    
    // 使用Vue的响应式API更新数组
    analyzedStocks.value[stockIndex] = stock;
    
    // 强制触发响应式更新
    analyzedStocks.value = [...analyzedStocks.value];
    
    // 检查是否所有股票都已完成或出错
    const allStocksFinished = analyzedStocks.value.every(s => 
      s.analysisStatus === 'completed' || s.analysisStatus === 'error'
    );
    
    if (allStocksFinished && isAnalyzing.value) {
      isAnalyzing.value = false;
      message.success('所有股票分析完成');
    }
  }
}

// 分析股票
async function analyzeStocks() {
  if (!stockCodes.value.trim()) {
    message.warning('请输入股票代码');
    return;
  }
  
  // 解析股票代码
  const codes = stockCodes.value
    .split(/[,\s\n]+/)
    .map((code: string) => code.trim())
    .filter((code: string) => code);
  
  if (codes.length === 0) {
    message.warning('未找到有效的股票代码');
    return;
  }
  
  // 去除重复的股票代码
  const uniqueCodes = Array.from(new Set(codes));
  
  // 检查是否有重复代码被移除
  if (uniqueCodes.length < codes.length) {
    message.info(`已自动去除${codes.length - uniqueCodes.length}个重复的股票代码`);
  }
  
  // 在前端验证股票代码
  const marketTypeEnum = marketType.value as keyof typeof MarketType;
  const invalidCodes = validateMultipleStockCodes(
    uniqueCodes, 
    MarketType[marketTypeEnum]
  );
  
  // 如果有无效代码，显示错误信息并返回
  if (invalidCodes.length > 0) {
    const errorMessages = invalidCodes.map(item => item.errorMessage).join('\n');
    message.error(`股票代码验证失败:${errorMessages}`);
    return;
  }
  
  isAnalyzing.value = true;
  analyzedStocks.value = [];
  
  // 等待状态清理完成
  await nextTick();
  
  try {
    // 构建请求参数
    const requestData = {
      stock_codes: uniqueCodes,
      market_type: marketType.value,
      analysis_days: analysisDays.value,
      preset_id: selectedPresetId.value || 'standard'
    } as any;
    
    // 优先使用用户选择的API配置
    let hasCustomApiConfig = false;
    
    // 检查是否有直接填写的API配置
    if (apiConfig.value.apiUrl || apiConfig.value.apiKey || apiConfig.value.apiModel) {
      hasCustomApiConfig = true;
      if (apiConfig.value.apiUrl) {
        requestData.api_url = apiConfig.value.apiUrl;
      }
      if (apiConfig.value.apiKey) {
        requestData.api_key = apiConfig.value.apiKey;
      }
      if (apiConfig.value.apiModel) {
        requestData.api_model = apiConfig.value.apiModel;
      }
      if (apiConfig.value.apiTimeout) {
        requestData.api_timeout = apiConfig.value.apiTimeout;
      }
    } else {
      // 如果没有直接填写的配置，尝试使用用户选择的配置
      try {
        const settings = await apiService.getUserSettings();
        if (settings && settings.selected_api_config) {
          requestData.config_name = settings.selected_api_config;
          console.log('使用用户选择的API配置:', settings.selected_api_config);
        }
      } catch (error) {
        console.error('获取用户API配置失败:', error);
      }
    }
    
    // 获取身份验证令牌
    const token = localStorage.getItem('token');
    
    // 构建请求头
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    // 如果有令牌，添加到请求头
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    // 发送分析请求
    // console.log('发送到 /api/analyze 的请求数据:', requestData);
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers,
      body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        message.error('未授权访问，请登录后再试');
        // 可以在这里触发登录流程
        return;
      }
      if (response.status === 404) {
        throw new Error('服务器接口未找到，请检查服务是否正常运行');
      }
      if (response.status === 422) {
        // 尝试读取错误详情
        try {
          const errorData = await response.json();
          console.error('422错误详情:', errorData);
          throw new Error(`请求参数错误: ${errorData.detail || errorData.message || '未知错误'}`);
        } catch (e) {
          throw new Error('请求参数错误，请检查输入数据');
        }
      }
      throw new Error(`服务器响应错误: ${response.status}`);
    }
    
    // 处理流式响应
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('无法读取响应流');
    }
    
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        break;
      }
      
      // 解码并处理数据
      const text = decoder.decode(value, { stream: true });
      buffer += text;
      
      // 按行处理数据
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // 最后一行可能不完整，保留到下一次
      
      for (const line of lines) {
        if (line.trim()) {
          try {
            processStreamData(line);
          } catch (e: Error | unknown) {
            console.error('处理数据流时出错:', e);
            message.error(`处理数据时出错: ${e instanceof Error ? e.message : '未知错误'}`);
          }
        }
      }
    }
    
    // 处理最后可能剩余的数据
    if (buffer.trim()) {
      try {
        processStreamData(buffer);
      } catch (e: Error | unknown) {
        console.error('处理最后的数据块时出错:', e);
        message.error(`处理数据时出错: ${e instanceof Error ? e.message : '未知错误'}`);
      }
    }
    
    message.success('分析完成');
  } catch (error: any) {
    let errorMessage = '分析出错: ';
    if (error.message.includes('404')) {
      errorMessage += '服务器接口未找到，请确保后端服务正常运行';
    } else {
      errorMessage += error.message || '未知错误';
    }
    message.error(errorMessage);
    console.error('分析股票时出错:', error);
    
    // 清空分析状态
    analyzedStocks.value = [];
  } finally {
    isAnalyzing.value = false;
  }
}

// 复制分析结果
async function copyAnalysisResults() {
  if (analyzedStocks.value.length === 0) {
    message.warning('没有可复制的分析结果');
    return;
  }
  
  try {
    // 格式化分析结果
    const formattedResults = analyzedStocks.value
      .filter((stock: StockInfo) => stock.analysisStatus === 'completed')
      .map((stock: StockInfo) => {
        let result = `【${stock.code} ${stock.name || ''}】\n`;
        
        // 添加分析日期
        if (stock.analysis_date) {
          try {
            const date = new Date(stock.analysis_date);
            if (!isNaN(date.getTime())) {
              result += `分析日期: ${date.toISOString().split('T')[0]}\n`;
            } else {
              result += `分析日期: ${stock.analysis_date}\n`;
            }
          } catch (e) {
            result += `分析日期: ${stock.analysis_date}\n`;
          }
        }
        
        // 添加评分和推荐信息
        if (stock.score !== undefined) {
          result += `评分: ${stock.score}\n`;
        }
        
        if (stock.recommendation) {
          result += `推荐: ${stock.recommendation}\n`;
        }
        
        // 添加技术指标信息
        if (stock.rsi !== undefined) {
          result += `RSI: ${stock.rsi.toFixed(2)}\n`;
        }
        
        if (stock.price_change !== undefined) {
          const sign = stock.price_change > 0 ? '+' : '';
          result += `涨跌额: ${sign}${stock.price_change.toFixed(2)}\n`;
        }
        
        if (stock.ma_trend) {
          const trendMap: Record<string, string> = {
            'UP': '上升',
            'DOWN': '下降',
            'NEUTRAL': '平稳'
          };
          const trend = trendMap[stock.ma_trend] || stock.ma_trend;
          result += `均线趋势: ${trend}\n`;
        }
        
        if (stock.macd_signal) {
          const signalMap: Record<string, string> = {
            'BUY': '买入',
            'SELL': '卖出',
            'HOLD': '持有',
            'NEUTRAL': '中性'
          };
          const signal = signalMap[stock.macd_signal] || stock.macd_signal;
          result += `MACD信号: ${signal}\n`;
        }
        
        if (stock.volume_status) {
          const statusMap: Record<string, string> = {
            'HIGH': '放量',
            'LOW': '缩量',
            'NORMAL': '正常'
          };
          const status = statusMap[stock.volume_status] || stock.volume_status;
          result += `成交量: ${status}\n`;
        }
        
        // 添加分析结果
        result += `\n${stock.analysis || '无分析结果'}\n`;
        
        return result;
      })
      .join('\n');
    
    if (!formattedResults) {
      message.warning('没有已完成的分析结果可复制');
      return;
    }
    
    // 复制到剪贴板
    await copy(formattedResults);
    message.success('已复制分析结果到剪贴板');
  } catch (error) {
    message.error('复制失败，请手动复制');
    console.error('复制分析结果时出错:', error);
  }
}

// 从本地存储恢复API配置
function restoreLocalApiConfig() {
  const savedConfig = loadApiConfig();
  if (savedConfig && savedConfig.saveApiConfig) {
    apiConfig.value = {
      apiUrl: savedConfig.apiUrl || '',
      apiKey: savedConfig.apiKey || '',
      apiModel: savedConfig.apiModel || defaultApiModel.value,
      apiTimeout: savedConfig.apiTimeout || defaultApiTimeout.value,
      saveApiConfig: savedConfig.saveApiConfig
    };
    
    // 通知父组件配置已更新
    updateApiConfig(apiConfig.value);
  }
}






const stockCardRefs = ref<any[]>([]);
watch(analyzedStocks, () => {
  stockCardRefs.value = [];
});

// 处理开始对话
const handleStartConversation = (stock: StockInfo) => {
  currentStockForConversation.value = stock;
  showConversationDialog.value = true;
};





// 页面加载时获取默认配置和公告
onMounted(async () => {
  try {
    // 添加窗口大小变化监听
    window.addEventListener('resize', handleResize);
    
    // 从API获取配置信息
    const config = await apiService.getConfig();
    
    // 检查登录状态
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const isAuth = await apiService.checkAuth();
        isLoggedIn.value = isAuth;
      } catch (error) {
        console.error('检查登录状态失败:', error);
        isLoggedIn.value = false;
      }
    } else {
      isLoggedIn.value = false;
    }
    
    if (config.default_api_url) {
      defaultApiUrl.value = config.default_api_url;
    }
    
    if (config.default_api_model) {
      defaultApiModel.value = config.default_api_model;
    }
    
    if (config.default_api_timeout) {
      defaultApiTimeout.value = config.default_api_timeout;
    }
    
    if (config.announcement) {
      announcement.value = config.announcement;
      // 使用通知显示公告
      showAnnouncement(config.announcement);
    }
    
    // 初始化后恢复本地保存的配置
    restoreLocalApiConfig();
    
    // 加载用户选择的API配置
    if (isLoggedIn.value) {
      await loadUserApiConfig();
    }

    // 获取多Agent预设
    try {
      presets.value = await apiService.getAgentPresets();
    } catch (e) {
      // 忽略错误，使用内置默认项
      presets.value = [];
    }
  } catch (error) {
    console.error('获取默认配置时出错:', error);
  }
});

// 组件销毁前移除事件监听
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
});

// 处理公告关闭事件
function handleAnnouncementClose() {
  showAnnouncementBanner.value = false;
}
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  width: 100%;
  max-width: 100vw;
  overflow-x: hidden;
  padding-bottom: 20px; /* 增加底部内边距 */
  box-sizing: border-box;
}

.main-layout {
  background-color: #f6f6f6;
  width: 100%;
  max-width: 100vw;
  overflow-x: hidden;
  min-height: calc(100vh - 20px); /* 确保至少占满视口高度减去底部空间 */
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
  width: 100%;
  box-sizing: border-box;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 600;
}

.analysis-container {
  margin-bottom: 1rem;
}

/* 修改卡片内容区域的内边距 */
.analysis-container :deep(.n-card__content) {
  padding: 16px;
}

.config-section {
  padding: 0.5rem;
}

.action-buttons {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}

.results-section {
  padding: 0.5rem;
  min-height: 200px;
}

.results-header {
  margin-bottom: 1rem;
}

.n-data-table .analysis-cell {
  max-width: 300px;
  white-space: normal;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: break-word;
}

/* 表格容器基础样式 */
.table-container {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch; /* 支持iOS的滚动惯性 */
  position: relative;
  border-radius: 0.5rem;
}

/* 表格横向滚动指示器 */
.table-container::after {
  content: '←→';
  position: absolute;
  bottom: 10px;
  right: 10px;
  color: rgba(32, 128, 240, 0.6);
  font-size: 14px;
  pointer-events: none;
  z-index: 2;
  animation: fadeInOut 2s infinite;
  display: none; /* 默认隐藏，只在移动端显示 */
}

/* 移动端适配的媒体查询 */
@media (max-width: 768px) {
  .main-content {
    padding: 0.5rem;
    max-width: 100%;
    width: 100%;
  }
  
  /* 显示滚动指示器 */
  .table-container::after {
    display: block;
  }
  
  /* 减少移动端卡片内容区域的内边距 */
  .analysis-container :deep(.n-card__content) {
    padding: 12px 8px;
  }
  
  /* 确保卡片内部没有多余边距 */
  :deep(.n-card > .n-card__content) {
    padding: 12px 8px;
  }
  
  /* 减少结果区域的内边距 */
  .results-section {
    padding: 0.25rem 0.125rem;
  }
  
  .action-buttons {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .action-buttons .n-button {
    width: 100%;
  }
  
  .card-title {
    font-size: 1.1rem;
  }
  
  .analysis-container {
    margin-bottom: 0.75rem;
    border-radius: 0.75rem;
    overflow: hidden;
    width: 100%;
    box-sizing: border-box;
  }
  
  .config-section {
    padding: 0.25rem;
    width: 100%;
    box-sizing: border-box;
  }
  
  /* 移动端表格样式优化 */
  .table-container {
    margin: 0 -4px; /* 抵消父容器的padding */
    padding: 0 4px;
  }

  /* 表格组件移动端优化 */
  :deep(.n-data-table-wrapper) {
    border-radius: 0.5rem;
  }

  :deep(.n-data-table-base-table-header, .n-data-table-base-table-body) {
    min-width: 100%;
  }

  :deep(.n-pagination) {
    flex-wrap: wrap;
    justify-content: center;
    margin-top: 8px;
  }
  
  /* 保留原有移动端优化样式 */
  :deep(.n-form-item) {
    margin-bottom: 0.75rem;
  }

  :deep(.n-grid) {
    width: 100% !important;
  }

  :deep(.n-grid-item) {
    width: 100% !important;
    max-width: 100% !important;
  }

  :deep(.n-grid[cols="1 m\\:24"]) {
    gap: 8px !important;
  }

  :deep(.n-grid[cols="1 l\\:2"]) {
    gap: 6px !important;
  }

  :deep(.n-grid-item) > * {
    margin-bottom: 8px;
  }

  :deep(.n-dropdown-menu) {
    max-width: 90vw;
  }
  
  .app-container {
    padding-bottom: 30px; /* 增加移动端底部内边距 */
  }
}

/* 小屏幕手机适配 */
@media (max-width: 480px) {
  .main-content {
    padding: 0.25rem;
  }
  
  /* 进一步减少小屏幕卡片内容区域的内边距 */
  .analysis-container :deep(.n-card__content) {
    padding: 6px 4px;
  }
  
  /* 使用更精确的选择器确保覆盖 */
  :deep(.n-card) > :deep(.n-card__content),
  :deep(.n-card-header) {
    padding: 6px 4px !important;
  }
  
  /* 减少网格间距到最小 */
  :deep(.n-grid[cols="1 l\\:2"]) {
    gap: 4px !important;
  }
  
  .results-section {
    padding: 0.15rem 0.05rem;
  }
  
  .results-header {
    flex-direction: column;
    align-items: stretch;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }
  
  :deep(.n-space) {
    flex-wrap: wrap;
    width: 100%;
    justify-content: space-between;
  }
  
  :deep(.n-space .n-button) {
    margin-right: 0 !important;
  }
  
  .analysis-container {
    border-radius: 0.625rem;
    margin-bottom: 0.5rem;
  }
  
  /* 小屏幕下进一步优化n-grid */
  :deep(.n-grid) {
    gap: 4px !important;
  }
  
  :deep(.n-grid-item) {
    padding: 0 !important;
  }
  
  /* 确保n-grid-item内容在小屏幕下有更紧凑的间距 */
  :deep(.n-grid-item) > * {
    margin-bottom: 4px;
  }
  
  /* 小屏幕表格样式调整 */
  .table-container {
    margin: 0 -2px;
    padding: 0 2px;
  }
  
  /* 小屏幕分页控件优化 */
  :deep(.n-pagination .n-pagination-item) {
    margin: 0 2px;
  }
  
  .app-container {
    padding-bottom: 40px; /* 增加小屏幕底部内边距 */
  }
}

/* 超小屏幕适配 */
@media (max-width: 375px) {
  /* 超小屏幕卡片内容区域几乎无内边距 */
  .analysis-container :deep(.n-card__content) {
    padding: 4px 2px;
  }
  
  /* 使用更精确的选择器确保覆盖 */
  :deep(.n-card) > :deep(.n-card__content),
  :deep(.n-card-header) {
    padding: 3px 2px !important;
  }
  
  /* 网格间距最小化 */
  :deep(.n-grid[cols="1 l\\:2"]),
  :deep(.n-grid[cols="1 m\\:24"]) {
    gap: 3px !important;
  }
  
  /* 极简边距 */
  .results-section {
    padding: 0.1rem 0.025rem;
  }
  
  /* 进一步调整超小屏幕的间距和尺寸 */
  .main-content {
    padding: 0.15rem;
  }
  
  .config-section {
    padding: 0.15rem;
  }
  
  /* 确保StockCard组件最大化利用空间 */
  :deep(.stock-card) {
    margin: 2px 0 !important;
    border-radius: 4px !important;
  }
}



/* 用户面板样式 */
.user-panel-card {
  margin-bottom: 1rem;
}

.user-panel-card :deep(.n-card-header) {
  cursor: pointer;
}

.user-panel-card :deep(.n-card-header):hover {
  background-color: rgba(0, 0, 0, 0.02);
}

/* 注册模式下用户面板的特殊样式 */
.user-panel-card.register-mode {
  max-width: 500px;
  margin: 2rem auto;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

/* 注册模式下主内容区域居中 */
.main-content.register-mode-content {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: calc(100vh - 40px);
}

/* 隐藏导出容器 */
.export-container {
  position: absolute;
  left: -9999px;
  top: -9999px;
  visibility: hidden;
  pointer-events: none;
}
</style>
