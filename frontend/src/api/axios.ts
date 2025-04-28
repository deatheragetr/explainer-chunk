// src/api/axios.ts
import axios, {
  AxiosError,
  type AxiosRequestConfig,
  type AxiosInstance,
  type InternalAxiosRequestConfig
} from 'axios'
import store from '@/store/auth'
import router from '@/router'

const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
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

    // Only try to refresh token if:
    // 1. Error is 401 (Unauthorized)
    // 2. The request hasn't been retried yet
    // 3. We're not on the auth page already
    // 4. The API endpoint isn't for auth refresh (to avoid infinite loop)
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !window.location.pathname.includes('/auth') &&
      !originalRequest.url?.includes('/auth/refresh')
    ) {
      originalRequest._retry = true

      try {
        const newAccessToken = await store.dispatch('refreshToken')
        if (originalRequest.headers) {
          originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`
        }
        return api(originalRequest)
      } catch (refreshError) {
        // Token refresh failed, redirect to login
        console.log('Token refresh failed, redirecting to login page')

        // Clear auth state
        await store.dispatch('clearUserData')

        // Redirect to login page and save the current path for redirect after login
        const currentPath = router.currentRoute.value.fullPath
        console.log('Interceptor redirecting due to auth error, current path:', currentPath)

        // If we're already on the auth page, check if there's a redirect parameter we should preserve
        if (currentPath.includes('/auth')) {
          // Extract any existing redirect parameter
          const match = currentPath.match(/[?&]redirect=([^&]+)/)
          if (match && match[1]) {
            // We're on auth page with redirect param - preserve it
            console.log('On auth page with redirect param - preserving it:', match[1])
            // No need to redirect - we're already on the auth page with the correct redirect param
            return Promise.reject(error)
          } else {
            // On auth page without redirect param
            console.log('On auth page without redirect param - staying on page')
            // No need to redirect - we're already on the auth page
            return Promise.reject(error)
          }
        } else {
          // Not on auth page, add redirect parameter
          const destinationPath = currentPath.split('?redirect=')[0]
          console.log(
            'Not on auth page - redirecting to auth with redirect param:',
            destinationPath
          )
          router.push({
            path: '/auth',
            query: { redirect: destinationPath }
          })
        }

        return Promise.reject(refreshError)
      }
    }

    // For 401s on auth/refresh endpoint, just clear the data and redirect
    if (error.response?.status === 401 && originalRequest.url?.includes('/auth/refresh')) {
      // Clear auth state
      await store.dispatch('clearUserData')

      // If not already on auth page, redirect there
      if (!window.location.pathname.includes('/auth')) {
        router.push({ name: 'auth' })
      }
    }

    return Promise.reject(error)
  }
)

export default api
