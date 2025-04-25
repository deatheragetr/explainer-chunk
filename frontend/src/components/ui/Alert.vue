<template>
  <div :class="['mb-6 rounded-md p-4', variantClasses[variant]]" role="alert">
    <div class="flex">
      <div class="flex-shrink-0">
        <component :is="icon" class="h-5 w-5" aria-hidden="true" />
      </div>
      <div class="ml-3">
        <h3 :class="['text-sm font-medium', textColorClass]">
          {{ title }}
        </h3>
        <div :class="['mt-2 text-sm', textColorClass]">
          <slot></slot>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  ExclamationCircleIcon,
  CheckCircleIcon,
  InformationCircleIcon
} from '@heroicons/vue/24/solid'

type AlertVariant = 'info' | 'success' | 'warning' | 'error'

const props = defineProps({
  variant: {
    type: String as () => AlertVariant,
    default: 'info',
    validator: (value: string) => ['info', 'success', 'warning', 'error'].includes(value)
  },
  title: {
    type: String,
    required: true
  }
})

defineOptions({
  name: 'AlertMessage'
})

const variantClasses: Record<AlertVariant, string> = {
  info: 'bg-blue-50 border border-blue-200',
  success: 'bg-green-50 border border-green-200',
  warning: 'bg-yellow-50 border border-yellow-200',
  error: 'bg-red-50 border border-red-200'
}

const textColorClass = computed(() => {
  switch (props.variant) {
    case 'info':
      return 'text-blue-800'
    case 'success':
      return 'text-green-800'
    case 'warning':
      return 'text-yellow-800'
    case 'error':
      return 'text-red-800'
    default:
      return 'text-gray-800'
  }
})

const icon = computed(() => {
  switch (props.variant) {
    case 'info':
      return InformationCircleIcon
    case 'success':
      return CheckCircleIcon
    case 'warning':
    case 'error':
      return ExclamationCircleIcon
    default:
      return InformationCircleIcon
  }
})
</script>
