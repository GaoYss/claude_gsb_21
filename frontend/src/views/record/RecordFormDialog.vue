<template>
  <el-dialog :model-value="visible" :title="isEdit ? `编辑养护记录 · ${form.record_no}` : '录入养护记录'"
             width="760px" top="6vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-form-item label="所属绿地" prop="green_space_id" :error="fieldErrors.green_space_id">
        <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset"
                          placeholder="选择绿地（可与右侧任务二选一）"
                          @update:model-value="onGreenSpaceChange" />
      </el-form-item>
      <el-form-item label="关联养护任务" :error="fieldErrors.task_id">
        <TaskSelect v-model="form.task_id" :green-space-id="form.green_space_id" :preset="taskPreset"
                    @update:model-value="onTaskChange" />
        <div class="form-hint">关联任务后，绿地自动跟随任务；任务状态会随本记录的评定结果自动流转。</div>
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="养护日期" prop="record_date" :error="fieldErrors.record_date">
            <el-date-picker v-model="form.record_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择养护日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="天气" :error="fieldErrors.weather">
            <el-select v-model="form.weather" clearable placeholder="选择天气" style="width: 100%">
              <el-option v-for="item in weatherOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="作业人员" :error="fieldErrors.worker">
            <el-input v-model="form.worker" placeholder="如：王海涛" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="工时" :error="fieldErrors.work_hours">
            <el-input-number v-model="form.work_hours" :min="0" :max="1000" :precision="1"
                             :controls="false" placeholder="单位：小时" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- 气象核对：天气应与当日实际气象保持一致，浇灌类作业遇降雨时给出提示 -->
      <el-form-item label="气象核对" v-if="weatherCheck">
        <div class="weather-check">
          <template v-if="weatherCheck.actual_weather">
            <el-alert
              :type="alertType"
              :closable="false"
              show-icon
              class="check-alert"
            >
              <template #title>
                <div class="check-line">
                  <span v-if="weatherCheck.weather_match === 'mismatch'">
                    {{ weatherCheck.district }} {{ weatherCheck.record_date }} 实际气象为
                    <strong>{{ weatherCheck.actual_weather_label }}</strong>
                    <span v-if="weatherCheck.diary?.rainfall_mm">（降雨量 {{ weatherCheck.diary.rainfall_mm }}mm）</span>
                    ，与登记天气不一致
                  </span>
                  <span v-else-if="weatherCheck.weather_match === 'consistent'">
                    登记天气与{{ weatherCheck.district }}当日实际气象
                    <strong>{{ weatherCheck.actual_weather_label }}</strong>一致
                  </span>
                  <span v-else>
                    {{ weatherCheck.district }} {{ weatherCheck.record_date }} 实际气象为
                    <strong>{{ weatherCheck.actual_weather_label }}</strong>
                    <span v-if="weatherCheck.diary?.rainfall_mm">（降雨量 {{ weatherCheck.diary.rainfall_mm }}mm）</span>
                    ，尚未选择登记天气
                  </span>
                  <el-button v-if="weatherCheck.weather_match !== 'consistent'"
                             link type="primary" class="adopt-btn" @click="adoptActualWeather">
                    按实际气象填报
                  </el-button>
                </div>
              </template>
            </el-alert>
          </template>
          <el-alert v-else type="info" :closable="false" show-icon class="check-alert">
            <template #title>
              {{ weatherCheck.district }} {{ weatherCheck.record_date }} 暂无气象日志，天气按填报内容留存
            </template>
          </el-alert>
          <el-alert v-for="(warning, index) in weatherCheck.warnings" :key="index"
                    type="warning" :closable="false" show-icon class="check-alert">
            <template #title>{{ warning }}</template>
          </el-alert>
        </div>
      </el-form-item>

      <el-form-item label="作业内容" prop="work_content" :error="fieldErrors.work_content">
        <el-input v-model="form.work_content" type="textarea" :rows="3" maxlength="4000"
                  placeholder="如：修剪香樟下垂枝 32 株，清运枝条 2 车" />
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="质量评定" :error="fieldErrors.quality_result">
            <el-select v-model="form.quality_result" style="width: 100%">
              <el-option v-for="item in qualityOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="使用材料/药剂" :error="fieldErrors.materials">
            <el-input v-model="form.materials" placeholder="如：复合肥 180kg" maxlength="1000" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="发现问题" :error="fieldErrors.issue_found">
        <el-input v-model="form.issue_found" type="textarea" :rows="2" maxlength="2000"
                  placeholder="巡查或作业中发现的问题及处理情况" />
      </el-form-item>
      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { maintenanceRecordApi, maintenanceTaskApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import TaskSelect from '@/components/common/TaskSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { today } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: qualityOptions } = useEnumOptions('quality_result')
const { options: weatherOptions } = useEnumOptions('weather')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const spacePreset = ref(null)
const taskPreset = ref(null)
const form = reactive(emptyForm())
const weatherCheck = ref(null)
let checkTimer = null

const isEdit = computed(() => editingId.value !== null)

const ALERT_TYPES = { consistent: 'success', mismatch: 'warning', pending: 'info', unavailable: 'info' }
const alertType = computed(() => ALERT_TYPES[weatherCheck.value?.weather_match] || 'info')

const rules = {
  record_date: [{ required: true, message: '请选择养护日期', trigger: 'change' }],
  work_content: [{ required: true, message: '请输入作业内容', trigger: 'blur' }],
}

function emptyForm() {
  return {
    record_no: '',
    green_space_id: null,
    task_id: null,
    record_date: today(),
    work_content: '',
    worker: '',
    work_hours: null,
    weather: '',
    materials: '',
    quality_result: 'qualified',
    issue_found: '',
    remark: '',
  }
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  weatherCheck.value = null
  spacePreset.value = null
  taskPreset.value = null
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    spacePreset.value = row.green_space || null
    taskPreset.value = row.task ? { ...row.task, id: row.task_id } : null
  }
  visible.value = true
  scheduleCheck()
}

