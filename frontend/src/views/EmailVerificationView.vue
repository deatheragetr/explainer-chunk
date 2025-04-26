<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div>
        <img class="mx-auto h-12 w-auto" src="/images/logo.png" alt="Explainer Chonk" />
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          {{ verificationStatus.title }}
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          {{ verificationStatus.message }}
        </p>
      </div>

      <div v-if="verificationStatus.success" class="mt-8 space-y-6">
        <div class="verification-animation">
          <svg class="checkmark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
            <circle class="checkmark__circle" cx="26" cy="26" r="25" fill="none" />
            <path class="checkmark__check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8" />
          </svg>
        </div>
        <p class="text-center text-sm text-gray-500">
          Redirecting to home page in {{ redirectCountdown }} seconds...
        </p>
      </div>

      <div v-else class="mt-8 space-y-6">
        <div class="verification-animation">
          <svg class="crossmark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
            <circle class="crossmark__circle" cx="26" cy="26" r="25" fill="none" />
            <path class="crossmark__cross" fill="none" d="M16 16 36 36 M36 16 16 36" />
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const router = useRouter()

const verificationStatus = ref({
  success: false,
  title: 'Verifying your email...',
  message: 'Please wait while we confirm your email address.'
})

const redirectCountdown = ref(5)

onMounted(async () => {
  const token = route.query.token as string
  const baseApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  try {
    const response = await axios.post(`${baseApiUrl}/auth/verify-email`, { token })
    verificationStatus.value = {
      success: true,
      title: 'Email Verified!',
      message:
        'Your email has been successfully verified. You can now use all features of Explainer Chonk.'
    }
    startRedirectCountdown()
  } catch (error) {
    verificationStatus.value = {
      success: false,
      title: 'Verification Failed',
      message: "We couldn't verify your email. The link may have expired or is invalid."
    }
  }
})

const startRedirectCountdown = () => {
  const countdownInterval = setInterval(() => {
    redirectCountdown.value--
    if (redirectCountdown.value <= 0) {
      clearInterval(countdownInterval)
      router.push('/')
    }
  }, 1000)
}
</script>

<style scoped>
.verification-animation {
  display: flex;
  justify-content: center;
  align-items: center;
}

.checkmark__circle {
  stroke-dasharray: 166;
  stroke-dashoffset: 166;
  stroke-width: 2;
  stroke-miterlimit: 10;
  stroke: #7ac142;
  fill: none;
  animation: stroke 0.6s cubic-bezier(0.65, 0, 0.45, 1) forwards;
}

.checkmark {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: block;
  stroke-width: 2;
  stroke: #fff;
  stroke-miterlimit: 10;
  box-shadow: inset 0px 0px 0px #7ac142;
  animation:
    fill 0.4s ease-in-out 0.4s forwards,
    scale 0.3s ease-in-out 0.9s both;
}

.checkmark__check {
  transform-origin: 50% 50%;
  stroke-dasharray: 48;
  stroke-dashoffset: 48;
  animation: stroke 0.3s cubic-bezier(0.65, 0, 0.45, 1) 0.8s forwards;
}

@keyframes stroke {
  100% {
    stroke-dashoffset: 0;
  }
}

@keyframes scale {
  0%,
  100% {
    transform: none;
  }
  50% {
    transform: scale3d(1.1, 1.1, 1);
  }
}

@keyframes fill {
  100% {
    box-shadow: inset 0px 0px 0px 30px #7ac142;
  }
}

.crossmark__circle {
  stroke-dasharray: 166;
  stroke-dashoffset: 166;
  stroke-width: 2;
  stroke-miterlimit: 10;
  stroke: #c14242;
  fill: none;
  animation: stroke 0.6s cubic-bezier(0.65, 0, 0.45, 1) forwards;
}

.crossmark {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: block;
  stroke-width: 2;
  stroke: #fff;
  stroke-miterlimit: 10;
  box-shadow: inset 0px 0px 0px #c14242;
  animation:
    fill-red 0.4s ease-in-out 0.4s forwards,
    scale 0.3s ease-in-out 0.9s both;
}

.crossmark__cross {
  transform-origin: 50% 50%;
  stroke-dasharray: 48;
  stroke-dashoffset: 48;
  animation: stroke 0.3s cubic-bezier(0.65, 0, 0.45, 1) 0.8s forwards;
}

@keyframes fill-red {
  100% {
    box-shadow: inset 0px 0px 0px 30px #c14242;
  }
}
</style>
