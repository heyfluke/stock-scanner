<template>
  <div class="portfolio-panel">
    <n-card title="我的持仓" :bordered="false">
      <template #header-extra>
        <n-button type="primary" @click="showAddModal = true">
          <template #icon>
            <n-icon><add-outline /></n-icon>
          </template>
          添加持仓
        </n-button>
      </template>

      <n-spin :show="loading">
        <n-empty v-if="!loading && holdings.length === 0" description="暂无持仓记录">
          <template #extra>
            <n-button size="small" @click="showAddModal = true">
              立即添加
            </n-button>
          </template>
        </n-empty>

        <n-list v-else bordered>
          <n-list-item v-for="holding in holdings" :key="holding.id">
            <template #prefix>
              <n-tag :type="getMarketTypeColor(holding.market_type)" size="small">
                {{ holding.market_type }}
              </n-tag>
            </template>

            <n-space vertical>
              <n-space align="center">
                <n-text strong style="font-size: 16px;">
                  {{ holding.stock_code }}
                </n-text>
                <n-text v-if="holding.display_name" depth="3">
                  {{ holding.display_name }}
                </n-text>
              </n-space>

              <n-descriptions :column="2" size="small">
                <n-descriptions-item label="持股数量">
                  {{ holding.shares.toLocaleString() }} 股
                </n-descriptions-item>
                <n-descriptions-item label="成本价">
                  ¥{{ holding.average_cost.toFixed(2) }}
                </n-descriptions-item>
                <n-descriptions-item label="持仓市值" :span="2">
                  ¥{{ (holding.shares * holding.average_cost).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                </n-descriptions-item>
                <n-descriptions-item v-if="holding.purchase_date" label="购买日期" :span="2">
                  {{ formatDate(holding.purchase_date) }}
                </n-descriptions-item>
                <n-descriptions-item v-if="holding.notes" label="备注" :span="2">
                  {{ holding.notes }}
                </n-descriptions-item>
              </n-descriptions>
            </n-space>

            <template #suffix>
              <n-space>
                <n-button size="small" @click="editHolding(holding)">
                  <template #icon>
                    <n-icon><create-outline /></n-icon>
                  </template>
                  编辑
                </n-button>
                <n-button size="small" type="error" @click="confirmDelete(holding)">
                  <template #icon>
                    <n-icon><trash-outline /></n-icon>
                  </template>
                  删除
                </n-button>
              </n-space>
            </template>
          </n-list-item>
        </n-list>

        <n-divider v-if="holdings.length > 0" />

        <n-statistic v-if="holdings.length > 0" label="总持仓市值" :value="totalValue">
          <template #prefix>¥</template>
        </n-statistic>
      </n-spin>
    </n-card>

    <!-- 添加/编辑持仓对话框 -->
    <n-modal
      v-model:show="showAddModal"
      :title="editingHolding ? '编辑持仓' : '添加持仓'"
      preset="card"
      style="width: 600px;"
      :mask-closable="false"
    >
      <n-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-placement="left"
        label-width="100"
      >
        <n-form-item label="股票代码" path="stock_code" v-if="!editingHolding">
          <n-input
            v-model:value="formData.stock_code"
            placeholder="例如：600519"
            :disabled="!!editingHolding"
          />
        </n-form-item>

        <n-form-item label="市场类型" path="market_type" v-if="!editingHolding">
          <n-select
            v-model:value="formData.market_type"
            :options="marketOptions"
            :disabled="!!editingHolding"
          />
        </n-form-item>

        <n-form-item label="股票名称" path="display_name">
          <n-input
            v-model:value="formData.display_name"
            placeholder="例如：贵州茅台（可选）"
          />
        </n-form-item>

        <n-form-item label="持股数量" path="shares">
          <n-input-number
            v-model:value="formData.shares"
            placeholder="持股数量"
            :min="0"
            :step="100"
            style="width: 100%;"
          />
        </n-form-item>

        <n-form-item label="成本价" path="average_cost">
          <n-input-number
            v-model:value="formData.average_cost"
            placeholder="平均成本价"
            :min="0"
            :precision="2"
            :step="0.01"
            style="width: 100%;"
          >
            <template #prefix>¥</template>
          </n-input-number>
        </n-form-item>

        <n-form-item label="购买日期" path="purchase_date">
          <n-date-picker
            v-model:value="formData.purchase_date"
            type="date"
            placeholder="选择购买日期"
            style="width: 100%;"
          />
        </n-form-item>

        <n-form-item label="备注" path="notes">
          <n-input
            v-model:value="formData.notes"
            type="textarea"
            placeholder="添加备注信息（可选）"
            :rows="3"
          />
        </n-form-item>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="showAddModal = false">取消</n-button>
          <n-button type="primary" @click="handleSubmit" :loading="submitting">
            {{ editingHolding ? '保存' : '添加' }}
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import {
  NCard, NButton, NIcon, NSpin, NEmpty, NList, NListItem, NTag, NSpace,
  NText, NDescriptions, NDescriptionsItem, NDivider, NStatistic,
  NModal, NForm, NFormItem, NInput, NInputNumber, NSelect, NDatePicker,
  useMessage, type FormInst, type FormRules
} from 'naive-ui';
import { AddOutline, CreateOutline, TrashOutline } from '@vicons/ionicons5';
import axios from 'axios';

interface PortfolioHolding {
  id: number;
  stock_code: string;
  market_type: string;
  display_name?: string;
  shares: number;
  average_cost: number;
  purchase_date?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

interface FormData {
  stock_code: string;
  market_type: string;
  display_name?: string;
  shares: number;
  average_cost: number;
  purchase_date?: number;
  notes?: string;
}

const message = useMessage();
const loading = ref(false);
const submitting = ref(false);
const holdings = ref<PortfolioHolding[]>([]);
const showAddModal = ref(false);
const editingHolding = ref<PortfolioHolding | null>(null);
const formRef = ref<FormInst | null>(null);

const formData = ref<FormData>({
  stock_code: '',
  market_type: 'A',
  display_name: '',
  shares: 0,
  average_cost: 0,
  purchase_date: undefined,
  notes: ''
});

const marketOptions = [
  { label: 'A股', value: 'A' },
  { label: '港股', value: 'HK' },
  { label: '美股', value: 'US' }
];

const formRules: FormRules = {
  stock_code: [
    { required: true, message: '请输入股票代码', trigger: 'blur' }
  ],
  market_type: [
    { required: true, message: '请选择市场类型', trigger: 'change' }
  ],
  shares: [
    { required: true, type: 'number', message: '请输入持股数量', trigger: 'blur' },
    { type: 'number', min: 0, message: '持股数量不能为负数', trigger: 'blur' }
  ],
  average_cost: [
    { required: true, type: 'number', message: '请输入成本价', trigger: 'blur' },
    { type: 'number', min: 0, message: '成本价不能为负数', trigger: 'blur' }
  ]
};

const totalValue = computed(() => {
  return holdings.value.reduce((sum, holding) => {
    return sum + (holding.shares * holding.average_cost);
  }, 0).toFixed(2);
});

const getMarketTypeColor = (marketType: string) => {
  const colors: Record<string, 'success' | 'info' | 'warning'> = {
    'A': 'success',
    'HK': 'info',
    'US': 'warning'
  };
  return colors[marketType] || 'default';
};

const formatDate = (dateStr: string) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('zh-CN');
};

const loadPortfolio = async () => {
  loading.value = true;
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/user/portfolio', {
      headers: { Authorization: `Bearer ${token}` }
    });
    holdings.value = response.data.holdings || [];
  } catch (error: any) {
    console.error('获取持仓失败:', error);
    message.error(error.response?.data?.detail || '获取持仓失败');
  } finally {
    loading.value = false;
  }
};

