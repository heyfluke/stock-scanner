<template>
  <div class="analysis-form-container">
    <n-form :label-width="80" :label-placement="isMobile ? 'top' : 'left'">
      <n-form-item label="选择市场类型">
        <n-select
          v-model:value="marketType"
          :options="marketOptions"
          @update:value="handleMarketTypeChange"
        />
      </n-form-item>
      
      <n-form-item label="分析方案">
        <n-select
          v-model:value="selectedPresetId"
          :options="presetOptions"
          placeholder="标准版"
        />
      </n-form-item>

      <n-form-item :label='marketType === "US" ? "股票搜索" : "基金搜索"' v-if="showSearch">
        <StockSearch :market-type="marketType" @select="addSelectedStock" />
      </n-form-item>
      
      <n-form-item label="输入代码">
        <n-input
          v-model:value="stockCodes"
          type="textarea"
          placeholder="输入股票、基金代码，多个代码用逗号、空格或换行分隔"
          :autosize="{ minRows: 3, maxRows: 6 }"
        />
      </n-form-item>
      
      <n-form-item label="分析天数">
        <n-select
          v-model:value="analysisDays"
          :options="analysisDaysOptions"
        />
      </n-form-item>
      
      <n-form-item label="分析选项" v-if="isLoggedIn">
        <n-checkbox v-model:checked="includePortfolio">
          包含我的持仓信息
        </n-checkbox>
        <n-text depth="3" style="font-size: 12px; margin-top: 4px; display: block;">
          勾选后，AI将结合您的持仓组合进行分析并给出建议
        </n-text>
      </n-form-item>
      
      <div class="action-buttons">
        <n-button
          type="primary"
          size="large"
          :disabled="!stockCodes.trim()"
          @click="handleStartAnalysis"
          block
        >
          开始分析
        </n-button>
      </div>
    </n-form>
    
    <!-- 分析说明 -->
    <n-card class="help-info" size="small" style="margin-top: 16px;">
      <template #header>
        <n-space align="center">
          <n-icon :component="InformationCircleIcon" />
          <span>使用说明</span>
        </n-space>
      </template>
      
      <n-ul>
        <n-li>支持多个股票代码同时分析，用逗号、空格或换行分隔</n-li>
        <n-li>每次分析会创建一个新的标签页，最多支持8个并行分析</n-li>
        <n-li v-if="marketType === 'A'">A股代码示例：000001, 600519, 002415</n-li>
        <n-li v-if="marketType === 'HK'">港股代码示例：00700, 09988, 01024</n-li>
        <n-li v-if="marketType === 'US'">美股代码示例：AAPL, MSFT, TSLA</n-li>
        <n-li v-if="marketType === 'ETF'">ETF代码示例：159919, 512880, 588000</n-li>
        <n-li v-if="marketType === 'LOF'">LOF代码示例：161725, 163402, 160632</n-li>
      </n-ul>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { 
  NForm, 
  NFormItem, 
  NSelect, 
  NInput, 
  NButton,
  NCard,
  NSpace,
  NIcon,
  NUl,
  NLi,
  NCheckbox,
  NText,
  useMessage
} from 'naive-ui';
import { 
  InformationCircleOutline as InformationCircleIcon,
} from '@vicons/ionicons5';

import StockSearch from './StockSearch.vue';
import { validateMultipleStockCodes, MarketType } from '@/utils/stockValidator';
import type { ApiConfig, AgentPreset } from '@/types';
import { apiService } from '@/services/api';
import { onMounted } from 'vue';

// Props
interface Props {
  apiConfig: ApiConfig;
}

const props = defineProps<Props>();

// Emits
const emit = defineEmits<{
  'start-analysis': [config: {
    stockCodes: string[];
    marketType: string;
    analysisDays: number;
    apiConfig: ApiConfig;
    presetId?: string;
    includePortfolio?: boolean;
  }];
}>();

// 使用Naive UI的组件API
const message = useMessage();

// 表单状态
const marketType = ref('A');
const stockCodes = ref('');
const analysisDays = ref(30);
const selectedPresetId = ref<string | null>('standard');
const includePortfolio = ref(false);
const isLoggedIn = ref(false);
const presets = ref<AgentPreset[]>([]);
const presetOptions = computed(() => {
  const items = presets.value.map(p => ({ label: p.name, value: p.id }));
  // 确保标准版在首位
  return [{ label: '标准版', value: 'standard' }, ...items.filter(i => i.value !== 'standard')];
});

// 移动端检测
const isMobile = computed(() => {
  return window.innerWidth <= 768;
});

