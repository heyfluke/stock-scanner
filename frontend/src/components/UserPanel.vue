<template>
  <div class="user-panel">
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-section">
      <n-space justify="center" align="center" style="min-height: 120px;">
        <n-spin size="medium">
          <template #description>
            检查登录状态...
          </template>
        </n-spin>
      </n-space>
    </div>
    
    <!-- 用户未登录状态 -->
    <div v-else-if="!isLoggedIn" class="auth-section">
      <n-empty description="请先登录">
        <template #extra>
          <n-space>
            <n-button type="primary" @click="goToLogin">
              去登录
            </n-button>
            <n-button @click="goToRegister">
              去注册
            </n-button>
          </n-space>
        </template>
      </n-empty>
    </div>

    <!-- 用户已登录状态 -->
    <div v-else class="user-info-section">
      <n-card title="用户信息">
        <template #header-extra>
          <n-button text @click="handleLogout">
            <n-icon :component="LogOutIcon" />
            退出
          </n-button>
        </template>
        
        <n-descriptions :column="1" size="small">
          <n-descriptions-item label="用户名">{{ userProfile?.username }}</n-descriptions-item>
          <n-descriptions-item label="显示名称">{{ userProfile?.display_name }}</n-descriptions-item>
          <n-descriptions-item v-if="userProfile?.email" label="邮箱">{{ userProfile?.email }}</n-descriptions-item>
        </n-descriptions>
        
        <n-tabs type="line" animated class="user-tabs">
          <n-tab-pane name="favorites" tab="我的收藏">
            <div class="favorites-section">
              <n-empty v-if="favorites.length === 0" description="暂无收藏股票">
                <template #extra>
                  <n-text depth="3">在股票分析页面点击收藏按钮来添加股票</n-text>
                </template>
              </n-empty>
              
              <n-list v-else>
                <n-list-item v-for="favorite in favorites" :key="favorite.id">
                  <template #suffix>
                    <n-button text type="error" @click="removeFavorite(favorite)">
                      <n-icon :component="TrashIcon" />
                    </n-button>
                  </template>
                  
                  <n-thing :title="favorite.stock_code" :description="favorite.display_name">
                    <template #header-extra>
                      <n-tag size="small">{{ favorite.market_type }}</n-tag>
                    </template>
                    <template #description>
                      <n-space>
                        <span>{{ favorite.display_name || favorite.stock_code }}</span>
                        <n-tag
                          v-for="tag in favorite.tags"
                          :key="tag"
                          size="tiny"
                          type="info"
                        >
                          {{ tag }}
                        </n-tag>
                      </n-space>
                    </template>
                    <template #footer>
                      <n-text depth="3" style="font-size: 12px;">
                        收藏时间: {{ formatDate(favorite.created_at) }}
                      </n-text>
                    </template>
                  </n-thing>
                </n-list-item>
              </n-list>
            </div>
          </n-tab-pane>
          
          <n-tab-pane name="history" tab="分析历史">
            <div class="history-section">
              <n-empty v-if="analysisHistory.length === 0" description="暂无分析历史">
                <template #extra>
                  <n-text depth="3">进行股票分析后会自动保存历史记录</n-text>
                </template>
              </n-empty>
              
              <n-list v-else>
                <n-list-item v-for="history in analysisHistory" :key="history.id">
                  <n-thing class="history-item" :class="{ 'clickable': hasAnalysisData(history) }" @click="handleHistoryClick(history)">
                    <template #header>
                      <n-space align="center" justify="space-between">
                        <n-space>
                          <span>{{ history.stock_codes.join(', ') }}</span>
                          <n-tag size="small">{{ history.market_type }}</n-tag>
                          <n-tag v-if="history.ai_output" size="small" type="success">
                            <template #icon>
                              <n-icon><CheckmarkCircleOutline /></n-icon>
                            </template>
                            AI分析
                          </n-tag>
                          <n-tag v-if="history.chart_data" size="small" type="info">
                            <template #icon>
                              <n-icon><BarChartOutline /></n-icon>
                            </template>
                            图表
                          </n-tag>
                        </n-space>
                        <n-space>
                          <n-button 
                            size="small" 
                            type="primary" 
                            secondary 
                            @click.stop="handleStartConversation(history)"
                          >
                            <template #icon>
                              <n-icon><ChatbubbleEllipsesOutline /></n-icon>
                            </template>
                            对话
                          </n-button>
                          <n-button 
                            size="small" 
                            type="error" 
                            secondary 
                            @click.stop="handleDeleteHistory(history)"
                            :loading="deletingHistoryId === history.id"
                          >
                            <template #icon>
                              <n-icon><TrashIcon /></n-icon>
                            </template>
                          </n-button>
                        </n-space>
                      </n-space>
                    </template>
                    <template #description>
                      <n-space>
                        <span>分析天数: {{ history.analysis_days }}天</span>
                        <span v-if="history.analysis_result">
                          股票数: {{ Object.keys(history.analysis_result).length }}只
                        </span>
                      </n-space>
                    </template>
                    <template #footer>
                      <n-space align="center" justify="space-between">
                        <n-text depth="3" style="font-size: 12px;">
                          分析时间: {{ formatDate(history.created_at) }}
                        </n-text>
                        <n-text v-if="hasAnalysisData(history)" depth="2" style="font-size: 12px; color: #2080f0;">
                          点击查看详情
                        </n-text>
                      </n-space>
                    </template>
                  </n-thing>
                </n-list-item>
              </n-list>
            </div>
          </n-tab-pane>
          
          <n-tab-pane name="conversations" tab="AI对话">
            <div class="conversations-section">
              <n-empty v-if="conversations.length === 0" description="暂无对话">
                <template #extra>
                  <n-text depth="3">在分析历史中点击"对话"按钮开始与AI交流</n-text>
                </template>
              </n-empty>
              
              <n-list v-else>
                <n-list-item v-for="conversation in conversations" :key="conversation.id">
                  <n-thing class="conversation-item" @click="handleOpenConversation(conversation)">
                    <template #header>
                      <n-space align="center" justify="space-between">
                        <n-space>
                          <span>{{ conversation.title }}</span>
                          <n-tag size="small" type="info">
                            {{ conversation.message_count }}条消息
                          </n-tag>
                        </n-space>
                        <n-button 
                          size="small" 
                          type="error" 
                          secondary 
                          @click.stop="handleDeleteConversation(conversation)"
                          :loading="deletingConversationId === conversation.id"
                        >
                          <template #icon>
                            <n-icon><TrashIcon /></n-icon>
                          </template>
                        </n-button>
                      </n-space>
                    </template>
                    <template #description>
                      <n-text depth="3">{{ formatDate(conversation.updated_at) }}</n-text>
                    </template>
                  </n-thing>
                </n-list-item>
              </n-list>
            </div>
          </n-tab-pane>

          <n-tab-pane name="api-config" tab="API配置">
            <div class="api-config-section">
              <!-- API配置选择 -->
              <n-card title="API配置" size="small" style="margin-bottom: 16px;">
                <n-empty v-if="apiConfigs.length === 0" description="暂无可用的API配置">
                  <template #extra>
                    <n-text depth="3">请联系管理员添加API配置</n-text>
                  </template>
                </n-empty>
                
                <n-space v-else vertical>
                  <n-radio-group v-model:value="selectedApiConfig" @update:value="handleApiConfigChange">
                    <n-space vertical>
                      <n-radio
                        v-for="config in apiConfigs"
                        :key="config.config_name"
                        :value="config.config_name"
                      >
                          <n-space vertical :size="4">
                            <n-space align="center">
                              <n-text strong>{{ config.config_name }}</n-text>
                              <n-tag v-if="config.source === 'environment'" size="small" type="success">环境变量</n-tag>
                              <n-tag v-else-if="config.source === 'database'" size="small" type="info">预配置</n-tag>
                              <n-tag v-else-if="config.source === 'custom'" size="small" type="warning">自定义</n-tag>
                              <n-tag v-else size="small">其他</n-tag>
                            </n-space>
                            <n-text v-if="config.description" depth="3" style="font-size: 12px;">
                              {{ config.description }}
                            </n-text>
                          </n-space>
                      </n-radio>
                    </n-space>
                  </n-radio-group>
                  
                  <n-divider />
                  
                  <n-button
                    type="primary"
                    size="small"
                    @click="saveApiConfigSelection"
                    :loading="savingApiConfig"
                    :disabled="!selectedApiConfig"
                  >
                    保存选择
                  </n-button>
                </n-space>
              </n-card>
              
              <!-- API用量统计 -->
              <n-card size="small">
                <template #header>
                  <n-space align="center" justify="space-between">
                    <span>API用量统计</span>
                    <n-select
                      v-model:value="selectedUsageConfig"
                      :options="usageConfigOptions"
                      size="small"
                      style="width: 150px;"
                      @update:value="loadApiUsage"
                    />
                  </n-space>
                </template>
                
                <n-spin :show="loadingUsage">
                  <template v-if="usageSummary && usageSummary.total_tokens > 0">
                    <n-space vertical>
                      <!-- 汇总统计 -->
                      <n-alert type="info" :show-icon="false" style="overflow: visible;">
                        <template #header>
                          <n-space align="center">
                            <n-text strong>{{ selectedUsageConfig === 'all' ? '所有配置' : selectedUsageConfig }} - 本月汇总</n-text>
                            <n-tag v-if="selectedUsageConfig === selectedApiConfig" type="success" size="small">当前使用</n-tag>
                          </n-space>
                        </template>
                        <n-grid cols="1 s:2" :x-gap="12" :y-gap="12" responsive="screen">
                          <n-grid-item>
                            <n-statistic label="总Token消耗" :value="usageSummary.total_tokens" style="white-space: nowrap;">
                              <template #suffix>
                                <span style="white-space: nowrap;">tokens</span>
                              </template>
                            </n-statistic>
                          </n-grid-item>
                          <n-grid-item>
                            <n-statistic label="总请求次数" :value="usageSummary.total_requests" style="white-space: nowrap;">
                              <template #suffix>
                                <span style="white-space: nowrap;">次</span>
                              </template>
                            </n-statistic>
                          </n-grid-item>
                        </n-grid>
                      </n-alert>
                      
                      <!-- 仅在查看所有配置时显示详细分组 -->
                      <template v-if="selectedUsageConfig === 'all' && usageSummary.by_config">
                        <n-divider />
                        <n-text strong>按配置明细:</n-text>
                        
                        <n-list bordered>
                          <n-list-item v-for="(usage, configName) in usageSummary.by_config" :key="configName">
                            <template #prefix>
                              <n-icon 
                                :component="CheckmarkCircleIcon" 
                                :color="configName === selectedApiConfig ? '#18a058' : '#ccc'"
                              />
                            </template>
                            <n-thing>
                              <template #header>
                                <n-space align="center">
                                  <n-text strong>{{ configName }}</n-text>
                                  <n-tag v-if="configName === selectedApiConfig" type="success" size="tiny">当前使用</n-tag>
                                  <n-tag v-if="getConfigSource(configName) === 'environment'" size="tiny" type="success">环境变量</n-tag>
                                  <n-tag v-else-if="getConfigSource(configName) === 'database'" size="tiny" type="info">预配置</n-tag>
                                  <n-tag v-else-if="getConfigSource(configName) === '个性配置'" size="tiny" type="warning">自定义</n-tag>
                                </n-space>
                              </template>
                              <n-space vertical size="small">
                                <n-space>
                                  <n-text depth="3">📥 输入: {{ usage.prompt_tokens?.toLocaleString() || 0 }} tokens</n-text>
                                  <n-text depth="3">📤 输出: {{ usage.completion_tokens?.toLocaleString() || 0 }} tokens</n-text>
                                </n-space>
                                <n-space>
                                  <n-text depth="3">📊 总计: {{ usage.total_tokens?.toLocaleString() || 0 }} tokens</n-text>
                                  <n-text depth="3">🔄 请求: {{ usage.request_count }} 次</n-text>
                                  <n-tag v-if="usage.is_estimated" size="tiny" type="warning">估算值</n-tag>
                                </n-space>
                              </n-space>
                            </n-thing>
                          </n-list-item>
                        </n-list>
                      </template>
                      
                      <!-- 查看特定配置时的详细信息 -->
                      <template v-else-if="selectedUsageConfig !== 'all'">
                        <n-descriptions bordered :column="1" size="small">
                          <n-descriptions-item label="输入Token">
                            <n-text strong>{{ getConfigDetailValue('prompt_tokens') }}</n-text>
                          </n-descriptions-item>
                          <n-descriptions-item label="输出Token">
                            <n-text strong>{{ getConfigDetailValue('completion_tokens') }}</n-text>
                          </n-descriptions-item>
                          <n-descriptions-item label="总Token">
                            <n-text strong>{{ getConfigDetailValue('total_tokens') }}</n-text>
                          </n-descriptions-item>
                          <n-descriptions-item label="请求次数">
                            <n-text strong>{{ getConfigDetailValue('request_count') }}</n-text>
                          </n-descriptions-item>
                        </n-descriptions>
                      </template>
                    </n-space>
                  </template>
                  
                  <n-empty v-else description="本月暂无用量数据">
                    <template #extra>
                      <n-text depth="3" style="font-size: 12px;">
                        {{ selectedUsageConfig === 'all' ? '所有配置' : selectedUsageConfig }} 在本月尚未有使用记录
                      </n-text>
                    </template>
                  </n-empty>
                </n-spin>
              </n-card>
            </div>
          </n-tab-pane>
        </n-tabs>
      </n-card>
    </div>
  </div>

  <!-- 对话面板 -->
  <n-modal v-model:show="showConversation" :width="600" preset="card">
    <ConversationPanel
      v-if="showConversation && currentConversation"
      :conversation-id="currentConversation.id"
      :title="currentConversation.title"
      @close="handleCloseConversation"
    />
  </n-modal>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import {
  NCard, NTabs, NTabPane, NForm, NFormItem, NInput, NButton,
  NDescriptions, NDescriptionsItem, NList, NListItem, NThing,
  NTag, NSpace, NText, NEmpty, NIcon, NSpin, NModal, useMessage,
  NRadioGroup, NRadio, NDivider, NStatistic, NSelect, NAlert, NGrid, NGridItem
} from 'naive-ui';
import type { FormInst, FormRules } from 'naive-ui';
import { 
  LogOutOutline as LogOutIcon, 
  TrashOutline as TrashIcon,
  CheckmarkCircleOutline,
  CheckmarkCircleOutline as CheckmarkCircleIcon,
  BarChartOutline,
  ChatbubbleEllipsesOutline
} from '@vicons/ionicons5';
import { useRouter } from 'vue-router';
import { apiService } from '@/services/api';
import type { 
  UserProfile, UserRegisterRequest, LoginRequest, 
  UserFavorite, AnalysisHistoryItem, Conversation
} from '@/types';
import ConversationPanel from './ConversationPanel.vue';

