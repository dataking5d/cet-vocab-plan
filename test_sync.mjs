// 用 jsdom 真跑一遍「数据同步」：本机导出 → 另一台设备导入。
// 两个 JSDOM 实例 = 两台设备 —— jsdom 的 localStorage 按实例隔离，天然就是「两台互不相干的机器」。
//
// 本版把同步从「整份覆盖」改成「按操作日志合并」：每个对象（已掌握的一个词头 / 复习库的一个词头 /
// 判分记忆的一条「词头 + 答案」）只保留时间戳更大的那一次操作，时间戳相同而一加一移时算加入。
// 这个文件里除了原有的导出/导入流程，还有一节专门跑那 9 条「必须成立的例子」。
//
// 注意: jsdom 不实现 matchMedia / scrollTo / scrollIntoView，也不实现剪贴板与 createObjectURL，
//       这里全部补 shim；页面里对后两者都做了 try/catch 兜底，补上才能把两条路径也真跑到。
import { JSDOM, VirtualConsole } from "jsdom";
import fs from "fs";

// 产物名跟着 build_html.py 里的 VERSION 走，改版时不用回来改测试
const VERSION = /^VERSION = "(.+?)"/m.exec(fs.readFileSync("build_html.py", "utf8"))[1];
const html = fs.readFileSync(`out/四六级词汇背诵清单-${VERSION}.html`, "utf8");
const errors = [];
const MKEY = "cet_vocab_mastered_v1", RKEY = "cet_vocab_review_v1", AKEY = "cet_vocab_appeals_v1";
const BKEY = "cet_vocab_battle_v1";        // 决战「已过方向」的记录（ver 3 起进导出）
const OKEY = "cet_vocab_ops_v1";           // 操作日志（本版新增，同步搬的就是它）

/* seed 里给了什么就往 localStorage 里塞什么：
   给了 ops 就不走「升级播种」那条路，于是每台设备的日志是精确已知的 —— 9 条例子靠这个才钉得住。 */
function boot(tag, seed = {}) {
  const vc = new VirtualConsole();
  vc.on("jsdomError", e => {
    if (!/Not implemented/i.test(e.message)) errors.push(tag + " jsdomError: " + e.message);
  });
  vc.on("error", (...a) => errors.push(tag + " console.error: " + a.map(String).join(" ")));
  const dom = new JSDOM(html, {
    runScripts: "dangerously",
    pretendToBeVisual: true,
    url: "http://localhost/",
    virtualConsole: vc,
    beforeParse(w) {
      w.matchMedia = q => ({ media: q, matches: false, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} });
      w.scrollTo = () => {};
      w.Element.prototype.scrollIntoView = () => {};
      const clip = { text: "" };
      clip.writeText = t => { clip.text = String(t); return Promise.resolve(); };
      clip.readText = () => Promise.resolve(clip.text);
      Object.defineProperty(w.navigator, "clipboard", { value: clip, configurable: true });
      w.__clip = clip;
      w.URL.createObjectURL = () => "blob:mock/1";
      w.URL.revokeObjectURL = () => {};
      const put = (k, v) => w.localStorage.setItem(k, JSON.stringify(v));
      if (seed.ops) put(OKEY, seed.ops);
      if (seed.mastered) put(MKEY, seed.mastered);
      if (seed.review) put(RKEY, seed.review);
      if (seed.appeals) put(AKEY, seed.appeals);
      if (seed.battle) put(BKEY, seed.battle);
    },
  });
  return dom;
}

let pass = 0, fail = 0;
function check(name, cond, extra = "") {
  if (cond) { pass++; console.log("  ok   " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? "  -> " + extra : "")); }
}

function api(dom) {
  const { window } = dom;
  const doc = window.document;
  const $ = s => doc.querySelector(s);
  const $$ = s => [...doc.querySelectorAll(s)];
  const tick = () => new Promise(r => setTimeout(r, 40));
  const flush = () => new Promise(r => setTimeout(r, 300));   // save() 有 220ms 防抖
  const fire = (el, type) => el.dispatchEvent(new window.MouseEvent(type, { bubbles: true }));
  const type = el => el.dispatchEvent(new window.Event("input", { bubbles: true }));
  const esc = () => doc.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  const ls = k => { try { return JSON.parse(window.localStorage.getItem(k) || "null"); } catch (e) { return null; } };
  const wordAt = i => {
    const c = $('#content .card[data-i="' + i + '"]');
    return c ? c.querySelector(".word").textContent.trim().toLowerCase() : null;
  };
  // 把一段文本塞进同步框并触发 input —— 等价于用户手动粘贴
  const paste = async txt => { $("#syncBox").value = txt; type($("#syncBox")); await tick(); };
  const armed = () => $("#syncApply").classList.contains("armed");
  const apply = async () => { fire($("#syncApply"), "click"); await tick(); };
  // 导出 = 开弹层 + 点复制 + 取回文本框；导入 = 开弹层 + 粘贴 + 点两下（两段式确认）
  const exp = async () => {
    fire($("#syncBtn"), "click"); await tick();
    fire($("#syncCopy"), "click"); await tick();
    const t = $("#syncBox").value;
    esc(); await tick();
    return t;
  };
  const imp = async txt => {
    fire($("#syncBtn"), "click"); await tick();
    await paste(txt);
    await apply(); await apply();
    esc(); await tick();
  };
  // jsdom 的 load 可能在 await 别的设备时就先烧掉了，所以先问 readyState 再决定要不要等
  const ready = () => doc.readyState === "complete"
    ? Promise.resolve()
    : new Promise(r => window.addEventListener("load", r, { once: true }));
  return { window, doc, $, $$, tick, flush, fire, type, esc, ls, wordAt, paste, armed, apply, exp, imp, ready };
}

/* 派生集合的读法。导入后 applySync 是直接落盘的（不走防抖），所以不用 flush */
const inM = (d, w) => (d.ls(MKEY) || []).indexOf(w) >= 0;
const inR = (d, w) => (d.ls(RKEY) || []).indexOf(w) >= 0;
const inA = (d, w, a) => ((d.ls(AKEY) || {})[w] || []).indexOf(a) >= 0;
const opOf = (d, k) => (d.ls(OKEY) || {})[k];
const mKey = w => "m:" + w, rKey = w => "r:" + w, aKey = (w, a) => "a:" + w + "\n" + a;
const add = t => ({ op: "add", t: t }), del = t => ({ op: "del", t: t });
const fileOf = o => JSON.stringify(Object.assign({ app: "cet-vocab-plan", ver: 3, total: 5271 }, o));

/* ══════════════════════ 设备 A ══════════════════════ */
console.log("\n== A · 入口与首屏 ==");
const domA = boot("A");
const A = api(domA);
await A.ready();
await A.tick();

check("头部有 ⇅ 同步按钮", !!A.$(".head-row #syncBtn"), A.$(".head-row").innerHTML.slice(0, 200));
check("同步按钮是图标型 .iconbtn（不是文字按钮）", A.$("#syncBtn").classList.contains("iconbtn"));
check("头部控件仍是 5 个（主题 + ⇅ + 检测 + 当天检测 + 复习库）",
      A.$$(".head-row > button").length === 5, A.$$(".head-row > button").length + " 个");
