// Load this factory in the browser operator and pass the signed-in Flow tab.
// Labels are from the Simplified Chinese Flow UI. This uses visible controls only.
function createFlowUiWorker(tab) {
  const p = tab.playwright;
  const button = (name, scope = p) => scope.getByRole('button', {name, exact: true});
  const findRow = job => p.locator('.batch-container').filter({hasText: job.prompt});
  const restriction = /异常活动|unusual activity|reCAPTCHA|(?:修改|更改|改动).{0,16}(?:网页|页面).{0,16}(?:扩展|插件)|(?:扩展|插件).{0,24}(?:修改|更改|改动)|extension.{0,50}(?:modify|interfer)/i;
  const click = locator => locator.click({timeoutMs: 5000});
  const requireOne = async (locator, message) => {
    if (await locator.count() !== 1) throw Error(message);
    return locator;
  };
  const assertProject = async job => {
    if (!/^https:\/\/flow\.google\.com\/project\/[0-9a-f-]{36}$/.test(job.extra.project_url) ||
        (await tab.url()) !== job.extra.project_url) throw Error('Flow project mismatch');
  };
  const assertClear = async () => {
    const snap = await p.domSnapshot();
    if (restriction.test(snap)) throw Error('Flow displayed a restriction; stop the queue');
    return snap;
  };
  async function frame(slot, name) {
    await click(button(slot));
    const heading = p.getByRole('heading', {name: '选择画面图像', exact: true});
    await heading.waitFor({state: 'visible', timeoutMs: 5000});
    await click(await requireOne(p.getByRole('option', {name, exact: true}), `Missing or ambiguous asset: ${name}`));
    await p.domSnapshot();
    // Flow applies a click on the current selection immediately. Selecting a
    // different asset opens its preview and requires one extra confirmation.
    if (await heading.isVisible()) {
      await p.getByRole('img', {name: `“${name}”的预览`, exact: true}).waitFor({state: 'visible', timeoutMs: 5000});
      await click(button('添加到提示'));
    }
    await heading.waitFor({state: 'hidden', timeoutMs: 5000});
    if (await button(slot).isVisible()) throw Error(`Frame did not attach: ${slot}`);
  }
  return {
    async prepare(job) {
      await assertProject(job);
      await assertClear();
      const {start_asset, end_asset, resolution, duration, aspect, model, max_credits} = job.extra;
      if (!job.prompt?.trim() || !start_asset || !end_asset) throw Error('Prompt and both assets are required');
      if (await findRow(job).count()) throw Error('A matching Flow row exists; reconcile before resubmitting');
      if (!await button('开始').isVisible() || !await button('结束').isVisible() || await button('清除提示').isVisible()) {
        throw Error('Composer has a draft or is not in Frames mode');
      }
      await click(button('设置触发器'));
      const settings = await assertClear();
      const checked = (radio) => settings.split('\n').some(line => line.includes(`radio "${radio}" [checked]`));
      const resLine = settings.split('\n').find(line => line.includes(`radio "${resolution}`) && line.includes('[checked]'));
      const modelButton = await button('选择模型系列').innerText({timeoutMs: 3000});
      if (!['视频','帧',aspect,`${duration} 秒`,'x1'].every(checked) || !resLine || !modelButton.includes(model)) {
        throw Error('Current Flow settings differ from the queue manifest');
      }
      const credits = settings.match(/link "(\d+) 个点数"/)?.[1];
      if (credits === undefined || !Number.isInteger(max_credits) || Number(credits) > max_credits) {
        throw Error('Flow points unknown or above the per-job cap');
      }
      await click(button('设置触发器'));
      await frame('开始', start_asset);
      await frame('结束', end_asset);
      await p.getByRole('textbox', {name: '您希望创作什么？', exact: true}).fill(job.prompt, {timeoutMs: 5000});
      return {id: job.id, points: Number(credits), status: 'prepared'};
    },
    async submit(job) {
      await assertProject(job);
      const snap = await assertClear();
      if (await findRow(job).count()) throw Error('Matching Flow row already exists; will not resubmit');
      const textbox = p.getByRole('textbox', {name: '您希望创作什么？', exact: true});
      if ((await textbox.innerText({timeoutMs: 5000})).trim() !== job.prompt.trim() ||
          !snap.includes(`视频 · ${job.extra.resolution} · ${job.extra.duration} 秒`) ||
          !snap.includes('text: x1') || await button('图片素材').count() !== 2 || !await button('开始生成').isEnabled()) {
        throw Error('Composer no longer matches the prepared job');
      }
      // If this call fails, its outcome is unknown. Reconcile by job prompt; never retry blindly.
      await click(button('开始生成'));
      return this.status(job);
    },
    async status(job) {
      await assertProject(job);
      await assertClear();
      const row = findRow(job);
      const n = await row.count();
      if (n > 1) throw Error('Duplicate matching result cards; stop the queue');
      if (n === 0) return {id: job.id, status: 'not_visible'};
      const details = await row.innerText({timeoutMs: 5000});
      if (/生成失败|无法生成|^\s*失败\s*$/m.test(details)) throw Error(`Flow rejected job ${job.id}`);
      const download = button('下载', row);
      const video = row.getByRole('img', {name: '生成的视频缩略图', exact: true})
        .or(row.locator('[aria-label="生成的视频"]'));
      if (await download.count() === 1 && await download.isEnabled() && await video.count() > 0) {
        return {id: job.id, status: 'ready'};
      }
      const percent = details.match(/(\d{1,3})%/)?.[1];
      return {id: job.id, status: 'pending', percent: percent === undefined ? null : Number(percent)};
    },
    async requestDownload(job) {
      if ((await this.status(job)).status !== 'ready') throw Error('Video is not ready');
      // Chrome saves to its configured download directory; the browser bridge
      // did not emit a download event for this control. Check the file locally.
      const requestedAt = new Date().toISOString();
      await click(button('下载', findRow(job)));
      return {id: job.id, requestedAt};
    },
  };
}
