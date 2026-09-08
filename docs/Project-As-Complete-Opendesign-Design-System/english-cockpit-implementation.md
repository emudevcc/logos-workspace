# English Cockpit OS — UI/UX 实施指南

把 `english-cockpit-os.html`(设计原型)与 `english-cockpit-uiux-plan.md`(源真值)中的决策移植到真实仓库。
**本指南是唯一实施依据;原型 HTML 不进入仓库。**

- 真实仓库:`/Users/esteban/Documents/code_ai/english_cockpit_os`
- 基准 commit:`a8b6ade`(UI modernization),行号以该 commit 为准
- 技术栈:FastAPI + Jinja shell + Tailwind v4 + DaisyUI v5 + 原生 ESM + Vite
- 关键认知:UI 内容是 **JS 动态渲染**的。`templates/index.html` 只有 180 行 shell,每个模块是一个
  `<section data-module>` + 空 `<div data-slot>`,内容由 `static/js/components/*.js` 的 `init()` 生成。
  因此原型里的每个视觉决策都要翻译成「模板标记 + CSS 规则 + 组件 JS 输出」三处落点,而不是拷贝代码。

---

## 提交拆分总览(按序执行,每批可独立合入)

| # | 批次 | 风险 | 涉及 |
|---|---|---|---|
| C1 | 设计 token 单一化 + 死代码清理 | 低 | `cockpit.css`, `main.css` |
| C2 | 每模块唯一对比安全 accent 系统 | 低 | `cockpit.css`, `stats.js` |
| C3 | SVG 图标 helper,替换 emoji/text glyph 控件 | 低 | 新建 `static/js/lib/icons.js`,6 个组件 |
| C4 | kiosk 阅读尺度 + 触控目标 + 交互状态对比 | 低 | `main.css`, `cockpit.css`, `main.js` |
| C5 | shell 语义与可访问性 | 低 | `templates/index.html`, `main.js` |
| C6 | sidebar 状态脚重构 | 低 | `stats.js`, `main.css` |
| C7 | 卡片 → 模态「重新渲染」模式 | **中-高** | `main.js` + 全部 15 个组件 |
| C8 | 响应式 rail 折叠 + reduced-motion | 低 | `main.css` |

C1–C6、C8 互不依赖,可并行/任意序;C7 最大且触及所有组件,单独一个分支。
每批完成后跑:**`npm test`、`pytest`、`npm run build`** 全绿再进下一批。

---

## C1 — 设计 token 单一化 + 死代码清理

**问题(计划审计 A):** 两套平行样式系统——DaisyUI `cockpit` theme(`main.css`)与
`cockpit.css` 顶部 `:root`(1–21 行)各自定义一套暗色 token,组件规则吃后者。

**改动:**

1. `main.css` 的 `@plugin "daisyui/theme"`(5–32 行)保持为**唯一调色板源**
   (`--color-base-100…content`、`--color-primary` 等)。如需新增语义色,统一加在 theme 内
   (参考 C2 的 `--color-primary-deep`)。
2. `cockpit.css` 的 `:root` 从「定义值」改为「别名映射」,逐步迁移组件规则直接吃 `--color-*`:

   ```css
   :root {
     color-scheme: dark;
     --bg: var(--color-base-100);
     --surface: var(--color-base-200);
     --surface-2: var(--color-base-300);
     --text: var(--color-base-content);
     --muted: #98989d;            /* 提亮:原 #8e8e93 小字不足 4.5:1 */
     --accent: var(--color-primary);
     --accent-strong: #0a6cd6;
     --border: rgba(255, 255, 255, 0.1);
     --border-strong: rgba(255, 255, 255, 0.18);
     --font-serif: Georgia, "Iowan Old Style", "Times New Roman", serif;
   }
   ```
   (最终目标是组件规则直接用 `var(--color-*)`,别名只作过渡;`--radius/--shadow/--focus` 按需保留。)