function close() {
  visible.value = false
}

function adoptActualWeather() {
  if (weatherCheck.value?.suggested_weather) {
    form.weather = weatherCheck.value.suggested_weather
  }
}

function onGreenSpaceChange() {
  form.task_id = null
  taskPreset.value = null
  scheduleCheck()
}

async function onTaskChange(taskId) {
  if (!taskId) return
  const task = await maintenanceTaskApi.detail(taskId).catch(() => null)
  if (task?.green_space) {
    form.green_space_id = task.green_space_id
    spacePreset.value = task.green_space
    taskPreset.value = { id: task.id, task_no: task.task_no, title: task.title, status: task.status }
  }
  scheduleCheck()
}

// 绿地/任务/日期/天气/作业内容变化时，延迟拉取核对结论，避免输入过程中频繁请求
watch(
  () => [form.green_space_id, form.task_id, form.record_date, form.weather, form.work_content],
  () => {
    if (visible.value) scheduleCheck()
  },
)

function scheduleCheck() {
  clearTimeout(checkTimer)
  checkTimer = setTimeout(runWeatherCheck, 300)
}

async function runWeatherCheck() {
  if (!form.record_date || (!form.green_space_id && !form.task_id)) {
    weatherCheck.value = null
    return
  }
  const params = {
    record_date: form.record_date,
    weather: form.weather || undefined,
    work_content: form.work_content || undefined,
  }
  if (form.task_id) params.task_id = form.task_id
  if (form.green_space_id) params.green_space_id = form.green_space_id
  const data = await maintenanceRecordApi.weatherCheck(params).catch(() => null)
  if (data && visible.value) weatherCheck.value = data
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  if (!form.green_space_id && !form.task_id) {
    fieldErrors.value = { green_space_id: '请选择所属绿地或关联养护任务' }
    return
  }
  // 保存前再核对一次，若提示未被处理（天气仍不符或坚持雨后浇灌），由后端在档案中标注
  await runWeatherCheck()
  submitting.value = true
  fieldErrors.value = {}
  const payload = { ...form }
  delete payload.record_no
  if (!payload.record_no) delete payload.record_no
  if (!payload.task_id) payload.task_id = null
  try {
    if (isEdit.value) {
      await maintenanceRecordApi.update(editingId.value, payload)
      ElMessage.success('养护记录已更新')
    } else {
      await maintenanceRecordApi.create(payload)
      ElMessage.success('养护记录录入成功')
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

<style scoped>
.form-hint {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}

.weather-check {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.check-alert {
  align-items: flex-start;
}

.check-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.adopt-btn {
  margin-left: 4px;
  padding: 0;
  height: auto;
  font-weight: 600;
}
</style>
