import { createStore, type Commit } from 'vuex'
import axios, { type AxiosInstance } from 'axios'

const api: AxiosInstance = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: true
})

export interface User {
  id: string
  email: string
  // Add other user properties as needed
}

export interface AuthState {
  user: User | null
  accessToken: string | null
  isLoggedIn: boolean
  initialCheckDone: boolean
}

export default createStore<AuthState>({
  state: {
    user: null,
    accessToken: null,
    isLoggedIn: false,
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
    }
  },
  actions: {
    async login(
      { commit }: { commit: Commit },
      { email, password }: { email: string; password: string }
    ) {
      const formData = new URLSearchParams()
      formData.append('username', email)
      formData.append('password', password)

      const response = await api.post<{ user: User; access_token: string }>(
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
    },
    async logout({ commit }: { commit: Commit }) {
      await api.post('/auth/logout', {}, { withCredentials: true })
      commit('clearUserData')
    },
    async refreshToken({ commit }: { commit: Commit }): Promise<string> {
      try {
        const response = await api.post<{ user: User; access_token: string }>(
          '/auth/refresh',
          {},
          { withCredentials: true }
        )
        return response.data.access_token
      } catch (error) {
        commit('clearUserData')
        throw error
      }
    },
    async checkAuth({ commit, dispatch }: { commit: Commit; dispatch: any }) {
      const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true'
      if (isLoggedIn) {
        try {
          await dispatch('refreshToken')
        } catch (error) {
          commit('clearUserData')
        }
      }
      commit('setInitialCheckDone', true)
    }
  }
})