// 定义props
const props = defineProps<{
  defaultTab?: 'login' | 'register'
}>();

// 定义emits
const emit = defineEmits<{
  'restore-history': [history: AnalysisHistoryItem];
  'api-config-changed': [configName: string];
}>();

const message = useMessage();
const router = useRouter();

// 用户状态
const isLoggedIn = ref(false);
const isLoading = ref(true);  // 添加loading状态
const userProfile = ref<UserProfile | null>(null);

// 初始化时检查本地token状态
const initializeAuthState = () => {
  const token = localStorage.getItem('token');
  if (token && token.trim()) {
    // 如果有token，假设已登录，避免闪烁
    isLoggedIn.value = true;
  }
};
const favorites = ref<UserFavorite[]>([]);
const analysisHistory = ref<AnalysisHistoryItem[]>([]);
const deletingHistoryId = ref<number | null>(null);

// 对话状态
const conversations = ref<Conversation[]>([]);
const showConversation = ref(false);
const currentConversation = ref<Conversation | null>(null);
const deletingConversationId = ref<number | null>(null);

// API配置状态
const apiConfigs = ref<any[]>([]);
const selectedApiConfig = ref<string | null>(null);
const savingApiConfig = ref(false);
const usageSummary = ref<any>(null);
const loadingUsage = ref(false);
const selectedUsageConfig = ref<string>('all'); // 用量统计选择的配置