3. **删除死规则**(已用脚本核对:templates 与全部 JS 均未引用,可放心删):
   - `cockpit.css` 38–50 行 `.cockpit-header`(含 blur 伪背景)
   - 66–71 行 `.cockpit-title`、91–98 行 `.cockpit-grid`(含 `grid-in` 动画)、
   - 137–155 行 `.cockpit-card`(含 `::after` 高光)、**161–177 行整段
     `.cockpit-card[data-module=…]` accent 表**(模板只用 `.card`,这张表是死副本)
   - `.segmented`(无任何引用)
   - `main.css` 中与 cockpit.css 重复的 `.traffic-lights`/`.tl-*`(58–70 行)二选一保留
   - **保留(活):** `.cockpit-stats`、`.cockpit-status`、`.goal-ring`、`.goal-label`、`.traffic-lights`

4. 清残留内联 token(如有 `#d8d8de` 之类内联 hex)→ 收进 `:root` 别名或 `--color-*`。

**验收:** `grep -c 'border-top-color' static/css/cockpit.css` 只剩 C2 的一张表;
页面观感与基准零差异(纯收敛)。

---

## C2 — 每模块唯一、对比安全的 accent 系统

**问题(计划审计 B):** 现有 179–192 行 `.card[data-module=…]` 表内 `prep`/`grammar`/`register`
共用 `#ff9f0a`,`podcast`/`weekly-plan` 共用 `#bf5af2`;`#ff9f0a`、`#ffd60a` 在暗底作正文色对比不足。

**改动(替换 179–192 行为单一声明源):**

1. 每模块 3 个 CSS 变量(在 `:root` 或组件容器上按 `data-module` 注入):

   ```css
   .card[data-module] { --mod: …; --mod-deep: …; --mod-text: …; }
   /* 用法:
      --mod        卡片左/上 accent 条、选中态底(装饰)
      --mod-text   暗底上的亮文本变体(链接、数值、kicker)≥ 4.5:1
      --mod-deep   白字实心按钮底,保证白字 ≥ 4.5:1(实心按钮不可用亮色底) */
   ```

2. **14 槽定稿映射**(全部互异;硬约束是**同屏互异**——同一 view 内不允许两张卡同色,
   跨 view 因不同屏可复用;替换前用 OKLch 复核正文/装饰对比):

   | module | 主色 | view 内互异核对 |
   |---|---|---|
   | today | `#0a84ff` | Today 屏 5 卡:today 蓝 / word-of-day 橙 / news 亮青 / podcast 紫 / weekly-plan 靛 ✓ |
   | word-of-day | `#ff9f0a` | ↑ |
   | news | `#5ac8fa` | ↑ |
   | podcast | `#bf5af2` | ↑ |
   | weekly-plan | `#5e5ce6`(原与 podcast 撞 `#bf5af2`,让位) | ↑ |
   | srs | `#30d158` | Practice 屏 4 卡:srs 绿 / prep 黄 / grammar 粉 / shadowing 亮蓝 ✓ |
   | prep | `#ffd60a` | ↑(仅装饰条/大字,禁用于 <14px 正文) |
   | grammar | `#ff375f`(原与 prep 撞 `#ff9f0a`,让位) | ↑ |
   | shadowing | `#64d2ff`(原 `#ffd60a` 与 prep 撞,让位) | ↑ |
   | voice | `#00c7be`(teal;原 `#64d2ff` 与 shadowing 撞,让位) | Speak 屏 3 卡:voice teal / speech 绿 / radio 红 ✓ |
   | speech | `#32d74b` | ↑ |
   | radio | `#ff453a` | ↑ |
   | declutter | `#ff6482`(原 `#ff375f` 与 grammar 撞,让位) | Write 屏 2 卡:declutter 浅粉 / register 深紫 ✓ |
   | register | `#af52de`(原 `#ff9f0a` 与 word-of-day/prep 撞,让位) | ↑ |

   > **规则**:`--mod`(上表主色)只用于装饰——accent 条、≥12px 图形、选中态底。
   > 一切正文/链接/数值一律用 `--mod-text`(由主色在暗底上派生出的 ≥4.5:1 亮变体);
   > 实心按钮用 `--mod-deep`(白字 ≥4.5:1 的深变体)。黄色系(`#ff9f0a`/`#ffd60a`)禁止用于
   > <14px 正文或浅底按钮。三个变量都放同一张 `[data-module]` 规则里,派生用 `oklch()` 微调 L/C。
