<template>
  <div class="tabs-analysis-container mobile-bottom-extend">
    <!-- 顶部导航栏 -->
    <TopNavbar
      :default-api-url="defaultApiUrl"
      :default-api-model="defaultApiModel"
      :default-api-timeout="defaultApiTimeout"
      @update:api-config="updateApiConfig"
      @restore-history="handleRestoreHistory"
    />
    
    <!-- 公告横幅 -->
    <AnnouncementBanner 
      v-if="announcement && showAnnouncementBanner && !isRegisterMode" 
      :content="announcement" 
      :auto-close-time="5"
      @close="handleAnnouncementClose"
    />
    
    <!-- 多标签页分析容器 -->
    <n-card class="tabs-container mobile-card mobile-card-spacing mobile-shadow" v-if="!isRegisterMode">
      <n-tabs 
        v-model:value="activeTabId" 
        type="card" 
        closable
        addable
        @close="closeTab"
        @add="() => { activeTabId = 'new-analysis' }"
        :bar-width="isMobile ? 300 : 400"
      >
        <!-- 动态分析结果标签页 -->
        <n-tab-pane 
          v-for="tab in analysisTabs" 
          :key="tab.id"
          :name="tab.id" 
          :tab="tab.title"
          :closable="true"
        >
          <StockAnalysisPanel 
            :tab-id="tab.id"
            :initial-config="tab.config"
            :api-config="apiConfig"
            :tab-data="tab"
            @update-title="updateTabTitle"
            @restart-analysis="handleRestartAnalysis"
          />
        </n-tab-pane>
        
        <!-- 新建分析入口标签页 - 放在最右边 -->
        <n-tab-pane name="new-analysis" tab="+ 新建分析" :closable="false">
          <StockAnalysisForm 
            :api-config="apiConfig"
            @start-analysis="createNewAnalysisTab" 
          />
        </n-tab-pane>
      </n-tabs>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onBeforeUnmount } from 'vue';
import { 
  NCard, 
  NTabs,
  NTabPane,
  useMessage,
  useDialog
} from 'naive-ui';

import { useRoute, useRouter } from 'vue-router';

import TopNavbar from './TopNavbar.vue';
import AnnouncementBanner from './AnnouncementBanner.vue';
import StockAnalysisForm from './StockAnalysisForm.vue';
import StockAnalysisPanel from './StockAnalysisPanel.vue';

import { apiService } from '@/services/api';
import type { ApiConfig, StockInfo } from '@/types';
import { loadApiConfig } from '@/utils';

// 标签页数据结构
interface AnalysisTab {
  id: string;
  title: string;
  config: {
    stockCodes: string[];
    marketType: string;
    analysisDays: number;
  };
  createdAt: Date;
  // 分析状态管理
  hasStartedAnalysis: boolean;
  isAnalyzing: boolean;
  analyzedStocks: StockInfo[];
  analysisCompleted: boolean;
  // 历史记录ID（如果从历史记录恢复的话）
  historyId?: number;
  // 分析UUID（用于历史跳转）
  analysisId?: string;
}

// 使用Naive UI的组件API
const message = useMessage();
const dialog = useDialog();
const router = useRouter();
const route = useRoute();

// 基础状态
const defaultApiUrl = ref('');
const defaultApiModel = ref('');
const defaultApiTimeout = ref('60');
const announcement = ref('');
const showAnnouncementBanner = ref(true);



// 标签页管理状态
const analysisTabs = ref<AnalysisTab[]>([]);
const activeTabId = ref<string>('new-analysis');
const maxTabs = 8;

// API配置
const apiConfig = ref<ApiConfig>({
  apiUrl: '',
  apiKey: '',
  apiModel: '',
  apiTimeout: '60',
  saveApiConfig: false
});

// 移动端检测
const isMobile = computed(() => {
  return window.innerWidth <= 768;
});

// 检测是否为注册模式
const isRegisterMode = computed(() => {
  return route.query.register === 'true';
});

// 生成唯一ID
const generateId = () => {
  return 'tab_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
};

