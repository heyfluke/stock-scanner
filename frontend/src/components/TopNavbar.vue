<template>
  <div class="top-navbar">
    <div class="navbar-content">
      <!-- 左侧：紧凑的市场时间显示 -->
      <div class="market-time-compact">
        <n-space align="center" :size="8">
          <n-icon :component="TimeIcon" size="16" />
          <span class="current-time">{{ formatTime(marketTime.currentTime) }}</span>
          <n-divider vertical />
          <div class="market-status">
            <n-space :size="12" align="center">
              <div class="market-item">
                <span class="market-label">A股</span>
                <n-tag 
                  :type="marketTime.cnMarket.isOpen ? 'success' : 'default'" 
                  size="small" 
                  :bordered="false"
                >
                  {{ marketTime.cnMarket.isOpen ? '开盘' : '休市' }}
                </n-tag>
              </div>
              <div class="market-item">
                <span class="market-label">港股</span>
                <n-tag 
                  :type="marketTime.hkMarket.isOpen ? 'success' : 'default'" 
                  size="small" 
                  :bordered="false"
                >
                  {{ marketTime.hkMarket.isOpen ? '开盘' : '休市' }}
                </n-tag>
              </div>
              <div class="market-item">
                <span class="market-label">美股</span>
                <n-tag 
                  :type="marketTime.usMarket.isOpen ? 'success' : 'default'" 
                  size="small" 
                  :bordered="false"
                >
                  {{ marketTime.usMarket.isOpen ? '开盘' : '休市' }}
                </n-tag>
              </div>
            </n-space>
          </div>
        </n-space>
      </div>

      <!-- 右侧：菜单按钮 -->
      <div class="navbar-actions">
        <n-space align="center" :size="8">
          <!-- 侧边栏触发按钮 -->
          <n-button 
            text 
            @click="toggleSidebar"
            class="menu-button"
          >
            <template #icon>
              <n-icon :component="MenuIcon" size="20" />
            </template>
          </n-button>
        </n-space>
      </div>
    </div>

    <!-- 侧边栏抽屉 -->
    <n-drawer 
      v-model:show="showSidebar" 
      :width="drawerWidth"
      placement="right"
    >
      <n-drawer-content 
        title="设置和用户中心" 
        :native-scrollbar="false"
      >
        <!-- 用户中心部分 -->
        <div class="sidebar-section" v-if="isLoggedIn">
          <div class="section-header">
            <n-icon :component="PersonIcon" />
            <span>用户中心</span>
          </div>
          <UserPanel 
            @restore-history="handleRestoreHistory"
          />
        </div>

        <!-- API配置部分 -->
        <div class="sidebar-section">
          <div class="section-header">
            <n-icon :component="SettingsIcon" />
            <span>API配置</span>
          </div>
          <ApiConfigPanel
            :default-api-url="defaultApiUrl"
            :default-api-model="defaultApiModel"
            :default-api-timeout="defaultApiTimeout"
            @update:api-config="updateApiConfig"
          />
        </div>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import {
  NSpace,
  NIcon,
  NDivider,
  NTag,
  NButton,
  NDrawer,
  NDrawerContent
} from 'naive-ui';
import {
  TimeOutline as TimeIcon,
  MenuOutline as MenuIcon,
  PersonOutline as PersonIcon,
  SettingsOutline as SettingsIcon
} from '@vicons/ionicons5';
import { useRoute } from 'vue-router';

import UserPanel from './UserPanel.vue';
import ApiConfigPanel from './ApiConfigPanel.vue';
import { updateMarketTimeInfo } from '@/utils';
import { apiService } from '@/services/api';
import type { MarketTimeInfo, ApiConfig } from '@/types';

// Props
interface Props {
  defaultApiUrl: string;
  defaultApiModel: string;
  defaultApiTimeout: string;
}

const props = defineProps<Props>();

// Emits
const emit = defineEmits<{
  'update:api-config': [config: ApiConfig];
  'restore-history': [history: any];
}>();

const route = useRoute();

// 状态
const showSidebar = ref(false);
const isLoggedIn = ref(false);
const marketTime = ref<MarketTimeInfo>({
  currentTime: '',
  cnMarket: { isOpen: false, nextTime: '' },
  hkMarket: { isOpen: false, nextTime: '' },
  usMarket: { isOpen: false, nextTime: '' }
});

let intervalId: number | null = null;

// 移动端检测
const isMobile = computed(() => {
  return window.innerWidth <= 768;
});

// 抽屉宽度计算
const drawerWidth = computed(() => {
  if (isMobile.value) {
    // 移动端：85%宽度，但最大不超过350px
    return Math.min(window.innerWidth * 0.85, 350);
  } else {
    // 桌面端：固定400px
    return 400;
  }
});

// 切换侧边栏
const toggleSidebar = () => {
  showSidebar.value = !showSidebar.value;
};

// 更新市场时间
const updateMarketTimeData = () => {
  marketTime.value = updateMarketTimeInfo();
};

// 格式化时间显示
const formatTime = (timeStr: string) => {
  try {
    // 如果timeStr已经是时间格式（如"14:30:25"），直接返回
    if (/^\d{1,2}:\d{2}:\d{2}$/.test(timeStr)) {
      return timeStr;
    }
    
    const date = new Date(timeStr);
    if (isNaN(date.getTime())) {
      return timeStr;
    }
    
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  } catch (e) {
    return timeStr;
  }
};

// 处理API配置更新
const updateApiConfig = (config: ApiConfig) => {
  emit('update:api-config', config);
};

// 处理历史记录恢复
const handleRestoreHistory = (history: any) => {
  emit('restore-history', history);
  // 恢复历史后关闭侧边栏
  showSidebar.value = false;
};

// 监听窗口大小变化
const handleResize = () => {
  // 在移动端切换到桌面端时关闭侧边栏
  if (!isMobile.value && showSidebar.value) {
    showSidebar.value = false;
  }
};

onMounted(async () => {
  window.addEventListener('resize', handleResize);
  
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
  
  // 初始化市场时间并开始定时更新
  updateMarketTimeData();
  intervalId = window.setInterval(updateMarketTimeData, 1000);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  
  // 清理定时器
  if (intervalId) {
    clearInterval(intervalId);
  }
});
</script>

<style scoped>
.top-navbar {
  background: #ffffff;
  border-bottom: 1px solid #e0e0e6;
  padding: 8px 16px;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.navbar-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1200px;
  margin: 0 auto;
}

.market-time-compact {
  flex: 1;
  min-width: 0;
}

.current-time {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  font-family: 'Courier New', monospace;
}

.market-status {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.market-item {
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.market-label {
  font-size: 12px;
  color: #666;
  min-width: 24px;
}

.navbar-actions {
  display: flex;
  align-items: center;
}

.menu-button {
  padding: 8px;
  border-radius: 6px;
}

.menu-button:hover {
  background-color: #f0f0f0;
}

/* 侧边栏样式 */
.sidebar-section {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e0e0e6;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .top-navbar {
    padding: 8px 12px;
  }
  
  .current-time {
    font-size: 13px;
  }
  
  .market-label {
    font-size: 11px;
    min-width: 20px;
  }
  
  .market-status {
    max-width: 200px;
  }
  
  .section-header {
    font-size: 15px;
  }
}

/* 超小屏幕适配 */
@media (max-width: 480px) {
  .market-item {
    gap: 2px;
  }
  
  .market-label {
    font-size: 10px;
    min-width: 18px;
  }
  
  .current-time {
    font-size: 12px;
  }
}
</style> 