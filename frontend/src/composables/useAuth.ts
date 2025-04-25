// src/composables/useAuth.ts
import { computed, type ComputedRef } from 'vue'
import { useStore } from 'vuex'
import { useRouter } from 'vue-router'
import { type AuthState } from '@/store/auth' // Make sure to export AuthState from your store file

export function useAuth() {
  const store = useStore()
  const router = useRouter()

  const user: ComputedRef<AuthState['user']> = computed(() => store.state.user)
  const isAuthenticated: ComputedRef<boolean> = computed(() => store.getters.isAuthenticated)

  const login = async (email: string, password: string): Promise<void> => {
    try {
      console.log('Attempting login...')

      // Capture the redirect URL before login (it might be lost during store operation)
      const redirectUrl = router.currentRoute.value.query.redirect as string
      console.log('Stored redirect URL before login:', redirectUrl)

      await store.dispatch('login', { email, password })

      // Check if we need to redirect after successful login
      if (redirectUrl) {
        console.log('Login successful, redirecting to:', redirectUrl)
        router.push(redirectUrl)
      } else {
        console.log('Login successful, no redirect found, going to home page')
        router.push('/')
      }
    } catch (error) {
      console.error('Login failed', error)
      throw error
    }
  }

  const logout = async (): Promise<void> => {
    try {
      await store.dispatch('logout')
      router.push('/auth')
    } catch (error) {
      console.error('Logout failed', error)
      throw error
    }
  }

  const logoutAll = async (): Promise<void> => {
    try {
      await store.dispatch('logoutAll')
      router.push('/auth')
    } catch (error) {
      console.error('Logout all failed', error)
      throw error
    }
  }

  const changePassword = async ({
    current_password,
    new_password
  }: {
    current_password: string
    new_password: string
  }): Promise<void> => {
    try {
      await store.dispatch('changePassword', { current_password, new_password })
    } catch (error) {
      console.error('Change password failed', error)
      throw error
    }
  }

  const updateEmail = async ({ newEmail }: { newEmail: string }): Promise<void> => {
    try {
      await store.dispatch('updateEmail', { newEmail })
    } catch (error) {
      console.error('Update email failed', error)
      throw error
    }
  }

  // DELETE?
  const checkAuth = async (): Promise<void> => {
    if (!isAuthenticated.value && store.state.accessToken) {
      try {
        await store.dispatch('refreshToken')
      } catch (error) {
        router.push('/auth')
      }
    }
  }

  return {
    user,
    isAuthenticated,
    login,
    logout,
    logoutAll,
    changePassword,
    updateEmail,
    checkAuth
  }
}