const resetForm = () => {
  formData.value = {
    stock_code: '',
    market_type: 'A',
    display_name: '',
    shares: 0,
    average_cost: 0,
    purchase_date: undefined,
    notes: ''
  };
  editingHolding.value = null;
  formRef.value?.restoreValidation();
};

const editHolding = (holding: PortfolioHolding) => {
  editingHolding.value = holding;
  formData.value = {
    stock_code: holding.stock_code,
    market_type: holding.market_type,
    display_name: holding.display_name || '',
    shares: holding.shares,
    average_cost: holding.average_cost,
    purchase_date: holding.purchase_date ? new Date(holding.purchase_date).getTime() : undefined,
    notes: holding.notes || ''
  };
  showAddModal.value = true;
};

const handleSubmit = async () => {
  try {
    await formRef.value?.validate();
    
    submitting.value = true;
    const token = localStorage.getItem('token');
    
    const payload = {
      ...formData.value,
      purchase_date: formData.value.purchase_date 
        ? new Date(formData.value.purchase_date).toISOString() 
        : undefined
    };

    if (editingHolding.value) {
      // 更新持仓
      await axios.put(
        `/api/user/portfolio/${editingHolding.value.id}`,
        payload,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      message.success('持仓更新成功');
    } else {
      // 添加持仓
      await axios.post('/api/user/portfolio', payload, {
        headers: { Authorization: `Bearer ${token}` }
      });
      message.success('持仓添加成功');
    }

    showAddModal.value = false;
    resetForm();
    await loadPortfolio();
  } catch (error: any) {
    if (error?.errorFields) {
      // 表单验证错误
      return;
    }
    console.error('提交失败:', error);
    message.error(error.response?.data?.detail || '操作失败');
  } finally {
    submitting.value = false;
  }
};

const confirmDelete = (holding: PortfolioHolding) => {
  const dialog = window.confirm(
    `确定要删除持仓 ${holding.stock_code}${holding.display_name ? ` (${holding.display_name})` : ''} 吗？`
  );
  
  if (dialog) {
    deleteHolding(holding.id);
  }
};

const deleteHolding = async (holdingId: number) => {
  try {
    const token = localStorage.getItem('token');
    await axios.delete(`/api/user/portfolio/${holdingId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    message.success('持仓删除成功');
    await loadPortfolio();
  } catch (error: any) {
    console.error('删除失败:', error);
    message.error(error.response?.data?.detail || '删除失败');
  }
};

onMounted(() => {
  loadPortfolio();
});
</script>

<style scoped>
.portfolio-panel {
  padding: 20px;
}

.n-list-item {
  padding: 16px;
}
</style>

