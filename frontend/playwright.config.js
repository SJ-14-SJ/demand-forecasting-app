import {defineConfig} from '@playwright/test';
export default defineConfig({
 testDir:'./tests',workers:1,
 use:{baseURL:'http://127.0.0.1:8000',headless:true,viewport:{width:1440,height:1050},launchOptions:{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||undefined,args:['--no-sandbox','--disable-dev-shm-usage']},trace:'retain-on-failure'},
 webServer:{command:`${process.env.PYTHON_EXECUTABLE||'python'} -m uvicorn forecast.api:app --port 8000`,cwd:'..',url:'http://127.0.0.1:8000/api/health',reuseExistingServer:true,timeout:30000},
});
