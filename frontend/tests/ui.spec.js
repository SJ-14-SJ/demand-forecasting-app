import {test,expect} from '@playwright/test';

test('forecast controls, table, inventory and download work',async({page})=>{
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'History meets the horizon'})).toBeVisible();
 await page.getByLabel('Forecast window').selectOption('28');
 await expect(page.getByText('Expected demand · 28 days')).toBeVisible();
 await page.getByLabel('Units on hand').fill('100000');
 await expect(page.locator('.order strong')).toHaveText('0 units');
 await page.getByText('View forecast values as a table').click();
 await expect(page.locator('details tbody tr')).toHaveCount(28);
 await page.getByText('View forecast values as a table').click();
 const downloadPromise=page.waitForEvent('download');
 await page.getByRole('button',{name:'Export forecast'}).click();
 expect((await downloadPromise).suggestedFilename()).toMatch(/^forecast-.*\.csv$/);
 await page.getByLabel('Forecast window').selectOption('14');
 await page.getByLabel('Units on hand').fill('100');
 await expect(page.getByText('Expected demand · 14 days')).toBeVisible();
 await page.screenshot({path:'../docs/demo-desktop.png',fullPage:true});
});

test('mobile layout has no horizontal overflow',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'History meets the horizon'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
 await page.screenshot({path:'../docs/demo-mobile.png',fullPage:true});
});

test('a failed API request exposes a retry action',async({page})=>{
 await page.route('**/api/catalog',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Service temporarily unavailable'})}));
 await page.goto('/');
 await expect(page.getByRole('alert')).toContainText('Service temporarily unavailable');
 await expect(page.getByRole('button',{name:'Try again'})).toBeVisible();
});
