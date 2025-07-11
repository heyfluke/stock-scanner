<template>
  <n-modal v-model:show="show" :width="900" preset="card" class="conversation-dialog">
    <template #header>
      <div class="dialog-header">
        <n-space align="center">
          <n-icon size="24" color="#2080f0">
            <ChatbubbleEllipsesOutline />
          </n-icon>
          <span class="dialog-title">AI 对话 - {{ stockInfo.code }}</span>
        </n-space>
        <n-button text @click="handleClose">
          <template #icon>
            <n-icon><CloseOutline /></n-icon>
          </template>
        </n-button>
      </div>
    </template>

    <div class="dialog-content">
      <!-- 左侧对话列表 -->
      <div class="conversation-list" v-if="conversations.length > 0">
        <div class="list-header">
          <n-space align="center" justify="space-between">
            <span class="list-title">对话列表</span>
            <n-button 
              size="small" 
              type="primary" 
              @click="handleCreateConversation"
              :loading="creatingConversation"
            >
              <template #icon>
                <n-icon><AddOutline /></n-icon>
              </template>
              新对话
            </n-button>
          </n-space>
        </div>
        
        <div class="list-content">
          <n-list>
            <n-list-item 
              v-for="conversation in conversations" 
              :key="conversation.id"
              :class="{ 'active': currentConversation?.id === conversation.id }"
              @click="handleSelectConversation(conversation)"
            >
              <n-thing>
                <template #header>
                  <n-space align="center" justify="space-between">
                    <span class="conversation-title">{{ conversation.title }}</span>
                    <n-tag size="small" type="info">
                      {{ conversation.message_count }}条消息
                    </n-tag>
                  </n-space>
                </template>
                <template #description>
                  <n-text depth="3">{{ formatTime(conversation.updated_at) }}</n-text>
                </template>
              </n-thing>
            </n-list-item>
          </n-list>
        </div>
      </div>

      <!-- 右侧对话内容 -->
      <div class="conversation-content">
        <ConversationPanel
          v-if="currentConversation"
          :conversation-id="currentConversation.id"
          :title="currentConversation.title"
          :analysis-context="buildAnalysisContext()"
          @close="handleCloseConversation"
        />
        <div v-else class="empty-content">
          <n-empty description="选择一个对话或创建新对话">
            <template #extra>
              <n-button type="primary" @click="handleCreateConversation">
                开始新对话
              </n-button>
            </template>
          </n-empty>
        </div>
      </div>
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import {
  NModal,
  NSpace,
  NIcon,
  NButton,
  NList,
  NListItem,
  NThing,
  NTag,
  NText,
  NEmpty,
  useMessage
} from 'naive-ui';
import {
  ChatbubbleEllipsesOutline,
  CloseOutline,
  AddOutline
} from '@vicons/ionicons5';
import { apiService } from '@/services/api';
import type { StockInfo, Conversation } from '@/types';
import ConversationPanel from './ConversationPanel.vue';

const message = useMessage();

// Props
interface Props {
  show: boolean;
  stockInfo: StockInfo;
}

const props = defineProps<Props>();

// Emits
const emit = defineEmits<{
  'update:show': [value: boolean];
}>();

// 响应式数据
const conversations = ref<Conversation[]>([]);
const currentConversation = ref<Conversation | null>(null);
const creatingConversation = ref(false);
const hasAttemptedCreate = ref(false); // 标记是否已经尝试过创建对话

// 计算属性
const show = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value)
});

// 加载对话列表
const loadConversations = async () => {
  try {
    // 先获取历史记录，找到对应的历史记录ID
    const historyId = await findHistoryIdByStock();
    
    if (historyId) {
      // 根据历史记录ID获取对话
      conversations.value = await apiService.getConversations(historyId);
    } else {
      // 如果没有找到对应的历史记录，加载所有对话
      conversations.value = await apiService.getConversations();
    }
    
    // 如果没有对话且还没有尝试过创建，则创建新对话
    if (conversations.value.length === 0 && !hasAttemptedCreate.value) {
      hasAttemptedCreate.value = true;
      await handleCreateConversation();
    }
  } catch (error) {
    message.error('加载对话列表失败');
  }
};

// 根据股票信息查找历史记录ID
const findHistoryIdByStock = async (): Promise<number | null> => {
  try {
    const history = await apiService.getAnalysisHistory(50);
    
    // 查找包含当前股票代码的历史记录
    for (const record of history) {
      if (record.stock_codes && Array.isArray(record.stock_codes)) {
        if (record.stock_codes.includes(props.stockInfo.code)) {
          return record.id;
        }
      }
    }
    
    return null;
  } catch (error) {
    console.error('查找历史记录失败:', error);
    return null;
  }
};

// 创建新对话
const handleCreateConversation = async () => {
  try {
    creatingConversation.value = true;
    
    // 构建包含分析上下文的对话标题
    const analysisContext = buildAnalysisContext();
    const title = `关于 ${props.stockInfo.code} 的分析对话`;
    
    // 查找对应的历史记录ID
    const historyId = await findHistoryIdByStock();
    
    if (!historyId) {
      message.error('未找到对应的分析历史记录，无法创建对话');
      return;
    }
    
    const response = await apiService.createConversation({
      history_id: historyId,
      title: title
    });
    
    if (response.success && response.conversation_id) {
      message.success('对话创建成功');
      await loadConversations();
      
      // 选择新创建的对话
      const newConversation = conversations.value.find(c => c.id === response.conversation_id);
      if (newConversation) {
        handleSelectConversation(newConversation);
      }
    } else {
      // 检查是否是频率限制错误
      if (response.status === 429) {
        message.warning('创建对话过于频繁，请稍后再试');
      } else {
        message.error(response.message || '创建对话失败');
      }
    }
  } catch (error: any) {
    console.error('创建对话失败:', error);
    message.error('创建对话失败');
  } finally {
    creatingConversation.value = false;
  }
};

