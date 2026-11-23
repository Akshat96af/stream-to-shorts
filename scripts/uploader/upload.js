// stream-to-shorts by Akshat96af⁠​‌​​​​​‌​‌‌​‌​‌‌​‌‌‌​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​‌​​​​‌‌‌​​‌​​‌‌​‌‌​​‌‌​​​​‌​‌‌​​‌‌​⁠ | Copyright (c) 2026 Akshat96af. All rights reserved. See LICENSE.
// Uploads the queued items to YouTube Studio. PRIVATE unless the item says visibility:"public"
// (make_run.py only queues public items after approval AND the release time). Tags/cover are best-effort.
// TEMPLATE: the MCP sandbox has no fs/require, so __QUEUE__ is filled in by the command in CLAUDE.md,
// which writes uploader/run.js; run THAT with Playwright MCP browser_run_code_unsafe(filename=run.js).
// queue.json: [{"file":"/path/to/final/clip 01.mp4","title":"...","desc":"...","done":false}]
async (page) => {
  const CH = '__CHANNEL__';  // your Studio URL, filled in from sts.config.json "studio_url" by make_run.py
  const queue = __QUEUE__;
  page.on('dialog', d => d.accept().catch(() => {}));
  const results = [];
  for (const it of queue) {
    if (it.done) continue;
    const notes = [];
    try {
      await page.goto(CH, {waitUntil: 'domcontentloaded'});
      await page.getByRole('button', {name: 'Create'}).first().click({timeout: 30000});
      await page.getByRole('menuitem', {name: /Upload videos/i}).click({timeout: 15000});
      await page.waitForSelector('input[type="file"]', {state: 'attached', timeout: 30000});
      await page.setInputFiles('input[type="file"]', it.file);
      const title = page.locator('#title-textarea #textbox');
      await title.waitFor({timeout: 90000});
      await title.evaluate(e => e.focus()); await page.keyboard.press('Control+A');  // focus, not click: an overlay backdrop can swallow clicks
      await page.keyboard.insertText(it.title.slice(0, 100));
      await page.locator('#description-textarea #textbox').evaluate(e => e.focus()); await page.keyboard.press('Control+A');
      await page.keyboard.insertText(it.desc || '');
      await page.locator('tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]').evaluate(e => e.click());
      const alt = page.locator('tp-yt-paper-radio-button[name="VIDEO_HAS_ALTERED_CONTENT_NO"]');
      if (await alt.count()) await alt.evaluate(e => e.click());
      try {  // best-effort: the first real upload verifies/fixes these selectors
        if (it.tags && it.tags.length) {
          await page.locator('#toggle-button').click({timeout: 4000});
          await page.locator('#tags-container input').first().fill(it.tags.join(',') + ',', {timeout: 4000});
        }
      } catch (e) { notes.push('tags skipped'); }
      try {
        if (it.cover) { await page.locator('#file-loader').first().setInputFiles(it.cover, {timeout: 4000}); await page.waitForTimeout(3000); if (!(await page.locator('ytcp-thumbnails-compact-editor-uploader img, #still-picker img').count())) notes.push('cover unverified (no thumb img; Shorts may ignore custom covers)'); }
      } catch (e) { notes.push('cover skipped'); }
      for (let i = 0; i < 6 && !(await page.locator('ytcp-uploads-dialog tp-yt-paper-radio-button[name="PUBLIC"]').isVisible()); i++) {
        await page.locator('ytcp-uploads-dialog #next-button').evaluate(e => e.click()); await page.waitForTimeout(2000);  // evaluate: an overlay backdrop can block real clicks  // the step count varies (Checks / Ads)
      }
      const vis = it.visibility === 'public' ? 'PUBLIC' : 'PRIVATE';
      const dlg = page.locator('ytcp-uploads-dialog');
      await dlg.locator('tp-yt-paper-radio-button[name="' + vis + '"]').evaluate(e => e.click());
      if (vis === 'PUBLIC') {  // root cause of the Drafts: publishing before the copyright check ends opens a "you may get a strike" warning
        await page.getByText('Checks complete').first().waitFor({timeout: 900000});  // WAIT for the check (never "Publish anyway")
        const after = (await dlg.innerText()).replace(/\s+/g, ' ');
        const seg = after.slice(after.indexOf('Checks complete'), after.indexOf('Checks complete') + 200);
        if (!/No issues found/i.test(seg)) throw new Error('YouTube check found issues, NOT publishing: ' + seg.slice(0, 120));
      }
      await page.waitForFunction(() => { const b = document.querySelector('ytcp-uploads-dialog #done-button'); return b && !b.hasAttribute('disabled') && b.getAttribute('aria-disabled') !== 'true'; }, null, {timeout: 240000});
      await dlg.locator('#done-button').evaluate(e => e.click());
      await page.waitForTimeout(3000);
      if (vis === 'PUBLIC') {
        await page.getByText('Video published').first().waitFor({timeout: 60000}).catch(() => {});  // publishing takes ~10-30 s
        if (!(await page.getByText('Video published').count())) throw new Error('no "Video published" confirmation after the checks passed: check Studio');
        await page.keyboard.press('Escape'); await page.waitForTimeout(1000);  // close the confirmation (its backdrop blocks the next upload)
      }
      results.push('ok: ' + it.file + (notes.length ? ' (' + notes.join(', ') + ')' : ''));
    } catch (e) {
      results.push('FAILED: ' + it.file + ' | ' + String(e).slice(0, 120));
    }
  }
  return results;
}