// 创建新的分析标签页
const createNewAnalysisTab = async (config: any) => {
  console.log('[Tabs] createNewAnalysisTab called with config:', config);
  // 检查标签页数量限制
  if (analysisTabs.value.length >= maxTabs) {
    const shouldReplace = await showReplaceOldestTabDialog();
    if (!shouldReplace) {
      return;
    }
    removeOldestTab();
  }
  
  // 创建新标签页
  const newTab: AnalysisTab = {
    id: generateId(),
    title: `${config.stockCodes.join(',')} (${config.marketType})`,
    config: {
      stockCodes: config.stockCodes,
      marketType: config.marketType,
      analysisDays: config.analysisDays
    },
    createdAt: new Date(),
    hasStartedAnalysis: false,
    isAnalyzing: false,
    analyzedStocks: [],
    analysisCompleted: false
  };
  
  analysisTabs.value.push(newTab);
  activeTabId.value = newTab.id;
  
  message.success(`已创建新的分析标签页: ${newTab.title}`);
  
  // 保存标签页状态
  saveTabs();
  
  // 立即开始分析（将 preset_id 传入请求体）
  console.log('[Tabs] starting analysis for tab:', newTab.id, 'presetId:', config.presetId);
  startTabAnalysis(newTab, config.presetId);
};

// 显示替换最旧标签页的确认对话框
const showReplaceOldestTabDialog = (): Promise<boolean> => {
  return new Promise((resolve) => {
    dialog.warning({
      title: '标签页数量限制',
      content: `最多只能打开 ${maxTabs} 个分析标签页。是否要关闭最早创建的标签页来创建新的分析？`,
      positiveText: '确定',
      negativeText: '取消',
      onPositiveClick: () => {
        resolve(true);
      },
      onNegativeClick: () => {
        resolve(false);
      }
    });
  });
};

// 移除最旧的标签页
const removeOldestTab = () => {
  if (analysisTabs.value.length > 0) {
    const oldestTab = analysisTabs.value.reduce((oldest, current) => 
      current.createdAt < oldest.createdAt ? current : oldest
    );
    closeTab(oldestTab.id);
  }
};

// 关闭标签页
const closeTab = (tabId: string) => {
  const index = analysisTabs.value.findIndex(tab => tab.id === tabId);
  if (index !== -1) {
    const closedTab = analysisTabs.value[index];
    analysisTabs.value.splice(index, 1);
    
    // 如果关闭的是当前活跃标签页，切换到其他标签页
    if (activeTabId.value === tabId) {
      if (analysisTabs.value.length > 0) {
        // 切换到最近的标签页
        const newActiveIndex = Math.min(index, analysisTabs.value.length - 1);
        activeTabId.value = analysisTabs.value[newActiveIndex].id;
      } else {
        // 如果没有其他标签页，切换到新建分析
        activeTabId.value = 'new-analysis';
      }
    }
    
    message.info(`已关闭标签页: ${closedTab.title}`);
    
    // 保存标签页状态
    saveTabs();
  }
};

// 更新标签页标题
const updateTabTitle = (tabId: string, newTitle: string) => {
  const tab = analysisTabs.value.find(t => t.id === tabId);
  if (tab) {
    tab.title = newTitle;
    saveTabs();
  }
};

// 启动标签页分析
const startTabAnalysis = async (tab: AnalysisTab, presetId?: string) => {
  console.log('[Tabs] startTabAnalysis tab:', tab.id, 'presetId:', presetId);
  // 更新分析状态
  tab.hasStartedAnalysis = true;
  tab.isAnalyzing = true;
  tab.analyzedStocks = [];
  tab.analysisCompleted = false;
  saveTabs();
  
  try {
    const requestData = {
      stock_codes: Array.isArray(tab.config.stockCodes) ? tab.config.stockCodes : [tab.config.stockCodes],
      market_type: tab.config.marketType,
      analysis_days: tab.config.analysisDays,
      preset_id: presetId || 'standard'
    } as any;
    
    // 添加自定义API配置
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
    
    // console.log('Sending re-analysis request to /api/analyze:', requestData);
    
    const token = localStorage.getItem('token');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers,
      body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        message.error('未授权访问，请登录后再试');
        return;
      }
      if (response.status === 404) {
        throw new Error('服务器接口未找到，请检查服务是否正常运行');
      }
      throw new Error(`服务器响应错误: ${response.status}`);
    }
    
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
      
      const text = decoder.decode(value, { stream: true });
      buffer += text;
      
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      
      for (const line of lines) {
        if (line.trim()) {
          try {
            // console.log('[Tabs] stream line:', line.substring(0, 200) + '...');
            processTabStreamData(tab, line);
          } catch (e: Error | unknown) {
            console.error('处理数据流时出错:', e);
            message.error(`处理数据时出错: ${e instanceof Error ? e.message : '未知错误'}`);
          }
        }
      }
    }
    
    if (buffer.trim()) {
      try {
        processTabStreamData(tab, buffer);
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
    
    tab.analyzedStocks = [];
    tab.isAnalyzing = false;
    saveTabs();
  } finally {
    tab.isAnalyzing = false;
    saveTabs();
  }
};

