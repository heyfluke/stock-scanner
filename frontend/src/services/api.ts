import axios from 'axios';
import type { 
  AnalyzeRequest, TestApiRequest, TestApiResponse, SearchResult, 
  LoginRequest, LoginResponse, UserRegisterRequest, UserProfile,
  UserFavorite, FavoriteRequest, AnalysisHistoryItem, 
  UserSettings, UserSettingsRequest 
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
  logout: () => {
    localStorage.removeItem('token');
    // 不在这里处理跳转，让调用方处理路由
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
  }
};