// 用量配置选项
const usageConfigOptions = computed(() => {
  const options = [
    { label: '所有配置', value: 'all' }
  ];
  
  // 添加所有可用的API配置
  apiConfigs.value.forEach(config => {
    options.push({
      label: config.config_name,
      value: config.config_name
    });
  });
  
  return options;
});

// Tab状态
const activeTab = ref(props.defaultTab || 'login');

// 登录表单
const loginFormRef = ref<FormInst | null>(null);
const loginLoading = ref(false);
const loginForm = reactive({
  username: '',
  password: ''
});

const loginRules: FormRules = {
  username: [{ required: true, message: '请输入用户名' }],
  password: [{ required: true, message: '请输入密码' }]
};

// 注册表单
const registerFormRef = ref<FormInst | null>(null);
const registerLoading = ref(false);
const registerForm = reactive({
  username: '',
  display_name: '',
  email: '',
  password: '',
  confirmPassword: ''
});

const registerRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名' },
    { min: 3, max: 20, message: '用户名长度应在3-20个字符之间' }
  ],
  password: [
    { required: true, message: '请输入密码' },
    { min: 6, message: '密码长度至少6个字符' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码' },
    {
      validator: (rule, value) => {
        return value === registerForm.password;
      },
      message: '两次输入的密码不一致'
    }
  ]
};