check("弹层初始是关的", !A.$("#sync").classList.contains("on"));
check("遮罩初始是关的", !A.$("#mask").classList.contains("on"));
check("离屏可及：同步框是 textarea", A.$("#syncBox").tagName === "TEXTAREA");
check("导入按钮不再叫「覆盖」", A.$("#syncApply").textContent.trim() === "导入并合并",
      A.$("#syncApply").textContent.trim());
check("弹层里的说明也不再说「只搬已掌握与复习库」",
      !/只搬已掌握与复习库/.test(A.$("#sync").textContent));

console.log("\n== A · 造点数据再导出 ==");
for (const i of [1, 2, 3]) A.fire(A.$('#content .card[data-i="' + i + '"] .tick label'), "click");
await A.tick();
for (const i of [9, 10]) A.fire(A.$('#content .card[data-i="' + i + '"] .star'), "click");
await A.tick();
await A.flush();
const mWords = [1, 2, 3].map(A.wordAt), rWords = [9, 10].map(A.wordAt);

check("A 已勾 3 个词", /已掌握 3 \/ 5271/.test(A.$("#progAll").textContent), A.$("#progAll").textContent);
check("A 复习库 2 词", /复习库 <b>2<\/b> 词/.test(A.$("#reviewCnt").innerHTML), A.$("#reviewCnt").innerHTML);
check("A 的 mastered 落盘了", (A.ls(MKEY) || []).length === 3, JSON.stringify(A.ls(MKEY)));
check("A 的 review 落盘了", (A.ls(RKEY) || []).length === 2, JSON.stringify(A.ls(RKEY)));

A.fire(A.$("#syncBtn"), "click");
await A.tick();
check("点 ⇅ 打开弹层", A.$("#sync").classList.contains("on"));
check("点 ⇅ 同时亮起遮罩", A.$("#mask").classList.contains("on"));
check("空框时提示「先导出」", /先从本机导出一份/.test(A.$("#syncMsg").textContent), A.$("#syncMsg").textContent);
check("空框时导入按钮不可点", A.$("#syncApply").disabled === true);

A.fire(A.$("#syncCopy"), "click");
await A.tick();
const payloadA = A.$("#syncBox").value;
check("复制后文本框里是一段 JSON", payloadA.startsWith("{") && payloadA.endsWith("}"), payloadA.slice(0, 60));
check("复制后提示为成功态", A.$("#syncMsg").classList.contains("ok"), A.$("#syncMsg").className);
check("导出不会顺手把导入按钮点亮", A.$("#syncApply").disabled === true);

let pA = null;
try { pA = JSON.parse(payloadA); } catch (e) {}
check("导出的是合法 JSON", pA !== null);
check("带 app 标记", pA && pA.app === "cet-vocab-plan", pA && pA.app);
check("带版本号 3", pA && pA.ver === 3, pA && pA.ver);
check("带总词数 5271（用于识别不同的清单版本）", pA && pA.total === 5271, pA && pA.total);
check("带 ISO 时间戳", pA && !isNaN(Date.parse(pA.ts)), pA && pA.ts);
check("mastered 就是刚勾的 3 个词头",
      JSON.stringify(pA && pA.mastered) === JSON.stringify([...mWords].sort()),
      JSON.stringify(pA && pA.mastered) + " vs " + JSON.stringify([...mWords].sort()));
check("review 就是刚加星的 2 个词头",
      JSON.stringify(pA && pA.review) === JSON.stringify([...rWords].sort()),
      JSON.stringify(pA && pA.review) + " vs " + JSON.stringify([...rWords].sort()));
check("mastered / review 全是小写词头", pA && [...pA.mastered, ...pA.review].every(s => s === s.toLowerCase()));
check("带判分记忆字段（本机还没记忆过所以是空对象）",
      pA && pA.appeals && typeof pA.appeals === "object" && !Array.isArray(pA.appeals)
        && Object.keys(pA.appeals).length === 0, JSON.stringify(pA && pA.appeals));
check("带决战方向字段（本机还没决战过所以是空对象）",
      pA && pA.battle && typeof pA.battle === "object" && !Array.isArray(pA.battle)
        && Object.keys(pA.battle).length === 0, JSON.stringify(pA && pA.battle));
check("数据里没有主题/天号/搜索历史这些本机偏好",
      pA && !("theme" in pA) && !("day" in pA) && !("hist" in pA), JSON.stringify(Object.keys(pA || {})));
check("剪贴板里拿到的就是文本框里那份", A.window.__clip.text === payloadA);
check("导出体积在合理范围（带 5 个词 + 5 条日志）", payloadA.length < 1200, payloadA.length + " 字节");

console.log("\n== A · 导出带的是完整操作日志 ==");
check("导出里有 ops 字段，且是数组", Array.isArray(pA && pA.ops), JSON.stringify(pA && pA.ops));
check("每条日志都有对象键 / add或del / 时间戳",
      pA.ops.every(o => typeof o.k === "string" && (o.op === "add" || o.op === "del")
                        && typeof o.t === "number"),
      JSON.stringify(pA.ops));
check("5 个词各一条加入（3 条已掌握 + 2 条复习库）", pA.ops.length === 5, JSON.stringify(pA.ops));
check("已掌握的键带 m: 前缀", pA.ops.filter(o => o.k.slice(0, 2) === "m:").length === 3,
      JSON.stringify(pA.ops.map(o => o.k)));
check("复习库的键带 r: 前缀", pA.ops.filter(o => o.k.slice(0, 2) === "r:").length === 2,
      JSON.stringify(pA.ops.map(o => o.k)));
check("日志按对象键排序（同一份数据两次导出逐字相同）",
      JSON.stringify(pA.ops.map(o => o.k)) === JSON.stringify(pA.ops.map(o => o.k).sort()),
      JSON.stringify(pA.ops.map(o => o.k)));
check("刚做的操作时间戳是「现在」，不是 0", pA.ops.every(o => o.t > 0), JSON.stringify(pA.ops.map(o => o.t)));
check("本机也把日志落了盘", Object.keys(A.ls(OKEY) || {}).length === 5, JSON.stringify(A.ls(OKEY)));

console.log("\n== A · 折叠态仍然不进导出 ==");
A.fire(A.$("#mask"), "click");
await A.tick();
A.fire(A.$('.sec-head .fold[data-lv="c4"]'), "click");
await A.tick();
const foldedA = A.ls("cet_vocab_fold_v1") || {};
check("导出前 A 确实折了第 1 天的四级（不是空折）", foldedA["0"] && foldedA["0"].c4 === true,
      JSON.stringify(foldedA));
A.fire(A.$("#syncBtn"), "click");
await A.tick();
A.fire(A.$("#syncCopy"), "click");
await A.tick();
const payloadFold = A.$("#syncBox").value;
let pF = null;
try { pF = JSON.parse(payloadFold); } catch (e) {}
check("折了之后导出的还是合法 JSON", pF !== null, payloadFold.slice(0, 60));
check("折叠态不出现在导出里",
      pF && !("fold" in pF) && !("cet_vocab_fold_v1" in pF), JSON.stringify(Object.keys(pF || {})));
