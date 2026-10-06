import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => { await page.goto('/'); });

test('匿名瀏覽首頁、六件作品及所有本地圖片', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.reload();
  await expect(page).toHaveTitle(/築跡/);
  await expect(page.locator('.project-card')).toHaveCount(6);
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-Hant');
  const images = page.locator('img');
  for (let i = 0; i < await images.count(); i++) {
    await images.nth(i).scrollIntoViewIfNeeded();
    await expect.poll(() => images.nth(i).evaluate((image: HTMLImageElement) => image.complete && image.naturalWidth > 0)).toBe(true);
  }
  expect(errors).toEqual([]);
});

test('所有作品分類顯示正確數量', async ({ page }) => {
  for (const [label, count] of [['建築設計', 2], ['模型製作', 2], ['BIM', 1], ['透視表現', 1], ['全部作品', 6]] as const) {
    await page.getByRole('button', { name: label, exact: true }).click();
    await expect(page.locator('.project-card')).toHaveCount(count);
    await expect(page.getByRole('button', { name: label, exact: true })).toHaveAttribute('aria-pressed', 'true');
  }
});

test('搜尋、空結果與重設', async ({ page }) => {
  await page.getByRole('textbox', { name: '搜尋作品' }).fill('Revit');
  await expect(page.locator('.project-card')).toHaveCount(1);
  await expect(page.locator('.project-card')).toContainText('BIM 建模練習');
  await page.getByRole('textbox', { name: '搜尋作品' }).fill('完全不存在的內容');
  await expect(page.locator('.project-card')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: '這裡還沒有作品' })).toBeVisible();
  await page.getByRole('button', { name: '查看全部作品 →' }).click();
  await expect(page.locator('.project-card')).toHaveCount(6);
});

test('彈窗內容、鍵盤 Escape 與關閉按鈕', async ({ page }) => {
  const trigger = page.getByRole('button', { name: '查看街角共享住宅詳細介紹' });
  await trigger.click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('dialog')).toContainText('設計與學習過程');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(trigger).toBeFocused();
  await trigger.click();
  await page.getByRole('button', { name: '關閉作品介紹' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
});

test('收藏、重新整理保留及取消收藏', async ({ page }) => {
  await page.getByRole('button', { name: '收藏街角共享住宅', exact: true }).click();
  await page.reload();
  await expect(page.getByRole('button', { name: '取消收藏街角共享住宅', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: /我的收藏/ }).click();
  await expect(page.locator('.project-card')).toHaveCount(1);
  await page.getByRole('button', { name: '取消收藏街角共享住宅', exact: true }).click();
  await expect(page.locator('.project-card')).toHaveCount(0);
  await expect(page.locator('.empty')).toContainText('點擊作品旁的星號');
});

test('损壞及停用瀏覽器儲存不會阻止瀏覽', async ({ page }) => {
  await page.evaluate(() => localStorage.setItem('architecture-studio-favorites', 'damaged-json'));
  await page.reload();
  await expect(page.locator('.project-card')).toHaveCount(6);
  await page.evaluate(() => { Storage.prototype.setItem = () => { throw new DOMException('Storage disabled'); }; });
  await page.getByRole('button', { name: '收藏街角共享住宅', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('無法儲存收藏');
  await expect(page.locator('.project-card')).toHaveCount(6);
});

test('手機、平板、桌面無水平溢出且保存截圖', async ({ page }) => {
  for (const [width, height, name] of [[390, 844, '手機'], [768, 1024, '平板'], [1440, 1000, '桌面']] as const) {
    await page.setViewportSize({ width, height });
    await page.evaluate(() => window.scrollTo(0, 0));
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `../驗證資料/${name}版.png`, fullPage: true });
  }
});

test('導覽、學習資源連結與彈窗內收藏', async ({ page }) => {
  await page.getByRole('navigation').getByRole('link', { name: '學習紀錄' }).click();
  await expect(page).toHaveURL(/#learning$/);
  const links = page.locator('.resource');
  await expect(links).toHaveCount(3);
  for (let i = 0; i < await links.count(); i++) {
    await expect(links.nth(i)).toHaveAttribute('href', /^https:\/\//);
    await expect(links.nth(i)).toHaveAttribute('rel', 'noopener noreferrer');
  }
  await page.getByRole('button', { name: '查看街角共享住宅詳細介紹' }).click();
  await page.getByRole('button', { name: '☆ 收藏這個作品' }).click();
  await expect(page.getByRole('button', { name: '★ 已收藏・點擊取消' })).toHaveAttribute('aria-pressed', 'true');
});