// 登录处理
const handleLogin = async () => {
  if (!loginFormRef.value) return;
  
  await loginFormRef.value.validate(async (errors) => {
    if (errors) return;
    
    loginLoading.value = true;
    try {
      const request: LoginRequest = {
        username: loginForm.username,
        password: loginForm.password
      };
      
      const response = await apiService.login(request);
      
      if (response.access_token) {
        message.success('登录成功');
        // 清除URL中的register参数
        if (router.currentRoute.value.query.register) {
          router.replace({ path: '/', query: {} });
        }
        await loadUserData();
      } else {
        message.error(response.message || '登录失败');
      }
    } catch (error: any) {
      message.error(error.message || '登录失败');
    } finally {
      loginLoading.value = false;
    }
  });
};

// 注册处理
const handleRegister = async () => {
  if (!registerFormRef.value) return;
  
  await registerFormRef.value.validate(async (errors) => {
    if (errors) return;
    
    registerLoading.value = true;
    try {
      const request: UserRegisterRequest = {
        username: registerForm.username,
        password: registerForm.password,
        display_name: registerForm.display_name || undefined,
        email: registerForm.email || undefined
      };
      
      const response = await apiService.register(request);
      
      if (response.access_token) {
        message.success('注册成功');
        // 清除URL中的register参数
        if (router.currentRoute.value.query.register) {
          router.replace({ path: '/', query: {} });
        }
        await loadUserData();
      } else {
        message.error(response.message || '注册失败');
      }
    } catch (error: any) {
      message.error(error.message || '注册失败');
    } finally {
      registerLoading.value = false;
    }
  });
};