check("折了之后导出的字段集和没折时一模一样",
      pF && JSON.stringify(Object.keys(pF)) === JSON.stringify(Object.keys(pA)),
      JSON.stringify(Object.keys(pF || {})));
A.fire(A.$("#mask"), "click");
await A.tick();
A.fire(A.$('.sec-head .fold[data-lv="c4"]'), "click");
await A.tick();
A.fire(A.$("#syncBtn"), "click");
await A.tick();
check("折回去后这一天的折叠键被删干净（不留残渣）",
      !(A.ls("cet_vocab_fold_v1") || {})["0"], A.window.localStorage.getItem("cet_vocab_fold_v1"));

console.log("\n== A · 坏数据必须被挡住，且本机一点不动 ==");
const before = A.ls(MKEY).length + "/" + A.ls(RKEY).length;
const bads = [
  ["空文本", "   ", /先从本机导出一份/],
  ["不是 JSON", "hello world", /不是合法的 JSON/],
  ["JSON 但是数组", "[1,2,3]", /这不是本词表的导出数据/],
  ["JSON 但是没有 app 标记", '{"hello":"world","items":[1,2,3]}', /缺少 app 标记/],
  ["app 标记是别的应用", '{"app":"other-app","ver":1,"mastered":[],"review":[]}', /缺少 app 标记/],
  ["版本号不认识", '{"app":"cet-vocab-plan","ver":4,"mastered":[],"review":[],"ops":[]}', /版本不认识/],
];
for (const [name, txt, re] of bads) {
  await A.paste(txt);
  const okReject = txt.trim() === "" || re.test(A.$("#syncMsg").textContent);
  check("挡住：" + name, okReject && A.$("#syncApply").disabled === true,
        A.$("#syncMsg").textContent + " / disabled=" + A.$("#syncApply").disabled);
}
await A.paste('{"app":"cet-vocab-plan","ver":1,"mastered":"abandon","review":42}');
check("字段类型不对时降级成「空数据」而不是崩（按钮可点，本机一个数都不变）",
      A.$("#syncApply").disabled === false && /已掌握 3 → 3，复习库 2 → 2/.test(A.$("#syncMsg").textContent),
      A.$("#syncMsg").textContent);
check("连试各种坏数据后，A 的数据没变",
      A.ls(MKEY).length + "/" + A.ls(RKEY).length === before,
      A.ls(MKEY).length + "/" + A.ls(RKEY).length + " vs " + before);

console.log("\n== A · 预告按合并结果写，不再写「覆盖」==");
await A.paste(fileOf({ ver: 3, ts: new Date().toISOString(), total: 9999,
                       mastered: [...mWords], review: [], appeals: {}, battle: {}, ops: [] }));
check("提示里点名了两边的词数不同", /不是同一份清单/.test(A.$("#syncMsg").innerHTML), A.$("#syncMsg").textContent);
check("警告归警告，按钮照常可点", A.$("#syncApply").disabled === false);
check("预告不再出现「覆盖」二字", !/覆盖/.test(A.$("#syncMsg").textContent), A.$("#syncMsg").textContent);
check("预告写明是按最后一次操作合并", /按最后一次操作合并/.test(A.$("#syncMsg").textContent),
      A.$("#syncMsg").textContent);
check("预告写明复习库以最后一次加入或移出为准",
      /复习库以最后一次加入或移出为准，不是整份替换/.test(A.$("#syncMsg").textContent),
      A.$("#syncMsg").textContent);

await A.paste(fileOf({ ver: 3, ts: new Date().toISOString(), total: 5271,
                       mastered: [...mWords], review: [], appeals: {}, battle: {}, ops: [] }));
check("同一份清单时不出现版本警告", !/不是同一份清单/.test(A.$("#syncMsg").innerHTML));
check("导入一份「什么都没有」的文件，本机一个数都不少（合并不是覆盖）",
      /已掌握 3 → 3，复习库 2 → 2，判分记忆 0 → 0/.test(A.$("#syncMsg").textContent),
      A.$("#syncMsg").textContent);
check("预告里的 <b> 真成了 DOM 节点，不是原样吐出来的字符",
      A.$("#syncMsg").querySelectorAll("b").length === 5,
      A.$("#syncMsg").querySelectorAll("b").length + " 个 <b>");

console.log("\n== A · 关弹层的三条路都通 ==");
A.esc();
await A.tick();
check("Escape 关掉弹层", !A.$("#sync").classList.contains("on"));
check("Escape 也收走遮罩", !A.$("#mask").classList.contains("on"));
A.fire(A.$("#syncBtn"), "click");
await A.tick();
A.fire(A.$("#syncClose"), "click");
await A.tick();
check("「关闭」按钮关掉弹层", !A.$("#sync").classList.contains("on"));
A.fire(A.$("#syncBtn"), "click");
await A.tick();
A.fire(A.$("#mask"), "click");
await A.tick();
check("点遮罩关掉弹层", !A.$("#sync").classList.contains("on"));
A.fire(A.$("#syncBtn"), "click");
await A.tick();
check("重开时保留上次粘的内容（不白粘）", A.$("#syncBox").value.indexOf("cet-vocab-plan") >= 0);
check("重开后按钮状态跟着内容走（这段数据是合法的，可点）", A.$("#syncApply").disabled === false);
A.esc();
await A.tick();

check("A 全程没有 JS 运行时错误", errors.length === 0, errors.slice(0, 3).join(" | "));

/* ══════════════════════ 设备 B（一台全新的机器）══════════════════════ */
console.log("\n== B · 空机器导入 A 的数据 ==");
const domB = boot("B");
const B = api(domB);
await B.ready();
await B.tick();

check("B 开箱是 0", /已掌握 0 \/ 5271/.test(B.$("#progAll").textContent), B.$("#progAll").textContent);
check("B 的 localStorage 是空的", B.ls(MKEY) === null && B.ls(RKEY) === null);
check("B 的日志也是空的（升级播种只给「原来有成员」的设备）",
      JSON.stringify(B.ls(OKEY)) === "{}", JSON.stringify(B.ls(OKEY)));

B.fire(B.$("#syncBtn"), "click");
await B.tick();

// 读剪贴板失败（真实浏览器里最常见的失败：没给权限 / 非 https / 用户拒绝）
const realRead = B.window.__clip.readText;
B.window.__clip.readText = () => Promise.reject(new Error("denied"));
B.fire(B.$("#syncPaste"), "click");
await B.tick(); await B.tick();
check("读剪贴板被拒时给出可操作的提示", /手动粘贴/.test(B.$("#syncMsg").textContent), B.$("#syncMsg").textContent);
check("读失败时提示是错误态", B.$("#syncMsg").classList.contains("bad"), B.$("#syncMsg").className);
B.window.__clip.readText = realRead;

