<template>
  <div class="user-panel">
    <!-- 用户未登录状态 -->
    <div v-if="!isLoggedIn" class="auth-section">
      <n-tabs type="segment" animated>
        <n-tab-pane name="login" tab="登录">
          <n-form ref="loginFormRef" :model="loginForm" :rules="loginRules">
            <n-form-item path="username" label="用户名">
              <n-input v-model:value="loginForm.username" placeholder="请输入用户名" />
            </n-form-item>
            <n-form-item path="password" label="密码">
              <n-input 
                v-model:value="loginForm.password" 
                type="password" 
                placeholder="请输入密码" 
                @keyup.enter="handleLogin"
              />
            </n-form-item>
            <n-button 
              type="primary" 
              block 
              :loading="loginLoading" 
              @click="handleLogin"
            >
              登录
            </n-button>
          </n-form>
        </n-tab-pane>
        
        <n-tab-pane name="register" tab="注册">
          <n-form ref="registerFormRef" :model="registerForm" :rules="registerRules">
            <n-form-item path="username" label="用户名">
              <n-input v-model:value="registerForm.username" placeholder="请输入用户名" />
            </n-form-item>
            <n-form-item path="display_name" label="显示名称">
              <n-input v-model:value="registerForm.display_name" placeholder="请输入显示名称（可选）" />
            </n-form-item>
            <n-form-item path="email" label="邮箱">
              <n-input v-model:value="registerForm.email" placeholder="请输入邮箱（可选）" />
            </n-form-item>
            <n-form-item path="password" label="密码">
              <n-input 
                v-model:value="registerForm.password" 
                type="password" 
                placeholder="请输入密码" 
              />
            </n-form-item>
            <n-form-item path="confirmPassword" label="确认密码">
              <n-input 
                v-model:value="registerForm.confirmPassword" 
                type="password" 
                placeholder="请再次输入密码" 
                @keyup.enter="handleRegister"
              />
            </n-form-item>
            <n-button 
              type="primary" 
              block 
              :loading="registerLoading" 
              @click="handleRegister"
            >
              注册
            </n-button>
          </n-form>
        </n-tab-pane>
      </n-tabs>
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
                  <n-thing>
                    <template #header>
                      <n-space>
                        <span>{{ history.stock_codes.join(', ') }}</span>
                        <n-tag size="small">{{ history.market_type }}</n-tag>
                      </n-space>
                    </template>
                    <template #description>
                      分析天数: {{ history.analysis_days }}天
                    </template>
                    <template #footer>
                      <n-text depth="3" style="font-size: 12px;">
                        分析时间: {{ formatDate(history.created_at) }}
                      </n-text>
                    </template>
                  </n-thing>
                </n-list-item>
              </n-list>
            </div>
          </n-tab-pane>
        </n-tabs>
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import {
  NCard, NTabs, NTabPane, NForm, NFormItem, NInput, NButton,
  NDescriptions, NDescriptionsItem, NList, NListItem, NThing,
  NTag, NSpace, NText, NEmpty, NIcon, useMessage
} from 'naive-ui';
import type { FormInst, FormRules } from 'naive-ui';
import { LogOutOutline as LogOutIcon, TrashOutline as TrashIcon } from '@vicons/ionicons5';
import { apiService } from '@/services/api';
import type { 
  UserProfile, UserRegisterRequest, LoginRequest, 
  UserFavorite, AnalysisHistoryItem 
} from '@/types';

const message = useMessage();

// 用户状态
const isLoggedIn = ref(false);
const userProfile = ref<UserProfile | null>(null);
const favorites = ref<UserFavorite[]>([]);
const analysisHistory = ref<AnalysisHistoryItem[]>([]);

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
const handleLogout = () => {
  apiService.logout();
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
      isLoggedIn.value = false;
      return;
    }
    
    // 获取用户信息
    const profile = await apiService.getUserProfile();
    if (profile) {
      userProfile.value = profile;
      isLoggedIn.value = true;
      
      // 加载收藏和历史记录
      await Promise.all([
        loadFavorites(),
        loadAnalysisHistory()
      ]);
    }
  } catch (error) {
    console.error('加载用户数据失败:', error);
    isLoggedIn.value = false;
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

// 格式化日期
const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString('zh-CN');
};

// 初始化
onMounted(() => {
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
.history-section {
  max-height: 400px;
  overflow-y: auto;
}
</style> 