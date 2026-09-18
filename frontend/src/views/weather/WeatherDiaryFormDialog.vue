<template>
  <el-dialog :model-value="visible" :title="isEdit ? `编辑气象日志 #${form.id}` : '登记气象日志'"
             width="520px" top="10vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <el-form-item label="行政区" prop="district" :error="fieldErrors.district">
        <el-select v-model="form.district" filterable allow-create default-first-option
                   placeholder="选择或输入行政区" style="width: 100%">
          <el-option v-for="item in districts" :key="item" :label="item" :value="item" />
        </el-select>
      </el-form-item>
      <el-form-item label="日期" prop="diary_date" :error="fieldErrors.diary_date">
        <el-date-picker v-model="form.diary_date" type="date" value-format="YYYY-MM-DD"
                        placeholder="选择气象日期" style="width: 100%" />
      </el-form-item>
      <el-form-item label="实际天气" prop="weather" :error="fieldErrors.weather">
        <el-select v-model="form.weather" placeholder="选择实际天气" style="width: 100%">
          <el-option v-for="item in weatherOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="降雨量(mm)" :error="fieldErrors.rainfall_mm">
        <el-input-number v-model="form.rainfall_mm" :min="0" :max="2000" :precision="1"
                         :controls="false" placeholder="无降雨可留空" style="width: 100%" />
      </el-form-item>
      <el-form-item label="数据来源" :error="fieldErrors.source">
        <el-select v-model="form.source" style="width: 100%">
          <el-option v-for="item in sourceOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="500"
                  placeholder="如：台风过境，傍晚转中雨" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { weatherDiaryApi } from '@/api'
import { useEnumOptions } from '@/composables/useEnumOptions'

const emit = defineEmits(['saved'])

const { options: weatherOptions } = useEnumOptions('weather')
const { options: sourceOptions } = useEnumOptions('weather_source')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const districts = ref([])
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const rules = {
  district: [{ required: true, message: '请选择或输入行政区', trigger: 'change' }],
  diary_date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  weather: [{ required: true, message: '请选择实际天气', trigger: 'change' }],
}

function emptyForm() {
  return {
    id: null,
    district: '',
    diary_date: '',
    weather: '',
    rainfall_mm: null,
    source: 'manual',
    remark: '',
  }
}

async function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  editingId.value = row?.id ?? null
  const data = await weatherDiaryApi.districts().catch(() => [])
  districts.value = (data || []).map((item) => item.district)
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
  }
  visible.value = true
}

function close() {
  visible.value = false
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  fieldErrors.value = {}
  const payload = { ...form }
  delete payload.id
  try {
    if (isEdit.value) {
      await weatherDiaryApi.update(editingId.value, payload)
      ElMessage.success('气象日志已更新')
    } else {
      await weatherDiaryApi.create(payload)
      ElMessage.success('气象日志已登记')
    }
    emit('saved')
    close()
  } catch (error) {
    fieldErrors.value = error?.details || {}
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>