3. `stats.js` 130 行的 `var(--accent)` 保留(全局主蓝)。

**验收:** 同屏任意两张卡 accent 不同;所有 accent 文本 ≥4.5:1、实心按钮白字 ≥4.5:1。

---

## C3 — SVG 图标 helper,替换 emoji/text glyph

**问题(计划审计 C):** 控件混杂——导航已是内联 SVG(`main.js`/`index.html`),但组件里
emoji/text glyph 当图标用。脚本核对含 glyph 的文件:
`static/js/main.js`(hints 的 `💡`)、`grammar.js`、`shadowing.js`、`weekly_plan.js`、
`today.js`、`stats.js`、`lib/pronounce.js`。

**改动:**

1. 新建 `static/js/lib/icons.js`,导出 `icon(name, cls?)` → 返回内联 SVG 字符串(24 viewBox、
   `stroke="currentColor"`、`aria-hidden="true"`),提供:speaker 🔊, mic 🎤、bulb/idea、flame/streak、
   check ✅、arrow-right、play、refresh、close ✕(纯文本 `✕`/`↗` 可保留为文本 glyph,不算图标)。
2. 逐文件把「emoji 作为功能图标」替换为 `icon('…')`;**提示条文案里的 💡 移到句子开头作文本**
   或改 SVG。`lib/pronounce.js` 若输出 `🔊` 到按钮 → 用 speaker 图标。
3. `main.js` 的 hints(136–164 行)保留 dismiss 逻辑,`💡` 移除。
4. 图标按钮补 `aria-label`(纯图标无文本时)。

**验收:** `grep -rn '🔊\|🎤\|💡\|🔥\|✅' static/js/` 零命中(文案中确需保留的除外,逐条说明)。

---

## C4 — kiosk 阅读尺度 + 触控目标 + 状态对比

**前提:** 1080p 电视、1–3 m、无鼠标、`--disable-gpu`。最小可读 ≈16px 正文、≥20px 卡片标题。

**改动:**

1. **字号档**:`main.css` 视口基准调大——
   `.nav-item` 0.9rem→1rem、`.view-title` 1.15rem→clamp(1.4rem,2vw,1.75rem)、
   `.card-title` 由 DaisyUI 默认调至 1.15rem+;组件内 13px 以下小字逐一提到 ≥14px(正文 ≥16px)。
2. **触控 ≥44px**:`.nav-item` padding 加到 ≥44px 命中高度;组件内可点 chip/选项按钮统一最小高度。
3. **实心按钮对比 + focus**:DaisyUI `.btn-primary`(白字 on `#0a84ff` ≈3.65:1,不足)。
   在 theme 加 `--color-primary-deep:#0a6cd6`(≈4.7:1)作主按钮实心底;
   `:focus-visible` 环改白色/反色环,避免融入同色底(原型的 `--acc-d/--acc-dh` 语义)。
4. **hover/active 成对变化**:背景按 OKLch L ±0.06–0.12 位移;前景永不变浅。
5. `cockpit-status` 的 online/offline 文本与边框色已达标,保留。

**验收:** 1080p 站 3 m 可读;Tab 全遍历有可见 focus;无 <44px 触控目标。

---

## C5 — shell 语义与可访问性

**改动:**

