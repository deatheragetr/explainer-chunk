<template>
  <div class="min-h-screen flex flex-col lg:flex-row">
    <!-- Left side - Image and Text -->
    <div class="hidden lg:block lg:w-2/3 relative">
      <img
        src="/images/login_bg.jpeg"
        alt="Background"
        class="absolute inset-0 w-full h-full object-cover"
      />
      <div class="absolute inset-0 bg-gradient-to-r from-blue-500 to-purple-600 opacity-50"></div>
      <div class="absolute inset-0 flex items-center justify-center">
        <div class="text-white text-center max-w-2xl px-4">
          <h1 class="text-6xl font-bold mb-4">Explainer Chonk</h1>
          <p class="text-2xl mb-8">
            Discover
            <span class="animated-text-wrapper">
              <AnimatedText
                :words="[
                  'Science',
                  'Mathematics',
                  'Literature',
                  'Philosophy',
                  'Culture',
                  'History',
                  'Politics',
                  'Biography'
                ]"
                :typingSpeed="80"
                :deletingSpeed="40"
                :pauseDuration="1500"
              />
            </span>
          </p>
          <!-- Stylized Dictionary Definition -->
          <div
            class="bg-white bg-opacity-10 backdrop-filter backdrop-blur-md rounded-lg p-6 text-left"
          >
            <div class="flex items-center mb-2">
              <span class="text-sm italic mr-2">transitive verb</span>
              <span class="text-sm font-mono">| \ ˈchȯŋk \</span>
            </div>
            <p class="text-base">
              : to chew energetically : <span class="font-medium">champ</span>
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Right side - Form -->
    <div class="w-full lg:w-1/3 bg-white flex flex-col items-center justify-center p-8 lg:p-16">
      <div class="w-full max-w-md">
        <!-- Updated logo styling -->
        <div class="flex justify-center mb-12">
          <img class="h-20 w-auto" src="/images/logo.png" alt="Your Company Logo" />
        </div>

        <transition name="fade" mode="out-in">
          <div v-if="showVerificationMessage" class="text-center">
            <h2 class="text-3xl font-extrabold text-gray-900 mb-6">Welcome aboard!</h2>
            <div class="mb-6">
              <svg class="verification-animation" viewBox="0 0 100 100" width="100" height="100">
                <path
                  class="envelope"
                  d="M10,20 L50,45 L90,20 L90,80 L10,80 L10,20 Z M10,20 L50,45 L90,20"
                  fill="none"
                  stroke="#4F46E5"
                  stroke-width="2"
                />
                <path
                  class="checkmark"
                  d="M20,50 L40,70 L80,30"
                  fill="none"
                  stroke="#4F46E5"
                  stroke-width="2"
                  stroke-dasharray="100"
                  stroke-dashoffset="100"
                />
              </svg>
            </div>
            <p class="text-lg text-gray-600 mb-4">
              Please check your inbox for a verification email.
            </p>
            <p class="text-base text-gray-500">
              We've sent you a message to confirm your email address and activate your account.
            </p>
            <p class="text-sm text-gray-400 mt-4">
              Redirecting you to the home page in {{ redirectCountdown }} seconds...
            </p>
          </div>

          <div v-else>
            <h2 class="text-3xl font-extrabold text-gray-900 mb-6 text-center">
              {{ isLogin ? 'Sign in to your account' : 'Create your account' }}
            </h2>

            <form @submit.prevent="handleSubmit" class="space-y-6">
              <div>
                <label for="email" class="block text-sm font-medium text-gray-700"
                  >Email address</label
                >
                <input
                  id="email"
                  name="email"
                  type="email"
                  autocomplete="email"
                  required
                  v-model="email"
                  :class="{ 'border-red-500': v$.email.$error }"
                  class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                />
              </div>

              <div>
                <label for="password" class="block text-sm font-medium text-gray-700"
                  >Password</label
                >
                <input
                  id="password"
                  name="password"
                  type="password"
                  autocomplete="current-password"
                  required
                  v-model="password"
                  :class="{ 'border-red-500': v$.password.$error }"
                  class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                />
              </div>

              <div v-if="!isLogin">
                <label for="confirmPassword" class="block text-sm font-medium text-gray-700"
                  >Confirm Password</label
                >
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  required
                  v-model="confirmPassword"
                  :class="{ 'border-red-500': v$.confirmPassword.$error }"
                  class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                />
              </div>

              <div v-if="v$.$error" class="rounded-md bg-red-50 p-4 animate-fade-in-down">
                <div class="flex">
                  <div class="flex-shrink-0">
                    <svg
                      class="h-5 w-5 text-red-400"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        fill-rule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                        clip-rule="evenodd"
                      />
                    </svg>
                  </div>
                  <div class="ml-3">
                    <h3 class="text-sm font-medium text-red-800">
                      Please correct the following errors:
                    </h3>
                    <ul class="mt-2 text-sm text-red-700 list-disc list-inside">
                      <li v-for="error of v$.$errors" :key="error.$uid">{{ error.$message }}</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out"
                >
                  {{ isLogin ? 'Sign in' : 'Sign up' }}
                </button>
              </div>
            </form>

            <div class="mt-6">
              <div class="relative">
                <div class="absolute inset-0 flex items-center">
                  <div class="w-full border-t border-gray-300"></div>
                </div>
                <div class="relative flex justify-center text-sm">
                  <span class="px-2 bg-white text-gray-500">
                    Or {{ isLogin ? 'create a new account' : 'sign in to your account' }}
                  </span>
                </div>
              </div>

              <div class="mt-6">
                <button
                  @click="toggleAuthMode"
                  class="w-full inline-flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out"
                >
                  {{ isLogin ? 'Sign up' : 'Sign in' }}
                </button>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useVuelidate } from '@vuelidate/core'