// 整个没有剪贴板 API 的环境（http 下的老 Safari / 部分安卓 WebView）
delete B.window.navigator.clipboard;
B.fire(B.$("#syncPaste"), "click");
await B.tick();
check("没有剪贴板 API 时也给出可操作的提示", /手动粘贴/.test(B.$("#syncMsg").textContent), B.$("#syncMsg").textContent);
Object.defineProperty(B.window.navigator, "clipboard", { value: B.window.__clip, configurable: true });

B.window.__clip.text = payloadA;          // 相当于用户在另一台设备上复制了 A 导出的那段
B.fire(B.$("#syncPaste"), "click");
await B.tick();
await B.tick();
check("从剪贴板粘贴后文本框拿到数据", B.$("#syncBox").value === payloadA);
check("粘贴后按钮变可点", B.$("#syncApply").disabled === false);
check("粘贴后预告的是合并结果",
      /已掌握 0 → 3，复习库 0 → 2/.test(B.$("#syncMsg").textContent), B.$("#syncMsg").textContent);

B.fire(B.$("#syncApply"), "click");
await B.tick();
check("第一下只进入待确认态，不真导入", B.armed() === true);
check("待确认时按钮文案变成「确认合并」", B.$("#syncApply").textContent.trim() === "确认合并",
      B.$("#syncApply").textContent.trim());
check("待确认时 B 的数据一个字没动", B.ls(MKEY) === null && B.ls(RKEY) === null);

B.fire(B.$("#syncApply"), "click");
await B.tick();
check("第二下才真导入：mastered 落盘", (B.ls(MKEY) || []).length === 3, JSON.stringify(B.ls(MKEY)));
check("第二下才真导入：review 落盘", (B.ls(RKEY) || []).length === 2, JSON.stringify(B.ls(RKEY)));
check("日志也落盘了（5 条）", Object.keys(B.ls(OKEY) || {}).length === 5, JSON.stringify(B.ls(OKEY)));
check("顶栏计数刷新", /已掌握 3 \/ 5271/.test(B.$("#progAll").textContent), B.$("#progAll").textContent);
check("复习库计数刷新", /复习库 <b>2<\/b> 词/.test(B.$("#reviewCnt").innerHTML), B.$("#reviewCnt").innerHTML);
check("按钮复位成「导入并合并」", B.$("#syncApply").textContent.trim() === "导入并合并");
check("按钮上的待确认态被摘掉", B.armed() === false);
check("导入完的提示是成功态", B.$("#syncMsg").classList.contains("ok"), B.$("#syncMsg").className);
check("提示里报出本机现在的词数", /已掌握 <b>3<\/b> 词、复习库 <b>2<\/b> 词/.test(B.$("#syncMsg").innerHTML),
      B.$("#syncMsg").textContent);
check("提示里不再说「已覆盖」", !/覆盖/.test(B.$("#syncMsg").textContent), B.$("#syncMsg").textContent);

check("B 的卡片 ✓ 直接就是选中的（不用重开页面）",
      A.$$("#content .card[data-i]").length > 0 &&
      [1, 2, 3].every(i => B.$('#content .card[data-i="' + i + '"] input').checked === true),
      [1, 2, 3].map(i => B.$('#content .card[data-i="' + i + '"] input').checked).join(","));
check("没导进来的词保持未选中", B.$('#content .card[data-i="0"] input').checked === false);
check("B 的卡片 ★ 直接就是按下的（不用重开页面）",
      [9, 10].every(i => B.$('#content .card[data-i="' + i + '"] .star').getAttribute("aria-pressed") === "true"));
check("★ 状态同步到卡片本身的 inreview 类",
      [9, 10].every(i => B.$('#content .card[data-i="' + i + '"]').classList.contains("inreview")));
check("进度条按已掌握比例撑开", /^0\.05/.test(B.$("#barFill").style.width), B.$("#barFill").style.width);

B.esc();
await B.flush();

console.log("\n== B · 导入的数据还是要能继续用 ==");
const cbB = B.$('#content .card[data-i="4"] input');
B.fire(B.$('#content .card[data-i="4"] .tick label'), "click");
await B.tick();
check("导入后勾新词照常工作", cbB.checked === true && /已掌握 4 \/ 5271/.test(B.$("#progAll").textContent),
      B.$("#progAll").textContent);
B.fire(B.$('#content .card[data-i="4"] .tick label'), "click");
await B.tick();
check("取消勾选也照常", cbB.checked === false && /已掌握 3 \/ 5271/.test(B.$("#progAll").textContent),
      B.$("#progAll").textContent);
await B.flush();
check("取消勾选记的是一条移出（不是把记录删掉）",
      opOf(B, mKey(B.wordAt(4))) && opOf(B, mKey(B.wordAt(4))).op === "del",
      JSON.stringify(opOf(B, mKey(B.wordAt(4)))));

B.fire(B.$("#revBtn"), "click");
await B.tick();
check("导入后复习库面板打开", B.$("#rev").classList.contains("on"));
const rowsB = () => B.$$("#revList .revrow");
check("面板里正好 2 行", rowsB().length === 2, rowsB().length + " 行");
check("面板按词表原序排（about 在前、above 在后）",
      rowsB().map(r => r.querySelector(".w").textContent.trim()).join("|") === [...rWords].sort().join("|"),
      rowsB().map(r => r.querySelector(".w").textContent.trim()).join("|"));
B.fire(rowsB()[0].querySelector(".x"), "click");
await B.tick();
check("面板 ✕ 出库照常工作", rowsB().length === 1, rowsB().length + " 行");
await B.flush();                          // saveReview() 也有 220ms 防抖
check("✕ 出库后落盘的也少了一个", (B.ls(RKEY) || []).length === 1, JSON.stringify(B.ls(RKEY)));
check("✕ 出库记的是一条移出",
      opOf(B, rKey(rWords[0])) && opOf(B, rKey(rWords[0])).op === "del",
      JSON.stringify(opOf(B, rKey(rWords[0]))));
B.esc();
await B.tick();
check("Escape 关复习库面板照常", !B.$("#rev").classList.contains("on"));

console.log("\n== B · 陌生词头被丢、且不灌进不存在的词（旧文件，没有日志） ==");
/* 这是一份「很久以前导出」的文件（ts = 1970 年那一秒），所以本机后来做的操作都压得过它：
   abandon 本来就在、crew 是文件带来的新词、about 是本机已经移出去的（文件的加入更旧，回不来）。 */
const unknown = JSON.stringify({
  app: "cet-vocab-plan", ver: 1, ts: new Date(1000).toISOString(), total: 9999,
  mastered: ["abandon", "zzzznotaword", "Crew"],     // 大小写也要归一
  review: ["about", "qqqqqq"],
});
const bMasteredBefore = [...B.ls(MKEY)].sort(), bReviewBefore = [...B.ls(RKEY)].sort();
B.fire(B.$("#syncBtn"), "click");
await B.tick();
await B.paste(unknown);
check("提示里点名跳过了 2 个词头", /另有 <b>2<\/b> 个词不在本机清单里/.test(B.$("#syncMsg").innerHTML),
      B.$("#syncMsg").textContent);
