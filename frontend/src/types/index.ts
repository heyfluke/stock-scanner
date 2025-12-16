// API接口相关类型
export interface ApiConfig {
  apiUrl: string;
  apiKey: string;
  apiModel: string;
  apiTimeout: string;
  saveApiConfig: boolean;
}

// 登录相关类型
export interface LoginRequest {
  password?: string;  // 兼容旧版密码登录
  username?: string;  // 新用户系统登录
}

export interface LoginResponse {
  access_token?: string;
  token_type?: string;
  success?: boolean;
  message?: string;
  user?: UserProfile;
}

// 用户相关类型
export interface UserProfile {
  id: number;
  username: string;
  display_name: string;
  email?: string;
  created_at?: string;
}

export interface UserRegisterRequest {
  username: string;
  password: string;
  email?: string;
  display_name?: string;
}

export interface UserFavorite {
  id: number;
  stock_code: string;
  market_type: string;
  display_name?: string;
  tags: string[];
  created_at: string;
}

export interface FavoriteRequest {
  stock_code: string;
  market_type: string;
  display_name?: string;
  tags?: string[];
}

export interface AnalysisHistoryItem {
  id: number;
  stock_codes: string[];
  market_type: string;
  analysis_days: number;
  analysis_result?: any;
  ai_output?: string;
  chart_data?: any;
  created_at: string;
}

export interface Conversation {
  id: number;
  history_id: number;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface CreateConversationRequest {
  history_id: number;
  title?: string;
}

export interface SendMessageRequest {
  message: string;
}

export interface ConversationResponse {
  content?: string;
  status: 'streaming' | 'completed' | 'error';
  error?: string;
}

export interface UserSettings {
  default_market_type: string;
  default_analysis_days: number;
  api_preferences: Record<string, any>;
  ui_preferences: Record<string, any>;
  updated_at?: string;
}

export interface UserSettingsRequest {
  default_market_type?: string;
  default_analysis_days?: number;
  api_preferences?: Record<string, any>;
  ui_preferences?: Record<string, any>;
}

export interface TokenUsage {
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens: number;
  estimated?: boolean;
  input_chars?: number;
  output_chars?: number;
}

export interface StockInfo {
  code: string;
  name: string;
  marketType: string;
  price?: number;
  changePercent?: number;
  marketValue?: number;
  analysis?: string;
  analysisStatus: 'waiting' | 'analyzing' | 'completed' | 'error';
  error?: string;
  score?: number;
  recommendation?: string;
  price_change?: number;
  rsi?: number;
  ma_trend?: string;
  macd_signal?: string;
  volume_status?: string;
  analysis_date?: string;
  chart_data?: (string | number)[][];
  token_usage?: TokenUsage;
}

export interface SearchResult {
  symbol: string;
  name: string;
  market: string;
  market_value?: number;
  price_change?: number;
  rsi?: number;
  ma_trend?: string;
  macd_signal?: string;
  volume_status?: string;
  analysis_date?: string;
  ai_analysis_chunk?: string;
  chart_data?: (string | number)[][];
}

export interface MarketStatus {
  isOpen: boolean;
  nextTime: string;
  progressPercentage?: number;
}

export interface MarketTimeInfo {
  currentTime: string;
  cnMarket: MarketStatus;
  hkMarket: MarketStatus;
  usMarket: MarketStatus;
}

// 分析请求和响应
export interface AnalyzeRequest {
  stock_codes: string[];
  market_type: string;
  api_url?: string;
  api_key?: string;
  api_model?: string;
  api_timeout?: number;
  analysis_days?: number; // AI分析使用的天数，默认30天
  preset_id?: string; // 多Agent分析方案（可选）
  config_name?: string; // API配置名称（新增）
}

export interface TestApiRequest {
  api_url: string;
  api_key: string;
  api_model?: string;
  api_timeout: number;
}

export interface TestApiResponse {
  success: boolean;
  message: string;
  status_code?: number;
}

// 多Agent相关类型
export interface AgentPreset {
  id: string;
  name: string;
  description?: string;
  enabled?: boolean;
  is_builtin?: boolean;
}

// 流式响应类型
export interface StreamInitMessage {
  stream_type: 'single' | 'batch';
  stock_code?: string;
  stock_codes?: string[];
}

export interface StreamAnalysisUpdate {
  stock_code: string;
  analysis?: string;
  status: 'analyzing' | 'completed' | 'error';
  error?: string;
  name?: string;
  price?: number;
  change_percent?: number;
  price_change_value?: number;
  market_value?: number;
  score?: number;
  recommendation?: string;
  price_change?: number;
  rsi?: number;
  ma_trend?: string;
  macd_signal?: string;
  volume_status?: string;
  analysis_date?: string;
  ai_analysis_chunk?: string;
  chart_data?: (string | number)[][];
  token_usage?: TokenUsage;
}
