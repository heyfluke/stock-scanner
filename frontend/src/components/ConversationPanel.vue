<template>
  <div class="conversation-panel">
    <div class="conversation-header">
      <n-space align="center" justify="space-between">
        <n-space>
          <n-icon size="20" color="#2080f0">
            <ChatbubbleEllipsesOutline />
          </n-icon>
          <span class="conversation-title">{{ title }}</span>
        </n-space>
        <n-space>
          <n-button 
            size="small" 
            @click="getRandomPrompt"
            :loading="loadingPrompt"
            secondary
          >
            随机提示
          </n-button>
          <n-button 
            size="small" 
            type="error" 
            @click="handleClose"
            secondary
          >
            关闭
          </n-button>
        </n-space>
      </n-space>
    </div>

    <div class="conversation-messages" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-messages">
        <n-empty description="开始与AI对话">
          <template #extra>
            <n-text depth="3">点击"随机提示"获取建议问题，或直接输入您的问题</n-text>
            <n-text depth="3" style="margin-top: 8px; display: block;">AI将基于您的分析结果提供专业建议</n-text>
          </template>
        </n-empty>
      </div>
      
      <div v-else class="message-list">
        <div 
          v-for="message in messages" 
          :key="message.id"
          class="message-item"
          :class="message.role"
        >
          <div class="message-avatar">
            <n-avatar 
              :src="message.role === 'user' ? undefined : undefined"
              :fallback-src="message.role === 'user' ? undefined : undefined"
              size="small"
            >
              <template #default>
                <n-icon v-if="message.role === 'user'">
                  <PersonOutline />
                </n-icon>
                <n-icon v-else>
                  <SparklesOutline />
                </n-icon>
              </template>
            </n-avatar>
          </div>
          <div class="message-content">
            <div class="message-text" v-html="formatMessage(message.content)"></div>
            <div class="message-time">{{ formatTime(message.created_at) }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="conversation-input">
      <n-input-group>
        <n-input
          v-model:value="inputMessage"
          placeholder="输入您的问题..."
          :disabled="sending"
          @keyup.enter="handleSendMessage"
          size="large"
        />
        <n-button
          type="primary"
          size="large"
          :loading="sending"
          :disabled="!inputMessage.trim()"
          @click="handleSendMessage"
        >
          发送
        </n-button>
      </n-input-group>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue';
import {
  NSpace,
  NButton,
  NIcon,
  NEmpty,
  NText,
  NInput,
  NInputGroup,
  NAvatar,
  useMessage
} from 'naive-ui';
import {
  ChatbubbleEllipsesOutline,
  PersonOutline,
  SparklesOutline
} from '@vicons/ionicons5';
import { marked } from 'marked';
import { apiService } from '@/services/api';
import type { ConversationMessage } from '@/types';

const message = useMessage();

// Props
interface Props {
  conversationId: number;
  title: string;
  analysisContext?: string; // 新增：分析上下文
}

const props = defineProps<Props>();

// Emits
const emit = defineEmits<{
  close: [];
}>();

// 响应式数据
const messages = ref<ConversationMessage[]>([]);
const inputMessage = ref('');
const sending = ref(false);
const loadingPrompt = ref(false);
const messagesContainer = ref<HTMLElement | null>(null);

// 加载对话消息
const loadMessages = async () => {
  try {
    const loadedMessages = await apiService.getConversationMessages(props.conversationId);
    messages.value = loadedMessages;
    await nextTick();
    scrollToBottom();
  } catch (error) {
    message.error('加载对话消息失败');
  }
};

// 发送消息
const handleSendMessage = async () => {
  if (!inputMessage.value.trim() || sending.value) return;
  
  const messageText = inputMessage.value.trim();
  inputMessage.value = '';
  sending.value = true;
  
  try {
    // 添加用户消息到界面
    const userMessage: ConversationMessage = {
      id: Date.now(), // 临时ID
      role: 'user',
      content: messageText,
      created_at: new Date().toISOString()
    };
    messages.value.push(userMessage);
    await nextTick();
    scrollToBottom();
    
    // 发送消息到后端
    const stream = await apiService.sendMessage(props.conversationId, messageText);
    
    if (stream) {
      // 创建AI回复消息
      const aiMessage: ConversationMessage = {
        id: Date.now() + 1, // 临时ID
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString()
      };
      messages.value.push(aiMessage);
      await nextTick();
      scrollToBottom();
      
      // 处理流式响应
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value, { stream: true });
          buffer += chunk;
          
          // 按行分割并处理
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // 保留不完整的行
          
          for (const line of lines) {
            if (line.trim()) {
              try {
                const data = JSON.parse(line);
                console.log('收到流数据:', data); // 调试日志
                
                if (data.content) {
                  aiMessage.content += data.content;
                  console.log('当前AI消息内容:', aiMessage.content); // 调试日志
                  // 强制触发响应式更新
                  messages.value = [...messages.value];
                  // 实时更新显示
                  await nextTick();
                  scrollToBottom();
                }
                
                if (data.status === 'completed') {
                  console.log('流式响应完成'); // 调试日志
                  // 重新加载消息以获取正确的ID
                  await loadMessages();
                  break;
                }
                
                if (data.status === 'error') {
                  console.error('流式响应错误:', data.error);
                  message.error(`AI响应错误: ${data.error}`);
                  break;
                }
              } catch (e) {
                console.error('JSON解析错误:', e, '原始数据:', line);
              }
            }
          }
        }
        
        // 处理剩余的buffer
        if (buffer.trim()) {
          try {
            const data = JSON.parse(buffer);
            if (data.content) {
              aiMessage.content += data.content;
              await nextTick();
              scrollToBottom();
            }
          } catch (e) {
            console.error('处理剩余buffer时出错:', e);
          }
        }
      } finally {
        reader.releaseLock();
      }
    } else {
      message.error('发送消息失败');
    }
  } catch (error) {
    message.error('发送消息失败');
  } finally {
    sending.value = false;
  }
};