check("提示里同时给出清单版本警告", /不是同一份清单/.test(B.$("#syncMsg").innerHTML));
await B.apply(); await B.apply();
check("文件里的大写 Crew 归一成 crew 并进来了", (B.ls(MKEY) || []).includes("crew"), JSON.stringify(B.ls(MKEY)));
check("本机原来掌握的词一个都没被删（合并不是覆盖）",
      bMasteredBefore.every(w => (B.ls(MKEY) || []).includes(w)), JSON.stringify(B.ls(MKEY)));
check("不存在的词头没有进任何集合",
      !(B.ls(MKEY) || []).includes("zzzznotaword") && !(B.ls(RKEY) || []).includes("qqqqqq"));
check("文件里没有的词不会被当成移出（本机复习库一个没少）",
      bReviewBefore.every(w => (B.ls(RKEY) || []).includes(w)), JSON.stringify(B.ls(RKEY)));
check("本机已经移出去的词，不会被这份更旧的文件救回来",
      !(B.ls(RKEY) || []).includes("about"), JSON.stringify(B.ls(RKEY)));

console.log("\n== B · 日志里对不上词表的对象也静默丢掉 ==");
const unknownOps = fileOf({
  ver: 3, ts: new Date().toISOString(), mastered: [], review: [], battle: {},
  ops: [{ k: "m:zzzznotaword", op: "add", t: 5000 },
        { k: "r:qqqqqq", op: "add", t: 5000 },
        { k: "a:zzzznotaword\n不存在", op: "add", t: 5000 }],
});
await B.paste(unknownOps);
check("提示里点名跳过了 3 个对象", /另有 <b>3<\/b> 个词不在本机清单里/.test(B.$("#syncMsg").innerHTML),
      B.$("#syncMsg").textContent);
await B.apply(); await B.apply();
await B.flush();
check("日志里没落下任何不存在的词头",
      !opOf(B, "m:zzzznotaword") && !opOf(B, "r:qqqqqq") && !opOf(B, "a:zzzznotaword\n不存在"),
      JSON.stringify(B.ls(OKEY)));
check("三个派生集合也没多出东西",
      !(B.ls(MKEY) || []).includes("zzzznotaword") && !(B.ls(RKEY) || []).includes("qqqqqq")
        && !("zzzznotaword" in (B.ls(AKEY) || {})),
      JSON.stringify([B.ls(MKEY), B.ls(RKEY), B.ls(AKEY)]));

console.log("\n== B · 判分记忆跟着一起搬（ver 2 旧文件） ==");
const withAppeals = JSON.stringify({
  app: "cet-vocab-plan", ver: 2, ts: new Date().toISOString(), total: 5271,
  mastered: ["abandon"], review: ["about"],
  appeals: {
    about: ["关于", "大约"],              // 正常
    abandon: [""],                        // 空答案要丢，丢完这个词就没条目了
    zzzznotaword: ["不存在的词"],          // 键不在清单里 → 整个词丢
    Crew: ["全体船员"],                    // 键大小写要归一
    above: "不是数组",                     // 值类型不对 → 当空
  },
});
B.fire(B.$("#syncBtn"), "click");
await B.tick();
await B.paste(withAppeals);
check("ver 2 不被当成「版本不认识」（上一版的文件照样收）",
      !/版本不认识/.test(B.$("#syncMsg").textContent), B.$("#syncMsg").textContent);
check("ver 2 的预告里决战过半场显示为 0 → 0 词（缺字段当空）",
      /决战过半场 0 → 0 词/.test(B.$("#syncMsg").textContent), B.$("#syncMsg").textContent);
check("预告里给出判分记忆的条数变化（本机 0 → 合并后 3 条）",
      /判分记忆 0 → 3 条/.test(B.$("#syncMsg").textContent), B.$("#syncMsg").textContent);
check("旧文件没有日志时预告里说明按文件成员合并",
      /没有操作日志/.test(B.$("#syncMsg").textContent), B.$("#syncMsg").textContent);
check("判分记忆里不认识的词头也算进「已跳过」计数",
      /另有 <b>1<\/b> 个词不在本机清单里/.test(B.$("#syncMsg").innerHTML), B.$("#syncMsg").textContent);
await B.apply(); await B.apply();
await B.flush();
const apB = B.ls(AKEY) || {};
check("判分记忆落盘了", Object.keys(apB).length === 2, JSON.stringify(apB));
check("答案原样存进去（两条都在）", JSON.stringify(apB.about) === '["关于","大约"]', JSON.stringify(apB.about));
check("键归一成小写（Crew → crew）", JSON.stringify(apB.crew) === '["全体船员"]', JSON.stringify(apB.crew));
check("不在清单里的词头没进记忆", !("zzzznotaword" in apB), JSON.stringify(Object.keys(apB)));
check("空答案的词没留下空条目", !("abandon" in apB), JSON.stringify(Object.keys(apB)));
check("值不是数组的词当空处理", !("above" in apB), JSON.stringify(Object.keys(apB)));
check("旧文件的成员在日志里记成了加入（时间戳取文件的 ISO 时间）",
      opOf(B, aKey("about", "关于")) && opOf(B, aKey("about", "关于")).op === "add"
        && opOf(B, aKey("about", "关于")).t > 0,
      JSON.stringify(opOf(B, aKey("about", "关于"))));

console.log("\n== B · 每个词的判分记忆最多留 20 条 ==");
const many = [];
// 时间戳压得比上面那些「现在」记下的还晚，被挤掉的才是真正最早的那 5 条
for (let i = 1; i <= 25; i++) many.push({ k: aKey("about", "答案" + String(i).padStart(2, "0")), op: "add", t: 2e12 + i });
await B.paste(fileOf({ ver: 3, ts: new Date().toISOString(), mastered: [], review: [], battle: {}, ops: many }));
await B.apply(); await B.apply();
await B.flush();
const apMany = (B.ls(AKEY) || {}).about || [];
check("25 条里只留 20 条", apMany.length === 20, apMany.length + " 条");
check("留的是加入时间最新的 20 条（最早那 5 条被挤掉）",
      apMany.indexOf("答案01") < 0 && apMany.indexOf("答案05") < 0 && apMany.indexOf("答案06") >= 0
        && apMany.indexOf("答案25") >= 0, JSON.stringify(apMany));

console.log("\n== B · 决战过半场的方向跟着一起搬（ver 3） ==");
const withBattle = JSON.stringify({
  app: "cet-vocab-plan", ver: 3, ts: new Date().toISOString(), total: 5271,
  mastered: ["abandon"], review: ["about"], appeals: {},
  battle: {
    about: ["spell"],                     // 正常：只过了一个方向
    abandon: ["spell", "mean"],           // 双向齐 = 这个词早该出库 → 整条丢
    zzzznotaword: ["spell"],              // 键不在本机清单里 → 丢，且计入「已跳过」
    Crew: ["mean"],                       // 键大小写要归一
    above: "不是数组",                     // 值类型不对 → 当空
    crew: ["bogus", "mean"],              // 不认识的方向名筛掉，剩一个才是有效记录
  },
  ops: [{ k: "m:abandon", op: "add", t: 5000 }],
});
B.fire(B.$("#syncBtn"), "click");
await B.tick();
await B.paste(withBattle);
check("预告里给出决战过半场的词数变化（本机 0 → 2 词）",
      /决战过半场 0 → 2 词/.test(B.$("#syncMsg").textContent), B.$("#syncMsg").textContent);
