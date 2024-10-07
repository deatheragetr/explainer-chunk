<template>
  <div class="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-3xl mx-auto">
      <h1 class="text-4xl font-extralight text-gray-900 mb-12">Settings</h1>

      <Alert v-if="error" variant="error" title="Error">
        {{ error }}
      </Alert>

      <Alert v-if="success" variant="success" title="Success">
        {{ success }}
      </Alert>

      <div class="space-y-10">
        <!-- Profile Section -->
        <section
          class="bg-white shadow-sm rounded-xl p-8 transition-all duration-300 hover:shadow-md"
        >
          <h2 class="text-2xl font-extralight text-gray-700 mb-6">Profile</h2>
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-500">Email</p>
              <p class="mt-1 text-sm text-gray-900">{{ user?.email }}</p>
            </div>
            <button
              @click="showUpdateEmailModal = true"
              class="text-indigo-600 hover:text-indigo-800 text-sm font-medium transition-colors duration-300"
            >
              Update
            </button>
          </div>
          <div class="mt-4 flex items-center">
            <span
              :class="[
                'px-3 py-1 text-xs font-medium rounded-full',
                user?.is_verified ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
              ]"
            >
              {{ user?.is_verified ? 'Verified' : 'Not Verified' }}
            </span>
            <button
              v-if="!user?.is_verified"
              @click="resendVerificationEmail"
              class="ml-2 text-sm text-indigo-600 hover:text-indigo-800 transition-colors duration-300"
            >
              Resend Verification Email
            </button>
          </div>
        </section>

        <!-- Password Section -->
        <section
          class="bg-white shadow-sm rounded-xl p-8 transition-all duration-300 hover:shadow-md"
        >
          <h2 class="text-2xl font-extralight text-gray-700 mb-6">Password</h2>
          <form @submit.prevent="handleChangePassword" class="space-y-6">
            <div>
              <label for="current-password" class="block text-sm text-gray-500 mb-1"
                >Current Password</label
              >
              <input
                id="current-password"
                v-model="passwordForm.currentPassword"
                type="password"
                required
                class="mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md text-sm shadow-sm placeholder-gray-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors duration-300"
              />
            </div>
            <div>
              <label for="new-password" class="block text-sm text-gray-500 mb-1"
                >New Password</label
              >
              <input
                id="new-password"
                v-model="passwordForm.newPassword"
                type="password"
                required
                class="mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md text-sm shadow-sm placeholder-gray-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors duration-300"
              />
            </div>
            <div>
              <label for="confirm-password" class="block text-sm text-gray-500 mb-1"
                >Confirm New Password</label
              >
              <input
                id="confirm-password"
                v-model="passwordForm.confirmPassword"
                type="password"
                required
                class="mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md text-sm shadow-sm placeholder-gray-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors duration-300"
              />
            </div>
            <div>
              <button
                type="submit"
                class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all duration-300"
              >
                Change Password
              </button>
            </div>
          </form>
        </section>

        <!-- Active Sessions Section -->
        <section
          class="bg-white shadow-sm rounded-xl p-8 transition-all duration-300 hover:shadow-md"
        >
          <h2 class="text-2xl font-extralight text-gray-700 mb-6">Active Sessions</h2>
          <div class="space-y-4">
            <div
              v-for="(session, index) in sessions"
              :key="index"
              class="flex items-center justify-between py-3 border-b border-gray-200 last:border-b-0"
            >
              <div>
                <p class="text-sm text-gray-900">{{ session.user_agent }}</p>
                <p class="text-xs text-gray-500">
                  {{ session.ip }} • {{ formatDate(session.created_at) }}
                </p>
              </div>
              <div class="text-sm text-gray-500">
                {{ session.geolocation.city }}, {{ session.geolocation.country }}
              </div>
            </div>
          </div>
          <div class="mt-6 flex justify-end space-x-4">
            <button
              @click="logoutCurrentSession"
              class="text-red-600 hover:text-red-800 text-sm font-medium transition-colors duration-300"
            >
              Logout Current Session
            </button>
            <button
              @click="logoutAllSessions"
              class="text-red-600 hover:text-red-800 text-sm font-medium transition-colors duration-300"
            >
              Logout All Sessions
            </button>
          </div>
        </section>
      </div>
    </div>

    <!-- Update Email Modal -->
    <TransitionRoot appear :show="showUpdateEmailModal" as="template">
      <Dialog as="div" @close="showUpdateEmailModal = false" class="relative z-10">
        <TransitionChild
          as="template"
          enter="duration-300 ease-out"
          enter-from="opacity-0"
          enter-to="opacity-100"
          leave="duration-200 ease-in"
          leave-from="opacity-100"
          leave-to="opacity-0"
        >
          <div class="fixed inset-0 bg-black bg-opacity-25" />
        </TransitionChild>

        <div class="fixed inset-0 overflow-y-auto">
          <div class="flex min-h-full items-center justify-center p-4 text-center">
            <TransitionChild
              as="template"
              enter="duration-300 ease-out"
              enter-from="opacity-0 scale-95"
              enter-to="opacity-100 scale-100"
              leave="duration-200 ease-in"
              leave-from="opacity-100 scale-100"
              leave-to="opacity-0 scale-95"
            >
              <DialogPanel
                class="w-full max-w-md transform overflow-hidden rounded-lg bg-white p-6 text-left align-middle shadow-xl transition-all"
              >
                <DialogTitle as="h3" class="text-lg font-light text-gray-900">
                  Update Email
                </DialogTitle>
                <div class="mt-2">
                  <p class="text-sm text-gray-500">
                    Enter your new email address. You'll need to verify this new email address.
                  </p>
                </div>

                <form @submit.prevent="handleUpdateEmail" class="mt-4">
                  <div>
                    <label for="new-email" class="block text-sm text-gray-500 mb-1"
                      >New Email</label
                    >
                    <input
                      id="new-email"
                      v-model="newEmail"
                      type="email"
                      required
                      class="mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md text-sm shadow-sm placeholder-gray-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors duration-300"
                    />
                  </div>
                  <div class="mt-4">
                    <button
                      type="submit"
                      class="inline-flex justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 transition-all duration-300"
                    >
                      Update Email
                    </button>
                  </div>
                </form>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { useAuth } from '@/composables/useAuth'
