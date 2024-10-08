/* eslint-env node */
require('@rushstack/eslint-patch/modern-module-resolution')

module.exports = {
  root: true,
  extends: [
    'plugin:vue/vue3-essential',
    'eslint:recommended',
    '@vue/eslint-config-typescript',
    '@vue/eslint-config-prettier/skip-formatting'
  ],
  overrides: [
    {
      files: ['cypress/e2e/**/*.{cy,spec}.{js,ts,jsx,tsx}', 'cypress/support/**/*.{js,ts,jsx,tsx}'],
      extends: ['plugin:cypress/recommended']
    }
  ],
  parserOptions: {
    ecmaVersion: 'latest'
  },
  plugins: ['tailwindcss'],
  rules: {
    'tailwindcss/no-custom-classname': 'warn' // You can adjust this as needed
  },
  settings: {
    tailwindcss: {
      // fa = font awesome
      whitelist: [
        'fas',
        'fa-columns',
        'fa-edit',
        'fa-sun',
        'fa-moon',
        'fa-save',
        'editor-container',
        'editor-wrapper',
        'preview-wrapper',
        'markdown-preview',
        'notepad-editor',
        'notepad-container'
      ]
    }
  }
}
