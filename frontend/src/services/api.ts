import axios from 'axios';
import type { 
  AnalyzeRequest, TestApiRequest, TestApiResponse, SearchResult, 
  LoginRequest, LoginResponse, UserRegisterRequest, UserProfile,
  UserFavorite, FavoriteRequest, AnalysisHistoryItem, 
  UserSettings, UserSettingsRequest, CreateConversationRequest, Conversation, ConversationMessage,
  AgentPreset
} from '@/types';

// API前缀
const API_PREFIX = '/api';

// 创建axios实例
const axiosInstance = axios.create({
  baseURL: API_PREFIX
});

// 请求拦截器，添加token
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器，处理401错误
axiosInstance.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      // 清除token
      localStorage.removeItem('token');
      // 不要在这里跳转，避免循环重定向
    }
    return Promise.reject(error);
  }
);

export const apiService = {
  // 用户注册
  register: async (request: UserRegisterRequest): Promise<LoginResponse> => {
    try {
      const response = await axiosInstance.post('/register', request);
      if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
      }
      return response.data;
    } catch (error: any) {
      if (error.response) {
        return {
          success: false,
          message: error.response.data.detail || '注册失败',
        };
      }
      return {
        success: false,
        message: error.message || '注册失败'
      };
    }
  },

  // 用户登录（升级版）
  login: async (request: LoginRequest): Promise<LoginResponse> => {
    try {
      const response = await axiosInstance.post('/login', request);
      if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
      }
      return response.data;
    } catch (error: any) {
      if (error.response) {
        return {
          success: false,
          message: error.response.data.detail || '登录失败',
        };
      }
      return {
        success: false,
        message: error.message || '登录失败'
      };
    }
  },

  // 检查认证状态
  checkAuth: async (): Promise<boolean> => {
    try {
      const response = await axiosInstance.get('/check_auth');
      return response.data.authenticated === true;
    } catch (error) {
      // 认证失败，清除token
      localStorage.removeItem('token');
      return false;
    }
  },

  // 获取用户信息
  getUserProfile: async (): Promise<UserProfile | null> => {
    try {
      const response = await axiosInstance.get('/user/profile');
      return response.data;
    } catch (error) {
      return null;
    }
  },

  // 登出
  logout: async (): Promise<void> => {
    try {
      // 调用后端登出接口
      await axiosInstance.post('/logout');
    } catch (error) {
      // 即使后端调用失败，也要清除本地token
      console.warn('登出接口调用失败，但已清除本地token');
    } finally {
      // 清除本地token
      localStorage.removeItem('token');
    }
  },

  // 收藏功能
  addFavorite: async (request: FavoriteRequest): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await axiosInstance.post('/user/favorites', request);
      return { success: true, message: response.data.message };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.detail || '添加收藏失败'
      };
    }
  },

  removeFavorite: async (stockCode: string, marketType: string): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await axiosInstance.delete(`/user/favorites/${stockCode}?market_type=${marketType}`);
      return { success: true, message: response.data.message };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.detail || '移除收藏失败'
      };
    }
  },

  getFavorites: async (): Promise<UserFavorite[]> => {
    try {
      const response = await axiosInstance.get('/user/favorites');
      return response.data.favorites || [];
    } catch (error) {
      return [];
    }
  },

  // 历史记录功能
  getAnalysisHistory: async (limit: number = 50): Promise<AnalysisHistoryItem[]> => {
    try {
      const response = await axiosInstance.get(`/user/history?limit=${limit}`);
      return response.data.history || [];
    } catch (error) {
      return [];
    }
  },

  deleteAnalysisHistory: async (historyId: number): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await axiosInstance.delete(`/user/history/${historyId}`);
      return { success: true, message: response.data.message };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.detail || '删除历史记录失败'
      };
    }
  },

  // 对话功能
  createConversation: async (request: CreateConversationRequest): Promise<{ success: boolean; conversation_id?: number; message: string; status?: number }> => {
    try {
      const response = await axiosInstance.post('/conversations', request);
      return { 
        success: true, 
        conversation_id: response.data.conversation_id,
        message: response.data.message 
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.detail || '创建对话失败',
        status: error.response?.status
      };
    }
  },

  getConversations: async (historyId?: number): Promise<Conversation[]> => {
    try {
      const params = historyId ? `?history_id=${historyId}` : '';
      const response = await axiosInstance.get(`/conversations${params}`);
      return response.data.conversations || [];
    } catch (error) {
      return [];
    }
  },

  getConversationMessages: async (conversationId: number): Promise<ConversationMessage[]> => {
    try {
      const response = await axiosInstance.get(`/conversations/${conversationId}/messages`);
      return response.data.messages || [];
    } catch (error) {
      return [];
    }
  },

  sendMessage: async (conversationId: number, message: string): Promise<ReadableStream<Uint8Array> | null> => {
    try {
      // 构建完整的URL
      const baseURL = window.location.origin;
      
      // 构建headers，只有在token存在时才添加Authorization
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };
      
      const token = localStorage.getItem('token');
      if (token && token.trim()) {
        headers['Authorization'] = `Bearer ${token}`;
      } else {
        console.warn('发送消息时未找到有效的认证token，这可能会导致认证失败');
      }
      
      const response = await fetch(`${baseURL}/api/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message })
      });
      
      if (!response.ok) {
        let errorMessage = `HTTP error! status: ${response.status}`;
        try {
          const errorText = await response.text();
          if (errorText) {
            errorMessage += ` - ${errorText}`;
          }
        } catch (e) {
          // 忽略解析错误文本失败的情况
        }
        throw new Error(errorMessage);
      }
      
      return response.body;
    } catch (error) {
      console.error('发送消息失败:', error);
      return null;
    }
  },

  deleteConversation: async (conversationId: number): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await axiosInstance.delete(`/conversations/${conversationId}`);
      return { success: true, message: response.data.message };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.detail || '删除对话失败'
      };
    }
  },

  getRandomPrompt: async (): Promise<string> => {
    try {
      const response = await axiosInstance.get('/conversations/prompts/random');
      return response.data.prompt || '';
    } catch (error) {
      return '';
    }
  },

  // 用户设置功能
  updateUserSettings: async (settings: UserSettingsRequest): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await axiosInstance.put('/user/settings', settings);
      return { success: true, message: response.data.message };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.detail || '设置更新失败'
      };
    }
  },

  getUserSettings: async (): Promise<UserSettings | null> => {
    try {
      const response = await axiosInstance.get('/user/settings');
      return response.data.settings;
    } catch (error) {
      return null;
    }
  },

  // 分析股票
  analyzeStocks: async (request: AnalyzeRequest) => {
    return axiosInstance.post('/analyze', request, {
      responseType: 'stream'
    });
  },

  // 获取多Agent预设
  getAgentPresets: async (): Promise<AgentPreset[]> => {
    try {
      const response = await axiosInstance.get('/agent/presets');
      return response.data.presets || [];
    } catch (error) {
      return [];
    }
  },

  // 测试API连接
  testApiConnection: async (request: TestApiRequest): Promise<TestApiResponse> => {
    try {
      const response = await axiosInstance.post('/test_api_connection', request);
      return response.data;
    } catch (error: any) {
      if (error.response) {
        return error.response.data;
      }
      return {
        success: false,
        message: error.message || '连接失败'
      };
    }
  },

  // 搜索美股
  searchUsStocks: async (keyword: string): Promise<SearchResult[]> => {
    try {
      const response = await axiosInstance.get('/search_us_stocks', {
        params: { keyword }
      });
      return response.data.results || [];
    } catch (error) {
      console.error('搜索美股时出错:', error);
      return [];
    }
  },

  // 搜索基金
  searchFunds: async (keyword: string): Promise<SearchResult[]> => {
    try {
      const response = await axiosInstance.get('/search_funds', {
        params: { keyword }
      });
      return response.data.results || [];
    } catch (error) {
      console.error('搜索基金时出错:', error);
      return [];
    }
  },
  
  // 获取配置
  getConfig: async () => {
    try {
      const response = await axiosInstance.get('/config');
      return response.data;
    } catch (error) {
      console.error('获取配置时出错:', error);
      return {
        announcement: '',
        default_api_url: '',
        default_api_model: '',
        default_api_timeout: '60'
      };
    }
  },

  // 检查是否需要登录
  checkNeedLogin: async (): Promise<boolean> => {
    try {
      const response = await axiosInstance.get('/need_login');
      return response.data.require_login;
    } catch (error) {
      console.error('检查是否需要登录时出错:', error);
      // 默认为需要登录，确保安全
      return true;
    }
  },

  // 获取API配置列表
  getApiConfigs: async (): Promise<any> => {
    try {
      const response = await axiosInstance.get('/user/api-configs');
      return response.data;
    } catch (error) {
      console.error('获取API配置列表时出错:', error);
      return { configs: [] };
    }
  },

  // 获取API用量统计
  getApiUsage: async (configName?: string, yearMonth?: string): Promise<any> => {
    try {
      const params: any = {};
      if (configName) params.config_name = configName;
      if (yearMonth) params.year_month = yearMonth;
      
      const response = await axiosInstance.get('/user/api-usage', { params });
      return response.data;
    } catch (error) {
      console.error('获取API用量时出错:', error);
      return { summary: null, records: [] };
    }
  }
};