// 市场选项
const marketOptions = [
  { label: 'A股', value: 'A' },
  { label: '港股', value: 'HK' },
  { label: '美股', value: 'US', showSearch: true },
  { label: 'ETF', value: 'ETF', showSearch: true  },
  { label: 'LOF', value: 'LOF', showSearch: true  }
];

// 分析天数选项
const analysisDaysOptions = [
  { label: '7天', value: 7 },
  { label: '14天', value: 14 },
  { label: '30天（推荐）', value: 30 },
  { label: '60天', value: 60 },
  { label: '90天', value: 90 }
];

// 是否显示搜索
const showSearch = computed(() => 
  marketOptions.find(option => option.value === marketType.value)?.showSearch
);

// 处理市场类型变更
const handleMarketTypeChange = () => {
  stockCodes.value = '';
};

// 添加选择的股票
const addSelectedStock = (symbol: string) => {
  // 确保symbol不包含序号或其他不需要的信息
  const cleanSymbol = symbol.trim().replace(/^\d+\.\s*/, '');
  
  if (stockCodes.value) {
    stockCodes.value += ', ' + cleanSymbol;
  } else {
    stockCodes.value = cleanSymbol;
  }
};

// 开始分析
const handleStartAnalysis = () => {
  if (!stockCodes.value.trim()) {
    message.warning('请输入股票代码');
    return;
  }
  
  // 解析股票代码
  const codes = stockCodes.value
    .split(/[,\s\n]+/)
    .map((code: string) => code.trim())
    .filter((code: string) => code);
  
  if (codes.length === 0) {
    message.warning('未找到有效的股票代码');
    return;
  }
  
  // 去除重复的股票代码
  const uniqueCodes = Array.from(new Set(codes));
  
  // 检查是否有重复代码被移除
  if (uniqueCodes.length < codes.length) {
    message.info(`已自动去除${codes.length - uniqueCodes.length}个重复的股票代码`);
  }
  
  // 在前端验证股票代码
  const marketTypeEnum = marketType.value as keyof typeof MarketType;
  const invalidCodes = validateMultipleStockCodes(
    uniqueCodes, 
    MarketType[marketTypeEnum]
  );
  
  // 如果有无效代码，显示错误信息并返回
  if (invalidCodes.length > 0) {
    const errorMessages = invalidCodes.map(item => item.errorMessage).join('\n');
    message.error(`股票代码验证失败:${errorMessages}`);
    return;
  }
  
  // 发射开始分析事件
  emit('start-analysis', {
    stockCodes: uniqueCodes,
    marketType: marketType.value,
    analysisDays: analysisDays.value,
    apiConfig: props.apiConfig,
    presetId: selectedPresetId.value || undefined,
    includePortfolio: includePortfolio.value
  });
  
  // 清空输入
  stockCodes.value = '';
  
  message.success(`开始分析 ${uniqueCodes.length} 只股票，将在新标签页中显示结果`);
};

// 加载后端预设列表
onMounted(async () => {
  // 检查登录状态
  const token = localStorage.getItem('token');
  if (token) {
    try {
      isLoggedIn.value = await apiService.checkAuth();
    } catch (error) {
      console.error('检查登录状态失败:', error);
      isLoggedIn.value = false;
    }
  }
  
  // 加载预设
  try {
    const serverPresets = await apiService.getAgentPresets();
    if (Array.isArray(serverPresets) && serverPresets.length > 0) {
      presets.value = serverPresets;
    }
  } catch (e) {
    // 忽略错误，保持仅有标准版
  }
});
</script>

<style scoped>
.analysis-form-container {
  padding: 16px;
}

.action-buttons {
  margin-top: 24px;
}

.help-info {
  border: 1px solid #e0e0e6;
  background-color: #fafafa;
}

.help-info :deep(.n-card-header) {
  padding: 12px 16px;
  color: #666;
}

.help-info :deep(.n-card__content) {
  padding: 12px 16px;
}

.help-info :deep(.n-ul) {
  margin: 0;
}

.help-info :deep(.n-li) {
  font-size: 14px;
  color: #666;
  margin-bottom: 4px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .analysis-form-container {
    padding: 12px;
  }
  
  .action-buttons {
    margin-top: 16px;
  }
  
  .help-info {
    margin-top: 12px;
  }
  
  .help-info :deep(.n-card-header) {
    padding: 8px 12px;
  }
  
  .help-info :deep(.n-card__content) {
    padding: 8px 12px;
  }
  
  .help-info :deep(.n-li) {
    font-size: 13px;
  }
}
</style> 