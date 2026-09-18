import { createResourceApi } from './client'
import http from './client'

export const maintenanceRecordApi = {
  ...createResourceApi('maintenance-records'),
  summary: (params) => http.get('/maintenance-records/summary', { params }),
  /** 表单实时核对登记天气与当日实际气象 */
  weatherCheck: (params) => http.get('/maintenance-records/weather-check', { params }),
}