1. `templates/index.html`:
   - 卡片标题层级已连续(`h1` sidebar app-title → `h2` view-title → `h3` card-title);确认 modal 标题
     (165–176 行)不用 `h3` 而用 `h2`,并与打开来源卡在文档序上不重复。
   - `<dialog id="card-modal">` 补 `aria-labelledby="card-modal-title"`。
   - 卡片区 `<section>` 已带 `aria-labelledby`(模板现状),保留。
2. `main.js`:
   - `setupNavigation()`(120–134 行):活跃项设 `aria-current="page"`,切换时同步移除旧项。
   - modal 打开函数给关闭按钮 `aria-label="Close"`(模板已有)+ 打开后焦点移入、关闭回焦点(见 C7 一起做)。
3. 若卡片标题可点击是唯一开模态入口且无文本提示,补 `data-od` 风格的可发现提示(如标题行尾
   「Open ↗」,文本 glyph 即可,原型同款)。

**验收:** 键盘 Tab 可进入并打开每个模块;NVDA/VoiceOver 读出正确层级;`aria-current` 随视图切换。

---

## C6 — sidebar 状态脚重构

**问题:** `stats.js` 137 行 `goal-label` 渲染 `${done}/${goal}` 单行,与相邻词连排成
「6 / 20reviews done」(原型修的粘连 bug);goal ring 的 dashoffset 与比例不符。

**改动:**

1. `stats.js` 状态脚渲染为结构化两行:
   - 行 1:大号数值(`font-variant-numeric: tabular-nums`,mono/数显)→ 行 2:小号标签,两行各自独立块。
   - greeting、due 数、目标环保持真实 API/本地数据,**不改数值来源、不造数**。
2. goal ring:`dashoffset = circumference × (1 − done/goal)`,stroke 用 `var(--accent)`(现状已引用,
   保留);比例文案与环必须一致。
3. `main.css` 141–149 行 `.app-sidebar .cockpit-stats` 垂直布局微调 gap、字号 0.85rem→0.95rem。

**验收:** 「done/goal + reviews」不再粘连;环弧长与数字比例一致。

---

## C7 — 卡片 → 模态「重新渲染」模式(唯一中-高工作量)

**问题(计划审计 E、S06):** `main.js` `setupCardModal()`(87–118 行)把卡片里的整个 `data-slot`
**append 进** modal,关闭再搬回——活 DOM 搬迁,状态/事件/滚动位置全带进带出,文档描述的旧「focus mode」与此不符。

**目标模式(来自原型):** 卡片摘要与模态全视图是两个独立渲染;点开卡片 → 按当前数据**重新渲染**全视图进
modal;关闭 → 丢弃,卡片摘要原地刷新。数据源一致 ⇒ 无 DOM 搬迁。

**改动:**

1. `main.js`:删除「搬迁」逻辑,改为
   `openModule(name, ctx)`:`bodyEl.replaceChildren(renderModuleFull(name))`,`dialog.showModal()`;
   `close` 事件只清空 body、触发该模块 `refreshSummary()`(若需要)。
2. 每个组件 `init(slot, ctx)` 拆两个入口(命名约定,全组件一致):

   ```js
   export function init(slot, ctx) { slot.replaceChildren(renderSummary(ctx)); }
   export function renderSummary(ctx) { … }   // 卡片态:紧凑,含 1 个主 CTA
   export function renderFull(ctx)   { … }    // 模态态:全工作区(原 init 的完整内容)
   ```

   组件若订阅 WS/定时器,`renderFull` 返回的 DOM 需自带 `onclose`/清理,或由 `openModule` 在关闭时
   触发 `module.dispose?.(viewEl)`。**新增 dispose 约定:** `dispose(viewEl)` 停定时器/取消订阅。
3. 15 个组件逐一迁移;每个组件迁移 = 一次小 commit,便于回归。
4. 卡片主 CTA(如 Today「Study next card」)保持:跳转视图 + 打开目标模块模态,逻辑不变。

