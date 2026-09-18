<template>
  <div class="page">
    <PageHeader title="气象日志" description="按行政区登记每日实际气象（人工记录或气象台导入），作为养护记录天气核对依据">
      <template #actions>
        <el-button :icon="'Upload'" @click="importDialog.open()">批量导入</el-button>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">登记气象</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-select v-model="filters.district" placeholder="行政区" clearable filterable style="width: 160px"
                   @change="search">
          <el-option v-for="item in districts" :key="item.district" :label="item.district" :value="item.district" />
        </el-select>
        <el-select v-model="filters.weather" placeholder="实际天气" clearable style="width: 130px" @change="search">
          <el-option v-for="item in weatherOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.source" placeholder="数据来源" clearable style="width: 140px" @change="search">
          <el-option v-for="item in sourceOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-checkbox v-model="filters.rainy" label="仅看降雨/雪" border @change="search" />
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="日期起" end-placeholder="日期止" @change="onDateChange" />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
      </div>
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">共 <strong>{{ meta.total }}</strong> 条气象日志</span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column prop="district" label="行政区" width="110" />
        <el-table-column label="日期" width="120">
          <template #default="{ row }">{{ row.diary_date }}</template>
        </el-table-column>
        <el-table-column label="实际天气" width="110">
          <template #default="{ row }">
            <EnumTag group="weather" :value="row.weather" :label="row.weather_label" />
            <el-tag v-if="row.is_rainy" size="small" type="primary" effect="plain" class="rain-tag">有降水</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="降雨量(mm)" width="110" align="right">
          <template #default="{ row }">{{ row.rainfall_mm ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="数据来源" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="row.source === 'imported' ? 'success' : 'info'" effect="plain">
              {{ row.source_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="formDialog.open(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="meta.total"
        :current-page="meta.page"
        :page-size="meta.page_size"
        :page-sizes="[10, 20, 50]"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <WeatherDiaryFormDialog ref="formDialog" @saved="load" />
    <WeatherImportDialog ref="importDialog" @saved="load" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { weatherDiaryApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'

import WeatherDiaryFormDialog from './WeatherDiaryFormDialog.vue'
import WeatherImportDialog from './WeatherImportDialog.vue'

const formDialog = ref(null)
const importDialog = ref(null)
const dateRange = ref([])
const districts = ref([])

const { options: weatherOptions } = useEnumOptions('weather')
const { options: sourceOptions } = useEnumOptions('weather_source')

const { filters, meta, items, loading, load, search, resetFilters, handlePageChange, handleSizeChange } =
  useListQuery(weatherDiaryApi.list, {
    initialFilters: {
      district: '',
      weather: '',
      source: '',
      rainy: false,
      date_from: '',
      date_to: '',
    },
  })

async function loadDistricts() {
  districts.value = (await weatherDiaryApi.districts().catch(() => [])) || []
}

function onDateChange(value) {
  filters.date_from = value?.[0] || ''
  filters.date_to = value?.[1] || ''
  search()
}

function reset() {
  dateRange.value = []
  resetFilters()
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(
      `删除 ${row.district} ${row.diary_date} 的气象日志后，相关养护记录会重新核对，是否继续？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await weatherDiaryApi.remove(row.id)
    ElMessage.success('气象日志已删除')
    await load()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  }
}

onMounted(loadDistricts)
</script>

<style scoped>
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

.rain-tag {
  margin-left: 6px;
}
</style>