// 退出登录
const handleLogout = async () => {
  try {
    await apiService.logout();
    message.success('登出成功');
  } catch (error) {
    console.error('登出失败:', error);
  } finally {
    // 使用Vue Router跳转到登录页
    router.push('/login');
  }
};

// 跳转到登录页
const goToLogin = () => {
  router.push('/login');
};

// 跳转到注册页
const goToRegister = () => {
  router.push('/login?register=true');
};

// 移除收藏
const removeFavorite = async (favorite: UserFavorite) => {
  try {
    const response = await apiService.removeFavorite(favorite.stock_code, favorite.market_type);
    if (response.success) {
      message.success('移除收藏成功');
      await loadFavorites();
    } else {
      message.error(response.message);
    }
  } catch (error: any) {
    message.error('移除收藏失败');
  }
};

// 加载用户数据
const loadUserData = async () => {
  try {
    // 检查认证状态
    const isAuth = await apiService.checkAuth();
    if (!isAuth) {
      // token验证失败，切换为未登录状态
      isLoggedIn.value = false;
      isLoading.value = false;
      return;
    }
    
    // 获取用户信息
    const profile = await apiService.getUserProfile();
    if (profile) {
      userProfile.value = profile;
      isLoggedIn.value = true;
      
      // 加载收藏、历史记录、对话、API配置和用量
      await Promise.all([
        loadFavorites(),
        loadAnalysisHistory(),
        loadConversations(),
        loadApiConfigs(),
        loadApiUsage()
      ]);
    } else {
      isLoggedIn.value = false;
    }
  } catch (error) {
    console.error('加载用户数据失败:', error);
    isLoggedIn.value = false;
  } finally {
    // 无论成功失败都结束loading状态
    isLoading.value = false;
  }
};

