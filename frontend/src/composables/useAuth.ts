import { computed, type ComputedRef } from 'vue'
import { useStore, Store } from 'vuex'
import { useRouter } from 'vue-router'
import { type AuthState } from '@/store/auth' // Make sure to export AuthState from your store file

export function useAuth() {
  const store: Store<AuthState> = useStore()
  const router = useRouter()

  const user: ComputedRef<AuthState['user']> = computed(() => store.state.user)
  const isAuthenticated: ComputedRef<boolean> = computed(() => store.getters.isAuthenticated)

  const login = async (email: string, password: string): Promise<void> => {
    try {
      await store.dispatch('login', { email, password })
      router.push('/')
    } catch (error) {
      console.error('Login failed', error)
      throw error
    }
  }

  const logout = async (): Promise<void> => {
    try {
      await store.dispatch('logout')
      router.push('/login')
    } catch (error) {
      console.error('Logout failed', error)
    }
  }

  // DELETE?
  const checkAuth = async (): Promise<void> => {
    if (!isAuthenticated.value && store.state.accessToken) {
      try {
        await store.dispatch('refreshToken')
      } catch (error) {
        router.push('/login')
      }
    }
  }

  return {
    user,
    isAuthenticated,
    login,
    logout,
    checkAuth
  }
}