// 处理标签页的流式数据
const processTabStreamData = (tab: AnalysisTab, text: string) => {
  try {
    const data = JSON.parse(text);
    // console.log('[Tabs] parsed chunk keys:', Object.keys(data));
    
    // 处理orchestrator初始化消息，提取analysis_id
    if (data.orchestrator && data.orchestrator.analysis_id) {
      tab.analysisId = data.orchestrator.analysis_id;
      // console.log('[Tabs] orchestrator init, analysis_id:', tab.analysisId);
    }
    
    if (data.stream_type === 'single' || data.stream_type === 'batch') {
      handleTabStreamInit(tab, data);
    } else if (data.stock_code) {
      handleTabStreamUpdate(tab, data);
    } else if (data.scan_completed) {
      message.success(`分析完成，共扫描 ${data.total_scanned} 只股票，符合条件 ${data.total_matched} 只`);
      
      const completedStocks = tab.analyzedStocks.map(stock => {
        if (stock.analysisStatus === 'analyzing') {
          return { 
            ...stock, 
            analysisStatus: 'completed' as const 
          };
        }
        return stock;
      });
      
      tab.analyzedStocks = completedStocks;
      tab.isAnalyzing = false;
      tab.analysisCompleted = true;
      saveTabs();
    }
  } catch (e) {
    console.error('解析流数据出错:', e);
  }
};

// 处理标签页流式初始化消息
const handleTabStreamInit = (tab: AnalysisTab, data: any) => {
  console.log('[Tabs] handleTabStreamInit:', data);
  if (data.stream_type === 'single' && data.stock_code) {
    tab.analyzedStocks = [{
      code: data.stock_code,
      name: '',
      marketType: tab.config.marketType,
      analysisStatus: 'waiting'
    }];
  } else if (data.stream_type === 'batch' && data.stock_codes) {
    tab.analyzedStocks = data.stock_codes.map((code: string) => ({
      code,
      name: '',
      marketType: tab.config.marketType,
      analysisStatus: 'waiting'
    }));
  }
  saveTabs();
};

