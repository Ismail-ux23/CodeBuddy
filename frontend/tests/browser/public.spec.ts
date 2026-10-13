import { test, expect } from "@playwright/test";
for (const [width, height] of [
  [390, 844],
  [768, 1024],
  [1024, 768],
  [1440, 900],
  [1920, 1080],
  [1280, 600],
]) {
  test(`landing ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.waitForTimeout(1800);
    expect(
      await page.evaluate(
        () => getComputedStyle(document.body).backgroundColor,
      ),
    ).toBe("rgb(0, 0, 0)");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    if (width > 900)
      expect(
        await page.evaluate(
          () => document.documentElement.scrollHeight <= innerHeight,
        ),
      ).toBeTruthy();
    await page.screenshot({
      path: `test-results/landing-${width}x${height}.png`,
      fullPage: true,
    });
  });
}
test("mobile keyboard menu closes and restores focus", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const menu = page.getByRole("button", { name: "Open menu" });
  await menu.click();
  await expect(page.getByRole("navigation")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(menu).toBeFocused();
  await expect(page.getByRole("navigation")).toBeHidden();
});
test("demo citation opens real source lines", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/demo");
  await page
    .getByRole("button", { name: "What happens when a quiz is submitted?" })
    .click();
  await expect(
    page.getByText("Precomputed demo answer", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /routes.py:16–19/ }).click();
  await expect(page.locator(".citation-bar")).toContainText("16–19");
  await expect(page.locator(".citation-highlight")).toHaveCount(4);
  await page.screenshot({
    path: "test-results/demo-workspace.png",
    fullPage: true,
  });
});
test("reduced motion stays visible", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  expect(
    await page.locator(".lede").evaluate((e) => getComputedStyle(e).opacity),
  ).toBe("1");
});
test("ambient animation runs and honors reduced motion", async ({ page }) => {
  await page.goto("/");
  expect(
    await page
      .locator(".grain")
      .evaluate((e) => getComputedStyle(e).animationName),
  ).toBe("none");
  expect(
    await page
      .locator(".badge")
      .evaluate((e) => getComputedStyle(e, "::after").animationName),
  ).toBe("badge-glint");
  await page.emulateMedia({ reducedMotion: "reduce" });
  expect(
    await page
      .locator(".grain")
      .evaluate((e) => getComputedStyle(e).animationName),
  ).toBe("none");
});

test("hero video plays, pauses, and respects reduced motion", async ({ page }) => {
  await page.goto("/");
  const video=page.locator(".hero-motion video");
  await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>!v.paused&&v.currentTime>.1)).toBeTruthy();
  expect(await video.evaluate((v:HTMLVideoElement)=>v.muted)).toBeTruthy();
  await page.getByRole("button",{name:"Pause hero animation"}).click();
  expect(await video.evaluate((v:HTMLVideoElement)=>v.paused)).toBeTruthy();
  await page.getByRole("button",{name:"Play hero animation"}).click();
  await page.emulateMedia({reducedMotion:"reduce"});
  await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>v.paused)).toBeTruthy();
  await expect(page.getByRole("button",{name:/hero animation/})).toBeHidden();
});

test("4K hero and cursor light follow the pointer without blocking controls", async ({page}) => {
  await page.setViewportSize({width:1440,height:900});
  await page.goto('/');
  await expect.poll(()=>page.locator('video').evaluate((v:HTMLVideoElement)=>v.videoWidth)).toBe(3840);
  expect(await page.locator('video').evaluate((v:HTMLVideoElement)=>v.videoHeight)).toBe(2160);
  await expect(page.getByText('Powered by Malik Ismail Manzoor')).toBeVisible();
  await page.mouse.move(700,300);
  await expect(page.locator('.cursor-light')).toHaveCSS('opacity','1');
  await page.mouse.move(900,240);
  await expect.poll(()=>page.locator('.cursor-light').evaluate(e=>Math.round(new DOMMatrix(getComputedStyle(e).transform).m41))).toBe(900);
  await expect(page.locator('.cursor-light')).toHaveCSS('pointer-events','none');
  await page.screenshot({path:'test-results/hero-4k-cursor.png'});
  await page.emulateMedia({reducedMotion:'reduce'});
  await expect(page.locator('.cursor-light')).toHaveCSS('display','none');
});