import api from '@/api/axios'
import Alert from '@/components/ui/Alert.vue'

const { user, logout, logoutAll, changePassword, updateEmail } = useAuth()
const sessions = ref([])
const showUpdateEmailModal = ref(false)
const newEmail = ref('')
const error = ref('')
const success = ref('')

const passwordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

onMounted(async () => {
  await fetchUserData()
  await fetchSessions()
})

async function fetchUserData() {
  try {
    const response = await api.get('/auth/users/me')
    user.value = response.data
  } catch (err) {
    error.value = 'Error fetching user data'
  }
}

async function fetchSessions() {
  try {
    const response = await api.get('/auth/sessions')
    sessions.value = response.data
  } catch (err) {
    error.value = 'Error fetching sessions'
  }
}

async function handleUpdateEmail() {
  try {
    await updateEmail({ newEmail: newEmail.value })
    showUpdateEmailModal.value = false
    success.value = 'Email updated successfully'
  } catch (err) {
    error.value = 'Error updating email'
  }
}

async function handleChangePassword() {
  error.value = ''
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    error.value = "Passwords don't match"
    return
  }
  try {
    await changePassword({
      current_password: passwordForm.value.currentPassword,
      new_password: passwordForm.value.newPassword
    })
    success.value = 'Password changed successfully'
    passwordForm.value = { currentPassword: '', newPassword: '', confirmPassword: '' }
  } catch (err) {
    error.value = 'Error changing password'
  }
}

async function logoutCurrentSession() {
  try {
    await logout()
  } catch (err) {
    error.value = 'Error logging out current session'
  }
}

async function logoutAllSessions() {
  try {
    await logoutAll()
    // Redirect to login page
  } catch (err) {
    error.value = 'Error logging out all sessions'
  }
}

async function resendVerificationEmail() {
  // Implement this function to resend verification email
  // You'll need to add an endpoint for this on your backend
  if (user?.is_verified) {
    error.value = 'User already verified'
  }
  try {
    await api.post('/auth/verification-email', {})
    success.value = 'Resent verification email!'
  } catch (err) {
    error.value = 'Error resending verification email'
  }
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleString()
}
</script>
