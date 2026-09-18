import { createResourceApi } from './client'
import http from './client'

export const weatherDiaryApi = {
  ...createResourceApi('weather-diaries'),
  districts: () => http.get('/weather-diaries/districts'),
  import: (items) => http.post('/weather-diaries/import', { items }),
}