check("报的是「词数」不是「方向数」（abandon 那条双向齐的没算进来）",
      !/决战过半场 0 → 3 词/.test(B.$("#syncMsg").textContent), B.$("#syncMsg").textContent);
check("决战里不认识的词头也计入「已跳过」计数",
      /另有 <b>1<\/b> 个词不在本机清单里/.test(B.$("#syncMsg").innerHTML), B.$("#syncMsg").textContent);
await B.apply(); await B.apply();
await B.flush();
const btB = B.ls(BKEY) || {};
check("决战记录落盘了", Object.keys(btB).length === 2, JSON.stringify(btB));
check("只过一个方向的词原样存进去", JSON.stringify(btB.about) === '["spell"]', JSON.stringify(btB.about));
check("键归一成小写（Crew → crew）", JSON.stringify(btB.crew) === '["mean"]', JSON.stringify(btB.crew));
check("方向名不认识的被筛掉，有效记录留下", JSON.stringify(btB.crew) === '["mean"]', JSON.stringify(btB.crew));
check("双向都齐的条目被丢掉（留着就是留一个「都过了却还在库里」的空档）",
      !("abandon" in btB), JSON.stringify(Object.keys(btB)));
check("不在清单里的词头没进决战记录", !("zzzznotaword" in btB), JSON.stringify(Object.keys(btB)));
check("值不是数组的词当空处理", !("above" in btB), JSON.stringify(Object.keys(btB)));

console.log("\n== B · 再导出一次，和 A 的那份对得上 ==");
B.fire(B.$("#syncBtn"), "click");
await B.tick();
B.fire(B.$("#syncCopy"), "click");
await B.tick();
check("文本框被本机数据整体换掉（不是接着旧的往下贴）",
      B.$("#syncBox").value.indexOf("zzzznotaword") < 0);
let pB = null;
try { pB = JSON.parse(B.$("#syncBox").value); } catch (e) {}
check("B 导出的也是合法 JSON", pB !== null);
check("B 导出的 mastered 与落盘一致",
      JSON.stringify(pB && pB.mastered) === JSON.stringify([...B.ls(MKEY)].sort()),
      JSON.stringify(pB && pB.mastered));
check("A/B 两边的导出格式完全一致（字段集合相同）",
      JSON.stringify(Object.keys(pA).sort()) === JSON.stringify(Object.keys(pB).sort()),
      Object.keys(pB).join(","));
check("B 导出时清单词数与 A 相同", pB && pB.total === 5271);
check("B 导出的日志与落盘一致",
      JSON.stringify(pB && pB.ops) === JSON.stringify(Object.keys(B.ls(OKEY)).sort()
        .map(k => ({ k: k, op: B.ls(OKEY)[k].op, t: B.ls(OKEY)[k].t }))),
      JSON.stringify(pB && pB.ops));

console.log("\n== B · 下载 .json 这条路 ==");
B.fire(B.$("#syncDl"), "click");
await B.tick();
check("下载路径没有抛错", B.$("#syncMsg").classList.contains("ok"), B.$("#syncMsg").className);
check("下载后文本框里同样是本机数据", B.$("#syncBox").value.indexOf("cet-vocab-plan") >= 0);

console.log("\n== B · 三个弹层共用一块遮罩，各关各的 ==");
B.esc();
await B.tick();
for (const [btn, box, name] of [["#quizBtn", "#cfg", "检测配置"], ["#revBtn", "#rev", "复习库"],
                                ["#syncBtn", "#sync", "数据同步"]]) {
  B.fire(B.$(btn), "click");
  await B.tick();
  const opened = B.$(box).classList.contains("on") && B.$("#mask").classList.contains("on");
  B.fire(B.$("#mask"), "click");
  await B.tick();
  const closed = !B.$(box).classList.contains("on") && !B.$("#mask").classList.contains("on");
  check("点遮罩能开关「" + name + "」", opened && closed,
        "opened=" + opened + " closed=" + closed);
}
check("遮罩在最上层（z-index 高于吸顶头部），弹层开着时点头部点不到",
      (() => {
        const css = html.match(/\.mask\{[^}]*z-index:(\d+)/), hd = html.match(/header\{[^}]*z-index:(\d+)/);
        return css && hd && +css[1] > +hd[1];
      })());

/* ══════════════════════ 升级播种 ══════════════════════ */
console.log("\n== 升级播种：现有成员记成加入，时间戳一律 0 ==");
const domU = boot("升级", { mastered: ["abandon", "about"], review: ["crew"],
                            appeals: { crew: ["全体人员"] } });
const U = api(domU);
await U.ready();
await U.tick();
const opsU = U.ls(OKEY) || {};
check("三个集合的成员都进了日志", Object.keys(opsU).length === 4, JSON.stringify(opsU));
check("时间戳一律是 0（不是迁移时的 Date.now()）",
      Object.keys(opsU).every(k => opsU[k].t === 0), JSON.stringify(opsU));
check("记的全是加入，不给「不在库里的词」补移出",
      Object.keys(opsU).every(k => opsU[k].op === "add"), JSON.stringify(opsU));
check("升级后派生集合没变（已掌握 2、复习库 1、记忆 1 条）",
      (U.ls(MKEY) || []).length === 2 && (U.ls(RKEY) || []).length === 1
        && ((U.ls(AKEY) || {}).crew || []).length === 1,
      JSON.stringify([U.ls(MKEY), U.ls(RKEY), U.ls(AKEY)]));

/* ══════════════════════ 九条必须成立的例子 ══════════════════════ */
console.log("\n== 例 1 · 手机掌握 A、电脑掌握 B，互相同步后两边都是 A 和 B ==");
const WA = A.wordAt(1), WB = A.wordAt(2), WC = A.wordAt(3);
const d1p = boot("例1-手机", { ops: { [mKey(WA)]: add(1000) } });
const d1c = boot("例1-电脑", { ops: { [mKey(WB)]: add(1000) } });
const P1 = api(d1p), C1 = api(d1c);
await P1.ready();
await C1.ready();
await P1.tick(); await C1.tick();
await C1.imp(await P1.exp());
check("电脑侧拿到手机的 A（两边都有）", inM(C1, WA) && inM(C1, WB),
      JSON.stringify([C1.ls(MKEY), WA, WB]));
await P1.imp(await C1.exp());
check("手机侧拿到电脑的 B（两边都有）", inM(P1, WA) && inM(P1, WB), JSON.stringify(P1.ls(MKEY)));
check("两边结果逐字相同（对向同步结果必须一样）",
      JSON.stringify([...P1.ls(MKEY)].sort()) === JSON.stringify([...C1.ls(MKEY)].sort()),
      JSON.stringify([P1.ls(MKEY), C1.ls(MKEY)]));

