import axios, {
  AxiosError,
  type AxiosRequestConfig,
  type AxiosInstance,
  type InternalAxiosRequestConfig
} from 'axios'
import store from '@/store/auth'

const api: AxiosInstance = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: true
})

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const token = store.state.accessToken
    if (token && config.headers) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError): Promise<AxiosError> => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        const newAccessToken = await store.dispatch('refreshToken')
        if (originalRequest.headers) {
          originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`
        }
        return api(originalRequest)
      } catch (refreshError) {
        // Redirect to login page or handle refresh failure
        return Promise.reject(refreshError)
      }
    }
    return Promise.reject(error)
  }
)

export default api