// 处理标签页流式更新消息
const handleTabStreamUpdate = (tab: AnalysisTab, data: any) => {
  // console.log('[Tabs] handleTabStreamUpdate for', data.stock_code, 'status:', data.status, 'has chunk:', 'ai_analysis_chunk' in data, 'has analysis:', 'analysis' in data);
  const stockIndex = tab.analyzedStocks.findIndex((s: StockInfo) => s.code === data.stock_code);
  
  if (stockIndex >= 0) {
    const stock = { ...tab.analyzedStocks[stockIndex] };
    
    stock.price = data.price ?? stock.price ?? undefined;
    stock.price_change = data.price_change_value ?? data.price_change ?? stock.price_change ?? undefined;
    stock.changePercent = data.change_percent ?? stock.changePercent ?? undefined;
    stock.marketValue = data.market_value ?? stock.marketValue ?? undefined;
    stock.score = data.score ?? stock.score ?? undefined;
    stock.rsi = data.rsi ?? stock.rsi ?? undefined;

    if (data.status) {
      stock.analysisStatus = data.status;
    }
    
    if (data.analysis !== undefined) {
      // 如果analysis包含<final>标签，说明这是综合决策结果，应该追加而不是覆盖
      if (data.analysis.includes('<final>')) {
        console.log('📥 收到final块，追加到现有分析内容');
        stock.analysis = (stock.analysis || '') + data.analysis;
      } else {
        // 否则直接设置（适用于非多角色模式）
        stock.analysis = data.analysis;
      }
    }
    
    if (data.ai_analysis_chunk !== undefined) {
      // console.log('📥 收到ai_analysis_chunk，长度:', data.ai_analysis_chunk.length);
      // console.log('📥 chunk内容预览:', data.ai_analysis_chunk.substring(0, 100) + '...');
      stock.analysis = (stock.analysis || '') + data.ai_analysis_chunk;
      stock.analysisStatus = 'analyzing';
      // console.log('📥 更新后analysis总长度:', stock.analysis.length);
    }
    
    if (data.error !== undefined) {
      stock.error = data.error;
      stock.analysisStatus = 'error';
    }
    
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
    if (data.chart_data) stock.chart_data = data.chart_data;
    if (data.token_usage) stock.token_usage = data.token_usage;
    
    tab.analyzedStocks[stockIndex] = stock;
    
    // 强制触发响应式更新
    tab.analyzedStocks = [...tab.analyzedStocks];
    
    // 强制更新整个tab对象以确保Vue检测到变化
    const tabIndex = analysisTabs.value.findIndex(t => t.id === tab.id);
    if (tabIndex >= 0) {
      // 创建一个新的tab对象
      const newTab = { ...tab };
      analysisTabs.value[tabIndex] = newTab;
      // 再强制更新整个tabs数组
      analysisTabs.value = [...analysisTabs.value];
    }
    
    // 检查是否所有股票都已完成或出错
    const allStocksFinished = tab.analyzedStocks.every(s => 
      s.analysisStatus === 'completed' || s.analysisStatus === 'error'
    );
    
    if (allStocksFinished && tab.isAnalyzing) {
      tab.isAnalyzing = false;
      tab.analysisCompleted = true;
      
      // 强制刷新tab状态 - 在全局tabs数组中更新
      const tabIndex = analysisTabs.value.findIndex(t => t.id === tab.id);
      if (tabIndex >= 0) {
        // 创建全新的tab对象确保Vue检测到变化
        const newTab = { 
          ...tab, 
          isAnalyzing: false, 
          analysisCompleted: true 
        };
        analysisTabs.value[tabIndex] = newTab;
        analysisTabs.value = [...analysisTabs.value];
      }
      
      message.success('所有股票分析完成');
    }
    
    saveTabs();
  }
};

// 处理重新分析请求
const handleRestartAnalysis = (tabId: string) => {
  const tab = analysisTabs.value.find(t => t.id === tabId);
  if (tab) {
    // console.log('Restarting analysis for tab:', tabId, 'with config:', tab.config);
    startTabAnalysis(tab);
  }/* else {
    console.error('Tab not found for re-analysis:', tabId);
  }*/
};

// 更新API配置
const updateApiConfig = (config: ApiConfig) => {
  apiConfig.value = { ...config };
};