import { required, email as emailValidator, minLength, sameAs } from '@vuelidate/validators'
import axios from 'axios'
import { useToast } from 'vue-toastification'
import AnimatedText from '@/components/AnimatedText.vue'
import { useAuth } from '@/composables/useAuth'
import api from '@/api/axios'
import router from '@/router'
const toast = useToast()

const isLogin = ref(true)
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const showVerificationMessage = ref(false)
const redirectCountdown = ref(5)
const { login } = useAuth()

const rules = computed(() => ({
  email: { required, emailValidator },
  password: { required, minLength: minLength(8) },
  ...(isLogin.value
    ? {}
    : {
        confirmPassword: { required, sameAsPassword: sameAs(password) }
      })
}))

const v$ = useVuelidate(rules, { email, password, confirmPassword })

const toggleAuthMode = () => {
  isLogin.value = !isLogin.value
  v$.value.$reset()
}

const handleSubmit = async () => {
  const isFormCorrect = await v$.value.$validate()
  if (!isFormCorrect) return

  try {
    if (isLogin.value) {
      await handleLogin()
    } else {
      await register()
    }
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      toast.error(error.response.data.detail || 'An error occurred. Please try again.')
    } else {
      toast.error('An unexpected error occurred. Please try again.')
    }
  }
}

const handleLogin = async () => {
  try {
    // Log the current URL to see if redirect parameter exists
    console.log('Login form submitted, current URL:', window.location.href)

    // Explicitly extract the redirect URL
    const urlParams = new URLSearchParams(window.location.search)
    const redirectUrl = urlParams.get('redirect')
    console.log('Extracted redirect URL from query params:', redirectUrl)

    // The login function in useAuth will handle redirects based on query parameters
    await login(email.value, password.value)

    // If login was successful but useAuth didn't redirect (for some reason),
    // handle it here as a fallback
    if (redirectUrl && !redirectUrl.includes('/auth')) {
      console.log('Fallback redirect after successful login to:', redirectUrl)
      router.push(redirectUrl)
    } else if (!redirectUrl) {
      console.log('No redirect URL found, fallback to home page')
      router.push('/')
    }
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      toast.error(error.response.data.detail || 'Login failed. Please check your credentials.')
    } else {
      toast.error('An unexpected error occurred. Please try again.')
    }
  }
}

const register = async () => {
  const response = await api.post('/auth/register', {
    email: email.value,
    password: password.value
  })
  console.log('Registration successful:', response.data)

  showVerificationMessage.value = true

  const countdownInterval = setInterval(() => {
    redirectCountdown.value--
    if (redirectCountdown.value <= 0) {
      clearInterval(countdownInterval)
      showVerificationMessage.value = false
      handleLogin() // Attempt to log in after registration
    }
  }, 1000)
}
</script>

<style scoped>
@keyframes fade-in-down {
  0% {
    opacity: 0;
    transform: translateY(-10px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in-down {
  animation: fade-in-down 0.5s ease-out;
}
.verification-animation {
  margin: 0 auto;
}

.envelope {
  animation: draw-envelope 2s ease-in-out forwards;
}

.checkmark {
  animation: draw-checkmark 1s ease-in-out 2s forwards;
}

@keyframes draw-envelope {
  0% {
    stroke-dasharray: 300;
    stroke-dashoffset: 300;
  }
  100% {
    stroke-dasharray: 300;
    stroke-dashoffset: 0;
  }
}

@keyframes draw-checkmark {
  from {
    stroke-dashoffset: 100;
  }
  to {
    stroke-dashoffset: 0;
  }
}
</style>