// 选择对话
const handleSelectConversation = (conversation: Conversation) => {
  currentConversation.value = conversation;
};

// 关闭对话
const handleCloseConversation = () => {
  currentConversation.value = null;
  loadConversations(); // 重新加载以获取最新消息数量
};

// 关闭对话框
const handleClose = () => {
  show.value = false;
};

// 格式化时间
const formatTime = (timeStr: string) => {
  const date = new Date(timeStr);
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// 构建分析上下文
const buildAnalysisContext = () => {
  const context = [];
  
  // 基本信息
  context.push(`股票代码: ${props.stockInfo.code}`);
  if (props.stockInfo.name) {
    context.push(`股票名称: ${props.stockInfo.name}`);
  }
  
  // 价格信息
  if (props.stockInfo.price !== undefined) {
    context.push(`当前价格: ${props.stockInfo.price.toFixed(2)}`);
  }
  
  if (props.stockInfo.changePercent !== undefined) {
    const sign = props.stockInfo.changePercent > 0 ? '+' : '';
    context.push(`涨跌幅: ${sign}${props.stockInfo.changePercent.toFixed(2)}%`);
  }
  
  // 技术指标
  if (props.stockInfo.rsi !== undefined) {
    context.push(`RSI: ${props.stockInfo.rsi.toFixed(2)}`);
  }
  
  if (props.stockInfo.ma_trend) {
    context.push(`均线趋势: ${getChineseTrend(props.stockInfo.ma_trend)}`);
  }
  
  if (props.stockInfo.macd_signal) {
    context.push(`MACD信号: ${getChineseSignal(props.stockInfo.macd_signal)}`);
  }
  
  if (props.stockInfo.volume_status) {
    context.push(`成交量: ${getChineseVolumeStatus(props.stockInfo.volume_status)}`);
  }
  
  // 评分和推荐
  if (props.stockInfo.score !== undefined) {
    context.push(`评分: ${props.stockInfo.score}`);
  }
  
  if (props.stockInfo.recommendation) {
    context.push(`推荐: ${props.stockInfo.recommendation}`);
  }
  
  // 分析结果
  if (props.stockInfo.analysis) {
    context.push(`\n分析结果:\n${props.stockInfo.analysis}`);
  }
  
  return context.join('\n');
};

// 辅助函数：获取中文趋势描述
const getChineseTrend = (trend: string): string => {
  const trendMap: Record<string, string> = {
    'UP': '上升',
    'DOWN': '下降',
    'NEUTRAL': '平稳'
  };
  return trendMap[trend] || trend;
};

// 辅助函数：获取中文信号描述
const getChineseSignal = (signal: string): string => {
  const signalMap: Record<string, string> = {
    'BUY': '买入',
    'SELL': '卖出',
    'HOLD': '持有',
    'NEUTRAL': '中性'
  };
  return signalMap[signal] || signal;
};

// 辅助函数：获取中文成交量状态描述
const getChineseVolumeStatus = (status: string): string => {
  const statusMap: Record<string, string> = {
    'HIGH': '放量',
    'LOW': '缩量',
    'NORMAL': '正常',
    'INCREASING': '增加',
    'DECREASING': '减少'
  };
  return statusMap[status] || status;
};

// 监听显示状态
watch(() => props.show, (newVal) => {
  if (newVal) {
    // 重置创建标记，允许重新尝试创建对话
    hasAttemptedCreate.value = false;
    loadConversations();
  }
});

// 组件挂载时加载数据
onMounted(() => {
  if (props.show) {
    loadConversations();
  }
});
</script>

<style scoped>
.conversation-dialog {
  max-height: 80vh;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.dialog-title {
  font-size: 18px;
  font-weight: 500;
  color: #333;
}

.dialog-content {
  display: flex;
  height: 600px;
  gap: 16px;
}

.conversation-list {
  width: 300px;
  border-right: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
}

.conversation-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 当没有对话列表时，对话内容占据全宽 */
.dialog-content:has(.conversation-list:not([style*="display: none"])) .conversation-content {
  flex: 1;
}

.dialog-content:not(:has(.conversation-list)) .conversation-content {
  width: 100%;
}

.list-header {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.list-title {
  font-weight: 500;
  color: #333;
}

.list-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conversation-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.empty-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

:deep(.n-list-item) {
  cursor: pointer;
  border-radius: 8px;
  margin-bottom: 8px;
  transition: all 0.2s ease;
}

:deep(.n-list-item:hover) {
  background-color: rgba(32, 128, 240, 0.05);
}

:deep(.n-list-item.active) {
  background-color: rgba(32, 128, 240, 0.1);
  border: 1px solid rgba(32, 128, 240, 0.3);
}

.conversation-title {
  font-weight: 500;
  color: #333;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .dialog-content {
    flex-direction: column;
    height: auto;
  }
  
  .conversation-list {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #f0f0f0;
    max-height: 200px;
  }
}
</style> 