// 处理历史记录恢复
const handleRestoreHistory = (history: any) => {
  try {
    message.info('正在恢复历史分析结果...');
    
    // 检查是否已经存在相同历史记录ID或analysisId的标签页
    let existingTab = null;
    if (history.id) {
      // 首先检查historyId
      existingTab = analysisTabs.value.find(tab => 
        tab.historyId && tab.historyId === history.id
      );
      
      if (existingTab) {
        // 如果已存在相同历史记录的标签页，直接切换到该标签页
        activeTabId.value = existingTab.id;
        message.success('已切换到现有的历史分析标签页');
        return;
      }
    }
    
    // 如果历史记录有analysisId，也检查是否已存在
    if (history.analysis_id) {
      existingTab = analysisTabs.value.find(tab => 
        tab.analysisId && tab.analysisId === history.analysis_id
      );
      
      if (existingTab) {
        activeTabId.value = existingTab.id;
        message.success('已切换到现有的分析标签页');
        return;
      }
    }
    
         // 准备股票代码数组
     const stockCodesArray = Array.isArray(history.stock_codes) ? history.stock_codes : [history.stock_codes];
     const stockCodesStr = stockCodesArray.join(',');
     
     // 解析历史数据中的股票信息
     const historyStocks: StockInfo[] = [];
    
         if (history.stock_codes && Array.isArray(history.stock_codes)) {
       history.stock_codes.forEach((code: string, index: number) => {
         const stock: StockInfo = {
           code: code,
           name: '', // 历史记录可能没有名称
           marketType: history.market_type,
           analysisStatus: 'completed',
           analysis: '', // 从ai_output或analysis_result中获取
           score: undefined,
           recommendation: '',
           rsi: undefined,
           ma_trend: '',
           macd_signal: '',
           volume_status: '',
           price: undefined,
           changePercent: undefined,
           analysis_date: history.created_at || new Date().toISOString()
         };
         
         // 如果有AI输出，作为分析结果
         if (history.ai_output) {
           stock.analysis = history.ai_output;
         } else if (history.analysis_result) {
           stock.analysis = history.analysis_result;
         }
         
         // 解析analysis_result中的技术指标数据
         if (history.analysis_result) {
           try {
             let analysisData = history.analysis_result;
             if (typeof analysisData === 'string') {
               analysisData = JSON.parse(analysisData);
             }
             
             // 如果analysis_result是数组，找到对应的股票数据
             if (Array.isArray(analysisData) && analysisData[index]) {
               const stockData = analysisData[index];
               stock.name = stockData.name || stock.name;
               stock.price = stockData.price || stock.price;
               stock.changePercent = stockData.changePercent || stockData.change_percent || stock.changePercent;
               stock.price_change = stockData.price_change || stock.price_change;
               stock.marketValue = stockData.marketValue || stockData.market_value || stock.marketValue;
               stock.score = stockData.score || stock.score;
               stock.recommendation = stockData.recommendation || stock.recommendation;
               stock.rsi = stockData.rsi || stock.rsi;
               stock.ma_trend = stockData.ma_trend || stock.ma_trend;
               stock.macd_signal = stockData.macd_signal || stock.macd_signal;
               stock.volume_status = stockData.volume_status || stock.volume_status;
               
               // 如果有图表数据
               if (stockData.chart_data) {
                 stock.chart_data = stockData.chart_data;
               }
             }
             // 如果analysis_result是单个对象（单股票分析）
             else if (!Array.isArray(analysisData) && typeof analysisData === 'object') {
               stock.name = analysisData.name || stock.name;
               stock.price = analysisData.price || stock.price;
               stock.changePercent = analysisData.changePercent || analysisData.change_percent || stock.changePercent;
               stock.price_change = analysisData.price_change || stock.price_change;
               stock.marketValue = analysisData.marketValue || analysisData.market_value || stock.marketValue;
               stock.score = analysisData.score || stock.score;
               stock.recommendation = analysisData.recommendation || stock.recommendation;
               stock.rsi = analysisData.rsi || stock.rsi;
               stock.ma_trend = analysisData.ma_trend || stock.ma_trend;
               stock.macd_signal = analysisData.macd_signal || stock.macd_signal;
               stock.volume_status = analysisData.volume_status || stock.volume_status;
               
               if (analysisData.chart_data) {
                 stock.chart_data = analysisData.chart_data;
               }
             }
           } catch (e) {
             console.warn('解析历史分析结果数据失败:', e);
           }
         }
         
         // 如果有单独的图表数据字段，优先使用
         if (history.chart_data) {
           try {
             const chartData = typeof history.chart_data === 'string' 
               ? JSON.parse(history.chart_data) 
               : history.chart_data;
             stock.chart_data = chartData;
           } catch (e) {
             console.warn('解析历史图表数据失败:', e);
           }
         }
         
         historyStocks.push(stock);
       });
     }
    
         // 创建基于历史记录的标签页
     const restoredTab: AnalysisTab = {
       id: generateId(),
       title: `历史-${stockCodesStr} (${history.market_type})`,
       config: {
         stockCodes: stockCodesArray,
         marketType: history.market_type,
         analysisDays: history.analysis_days || 30
       },
       createdAt: new Date(),
       hasStartedAnalysis: true,
       isAnalyzing: false,
       analyzedStocks: historyStocks,
       analysisCompleted: true,
       historyId: history.id // 设置历史记录ID用于排重
     };
    
    analysisTabs.value.push(restoredTab);
    activeTabId.value = restoredTab.id;
    
    message.success(`已恢复历史分析结果到新标签页 (${historyStocks.length} 只股票)`);
    saveTabs();
    
  } catch (error) {
    console.error('恢复历史记录失败:', error);
    console.error('历史记录数据:', history);
    message.error('恢复历史记录失败');
  }
};

