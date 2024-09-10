import { createStore, type Commit } from 'vuex'
import api from '@/api/axios'

export interface User {
  id: string
  email: string
  // Add other user properties as needed
}

export interface AuthState {
  user: User | null
  accessToken: string | null
}

export default createStore<AuthState>({
  state: {
    user: null,
    accessToken: null
  },
  getters: {
    isAuthenticated: (state: AuthState): boolean => !!state.user
  },
  mutations: {
    setUser(state: AuthState, user: User) {
      state.user = user
    },
    setAccessToken(state: AuthState, token: string) {
      state.accessToken = token
    },
    clearUserData(state: AuthState) {
      state.user = null
      state.accessToken = null
    }
  },
  actions: {
    async login(
      { commit }: { commit: Commit },
      { email, password }: { email: string; password: string }
    ) {
      const formData = new URLSearchParams()
      formData.append('username', email) // Note: The backend expects 'username', not 'email'
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
    },
    async logout({ commit }: { commit: Commit }) {
      await api.post('/auth/logout', {}, { withCredentials: true })
      commit('clearUserData')
    },
    async refreshToken({ commit }: { commit: Commit }): Promise<string> {
      try {
        const response = await axios.post<{ access_token: string }>(
          '/auth/refresh',
          {},
          { withCredentials: true }
        )
        commit('setAccessToken', response.data.access_token)
        return response.data.access_token
      } catch (error) {
        commit('clearUserData')
        throw error
      }
    }
  }
})