console.log("\n== 例 2 · 两边都掌握 A，只在电脑取消 → A 不在；手机又打 ✓ → A 回来 ==");
const d2p = boot("例2-手机", { ops: { [mKey(WA)]: add(0) } });
const d2c = boot("例2-电脑", { ops: { [mKey(WA)]: del(2000) } });   // 加入过、后来取消
const P2 = api(d2p), C2 = api(d2c);
await P2.ready();
await C2.ready();
await P2.tick(); await C2.tick();
await P2.imp(await C2.exp());
check("更晚的移出压过更早的加入：A 不在", !inM(P2, WA), JSON.stringify(P2.ls(MKEY)));
P2.fire(P2.$('#content .card[data-i="1"] .tick label'), "click");   // 手机又打上 ✓
await P2.tick(); await P2.flush();
await C2.imp(await P2.exp());
check("移出之后又加入，同步后 A 回来", inM(C2, WA), JSON.stringify(C2.ls(MKEY)));

console.log("\n== 例 3/4 · 复习库的移出 / 加回 ==");
const d3p = boot("例3-手机", { ops: { [rKey(WA)]: del(3000) } });
const d3c = boot("例3-电脑", { ops: { [rKey(WA)]: add(1000) } });
const P3 = api(d3p), C3 = api(d3c);
await P3.ready();
await C3.ready();
await P3.tick(); await C3.tick();
await C3.imp(await P3.exp());
check("例3：手机移出 X、电脑还是更早的加入 → 同步后 X 不在库里", !inR(C3, WA), JSON.stringify(C3.ls(RKEY)));
C3.fire(C3.$('#content .card[data-i="1"] .star'), "click");          // 那次移出之后，电脑又加回
await C3.tick(); await C3.flush();
await P3.imp(await C3.exp());
check("例4：更晚的加入压过更早的移出 → 同步后 X 在库里", inR(P3, WA), JSON.stringify(P3.ls(RKEY)));

console.log("\n== 例 5 · 手机清空复习库，不吃掉电脑更晚才加入的 Y ==");
const d5p = boot("例5-手机", { ops: { [rKey(WA)]: del(5000), [rKey(WC)]: del(5000) } });  // 清空 = 每个词一条移出
const d5c = boot("例5-电脑", { ops: { [rKey(WA)]: add(1000), [rKey(WB)]: add(6000) } });  // Y 在清空之后加入
const P5 = api(d5p), C5 = api(d5c);
await P5.ready();
await C5.ready();
await P5.tick(); await C5.tick();
await C5.imp(await P5.exp());
check("例5：清空吃掉了电脑里更早加入的 X", !inR(C5, WA), JSON.stringify(C5.ls(RKEY)));
check("例5：清空之后才加入的 Y 还在（清空不是全局水位）", inR(C5, WB), JSON.stringify(C5.ls(RKEY)));

console.log("\n== 例 6 · 决战出库后又答错加回 ==");
const d6p = boot("例6-手机", { ops: { [rKey(WA)]: del(7000) } });    // 决战双向通过 → 出库
const d6c = boot("例6-电脑", { ops: { [rKey(WA)]: add(1000) } });    // 另一台没有更晚的加入
const P6 = api(d6p), C6 = api(d6c);
await P6.ready();
await C6.ready();
await P6.tick(); await C6.tick();
await C6.imp(await P6.exp());
check("例6：出库那台同步过去，另一台的旧加入被压掉 → Z 不在", !inR(C6, WA), JSON.stringify(C6.ls(RKEY)));
C6.fire(C6.$('#content .card[data-i="1"] .star'), "click");          // 出库之后又加回（★ 与「答错入库」同一条入口）
await C6.tick(); await C6.flush();
await P6.imp(await C6.exp());
check("例6：出库之后又加回，同步后 Z 在库里", inR(P6, WA), JSON.stringify(P6.ls(RKEY)));

console.log("\n== 例 7 · 判分记忆按「词头 + 那一条答案」算，同词的另一条答案不动 ==");
const d7p = boot("例7-手机", { ops: { [aKey(WA, "关于")]: del(5000), [aKey(WA, "大约")]: add(1000) } });
const d7c = boot("例7-电脑", { ops: { [aKey(WA, "关于")]: add(9000) } });   // 取消之后，后来又记住
const P7 = api(d7p), C7 = api(d7c);
await P7.ready();
await C7.ready();
await P7.tick(); await C7.tick();
await P7.imp(await C7.exp());
check("例7：后记住的保留（取消之后又记住的那条在）", inA(P7, WA, "关于"), JSON.stringify(P7.ls(AKEY)));
check("例7：同一词的另一条答案不受牵连", inA(P7, WA, "大约"), JSON.stringify(P7.ls(AKEY)));
await C7.imp(await P7.exp());
check("例7：反向同步结果一样", inA(C7, WA, "关于") && inA(C7, WA, "大约"), JSON.stringify(C7.ls(AKEY)));

console.log("\n== 例 8 · 同一份文件来回导两次，结果不变 ==");
const d8a = boot("例8-甲", { ops: { [mKey(WA)]: add(1000), [rKey(WB)]: add(1000),
                                    [rKey(WC)]: del(1000), [aKey(WA, "关于")]: add(1000) } });
const A8 = api(d8a);
await A8.ready();
await A8.tick();
/* 比较两台设备的「进度本身」：集合排序、对象键排序，
   免得集合/对象的插入顺序不同就被误判成不一样 */
const canon = d => {
  const o = d.ls(OKEY) || {}, ap = d.ls(AKEY) || {};
  return JSON.stringify({
    m: [...(d.ls(MKEY) || [])].sort(),
    r: [...(d.ls(RKEY) || [])].sort(),
    a: Object.keys(ap).sort().map(k => [k, [...ap[k]].sort()]),
    o: Object.keys(o).sort().map(k => [k, o[k].op, o[k].t]),
  });
};
const file8 = await A8.exp();
const d8b = boot("例8-乙", {});
const B8 = api(d8b);
await B8.ready();
await B8.tick();
await B8.imp(file8);                       // 乙：第一次导
const s1 = canon(B8);
await A8.imp(file8);                       // 甲：把自己导出的那份导回来
check("例8：把本机自己导出的文件导回本机，一个数都不变", canon(A8) === s1, canon(A8) + " vs " + s1);
await B8.imp(file8);                       // 乙：同一份文件再导一次
check("例8：同一份文件连导两次，结果不变", canon(B8) === s1, canon(B8) + " vs " + s1);
const file8b = await B8.exp();
check("例8：乙再导出，日志与甲那份逐字相同（只有 ts 不同）",
      JSON.stringify(JSON.parse(file8b).ops) === JSON.stringify(JSON.parse(file8).ops),
      JSON.stringify(JSON.parse(file8b).ops));

console.log("\n== 例 9 · 版本 2 旧文件只含 A，本机 B 的移出更晚 → 有 A 无 B ==");
const d9 = boot("例9", { ops: { [mKey(WB)]: del(9000), [mKey(WC)]: add(6000) } });
const G9 = api(d9);
await G9.ready();
await G9.tick();
await G9.imp(fileOf({ ver: 2, ts: new Date(5000).toISOString(), mastered: [WA], review: [] }));
check("例9：文件里有的 A 进来了", inM(G9, WA), JSON.stringify(G9.ls(MKEY)));
check("例9：本机更晚的移出压过文件里的加入 → 没有 B", !inM(G9, WB), JSON.stringify(G9.ls(MKEY)));
check("例9：文件里没有的词不会被删（C 还在）", inM(G9, WC), JSON.stringify(G9.ls(MKEY)));