// 保存标签页状态到本地存储
const saveTabs = () => {
  try {
    const tabsData = {
      tabs: analysisTabs.value,
      activeTabId: activeTabId.value
    };
    localStorage.setItem('analysis-tabs', JSON.stringify(tabsData));
  } catch (error) {
    console.error('保存标签页状态失败:', error);
  }
};

// 从本地存储恢复标签页状态
const restoreTabs = () => {
  try {
    const saved = localStorage.getItem('analysis-tabs');
    if (saved) {
      const tabsData = JSON.parse(saved);
      analysisTabs.value = tabsData.tabs || [];
      
      // 验证恢复的activeTabId是否有效
      if (tabsData.activeTabId && 
          (tabsData.activeTabId === 'new-analysis' || 
           analysisTabs.value.find(tab => tab.id === tabsData.activeTabId))) {
        activeTabId.value = tabsData.activeTabId;
      } else {
        activeTabId.value = 'new-analysis';
      }
      
      // 清理过期的标签页（超过24小时）
      const now = new Date();
      analysisTabs.value = analysisTabs.value.filter(tab => {
        const tabAge = now.getTime() - new Date(tab.createdAt).getTime();
        return tabAge < 24 * 60 * 60 * 1000; // 24小时
      });
      
      if (analysisTabs.value.length > 0) {
        message.info(`已恢复 ${analysisTabs.value.length} 个分析标签页`);
      }
    }
  } catch (error) {
    console.error('恢复标签页状态失败:', error);
  }
};

// 从本地存储恢复API配置
const restoreLocalApiConfig = () => {
  const savedConfig = loadApiConfig();
  if (savedConfig && savedConfig.saveApiConfig) {
    apiConfig.value = {
      apiUrl: savedConfig.apiUrl || '',
      apiKey: savedConfig.apiKey || '',
      apiModel: savedConfig.apiModel || defaultApiModel.value,
      apiTimeout: savedConfig.apiTimeout || defaultApiTimeout.value,
      saveApiConfig: savedConfig.saveApiConfig
    };
    
    updateApiConfig(apiConfig.value);
  }
};

// 处理公告关闭事件
const handleAnnouncementClose = () => {
  showAnnouncementBanner.value = false;
};

// 监听窗口大小变化
const handleResize = () => {
  // 移动端适配逻辑
};

// 页面加载时获取默认配置和公告
onMounted(async () => {
  try {
    // 添加窗口大小变化监听
    window.addEventListener('resize', handleResize);
    
    // 从API获取配置信息
    const config = await apiService.getConfig();
    
    // 检查是否需要处理注册参数
    if (route.query.register === 'true') {
      if (!config.user_system_enabled) {
        console.log('用户系统未启用，忽略注册参数');
        router.push('/login');
        return;
      }
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
    }
    
    // 初始化后恢复本地保存的配置
    restoreLocalApiConfig();
    
    // 恢复标签页状态
    restoreTabs();
  } catch (error) {
    console.error('获取默认配置时出错:', error);
  }
});

// 组件销毁前移除事件监听
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  // 保存当前状态
  saveTabs();
});
</script>

<style scoped>
.tabs-analysis-container {
  min-height: 100vh;
  width: 100%;
  max-width: 100vw;
  overflow-x: hidden;
  box-sizing: border-box;
  background-color: #f6f6f6;
}

.tabs-container {
  margin: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.tabs-container :deep(.n-card__content) {
  padding: 16px;
}



/* 移动端适配 */
@media (max-width: 768px) {
  .tabs-analysis-container {
    padding: 0.5rem;
  }
  
  .tabs-container :deep(.n-card__content) {
    padding: 8px;
  }
  
  .tabs-container :deep(.n-tabs-nav) {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
  
  .tabs-container :deep(.n-tabs-tab) {
    min-width: 120px;
    flex-shrink: 0;
  }
}

/* 移动端卡片样式 */
.mobile-card {
  border-radius: 0.75rem;
  overflow: hidden;
  width: 100%;
  box-sizing: border-box;
}

.mobile-card-spacing {
  margin-bottom: 0.75rem;
}

.mobile-shadow {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.mobile-bottom-extend {
  padding-bottom: 20px;
}
</style> 