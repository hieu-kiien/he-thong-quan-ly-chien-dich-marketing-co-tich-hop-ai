module.exports = {
  root: true,
  env: { browser: true, es2022: true, node: true },
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
  },
  settings: {
    react: { version: 'detect' },
  },
  plugins: ['@typescript-eslint', 'react', 'react-hooks', 'jsx-a11y'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended',
    'plugin:jsx-a11y/recommended',
  ],
  rules: {
    // Hook rules: cảnh báo, không chặn build, để các case hợp lý (ví dụ
    // effect chỉ đọc ref) vẫn build được trong khi vẫn nhìn thấy cảnh báo.
    'react-hooks/exhaustive-deps': 'warn',
    'react-hooks/rules-of-hooks': 'error',

    '@typescript-eslint/no-unused-vars': [
      'warn',
      { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrors: 'none' },
    ],
    '@typescript-eslint/no-explicit-any': 'off',
    '@typescript-eslint/no-empty-object-type': 'off',
    '@typescript-eslint/ban-ts-comment': 'off',

    // Bỏ qua: prop spreading React 19 / jsx-a11y quá nhiều so với giá trị hiện tại.
    'jsx-a11y/no-autofocus': 'off',
    'jsx-a11y/label-has-associated-control': 'off',
    // Vùng cuộn (role=region/tabIndex=0) là kỹ thuật WCAG 2.1.1 hợp lệ: cho phép
    // người dùng bàn phím cuộn nội dung ngang mà không cần chuột.
    'jsx-a11y/no-noninteractive-tabindex': [
      'error',
      { tags: [], roles: ['region', 'group', 'list', 'dialog', 'alertdialog'] },
    ],

    'no-console': ['warn', { allow: ['warn', 'error'] }],
    eqeqeq: ['warn', 'smart'],
    'prefer-const': 'warn',
  },
  ignorePatterns: ['dist', 'node_modules', 'playwright-report', 'test-results', '*.cjs'],
  overrides: [
    {
      files: ['tests/**/*.ts', '**/*.e2e.ts', 'playwright.config.ts'],
      rules: {
        'no-console': 'off',
      },
    },
  ],
};
