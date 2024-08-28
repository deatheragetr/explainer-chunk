<template>
  <div>
    <label :for="id" class="block text-sm font-medium text-gray-700 mb-2"> Select Model </label>
    <div class="relative">
      <select
        :id="id"
        :value="modelValue"
        @change="handleChange"
        class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
      >
        <optgroup v-for="(group, groupName) in modelGroups" :key="groupName" :label="groupName">
          <option
            v-for="model in group"
            :key="model.value"
            :value="model.value"
            :disabled="model.disabled"
          >
            {{ model.label }}
          </option>
        </optgroup>
      </select>
      <div class="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none">
        <svg
          class="h-5 w-5 text-gray-400"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fill-rule="evenodd"
            d="M10 3a1 1 0 01.707.293l3 3a1 1 0 01-1.414 1.414L10 5.414 7.707 7.707a1 1 0 01-1.414-1.414l3-3A1 1 0 0110 3zm-3.707 9.293a1 1 0 011.414 0L10 14.586l2.293-2.293a1 1 0 011.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"
            clip-rule="evenodd"
          />
        </svg>
      </div>
    </div>
    <p class="mt-2 text-sm text-gray-500">
      Only GPT-4o Mini is available with your current plan. Upgrade to access more models.
    </p>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'ModelSelector',
  props: {
    modelValue: {
      type: String,
      required: true
    },
    id: {
      type: String,
      default: 'model-select'
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const modelGroups = {
      'OpenAI Models': [
        { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
        { value: 'gpt-4o', label: 'GPT-4o (Upgrade required)', disabled: true },
        { value: 'gpt-4-turbo', label: 'GPT-4 Turbo (Upgrade required)', disabled: true },
        { value: 'gpt-4', label: 'GPT-4 (Upgrade required)', disabled: true },
        { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo (Upgrade required)', disabled: true }
      ],
      'Anthropic Models': [
        {
          value: 'claude-3.5-sonnet',
          label: 'Claude 3.5 Sonnet (Upgrade required)',
          disabled: true
        },
        { value: 'claude-3-opus', label: 'Claude 3 Opus (Upgrade required)', disabled: true },
        { value: 'claude-3-haiku', label: 'Claude 3 Haiku (Upgrade required)', disabled: true }
      ],
      'Meta Models': [
        { value: 'llama-3.1', label: 'LLama 3.1 (Upgrade required)', disabled: true },
        { value: 'llama-3', label: 'LLama 3 (Upgrade required)', disabled: true }
      ]
    }

    const handleChange = (event: Event) => {
      const target = event.target as HTMLSelectElement | null
      if (target) {
        emit('update:modelValue', target.value)
      }
    }

    return {
      modelGroups,
      handleChange
    }
  }
})
</script>

<style scoped>
/* Custom styles for the dropdown */
select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
  background-position: right 0.5rem center;
  background-repeat: no-repeat;
  background-size: 1.5em 1.5em;
  padding-right: 2.5rem;
}

select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

optgroup {
  font-weight: bold;
  color: #4a5568;
}

option {
  font-weight: normal;
  color: #1a202c;
}

option:disabled {
  color: #a0aec0;
}
</style>