// 加载收藏列表
const loadFavorites = async () => {
  try {
    favorites.value = await apiService.getFavorites();
  } catch (error) {
    console.error('加载收藏列表失败:', error);
  }
};

// 加载分析历史
const loadAnalysisHistory = async () => {
  try {
    analysisHistory.value = await apiService.getAnalysisHistory(20);
  } catch (error) {
    console.error('加载分析历史失败:', error);
  }
};

// 加载对话列表
const loadConversations = async () => {
  try {
    conversations.value = await apiService.getConversations();
  } catch (error) {
    console.error('加载对话列表失败:', error);
  }
};

// 加载API配置列表
const loadApiConfigs = async () => {
  try {
    const response = await apiService.getApiConfigs();
    apiConfigs.value = response.configs || [];
    
    // 添加"个性配置"选项
    apiConfigs.value.push({
      config_name: '个性配置',
      source: 'custom',
      description: '在主界面直接填写API URL、Key等信息'
    });
    
    console.log('API配置列表已加载:', apiConfigs.value);
    
    // 加载用户当前选择的配置
    const settings = await apiService.getUserSettings();
    console.log('用户设置已加载:', settings);
    if (settings && settings.selected_api_config) {
      selectedApiConfig.value = settings.selected_api_config;
      console.log('✅ 已恢复API配置选择:', selectedApiConfig.value);
    } else {
      console.log('ℹ️ 未找到已保存的API配置选择，默认使用个性配置');
      selectedApiConfig.value = '个性配置';
    }
  } catch (error) {
    console.error('加载API配置失败:', error);
  }
};

// 加载API用量
const loadApiUsage = async () => {
  try {
    loadingUsage.value = true;
    const configName = selectedUsageConfig.value === 'all' ? undefined : selectedUsageConfig.value;
    const response = await apiService.getApiUsage(configName);
    usageSummary.value = response.summary || null;
    console.log('📊 加载API用量:', configName || '所有配置', usageSummary.value);
  } catch (error) {
    console.error('加载API用量失败:', error);
  } finally {
    loadingUsage.value = false;
  }
};

// 获取配置来源
const getConfigSource = (configName: string): string => {
  const config = apiConfigs.value.find(c => c.config_name === configName);
  return config?.source || 'unknown';
};

// 获取特定配置的详细数据
const getConfigDetailValue = (field: string): string => {
  if (!usageSummary.value) return '0';
  
  // 如果查看的是特定配置，数据在 by_config[config_name] 中
  if (selectedUsageConfig.value !== 'all' && usageSummary.value.by_config) {
    const configData = usageSummary.value.by_config[selectedUsageConfig.value];
    if (configData && configData[field] !== undefined) {
      return configData[field].toLocaleString();
    }
  }
  
  // 否则使用顶层数据
  const value = usageSummary.value[field];
  return value !== undefined ? value.toLocaleString() : '0';
};

// 处理API配置变更
const handleApiConfigChange = (value: string) => {
  // 配置变更时，暂不自动保存，等用户点击"保存选择"按钮
  console.log('选择API配置:', value);
};

