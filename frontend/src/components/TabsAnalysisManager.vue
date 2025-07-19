<template>
  <div class="tabs-analysis-container mobile-bottom-extend">
    <!-- 公告横幅 -->
    <AnnouncementBanner 
      v-if="announcement && showAnnouncementBanner" 
      :content="announcement" 
      :auto-close-time="5"
      @close="handleAnnouncementClose"
    />
    
    <!-- 市场时间显示 -->
    <MarketTimeDisplay :is-mobile="isMobile" />
    
    <!-- 用户面板（可折叠） -->
    <n-card class="user-panel-card mobile-card mobile-card-spacing mobile-shadow" :class="{ 'register-mode': isRegisterMode }">
      <template #header>
        <n-space align="center" justify="space-between">
          <n-space align="center">
            <n-icon :component="PersonIcon" />
            <span>{{ isRegisterMode ? '用户注册' : '用户中心' }}</span>
          </n-space>
          <n-button 
            v-if="!isRegisterMode"
            text 
            @click="toggleUserPanel"
            :style="{ transform: showUserPanel ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s' }"
          >
            <n-icon :component="ChevronDownIcon" />
          </n-button>
        </n-space>
      </template>
      
      <n-collapse-transition :show="showUserPanel || isRegisterMode">
        <UserPanel 
          :default-tab="route.query.register === 'true' ? 'register' : 'login'" 
          @restore-history="handleRestoreHistory"
        />
      </n-collapse-transition>
    </n-card>
    
    <!-- API配置面板 -->
    <ApiConfigPanel
      v-if="!isRegisterMode"
      :default-api-url="defaultApiUrl"
      :default-api-model="defaultApiModel"
      :default-api-timeout="defaultApiTimeout"
      @update:api-config="updateApiConfig"
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
  NIcon, 
  NSpace, 
  NButton,
  NTabs,
  NTabPane,
  NCollapseTransition,
  useMessage,
  useDialog
} from 'naive-ui';
import { 
  PersonOutline as PersonIcon,
  ChevronDownOutline as ChevronDownIcon,
} from '@vicons/ionicons5';
import { useRoute, useRouter } from 'vue-router';

import MarketTimeDisplay from './MarketTimeDisplay.vue';
import ApiConfigPanel from './ApiConfigPanel.vue';
import AnnouncementBanner from './AnnouncementBanner.vue';
import UserPanel from './UserPanel.vue';
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

// 用户面板状态
const showUserPanel = ref(false);

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
  
  // 立即开始分析
  startTabAnalysis(newTab);
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
const startTabAnalysis = async (tab: AnalysisTab) => {
  // 更新分析状态
  tab.hasStartedAnalysis = true;
  tab.isAnalyzing = true;
  tab.analyzedStocks = [];
  tab.analysisCompleted = false;
  saveTabs();
  
  try {
    const requestData = {
      stock_codes: tab.config.stockCodes,
      market_type: tab.config.marketType,
      analysis_days: tab.config.analysisDays
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
      stock.analysis = data.analysis;
    }
    
    if (data.ai_analysis_chunk !== undefined) {
      stock.analysis = (stock.analysis || '') + data.ai_analysis_chunk;
      stock.analysisStatus = 'analyzing';
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
    
    tab.analyzedStocks[stockIndex] = stock;
    saveTabs();
  }
};

// 处理重新分析请求
const handleRestartAnalysis = (tabId: string) => {
  const tab = analysisTabs.value.find(t => t.id === tabId);
  if (tab) {
    startTabAnalysis(tab);
  }
};

// 更新API配置
const updateApiConfig = (config: ApiConfig) => {
  apiConfig.value = { ...config };
};

// 切换用户面板显示状态
const toggleUserPanel = () => {
  showUserPanel.value = !showUserPanel.value;
};

// 处理历史记录恢复
const handleRestoreHistory = (history: any) => {
  try {
    message.info('正在恢复历史分析结果...');
    
    // 创建基于历史记录的标签页
    const restoredTab: AnalysisTab = {
      id: generateId(),
      title: `历史-${history.stock_codes.join(',')} (${history.market_type})`,
      config: {
        stockCodes: history.stock_codes,
        marketType: history.market_type,
        analysisDays: history.analysis_days
      },
      createdAt: new Date(),
      hasStartedAnalysis: true,
      isAnalyzing: false,
      analyzedStocks: [], // 这里可以预填充历史数据
      analysisCompleted: true
    };
    
    analysisTabs.value.push(restoredTab);
    activeTabId.value = restoredTab.id;
    
    // 关闭用户面板
    showUserPanel.value = false;
    
    message.success(`已恢复历史分析结果到新标签页`);
    saveTabs();
    
  } catch (error) {
    console.error('恢复历史记录失败:', error);
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
    
    // 检查是否需要打开注册面板
    if (route.query.register === 'true') {
      if (config.user_system_enabled) {
        console.log('用户系统已启用，展开用户面板进行注册');
        showUserPanel.value = true;
      } else {
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
  padding-bottom: 20px;
  box-sizing: border-box;
}

.tabs-container {
  margin-bottom: 1rem;
}

.tabs-container :deep(.n-card__content) {
  padding: 16px;
}

.user-panel-card.register-mode {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
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