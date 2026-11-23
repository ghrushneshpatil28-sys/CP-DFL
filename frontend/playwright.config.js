import { defineConfig } from '@playwright/test'
import process from 'node:process'

export default defineConfig({
  testDir: './e2e', workers: 1, timeout: 90000,
  use: { baseURL: 'http://127.0.0.1:5174', browserName: 'chromium', channel: 'msedge', trace: 'retain-on-failure' },
  webServer: [
    { command: '..\\backend\\venv\\Scripts\\python.exe -m uvicorn tests.e2e_setup_server:app --app-dir .. --port 8766', url: 'http://127.0.0.1:8766/api/health', timeout: 90000, reuseExistingServer: false, env: { ...process.env, CORS_ORIGINS: 'http://127.0.0.1:5174', COOKIE_SECURE: 'false' } },
    { command: '..\\backend\\venv\\Scripts\\python.exe -m uvicorn tests.e2e_server:app --app-dir .. --port 8765', url: 'http://127.0.0.1:8765/api/health', timeout: 90000, reuseExistingServer: false, env: { ...process.env, CORS_ORIGINS: 'http://127.0.0.1:5174', COOKIE_SECURE: 'false' } },
    { command: 'npm run dev -- --host 127.0.0.1 --port 5174 --strictPort', url: 'http://127.0.0.1:5174', reuseExistingServer: false, env: { ...process.env, API_PROXY_TARGET: 'http://127.0.0.1:8765' } },
  ],
})