**验收:** 打开-关闭-再打开同一模块,无重复事件监听、无残留定时器;播放/录音类模块关闭后确认
麦克风/音频停止;WS 消息不重复渲染;`npm test` 中纯逻辑测试不受影响。

---

## C8 — 响应式 rail 折叠 + reduced-motion

**改动(`main.css`):**

1. `@media (max-width: 760px)`:sidebar 从 15rem 折叠为 84px 图标 rail——隐藏 `.app-title`、
   `.traffic-lights`、`.cockpit-stats`/`.cockpit-status` 与 nav 文本,仅留 SVG 图标;
   面板卡片 1 列;禁横向滚动。
2. `@media (prefers-reduced-motion: reduce)`:关 `magic-fade`、`.card:hover::before` 过渡、
   btn shimmer;`setupMagic` 的 mousemove 监听在无指针设备直接不挂(见 C1)。
3. 若 C1 保留 shimmer/spotlight,此批兜底关闭;建议 C1 直接删。

**验收:** 760px 无横向滚动、图标 rail 可切全部 4 视图;系统开 reduced-motion 后无位移动画。

---

## 验证(每批后、合入前)

```bash
npm test          # node --test tests/frontend/ —— lib/ 纯逻辑
pytest            # tests/backend/
npm run build     # Vite → static/dist/(index.html 为 rollup input;无 bundle 时后端伺服源码)
```

**Kiosk 验收(合入主干后):** 1080p Chromium `--disable-gpu`,走三条验收流
(Today「Study next card」→ SRS;语音 hold-to-talk 往返;Writing Coach 两种动作)+
模态开合/点词翻译/WS 断线重连;目视 3 m 距离可读性。

**前端 UI 无自动化覆盖**:`tests/frontend/*.test.js` 只测 `lib/`。C3/C7 若想加保护,
为 icon helper 与 module registry 补 `node --test` 单测(纯函数可测部分)。

---

## 边界与风险

- **原型 token 名**(`--acc-t/--acc-d/--acc-dh/--mc/.kik/.phead`)仅作语义参考,不要求原名落库;
  本指南建议的 CSS 变量名可直接用,但**不要**把原型 HTML 结构/类名搬进模板。
- **C2 映射表需定稿唯一色**后再动 `stats.js`/`today.js` 引用 accent 处,避免中途不一致。
- 组件内 accent 若以 CSS 类(`.mc` 等)实现而非变量,先统一为变量再调色,避免逐处改 hex。
- `.cockpit-stats`/`.cockpit-status` 在 main.css 与 cockpit.css 各有一份定义,收敛时保留一份,勿双双保留。

## 依赖的仓库事实(已核对,基准 a8b6ade)

- 模板 shell:180 行;模块卡 14 张,均已带 `data-module` + `aria-labelledby` + `data-slot`。
- 死类(全库零引用):`cockpit-card`(含其 `[data-module]` 表与 `::after`)、`cockpit-grid`、
  `cockpit-header`、`cockpit-title`、`segmented`。
- emoji/glyph 控件文件:`main.js`、`grammar.js`、`shadowing.js`、`weekly_plan.js`、`today.js`、
  `stats.js`、`lib/pronounce.js`。
- 模态搬迁逻辑:`static/js/main.js` 87–118 行(`setupCardModal`)。
- 鼠标 spotlight:`main.js` 74–85 行(`setupMagic`)+ `main.css` `.card::before`;旋转渐变边框:
  `main.css` 213–244 行 `.magic-gradient-border`(today 卡在用,`--disable-gpu` 上昂贵)。
- accent 双份表:`cockpit.css` 161–177(死,`.cockpit-card*`)、179–192(活,`.card*`)。
- 导航切换:`main.js` 120–134 行(`setupNavigation`,无 `aria-current`)。
- sidebar 统计:`stats.js`(`goal-label` `${done}/${goal}` 粘连源;goal ring 用 `var(--accent)`)。