// 获取随机提示
const getRandomPrompt = async () => {
  loadingPrompt.value = true;
  try {
    const prompt = await apiService.getRandomPrompt();
    if (prompt) {
      inputMessage.value = prompt;
    }
  } catch (error) {
    message.error('获取随机提示失败');
  } finally {
    loadingPrompt.value = false;
  }
};

// 关闭对话
const handleClose = () => {
  emit('close');
};

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

// 配置marked选项
marked.use({
  breaks: true, // 支持换行
  gfm: true, // GitHub风格Markdown
});

// 格式化消息内容
const formatMessage = (content: string) => {
  if (!content) return '';
  
  console.log('格式化消息内容:', content); // 调试日志
  
  try {
    // 使用marked解析Markdown
    const result = marked(content);
    console.log('Markdown解析结果:', result); // 调试日志
    return result;
  } catch (error) {
    console.error('Markdown解析错误:', error);
    // 如果解析失败，回退到简单的换行处理
    return content.replace(/\n/g, '<br>');
  }
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

// 监听消息变化，自动滚动
watch(messages, () => {
  nextTick(() => {
    scrollToBottom();
  });
});

// 组件挂载时加载消息
onMounted(async () => {
  await loadMessages();
  
  // 移除自动发送分析上下文的功能
  // 让用户主动发送消息时才提供上下文
});


</script>

<style scoped>
.conversation-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.conversation-header {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
  border-radius: 8px 8px 0 0;
}

.conversation-title {
  font-weight: 500;
  color: #333;
}

.conversation-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  min-height: 300px;
}

.empty-messages {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.message-item.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
}

.message-content {
  flex: 1;
  max-width: 70%;
}

.message-item.user .message-content {
  text-align: right;
}

.message-text {
  padding: 12px 16px;
  border-radius: 12px;
  background: #f5f5f5;
  color: #333;
  line-height: 1.5;
  word-wrap: break-word;
}

/* Markdown样式 */
.message-text :deep(h1),
.message-text :deep(h2),
.message-text :deep(h3),
.message-text :deep(h4),
.message-text :deep(h5),
.message-text :deep(h6) {
  margin: 8px 0 4px 0;
  font-weight: 600;
  color: #333;
}

.message-text :deep(h1) { font-size: 1.4em; }
.message-text :deep(h2) { font-size: 1.3em; }
.message-text :deep(h3) { font-size: 1.2em; }
.message-text :deep(h4) { font-size: 1.1em; }
.message-text :deep(h5) { font-size: 1.0em; }
.message-text :deep(h6) { font-size: 0.9em; }

.message-text :deep(p) {
  margin: 4px 0;
}

.message-text :deep(ul),
.message-text :deep(ol) {
  margin: 4px 0;
  padding-left: 20px;
}

.message-text :deep(li) {
  margin: 2px 0;
}

.message-text :deep(blockquote) {
  margin: 8px 0;
  padding: 8px 12px;
  border-left: 4px solid #2080f0;
  background: #f8f9fa;
  color: #666;
}

.message-text :deep(code) {
  background: #f1f3f4;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.9em;
}

.message-text :deep(pre) {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}

.message-text :deep(pre code) {
  background: none;
  padding: 0;
}

.message-text :deep(strong) {
  font-weight: 600;
}

.message-text :deep(em) {
  font-style: italic;
}

.message-text :deep(a) {
  color: #2080f0;
  text-decoration: none;
}

.message-text :deep(a:hover) {
  text-decoration: underline;
}

.message-text :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}

.message-text :deep(th),
.message-text :deep(td) {
  border: 1px solid #ddd;
  padding: 6px 8px;
  text-align: left;
}

.message-text :deep(th) {
  background: #f8f9fa;
  font-weight: 600;
}

.message-item.user .message-text {
  background: #2080f0;
  color: white;
}

.message-item.assistant .message-text {
  background: #f0f9ff;
  border: 1px solid #e6f4ff;
}

.message-time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.message-item.user .message-time {
  text-align: right;
}

.conversation-input {
  padding: 16px;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
  border-radius: 0 0 8px 8px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .conversation-messages {
    padding: 12px;
  }
  
  .message-content {
    max-width: 85%;
  }
  
  .conversation-input {
    padding: 12px;
  }
}
</style> 