/* ══════════════════════ 哪些动作要记 ══════════════════════ */
console.log("\n== 动作 · 检测答错入库 / 申诉撤销入库并记记忆 ==");
const dq = boot("动作-检测", { ops: { [mKey("crew")]: add(0) } });   // crew 在第 41 天
const Q = api(dq);
await Q.ready();
await Q.tick();

// 范围选「已掌握」= 只有 crew 一个词，抽题池是确定的
Q.fire(Q.$("#quizBtn"), "click");
await Q.tick();
Q.fire(Q.$('#scopeSegs .seg[data-v="mastered"]'), "click");
await Q.tick();
Q.fire(Q.$('#typeSegs .seg[data-v="mean"]'), "click");
await Q.tick();
Q.fire(Q.$("#qStart"), "click");
await Q.tick();
check("答题页开出来的是 crew", Q.$("#qBody .qword").textContent.trim() === "crew",
      Q.$("#qBody").textContent.slice(0, 60));
Q.$("#qi").value = "完全不搭边的答案";
Q.fire(Q.$("#qSubmit"), "click");
await Q.tick();
await Q.flush();
check("检测答错 → 入库（记一条加入）", inR(Q, "crew"), JSON.stringify(Q.ls(RKEY)));
check("入库那条的时间戳是「现在」", opOf(Q, rKey("crew")).t > 0, JSON.stringify(opOf(Q, rKey("crew"))));
Q.fire(Q.$("#qAppeal"), "click");            // 「我写对了」
await Q.tick();
await Q.flush();
check("申诉撤销了那次入库（记一条移出）", !inR(Q, "crew"), JSON.stringify(Q.ls(RKEY)));
check("申诉同时记下一条判分记忆", inA(Q, "crew", "完全不搭边的答案"), JSON.stringify(Q.ls(AKEY)));
Q.fire(Q.$("#qNext"), "click");
await Q.tick();

console.log("\n== 动作 · 已经在库里再答错，不刷新时间戳 ==");
Q.fire(Q.$("#rRetryAll"), "click");
await Q.tick();
Q.$("#qi").value = "又一个不搭边的答案";
Q.fire(Q.$("#qSubmit"), "click");
await Q.tick();
await Q.flush();
check("答错入库了", inR(Q, "crew"), JSON.stringify(Q.ls(RKEY)));
const t1 = opOf(Q, rKey("crew")).t;
Q.fire(Q.$("#qNext"), "click");
await Q.tick();
Q.fire(Q.$("#rRetryAll"), "click");
await Q.tick();
Q.$("#qi").value = "再错一次";
Q.fire(Q.$("#qSubmit"), "click");
await Q.tick();
await Q.flush();
check("已经在库里再答错：时间戳一点没动", opOf(Q, rKey("crew")).t === t1,
      opOf(Q, rKey("crew")).t + " vs " + t1);
Q.fire(Q.$("#qAppeal"), "click");            // 再申诉一次，给同一词攒下第二条记忆
await Q.tick();
await Q.flush();
check("第二条记忆记下来了", inA(Q, "crew", "再错一次"), JSON.stringify(Q.ls(AKEY)));
Q.fire(Q.$("#qNext"), "click");
await Q.tick();

console.log("\n== 动作 · 取消这条记忆 ==");
Q.fire(Q.$("#rClose"), "click");
await Q.tick();
Q.fire(Q.$("#quizBtn"), "click");
await Q.tick();
Q.fire(Q.$('#scopeSegs .seg[data-v="mastered"]'), "click");
await Q.tick();
Q.fire(Q.$('#typeSegs .seg[data-v="mean"]'), "click");
await Q.tick();
Q.fire(Q.$("#qStart"), "click");
await Q.tick();
Q.$("#qi").value = "完全不搭边的答案";       // 与申诉时逐字相同 → 按记忆判对
Q.fire(Q.$("#qSubmit"), "click");
await Q.tick();
check("按记忆判对", !!Q.$("#qBody .fb.ok") && !!Q.$("#qForget"), Q.$("#qBody").textContent.slice(0, 80));
Q.fire(Q.$("#qForget"), "click");
await Q.tick();
await Q.flush();
check("取消记忆 → 记一条移出，那条答案不再生效", !inA(Q, "crew", "完全不搭边的答案"),
      JSON.stringify(Q.ls(AKEY)));
check("同一词的另一条记忆不受牵连", inA(Q, "crew", "再错一次"), JSON.stringify(Q.ls(AKEY)));

console.log("\n== 动作 · 清空复习库 = 每个词各一条移出（同一个时间戳） ==");
const dcl = boot("动作-清空", { ops: { [rKey(WA)]: add(1000), [rKey(WB)]: add(1000) } });
const CL = api(dcl);
await CL.ready();
await CL.tick();
CL.fire(CL.$("#revBtn"), "click");
await CL.tick();
CL.fire(CL.$("#revClear"), "click");
await CL.tick();
CL.fire(CL.$("#revClear"), "click");       // 两段式：再点一次才真清
await CL.tick();
await CL.flush();
check("清空后库是空的", (CL.ls(RKEY) || []).length === 0, JSON.stringify(CL.ls(RKEY)));
check("两个词各留一条移出（不是把记录删掉）",
      opOf(CL, rKey(WA)).op === "del" && opOf(CL, rKey(WB)).op === "del",
      JSON.stringify(CL.ls(OKEY)));
check("两条移出是同一个时间戳（一次清空 = 一次操作）",
      opOf(CL, rKey(WA)).t === opOf(CL, rKey(WB)).t,
      JSON.stringify([opOf(CL, rKey(WA)), opOf(CL, rKey(WB))]));

console.log("\n== 动作 · 决战双向通过 → 出库记一条移出 ==");
const dbt = boot("动作-决战", { ops: { [rKey("crew")]: add(1000) }, battle: { crew: ["spell"] } });
const BT = api(dbt);
await BT.ready();
await BT.tick();
BT.fire(BT.$("#revBtn"), "click");
await BT.tick();
BT.fire(BT.$("#battleStart"), "click");
await BT.tick();
check("过了拼写就必考认义", /看英文写中文/.test(BT.$("#qBody .qtag").textContent),
      BT.$("#qBody").textContent.slice(0, 80));
BT.$("#qi").value = "全体人员";
BT.fire(BT.$("#qSubmit"), "click");
await BT.tick();
await BT.flush();
check("两个方向都过 → 出库", !inR(BT, "crew"), JSON.stringify(BT.ls(RKEY)));
check("出库记的是一条移出", opOf(BT, rKey("crew")).op === "del", JSON.stringify(opOf(BT, rKey("crew"))));

check("全部流程无 JS 运行时错误", errors.length === 0, errors.slice(0, 3).join(" | "));

console.log(`\n结果: ${pass} 通过 / ${fail} 失败`);
process.exit(fail ? 1 : 0);