// 保存API配置选择
const saveApiConfigSelection = async () => {
  if (!selectedApiConfig.value) {
    message.warning('请先选择一个API配置');
    return;
  }
  
  try {
    savingApiConfig.value = true;
    console.log('✏️ 正在保存API配置:', selectedApiConfig.value);
    const result = await apiService.updateUserSettings({
      selected_api_config: selectedApiConfig.value
    });
    console.log('✅ 保存结果:', result);
    message.success('API配置保存成功');
    
    // 通知父组件刷新API配置状态
    emit('api-config-changed', selectedApiConfig.value);
  } catch (error: any) {
    console.error('❌ 保存API配置失败:', error);
    message.error(error.message || '保存失败');
  } finally {
    savingApiConfig.value = false;
  }
};

// 格式化日期
const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString('zh-CN');
};

// 检查历史记录是否有分析数据
const hasAnalysisData = (history: AnalysisHistoryItem) => {
  return history.ai_output || history.chart_data || history.analysis_result;
};

// 处理历史记录点击事件
const handleHistoryClick = (history: AnalysisHistoryItem) => {
  if (!hasAnalysisData(history)) return;
  
  // 发出事件给父组件，重新显示历史分析结果
  emit('restore-history', history);
};

// 删除历史记录
const handleDeleteHistory = async (history: AnalysisHistoryItem) => {
  try {
    deletingHistoryId.value = history.id;
    const response = await apiService.deleteAnalysisHistory(history.id);
    
    if (response.success) {
      message.success('删除成功');
      await loadAnalysisHistory();
    } else {
      message.error(response.message);
    }
  } catch (error: any) {
    message.error('删除失败');
  } finally {
    deletingHistoryId.value = null;
  }
};

// 开始对话
const handleStartConversation = async (history: AnalysisHistoryItem) => {
  try {
    const response = await apiService.createConversation({
      history_id: history.id,
      title: `关于 ${history.stock_codes.join(', ')} 的对话`
    });
    
    if (response.success && response.conversation_id) {
      message.success('对话创建成功');
      await loadConversations();
      
      // 打开新创建的对话
      const newConversation = conversations.value.find(c => c.id === response.conversation_id);
      if (newConversation) {
        handleOpenConversation(newConversation);
      }
    } else {
      message.error(response.message);
    }
  } catch (error: any) {
    message.error('创建对话失败');
  }
};

// 打开对话
const handleOpenConversation = (conversation: Conversation) => {
  currentConversation.value = conversation;
  showConversation.value = true;
};

// 关闭对话
const handleCloseConversation = () => {
  showConversation.value = false;
  currentConversation.value = null;
  // 重新加载对话列表以获取最新消息数量
  loadConversations();
};

// 删除对话
const handleDeleteConversation = async (conversation: Conversation) => {
  try {
    deletingConversationId.value = conversation.id;
    const response = await apiService.deleteConversation(conversation.id);
    
    if (response.success) {
      message.success('删除成功');
      await loadConversations();
    } else {
      message.error(response.message);
    }
  } catch (error: any) {
    message.error('删除失败');
  } finally {
    deletingConversationId.value = null;
  }
};

// 初始化
onMounted(() => {
  // 先初始化认证状态（基于本地token）
  initializeAuthState();
  // 然后异步验证token有效性
  loadUserData();
});
</script>

<style scoped>
.user-panel {
  padding: 16px;
}

.auth-section {
  max-width: 400px;
  margin: 0 auto;
}

.user-info-section {
  max-width: 800px;
  margin: 0 auto;
}

.user-tabs {
  margin-top: 16px;
}

.favorites-section,
.history-section,
.conversations-section {
  max-height: 400px;
  overflow-y: auto;
}

.history-item {
  transition: all 0.2s ease;
}

.history-item.clickable {
  cursor: pointer;
}

.history-item.clickable:hover {
  background-color: rgba(32, 128, 240, 0.05);
  border-radius: 8px;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.conversation-item {
  transition: all 0.2s ease;
  cursor: pointer;
}

.conversation-item:hover {
  background-color: rgba(32, 128, 240, 0.05);
  border-radius: 8px;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
</style> 