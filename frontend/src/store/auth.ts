// src/store/auth.ts
import { createStore } from 'vuex'
import axios, { type AxiosInstance } from 'axios'
import router from '@/router'

// Plain API to avoid infinite access token refresh loops
const plainApi: AxiosInstance = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: true
})

export interface User {
  id: string
  email: string
  is_verified: string
  // Add other user properties as needed
}

export interface AuthState {
  user: User | null
  accessToken: string | null
  isLoggedIn: boolean
  initialCheckDone: boolean
}

// Define commit function type
type CommitFn = (type: string, payload?: any) => void

// Create the store without type arguments
const store = createStore({
  state: {
    user: null,
    accessToken: localStorage.getItem('accessToken') || null,
    isLoggedIn: localStorage.getItem('isLoggedIn') === 'true',
    initialCheckDone: false
  },
  getters: {
    isAuthenticated: (state: AuthState): boolean => state.isLoggedIn && !!state.accessToken
  },
  mutations: {
    setUser(state: AuthState, user: User) {
      state.user = user
    },
    setAccessToken(state: AuthState, token: string) {
      state.accessToken = token
      localStorage.setItem('accessToken', token)
    },
    setIsLoggedIn(state: AuthState, value: boolean) {
      state.isLoggedIn = value
      localStorage.setItem('isLoggedIn', value ? 'true' : 'false')
    },
    setInitialCheckDone(state: AuthState, value: boolean) {
      state.initialCheckDone = value
    },
    clearUserData(state: AuthState) {
      state.user = null
      state.accessToken = null
      state.isLoggedIn = false
      localStorage.removeItem('isLoggedIn')
      localStorage.removeItem('accessToken')
    }
  },
  actions: {
    async login(
      { commit }: { commit: CommitFn },
      { email, password }: { email: string; password: string }
    ) {
      const formData = new URLSearchParams()
      formData.append('username', email)
      formData.append('password', password)

      const response = await plainApi.post<{ user: User; access_token: string }>(
        '/auth/login',
        formData,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          withCredentials: true
        }
      )

      commit('setUser', response.data.user)
      commit('setAccessToken', response.data.access_token)
      commit('setIsLoggedIn', true)

      // Don't handle redirects here - let the useAuth composable handle it
      // This prevents multiple components trying to handle the redirect
      console.log('Login successful - return data to caller to handle redirect')

      return response.data
    },

    async logout({ commit }: { commit: CommitFn }) {
      try {
        await plainApi.post('/auth/logout', {}, { withCredentials: true })
      } catch (error) {
        console.error('Error during logout:', error)
      } finally {
        // Always clear user data, even if the API call fails
        commit('clearUserData')
        router.push('/auth')
      }
    },

    async logoutAll({ commit }: { commit: CommitFn }) {
      try {
        await plainApi.post('/auth/logout-all', {}, { withCredentials: true })
      } catch (error) {
        console.error('Error during logout-all:', error)
      } finally {
        // Always clear user data, even if the API call fails
        commit('clearUserData')
        router.push('/auth')
      }
    },

    async refreshToken({ commit }: { commit: CommitFn }): Promise<string> {
      try {
        // Critical: Must use "plainAPI", not the imported api with refresh interceptors, which can cause an infinite loop
        const response = await plainApi.post<{ user: User; access_token: string }>(
          '/auth/refresh',
          {},
          { withCredentials: true }
        )
        commit('setUser', response.data.user)
        commit('setAccessToken', response.data.access_token)
        commit('setIsLoggedIn', true)
        return response.data.access_token
      } catch (error) {
        commit('clearUserData')
        throw error
      }
    },

    // This action is called directly from axios.ts when we need to clear auth state
    clearUserData({ commit }: { commit: CommitFn }) {
      commit('clearUserData')
    },

    async changePassword(
      { commit }: { commit: CommitFn },
      { current_password, new_password }: { current_password: string; new_password: string }
    ): Promise<void> {
      const response = await plainApi.post('/auth/change-password', {
        current_password,
        new_password
      })
      commit('setUser', response.data.user)
      commit('setAccessToken', response.data.access_token)
      commit('setIsLoggedIn', true)
    },

    async updateEmail(
      { commit }: { commit: CommitFn },
      { newEmail }: { newEmail: string }
    ): Promise<void> {
      const response = await plainApi.put('/auth/users/me/email', { email: newEmail })
      commit('setUser', response.data.user)
      commit('setAccessToken', response.data.access_token)
      commit('setIsLoggedIn', true)
    },

    async checkAuth({ commit, dispatch }: { commit: CommitFn; dispatch: any }) {
      const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true'

      if (isLoggedIn) {
        try {
          await dispatch('refreshToken')
        } catch (error) {
          console.log('Failed to refresh token during initial auth check')
          commit('clearUserData')

          // If on a protected route, redirect to login
          const currentRoute = router.currentRoute.value
          if (currentRoute.meta.requiresAuth) {
            console.log('On protected route without auth, redirecting to login')

            // Clean the redirect path
            const destinationPath = currentRoute.fullPath.split('?redirect=')[0]
            console.log('Original path for redirect:', destinationPath)

            // Only add redirect param if not already on auth page
            if (!destinationPath.includes('/auth')) {
              console.log('Adding redirect parameter to auth redirect')
              router.push({
                path: '/auth',
                query: { redirect: destinationPath }
              })
            } else {
              console.log('Path includes auth, redirecting without parameters')
              router.push({ path: '/auth' })
            }
          }
        }
      }

      commit('setInitialCheckDone', true)
    }
  }
})

export default store
