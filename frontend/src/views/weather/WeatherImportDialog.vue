<template>
  <el-dialog :model-value="visible" title="批量导入气象日志" width="640px" top="8vh"
             destroy-on-close @update:model-value="close">
    <el-alert type="info" :closable="false" show-icon class="import-tip">
      <template #title>
        每行一条，格式：行政区,日期,实际天气[,降雨量]；同一行政区+日期已存在时自动更新。
        天气可填「晴/多云/阴/雨/雪/大风」或英文值，空行自动忽略。
      </template>
    </el-alert>
    <el-input v-model="text" type="textarea" :rows="10"
              placeholder="西湖区,2026-09-18,雨,12.5&#10;拱墅区,2026-09-18,多云&#10;滨江区,2026-09-17,晴" />
    <div v-if="parseError" class="parse-error">{{ parseError }}</div>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">导入</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { weatherDiaryApi } from '@/api'
import { useMetaStore } from '@/stores/meta'

const emit = defineEmits(['saved'])

const visible = ref(false)
const submitting = ref(false)
const text = ref('')
const parseError = ref('')
const meta = useMetaStore()

onMounted(() => meta.ensureLoaded())

function open() {
  text.value = ''
  parseError.value = ''
  visible.value = true
}

function close() {
  visible.value = false
}

function resolveWeather(token) {
  const value = token.trim()
  const options = meta.options('weather')
  const hit = options.find((item) => item.value === value || item.label === value)
  return hit?.value || null
}

function parseLines() {
  const entries = []
  const lines = text.value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  for (const [index, line] of lines.entries()) {
    const parts = line.split(/[,\t，]/).map((part) => part.trim())
    if (parts.length < 3) {
      parseError.value = `第 ${index + 1} 行字段不足，应为：行政区,日期,天气[,降雨量]`
      return null
    }
    const weather = resolveWeather(parts[2])
    if (!weather) {
      parseError.value = `第 ${index + 1} 行天气「${parts[2]}」无法识别`
      return null
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(parts[1])) {
      parseError.value = `第 ${index + 1} 行日期格式应为 YYYY-MM-DD`
      return null
    }
    const entry = { district: parts[0], diary_date: parts[1], weather, source: 'imported' }
    if (parts[3]) {
      const rainfall = Number(parts[3])
      if (!Number.isFinite(rainfall) || rainfall < 0) {
        parseError.value = `第 ${index + 1} 行降雨量不是有效数字`
        return null
      }
      entry.rainfall_mm = rainfall
    }
    entries.push(entry)
  }
  if (!entries.length) {
    parseError.value = '请输入至少一条气象日志'
    return null
  }
  return entries
}

async function submit() {
  parseError.value = ''
  const entries = parseLines()
  if (!entries) return
  submitting.value = true
  try {
    const result = await weatherDiaryApi.import(entries)
    ElMessage.success(`导入完成：新增 ${result.created} 条，更新 ${result.updated} 条`
      + (result.failed?.length ? `，${result.failed.length} 条失败` : ''))
    emit('saved')
    close()
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.import-tip {
  margin-bottom: 12px;
}

.parse-error {
  margin-top: 8px;
  color: var(--el-color-danger);
  font-size: 13px;
}
</style>
