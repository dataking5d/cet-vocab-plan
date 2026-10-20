// 用 jsdom 真跑一遍交付页面，验证渲染 / 勾选 / 持久化 / 翻页 / 搜索 / 主题
// 注意: jsdom 不实现 matchMedia / scrollTo / scrollIntoView，这里补 no-op shim，
//       仅为让脚本跑到底，被测的渲染与状态逻辑仍是页面原样代码。
import { JSDOM, VirtualConsole } from "jsdom";
import fs from "fs";

// 产物名跟着 build_html.py 里的 VERSION 走，改版时不用回来改测试
const VERSION = /^VERSION = "(.+?)"/m.exec(fs.readFileSync("build_html.py", "utf8"))[1];
const html = fs.readFileSync(`out/四六级词汇背诵清单-${VERSION}.html`, "utf8");
const errors = [];

const vc = new VirtualConsole();
vc.on("jsdomError", e => {
  if (!/Not implemented/i.test(e.message)) errors.push("jsdomError: " + e.message);
});
vc.on("error", (...a) => errors.push("console.error: " + a.map(String).join(" ")));

const dom = new JSDOM(html, {
  runScripts: "dangerously",
  pretendToBeVisual: true,
  url: "http://localhost/",
  virtualConsole: vc,
  beforeParse(w) {
    w.matchMedia = q => ({ media: q, matches: false, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} });
    w.scrollTo = () => {};
    w.Element.prototype.scrollIntoView = () => {};
  },
});

const { window } = dom;
const doc = window.document;
const $ = s => doc.querySelector(s);
const $$ = s => [...doc.querySelectorAll(s)];
const tick = () => new Promise(r => setTimeout(r, 40));
const flush = () => new Promise(r => setTimeout(r, 300));   // save() 有 220ms 防抖
const fire = (el, type) => el.dispatchEvent(new window.MouseEvent(type, { bubbles: true }));

let pass = 0, fail = 0;
function check(name, cond, extra = "") {
  if (cond) { pass++; console.log("  ok   " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? "  -> " + extra : "")); }
}

await new Promise(r => window.addEventListener("load", r, { once: true }));
await tick();

console.log("\n== 首屏渲染 ==");
let cards = $$(".card");
check("第1天渲染出 30 张词卡", cards.length === 30, "实际 " + cards.length);
check("有四级分区", !!$(".sec.s4"));
check("有六级分区", !!$(".sec.s6"));
const s4 = $$(".sec.s4 .card").length, s6 = $$(".sec.s6 .card").length;
check("四级+六级 = 30", s4 + s6 === 30, `四级${s4} 六级${s6}`);
check("天数下拉有 176 项", $$("#day option").length === 176, "实际 " + $$("#day option").length);
check("总词数 5271", /已掌握 0 \/ 5271/.test($("#progAll").textContent), $("#progAll").textContent);
check("顶栏显示总数", /5271 词 · 176 天/.test($("#totalLabel").textContent), $("#totalLabel").textContent);
check("prev 在第1天禁用", $("#prev").disabled === true);
check("next 可用", $("#next").disabled === false);

const first = cards[0];
check("首词有单词", first.querySelector(".word").textContent.trim().length > 0);
check("首词有中文释义", first.querySelector(".cn").textContent.trim() !== "—", first.querySelector(".cn").textContent);
check("首词有音标", !!first.querySelector(".ipa"));
check("首卡 data-i=0", first.dataset.i === "0", first.dataset.i);
// 分区会把六级词提到后面，所以 DOM 顺序 != 原始序号顺序，按集合断言
const idx = cards.map(c => +c.dataset.i).sort((a, b) => a - b);
check("30 张卡覆盖序号 0..29", idx.join(",") === [...Array(30).keys()].join(","), idx.join(","));
const asc = a => a.every((v, i) => i === 0 || a[i - 1] < v);
check("四级区内部按原序递增", asc($$(".sec.s4 .card").map(c => +c.dataset.i)));
check("六级区内部按原序递增", asc($$(".sec.s6 .card").map(c => +c.dataset.i)));
check("勾选框 id 唯一", new Set($$('.card input[type="checkbox"]').map(c => c.id)).size === cards.length);
check("每张卡都有 label 绑定 input",
      $$(".card").every(c => c.querySelector("label").htmlFor === c.querySelector("input").id));

// 派生词：第 14 版起带音标与释义（able 下面挂着 ability）。
// 第 1 天有 14 个带派生词的词条，其中 able->ability 是 ECDICT 里释义/音标都齐的典型样本。
const ableCard = cards.find(c => c.querySelector(".word").textContent.trim() === "able");
check("第 1 天找得到 able 这张卡", !!ableCard);
if (ableCard) {
  const dv = ableCard.querySelector(".deriv");
  check("able 卡有派生词区块", !!dv);
  check("派生词标着「派生」二字", dv && /派生/.test(dv.textContent), dv && dv.textContent.slice(0, 30));
  const dvw = dv && dv.querySelector(".dv .dv-w");
  check("派生词词形是 ability", dvw && dvw.textContent.trim() === "ability", dvw && dvw.textContent);
  const dvi = dv && dv.querySelector(".dv .dv-ipa");
  check("派生词带音标（able→ability）", !!dvi, dv && dv.innerHTML.slice(0, 120));
  check("派生词音标是英式 /əˈbɪlɪti/", dvi && /əˈbɪlɪti/.test(dvi.textContent), dvi && dvi.textContent);
  const dvc = dv && dv.querySelector(".dv .dv-cn");
  check("派生词带释义", !!dvc && dvc.textContent.trim().length > 0, dvc && dvc.textContent);
  check("派生词释义含「能力」", dvc && /能力/.test(dvc.textContent), dvc && dvc.textContent);
}
// 一个词挂多个派生词时，每个各占一行（academy -> academic / academician）
const acadCard = cards.find(c => c.querySelector(".word").textContent.trim() === "academy");
check("academy 卡有两个派生词", acadCard && acadCard.querySelectorAll(".deriv .dv").length === 2,
      acadCard && acadCard.querySelectorAll(".deriv .dv").length);
check("两个派生词各带自己的音标",
      acadCard && [...acadCard.querySelectorAll(".deriv .dv")].every(r => r.querySelector(".dv-ipa")));
/* 派生词层的两处修复 pin（第 14 版）。都直接读页面里的数据，不走 UI 翻页——
   被修的词散落在第 99 / 125 天，翻页去够它们既慢又脆。
   1. tokenize 里 ECDICT 优先于 wordninja——否则 microwavable / quantification / reparable
      这类不在 wordninja 的 3 万词表、却在 ECDICT 77 万词条里的派生词会被切碎，
      而且碎片恰好都是真词（micro/wav/able），"碎片不是真词"那条检查抓不住。
   2. DERIV_FIX 表修源文档录入错误（错拼 3 处 + 两词粘连 2 处）。
   这两条钉的是「数据层跑对了」：只测 UI 的话，词被切碎了照样渲染得出来。 */
const dataInto = (() => {
  const out = {};
  // 页面的 DAYS / ALL / DATA 都是顶层 const（词法绑定，不挂 window，所以 window.DAYS 取不到），
  // 而 function 声明的 spellOK / meanOK 才挂得上——这就是上面那几条能用 W.xxx 的原因。
  // eval 在页面全局作用域里执行，能读到顶层 const。
  const days = window.eval("typeof DAYS !== 'undefined' ? DAYS : []");
  for (const day of days) for (const w of day) out[w.w.toLowerCase()] = w;
  return out;
})();
const dvWords = w => (dataInto[w] ? dataInto[w].deriv.map(d => d.w) : null);
check("microwave 的派生词没被切碎（是 microwaveable，不是 micro/wav/able）",
      JSON.stringify(dvWords("microwave")) === JSON.stringify(["microwaveable"]),
      JSON.stringify(dvWords("microwave")));
check("microwave 的派生词带释义",
      dataInto["microwave"] && /微波炉/.test(dataInto["microwave"].deriv[0].cn),
      dataInto["microwave"] && dataInto["microwave"].deriv[0].cn);
check("quantify 的派生词是 quantification（原先切成 quant/if/cation）",
      JSON.stringify(dvWords("quantify")) === JSON.stringify(["quantification"]),
      JSON.stringify(dvWords("quantify")));
check("repair 的派生词是 reparable（原先切成 re/parable）",
      JSON.stringify(dvWords("repair")) === JSON.stringify(["reparable"]),
      JSON.stringify(dvWords("repair")));
check("suppress 的两个派生词都对（原先切成 suppression/ive...）",
      JSON.stringify(dvWords("suppress")) === JSON.stringify(["suppression", "suppressive"]),
      JSON.stringify(dvWords("suppress")));
check("complete 的派生词是 completion（源文档错拼 comletion）",
      JSON.stringify(dvWords("complete")) === JSON.stringify(["completion"]),
      JSON.stringify(dvWords("complete")));
check("compliment 的派生词是 complimentary（源文档错拼 complimetary）",
      JSON.stringify(dvWords("compliment")) === JSON.stringify(["complimentary"]),
      JSON.stringify(dvWords("compliment")));
check("habit 的两个派生词拆开了（源文档挤成一格 habitual habitat）",
      JSON.stringify(dvWords("habit")) === JSON.stringify(["habitual", "habitat"]),
      JSON.stringify(dvWords("habit")));
check("indignant 的两个派生词拆开了（源文档挤成一格）",
      JSON.stringify(dvWords("indignant")) === JSON.stringify(["indignation", "indispensable"]),
      JSON.stringify(dvWords("indignant")));
check("派生词全部带释义，覆盖率 100%", (() => {
  const all = Object.values(dataInto).flatMap(w => w.deriv);
  const miss = all.filter(d => !d.cn);
  return all.length > 2400 && miss.length === 0;
})(), (() => {
  const all = Object.values(dataInto).flatMap(w => w.deriv);
  return all.filter(d => !d.cn).length + " 条缺释义";
})());
check("全页无 __DATA__ 占位残留", !html.includes("__DATA__"));

console.log("\n== 勾选（点 label，走真实事件路径）==");
const cb0 = first.querySelector('input[type="checkbox"]');
check("初始未勾选", cb0.checked === false);
fire(first.querySelector(".tick label"), "click");
await tick();
check("input 被勾选", cb0.checked === true);
check("卡片加上 done 类", first.classList.contains("done"));
check("总进度 +1", /已掌握 1 \/ 5271/.test($("#progAll").textContent), $("#progAll").textContent);
check("本日进度 +1", /本日 1 \/ 30/.test($("#progDay").textContent), $("#progDay").textContent);

console.log("\n== 持久化（save 有 220ms 防抖，等 flush）==");
await flush();
const stored = JSON.parse(window.localStorage.getItem("cet_vocab_mastered_v1") || "[]");
check("localStorage 写入 1 条", stored.length === 1, JSON.stringify(stored));
check("写入的是刚勾的词", stored[0] === first.querySelector(".word").textContent.trim().toLowerCase(), String(stored[0]));

// 取消勾选应回滚
fire(first.querySelector(".tick label"), "click");
await tick();
check("再点一次取消勾选", cb0.checked === false && !first.classList.contains("done"));
await flush();
check("取消后存储清空", JSON.parse(window.localStorage.getItem("cet_vocab_mastered_v1")).length === 0,
      window.localStorage.getItem("cet_vocab_mastered_v1"));
fire(first.querySelector(".tick label"), "click");
await flush();

console.log("\n== 翻页 ==");
fire($("#next"), "click");
await tick();
cards = $$(".card");
check("第2天仍 30 卡", cards.length === 30, "实际 " + cards.length);
check("第2天首卡 data-i=30", cards[0].dataset.i === "30", cards[0].dataset.i);
check("下拉同步到第2天", $("#day").value === "1", $("#day").value);
check("第2天无 done 卡", $$(".card.done").length === 0);
check("第2天已掌握总数不变(1)", /已掌握 1 \/ 5271/.test($("#progAll").textContent), $("#progAll").textContent);
check("本日进度归零", /本日 0 \/ 30/.test($("#progDay").textContent), $("#progDay").textContent);

// 勾第2天一个词，验证两个词的 key 不冲突
fire($$(".card")[5].querySelector(".tick label"), "click");
await flush();
check("第2天勾选后总数=2", /已掌握 2 \/ 5271/.test($("#progAll").textContent), $("#progAll").textContent);
check("localStorage 有 2 条不同词", new Set(JSON.parse(window.localStorage.getItem("cet_vocab_mastered_v1"))).size === 2);

// 回到第1天，勾选状态应还在
fire($("#prev"), "click");
await tick();
check("返回第1天勾选仍在", $$(".card.done").length === 1);
check("返回第1天进度显示 1/30", /本日 1 \/ 30/.test($("#progDay").textContent), $("#progDay").textContent);

// 跳到第 176 天（末天 21 词）
$("#day").value = "175";
$("#day").dispatchEvent(new window.Event("change", { bubbles: true }));
await tick();
check("第176天有 21 卡", $$(".card").length === 21, "实际 " + $$(".card").length);
check("末天 next 禁用", $("#next").disabled === true);
check("末天 prev 可用", $("#prev").disabled === false);

console.log("\n== 搜索 ==");
fire($("#searchBtn"), "click");
const q = $("#q");
check("搜索面板打开", $("#panel").classList.contains("on"));
check("空输入显示提示", /输入关键词/.test($("#res").textContent), $("#res").textContent.slice(0, 40));
q.value = "abandon";
q.dispatchEvent(new window.Event("input", { bubbles: true }));
await tick();
let rows = $$("#res .row");
check("搜到 abandon", rows.length >= 1, "结果 " + rows.length);
check("结果显示所在天", /第 1 天/.test(rows[0].querySelector(".d").textContent), rows[0].querySelector(".d").textContent);
check("首条默认选中", rows[0].classList.contains("sel"));

q.value = "放弃";
q.dispatchEvent(new window.Event("input", { bubbles: true }));
await tick();
check("支持中文释义搜索", $$("#res .row").length >= 1, "结果 " + $$("#res .row").length);

q.value = "zzzqqq";
q.dispatchEvent(new window.Event("input", { bubbles: true }));
await tick();
check("无结果时提示", /没有匹配/.test($("#res").textContent), $("#res").textContent.slice(0, 40));

// 点结果跳转
q.value = "abandon";
q.dispatchEvent(new window.Event("input", { bubbles: true }));
await tick();
fire($$("#res .row")[0], "click");
await tick();
check("点击结果关闭面板", !$("#panel").classList.contains("on"));
check("点击结果跳到第1天", $("#day").value === "0", $("#day").value);

console.log("\n== 键盘快捷键 ==");
doc.body.dispatchEvent(new window.KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
await tick();
check("→ 翻到第2天", $("#day").value === "1", $("#day").value);
doc.body.dispatchEvent(new window.KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
await tick();
check("← 回到第1天", $("#day").value === "0", $("#day").value);
doc.body.dispatchEvent(new window.KeyboardEvent("keydown", { key: "/", bubbles: true }));
await tick();
check("/ 打开搜索", $("#panel").classList.contains("on"));
doc.body.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
await tick();
check("Esc 关闭搜索", !$("#panel").classList.contains("on"));

console.log("\n== 主题 ==");
const before = doc.documentElement.getAttribute("data-theme");
fire($("#themeBtn"), "click");
await tick();
const after = doc.documentElement.getAttribute("data-theme");
check("主题切换生效", before !== after, before + " -> " + after);
check("主题已持久化", window.localStorage.getItem("cet_vocab_theme") === after);
fire($("#themeBtn"), "click");
await tick();
check("再点回到浅色", doc.documentElement.getAttribute("data-theme") === "light", doc.documentElement.getAttribute("data-theme"));

console.log("\n== 重新打开（模拟刷新，读回进度与天数）==");
const dom2 = new JSDOM(html, {
  runScripts: "dangerously", pretendToBeVisual: true, url: "http://localhost/",
  beforeParse(w) {
    w.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
    w.scrollTo = () => {}; w.Element.prototype.scrollIntoView = () => {};
    // 把上一轮的 localStorage 灌进去
    w.localStorage.setItem("cet_vocab_mastered_v1", window.localStorage.getItem("cet_vocab_mastered_v1"));
    w.localStorage.setItem("cet_vocab_day", "1");
  },
});
await new Promise(r => dom2.window.addEventListener("load", r, { once: true }));
await new Promise(r => setTimeout(r, 80));
check("刷新后停在第2天", dom2.window.document.querySelector("#day").value === "1",
      dom2.window.document.querySelector("#day").value);
check("刷新后进度保留", /已掌握 2 \/ 5271/.test(dom2.window.document.querySelector("#progAll").textContent),
      dom2.window.document.querySelector("#progAll").textContent);

console.log("\n== 搜索长条 ==");
doc.body.dispatchEvent(new window.KeyboardEvent("keydown", { key: "/", bubbles: true }));
await tick();
check("/ 快捷键聚焦搜索长条", doc.activeElement === $("#q"), doc.activeElement ? doc.activeElement.tagName : "null");
check("/ 打开结果浮层", $("#panel").classList.contains("on"));
doc.body.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
await tick();
check("Esc 收起结果浮层", !$("#panel").classList.contains("on"));

console.log("\n== 复习库（★ 控件，cet_vocab_review_v1）==");
const cds = $$(".card");                       // 重新取：前面 render() 过多次，旧引用已脱离 DOM
check("header 有带文字的检测按钮", /检测/.test($("#quizBtn").textContent), $("#quizBtn").textContent);
check("搜索是整行长条（40px 级）", !!$(".searchbar") && !!$(".searchbar #q"));
check("长条里有搜索图标按钮", !!$(".searchbar #searchBtn"));
check("顶栏显示复习库计数", /复习库\s*0\s*词/.test($("#reviewCnt").textContent), $("#reviewCnt").textContent);
check("每张卡都有 ★ 控件", $$(".card .star").length === cds.length, "实际 " + $$(".card .star").length);

const star0 = cds[0].querySelector(".star");
const w0 = cds[0].querySelector(".word").textContent.trim().toLowerCase();
check("初始 ★ 未按下", star0.getAttribute("aria-pressed") === "false");
check("初始 title 是「加入复习库」", star0.title === "加入复习库", star0.title);

fire(star0, "click");
await tick();
check("点 ★ 后 aria-pressed=true", star0.getAttribute("aria-pressed") === "true");
check("点 ★ 后 title 变成「从复习库移除」", star0.title === "从复习库移除", star0.title);
check("点 ★ 后卡片加 .inreview", cds[0].classList.contains("inreview"));
check("顶栏复习库计数 +1", /复习库\s*1\s*词/.test($("#reviewCnt").textContent), $("#reviewCnt").textContent);
await flush();
let rv = JSON.parse(window.localStorage.getItem("cet_vocab_review_v1") || "[]");
check("★ 写入 cet_vocab_review_v1", rv.length === 1 && rv[0] === w0, JSON.stringify(rv));
check("★ 不影响 cet_vocab_mastered_v1", JSON.parse(window.localStorage.getItem("cet_vocab_mastered_v1")).length === 2);

fire(star0, "click");
await tick();
check("再点 ★ 取消按下", star0.getAttribute("aria-pressed") === "false");
check("再点 ★ 去掉 .inreview", !cds[0].classList.contains("inreview"));
check("再点 ★ 计数归零", /复习库\s*0\s*词/.test($("#reviewCnt").textContent), $("#reviewCnt").textContent);
await flush();
check("再点 ★ 出库（存储清空）", JSON.parse(window.localStorage.getItem("cet_vocab_review_v1")).length === 0,
      window.localStorage.getItem("cet_vocab_review_v1"));

console.log("\n== 运行时错误 ==");
check("无 JS 运行时错误", errors.length === 0, errors.slice(0, 3).join(" | "));

/* ══════════════════════════════════════════════════════════════
   检测：配置 → 逐题作答 → 结果。
   用独立 JSDOM 预置 localStorage，把复习库/已掌握压成已知集合，
   这样抽题池是确定的，可以逐题断言判分与进出库。
   ══════════════════════════════════════════════════════════════ */
function boot(seed = {}) {
  const errs = [];
  const v = new VirtualConsole();
  v.on("jsdomError", e => { if (!/Not implemented/i.test(e.message)) errs.push("jsdomError: " + e.message); });
  v.on("error", (...a) => errs.push("console.error: " + a.map(String).join(" ")));
  const d = new JSDOM(html, {
    runScripts: "dangerously", pretendToBeVisual: true, url: "http://localhost/",
    virtualConsole: v,
    beforeParse(w) {
      w.matchMedia = q => ({ media: q, matches: false, addEventListener() {}, removeEventListener() {},
                            addListener() {}, removeListener() {} });
      w.scrollTo = () => {};
      w.Element.prototype.scrollIntoView = () => {};
      w.localStorage.setItem("cet_vocab_review_v1", JSON.stringify(seed.review || []));
      w.localStorage.setItem("cet_vocab_mastered_v1", JSON.stringify(seed.mastered || []));
      w.localStorage.setItem("cet_vocab_appeals_v1", JSON.stringify(seed.appeals || {}));
      w.localStorage.setItem("cet_vocab_search_hist_v1", JSON.stringify(seed.hist || []));
      w.localStorage.setItem("cet_vocab_fold_v1", JSON.stringify(seed.fold || {}));
      // 决战的「已过方向」记录（第 11 版）。种子它能钉死 dirForWord() 的出题方向，
      // 于是「这个词这场考拼写还是考认义」不再靠撞运气——见后面的决战段。
      w.localStorage.setItem("cet_vocab_battle_v1", JSON.stringify(seed.battle || {}));
      w.localStorage.setItem("cet_vocab_day", "0");
    },
  });
  d.__errs = errs;
  return d;
}

const dq = boot({ mastered: ["crew"] });
await new Promise(r => dq.window.addEventListener("load", r, { once: true }));
await tick();

const W = dq.window, DQ = W.document;
const $d = s => DQ.querySelector(s);
const $$d = s => [...DQ.querySelectorAll(s)];
const tq = () => new Promise(r => setTimeout(r, 40));
const fq = () => new Promise(r => setTimeout(r, 300));   // saveReview() 也是 220ms 防抖
const fireQ = (el, type) => el.dispatchEvent(new W.MouseEvent(type, { bubbles: true }));
const rvNow = () => JSON.parse(W.localStorage.getItem("cet_vocab_review_v1") || "[]");
const seg = (group, v) => $d(`#${group}Segs .seg[data-v="${v}"]`);
const rvSize = () => +(/复习库 (\d+) 词/.exec(txt("#reviewCnt")) || [0, 0])[1];
const apNow = () => JSON.parse(W.localStorage.getItem("cet_vocab_appeals_v1") || "{}");
const bkCnt = i => $$d("#qBody .res-bk")[i].querySelector(".cnt").textContent;
const txt = s => (DQ.querySelector(s) ? DQ.querySelector(s).textContent.replace(/\s+/g, " ").trim() : "(缺 " + s + ")");

console.log("\n== 检测配置面板 ==");
fireQ($d("#quizBtn"), "click");
await tq();
check("检测按钮打开配置面板", $d("#cfg").classList.contains("on"));
check("范围默认选中复习库", seg("scope", "review").classList.contains("on"));
check("复习库为空时「开始」禁用", $d("#qStart").disabled === true);
check("空复习库提示文案", /复习库是空的，先背几天或选其它范围/.test(txt("#qEmpty")), txt("#qEmpty"));
check("范围按钮带各自词数", /复习库（0）/.test(txt('#scopeSegs .seg[data-v="review"]')) &&
      /全部（5271）/.test(txt('#scopeSegs .seg[data-v="all"]')) &&
      /已掌握（1）/.test(txt('#scopeSegs .seg[data-v="mastered"]')), txt("#scopeSegs"));
check("题型默认看中文写英文", seg("type", "spell").classList.contains("on"));

fireQ(seg("scope", "mastered"), "click");
await tq();
check("切范围后「开始」可用", $d("#qStart").disabled === false);
check("题数上限收敛到 min(范围内词数,200)", $d("#qNum").max === "1" && $d("#qNum").value === "1",
      $d("#qNum").max + " / " + $d("#qNum").value);
check("题数提示写明范围内词数", /范围内共 1 词，最多可抽 1 题/.test(txt("#qNumHint")), txt("#qNumHint"));

console.log("\n== 答题页 · 认义题（看英文写中文）==");
fireQ(seg("type", "mean"), "click");
await tq();
fireQ($d("#qStart"), "click");
await tq();
check("进入全屏答题页", $d("#qscreen").classList.contains("on"));
check("题数生效：第 1 题 / 1", txt("#qIdx") === "第 1 题 / 1", txt("#qIdx"));
check("认义题题干是英文大字", txt("#qBody .qword") === "crew", txt("#qBody .qword"));
check("认义题不给音标", !$d("#qBody .ipa"));
check("题干标签含题型", /看英文写中文/.test(txt("#qBody .qtag")), txt("#qBody .qtag"));

console.log("\n== 判错 → 进复习库 · 部分匹配提示 · 申诉 ==");
$d("#qi").value = "人员";                       // 与义项「全体人员」共享 2 个连续汉字
fireQ($d("#qSubmit"), "click");
await tq();
check("答错显示错态", !!$d("#qBody .fb.bad"));
check("答错立即显示正确答案", /全体人员/.test(txt("#qBody .fb .ans")), txt("#qBody .fb .ans"));
check("认义题给出部分匹配提示", /部分匹配/.test(txt("#qBody .fb .part")), txt("#qBody .fb .part"));
check("答错有「我写对了」申诉按钮", !!$d("#qAppeal"));
await fq();
check("检测答错 → 该词进复习库", rvNow().indexOf("crew") >= 0, JSON.stringify(rvNow()));

fireQ($d("#qAppeal"), "click");
await tq();
check("申诉后改判为对", !!$d("#qBody .fb.ok"));
check("申诉后注明不计入错题", /不计入错题/.test(txt("#qBody .fb .sub")), txt("#qBody .fb .sub"));
await fq();
check("申诉 → 不进库", rvNow().indexOf("crew") < 0, JSON.stringify(rvNow()));

console.log("\n== 结果页 ==");
fireQ($d("#qNext"), "click");
await tq();
check("进入结果页", txt("#qIdx") === "检测完成", txt("#qIdx"));
check("总分 1 / 1", /^1 \/ 1$/.test(txt("#qBody .big")), txt("#qBody .big"));
check("结果页显示范围与题型", /范围：已掌握/.test(txt("#qBody .lbl")) && /题型：看英文写中文/.test(txt("#qBody .lbl")),
      txt("#qBody .lbl"));
check("分题型得分：认义 1 / 1", /看英文写中文 1 \/ 1/.test(txt("#qBody .split")), txt("#qBody .split"));
check("分题型得分：拼写 0 / 0", /看中文写英文 0 \/ 0/.test(txt("#qBody .split")), txt("#qBody .split"));
check("申诉的题不计入错题列表", /0 词/.test(txt("#qBody .res-bk .cnt")), txt("#qBody .res-bk .cnt"));
check("有「再测 M 题」", /再测 1 题/.test(txt("#rRetryAll")), txt("#rRetryAll"));
check("无错题时不显示「只重测错词」", !$d("#rRetryWrong"));

console.log("\n== 再测 · 认义题写任一义项算对 ==");
fireQ($d("#rRetryAll"), "click");
await tq();
check("再测回到第 1 题", txt("#qIdx") === "第 1 题 / 1", txt("#qIdx"));
$d("#qi").value = "一群人";                     // 第 2 个义项
fireQ($d("#qSubmit"), "click");
await tq();
check("认义题写任一义项就算对", !!$d("#qBody .fb.ok"));
fireQ($d("#qNext"), "click");
await tq();
await fq();
check("答对且不在库时保持不入库", rvNow().length === 0, JSON.stringify(rvNow()));

console.log("\n== 答题页 · 拼写题（看中文写英文）==");
fireQ($d("#rClose"), "click");
await tq();
check("「返回列表」关闭答题页", !$d("#qscreen").classList.contains("on"));
fireQ($d("#quizBtn"), "click");
await tq();
fireQ(seg("type", "spell"), "click");
await tq();
fireQ($d("#qStart"), "click");
await tq();
check("拼写题题干是完整中文释义", /全体人员/.test(txt("#qBody .qcn")), txt("#qBody .qcn"));
check("拼写题不给英文大字", !$d("#qBody .qword"));
check("拼写题标签", /看中文写英文/.test(txt("#qBody .qtag")), txt("#qBody .qtag"));
$d("#qi").value = "crew";
fireQ($d("#qSubmit"), "click");
await tq();
check("拼写题答对", !!$d("#qBody .fb.ok"));
fireQ($d("#qNext"), "click");
await tq();
check("拼写题满分 1 / 1", /^1 \/ 1$/.test(txt("#qBody .big")), txt("#qBody .big"));
check("拼写题得分记在拼写半边", /看中文写英文 1 \/ 1/.test(txt("#qBody .split")), txt("#qBody .split"));

console.log("\n== 拼写题错拼：不给申诉，也不给部分匹配提示 ==");
fireQ($d("#rClose"), "click");
await tq();
fireQ($d("#quizBtn"), "click");
await tq();
fireQ($d("#qStart"), "click");                 // 范围/题型沿用上一次（已掌握 · 拼写）
await tq();
$d("#qi").value = "crcket";                     // 与 cricket 共享 6 个字符，但只是打错字
fireQ($d("#qSubmit"), "click");
await tq();
check("拼写题错拼判错", !!$d("#qBody .fb.bad"));
check("拼写题不做部分匹配提示", !$d("#qBody .fb .part"));
/* 第 8 版起拼写题没有申诉入口。拼写题的答案集由 spellAnswers() 唯一确定，
   「我写对了」在这个题型上没有立足点；词头记法没编码到的合法变体改由
   build_data.py 的 SPELL_VARIANTS 点名补进答案集（见后面「拼写变体」那段）。
   所以这里断言的是「没有按钮」，而不是「点了之后会怎样」——按钮已经不存在了。 */
check("拼写题判错不给「我写对了」", !$d("#qAppeal"));
await fq();
check("拼写题答错进复习库（出库只由手动操作）", rvNow().indexOf("crew") >= 0, JSON.stringify(rvNow()));
check("拼写题答错不留任何判分记忆", (apNow().crew || []).indexOf("crcket") < 0, JSON.stringify(apNow()));
fireQ($d("#qNext"), "click");
await tq();
fireQ($d("#rClose"), "click");
await tq();

console.log("\n== 复习库中答对 → 仍留库 · 申诉只撤销「本次入库」 ==");
$d("#day").value = "40";                        // crew 在第 41 天
$d("#day").dispatchEvent(new W.Event("change", { bubbles: true }));
await tq();
const crewCard = $$d(".card").find(c => c.querySelector(".word").textContent.trim() === "crew");
check("第 41 天能找到 crew 卡", !!crewCard);
/* 上面那道拼写题答错把 crew 留在了库里——第 8 版拿掉拼写申诉后不再自动移出
   （旧流程里那次申诉会顺手把它撤出，所以本段原先可以直接假定「不在库」）。
   ★ 是开关，所以先把状态归一成「未入库」，本段才测得到「入库」这个方向。 */
if (rvNow().indexOf("crew") >= 0){
  fireQ(crewCard.querySelector(".star"), "click");
  await tq(); await fq();
}
check("先把 crew 清成未入库（★ 是开关）", rvNow().indexOf("crew") < 0, JSON.stringify(rvNow()));
fireQ(crewCard.querySelector(".star"), "click");
await tq();
check("★ 让计数变 1", /复习库 1 词/.test(txt("#reviewCnt")), txt("#reviewCnt"));
await fq();
check("★ 把 crew 放进复习库", rvNow().indexOf("crew") >= 0, JSON.stringify(rvNow()));

fireQ($d("#quizBtn"), "click");
await tq();
fireQ(seg("scope", "review"), "click");
await tq();
check("范围切到复习库：可开始且题数上限 1", $d("#qStart").disabled === false && $d("#qNum").value === "1",
      $d("#qStart").disabled + " / " + $d("#qNum").value);
fireQ(seg("type", "mean"), "click");
await tq();
fireQ($d("#qStart"), "click");
await tq();
check("抽到复习库里的词", txt("#qBody .qword") === "crew", txt("#qBody .qword"));
$d("#qi").value = "全体人员";
fireQ($d("#qSubmit"), "click");
await tq();
check("复习库中答对判对", !!$d("#qBody .fb.ok"));
check("答对反馈不再提「移出」", !/移出/.test(txt("#qBody .fb .sub")), txt("#qBody .fb .sub"));
await fq();
check("答对后 crew 仍留在复习库（出库只由手动操作）", rvNow().indexOf("crew") >= 0, JSON.stringify(rvNow()));
fireQ($d("#qNext"), "click");
await tq();
check("结果页只剩「错题」一个 .res-bk 分区", $$d("#qBody .res-bk").length === 1,
      $$d("#qBody .res-bk").length + " 个");
check("结果页提示答对的词仍留在复习库", /仍留在复习库/.test(txt("#qBody .rhint")), txt("#qBody .rhint"));
check("结果页不再有「撤销移出」按钮", !$d("#rUndo"));

/* 申诉的边界：只该撤销「本次答错顺手入库」那一条。
   词本来就在库里时，答错 → 申诉 → 必须仍留在库里，不能被误删。 */
fireQ($d("#rRetryAll"), "click");
await tq();
check("再测回到第 1 题 / 1", txt("#qIdx") === "第 1 题 / 1", txt("#qIdx"));
$d("#qi").value = "电脑";                        // 故意答错
fireQ($d("#qSubmit"), "click");
await tq();
check("答错显示错态", !!$d("#qBody .fb.bad"));
await fq();
check("本来就在库里的词，答错后仍在库（未被「答错入库」重复添加）", rvNow().indexOf("crew") >= 0, JSON.stringify(rvNow()));
fireQ($d("#qAppeal"), "click");
await tq();
await fq();
check("申诉不误删「本来就在库里」的词", rvNow().indexOf("crew") >= 0, JSON.stringify(rvNow()));
fireQ($d("#qNext"), "click");
await tq();

/* 判分记忆：申诉过的答案再写一次不该重复报错。
   上面刚申诉过 crew 的「电脑」，所以此刻库里应当正好记着这一条。
   顺序有意为之：先验「只认那一串」，再验「按记忆判对」，最后拆掉记忆验它真的失效。 */
console.log("\n== 判分记忆 · 申诉过的答案下次直接判对 ==");
await fq();
check("申诉过的答案都记了下来（同一个词可累积多条）",
      JSON.stringify(apNow().crew) === '["人员","电脑"]', JSON.stringify(apNow()));
/* 第 7 版曾把拼写答案也记进这张表（判分规范化按题型分，拼写走 normEn）；
   第 8 版整块拿掉了拼写申诉。上面那道拼写题写过 crcket，这里确认它一个字节都没留下。 */
check("拼写题不留判分记忆（第 8 版起）", (apNow().crew || []).indexOf("crcket") < 0, JSON.stringify(apNow().crew));

fireQ($d("#rClose"), "click");
await tq();
fireQ($d("#quizBtn"), "click");
await tq();
fireQ(seg("scope", "review"), "click");
await tq();
fireQ(seg("type", "mean"), "click");
await tq();
fireQ($d("#qStart"), "click");
await tq();
$d("#qi").value = "计算机";                      // 同一道题，换个说法
fireQ($d("#qSubmit"), "click");
await tq();
check("换个说法不算：记忆是按答案记的，不是「这个词写什么都算对」", !!$d("#qBody .fb.bad"));
check("换说法判错时没有「按记忆判对」的文案", !/之前确认过的答案/.test(txt("#qBody .fb .sub")), txt("#qBody .fb .sub"));
fireQ($d("#qNext"), "click");
await tq();

fireQ($d("#rRetryAll"), "click");
await tq();
$d("#qi").value = "电脑";                        // 与申诉时逐字相同
fireQ($d("#qSubmit"), "click");
await tq();
check("写回申诉过的那串：直接判对", !!$d("#qBody .fb.ok"));
check("反馈说明是按记忆判对的", /按你之前确认过的答案判对/.test(txt("#qBody .fb .sub")), txt("#qBody .fb .sub"));
check("按记忆判对时不再给「我写对了」", !$d("#qAppeal"));
check("按记忆判对时给「取消这条记忆」", !!$d("#qForget") && /取消这条记忆/.test(txt("#qForget")));

fireQ($d("#qForget"), "click");
await tq();
check("取消记忆后反馈改口，不再说「按记忆判对」", /这条记忆已取消/.test(txt("#qBody .fb .sub")), txt("#qBody .fb .sub"));
check("取消后「取消这条记忆」入口自己收起来", !$d("#qForget"));
check("取消记忆不回退判分：本题仍是答对", !!$d("#qBody .fb.ok"));
await fq();
check("取消只删这一条，同词的其它记忆不受牵连",
      JSON.stringify(apNow().crew) === '["人员"]', JSON.stringify(apNow()));
fireQ($d("#qNext"), "click");
await tq();

fireQ($d("#rRetryAll"), "click");
await tq();
$d("#qi").value = "电脑";                        // 记忆已拆，应该恢复成正常判错
fireQ($d("#qSubmit"), "click");
await tq();
check("记忆拆掉后再写同一串，恢复成正常判错", !!$d("#qBody .fb.bad"));
check("恢复判错时又给出申诉入口", !!$d("#qAppeal"));
fireQ($d("#qNext"), "click");
await tq();
fireQ($d("#rClose"), "click");
await tq();

/* 拼写题不记判分记忆（第 8 版起）。
   第 7 版这一段验的是「申诉 → 下次写同一串直接判对」；第 8 版把拼写申诉整块拿掉了——
   拼写题的答案集由 spellAnswers() 唯一确定，「我写对了」在这个题型上没有立足点，
   而词头记法没编码到的合法变体改由 build_data.py 的 SPELL_VARIANTS 点名补进答案集
   （见「判分规则」里那几条 pin）。所以这段反过来钉：同一串写两次，两次都判错。 */
console.log("\n== 拼写题 · 同一串写两次都判错（第 8 版拿掉了拼写记忆） ==");
fireQ($d("#quizBtn"), "click");
await tq();
fireQ(seg("scope", "mastered"), "click");
await tq();
fireQ(seg("type", "spell"), "click");
await tq();
fireQ($d("#qStart"), "click");
await tq();
$d("#qi").value = "crue";                        // 一个上面没用过的错拼串
fireQ($d("#qSubmit"), "click");
await tq();
check("拼写题第一次写错拼串：判错", !!$d("#qBody .fb.bad"));
check("判错时没有申诉入口", !$d("#qAppeal"));
check("反馈里不提「已记住这个答案」", !/已记住这个答案/.test(txt("#qBody .fb .sub")), txt("#qBody .fb .sub"));
await fq();
check("这次判错没往判分记忆里写任何东西", (apNow().crew || []).indexOf("crue") < 0, JSON.stringify(apNow()));
fireQ($d("#qNext"), "click");
await tq();

fireQ($d("#rRetryAll"), "click");
await tq();
$d("#qi").value = "crue";                        // 与上次逐字相同
fireQ($d("#qSubmit"), "click");
await tq();
check("同一串再写一次：仍然判错（拼写题没有「下次自动判对」）", !!$d("#qBody .fb.bad"));
check("也没有「按你之前确认过的答案判对」这种文案", !/之前确认过的答案/.test(txt("#qBody .fb .sub")), txt("#qBody .fb .sub"));
check("判错时不给「取消这条记忆」（那条路只属于认义题）", !$d("#qForget"));
fireQ($d("#qNext"), "click");
await tq();
fireQ($d("#rClose"), "click");
await tq();

console.log("\n== 混合题型 · 范围=全部 ==");
const rvBefore = rvSize();
fireQ($d("#rClose"), "click");
await tq();
fireQ($d("#quizBtn"), "click");
await tq();
fireQ(seg("scope", "all"), "click");
await tq();
check("全部范围：默认 20 题、上限 200", $d("#qNum").value === "20" && $d("#qNum").max === "200",
      $d("#qNum").value + " / " + $d("#qNum").max);
fireQ(seg("type", "mixed"), "click");
await tq();
fireQ($d("#qStart"), "click");
await tq();
check("题数生效：共 20 题", txt("#qIdx") === "第 1 题 / 20", txt("#qIdx"));
const kinds = [];
for (let i = 0; i < 20; i++) {
  if (i === 19) check("最后一题是第 20 题 / 20", txt("#qIdx") === "第 20 题 / 20", txt("#qIdx"));
  kinds.push(/看中文写英文/.test(txt("#qBody .qtag")) ? "spell" : "mean");
  fireQ($d("#qSkip"), "click");
  await tq();
  check(`第 ${i + 1} 题跳过也判错并进库`, !!$d("#qBody .fb.bad"));
  fireQ($d("#qNext"), "click");
  await tq();
}
check("混合题型每题独立二选一（两种都出现）",
      kinds.indexOf("spell") >= 0 && kinds.indexOf("mean") >= 0, kinds.join(","));
check("20 题答完进入结果页", txt("#qIdx") === "检测完成", txt("#qIdx"));
check("结果页标注题型：混合", /题型：混合/.test(txt("#qBody .lbl")), txt("#qBody .lbl"));
await fq();
/* 用「这 20 个词是否都在库里」而不是 rvBefore + 20：
   全表随机抽题有极小概率抽到库里已有的词，那样计数会少 1，断言就会假失败 */
const skipped20 = $$d("#qBody .wrongrow .w").map(e => e.textContent.trim().toLowerCase());
check("跳过 20 题 → 这 20 个词全部进复习库", skipped20.length === 20 && skipped20.every(w => rvNow().includes(w)),
      rvBefore + " -> " + rvNow().length);
check("跳过 20 题 → 顶栏计数与存储一致", rvSize() === rvNow().length, rvSize() + " / " + rvNow().length);
check("错题列表 20 条且每条带题型标签", $$d("#qBody .wrongrow").length === 20 &&
      $$d("#qBody .wrongrow .mt").every(m => /^(拼写|认义)$/.test(m.textContent)),
      $$d("#qBody .wrongrow").length + " 条");
check("错题列表归属「错题」分区", /错题（已全部加入复习库）/.test($$d("#qBody .res-bk")[0].textContent.trim().slice(0, 30)), bkCnt(0));

/* ══════════════════════════════════════════════════════════════
   当天检测：头部一键开考「当前翻到的那天」的 30 词。
   重点验证它跟着 #day 走（翻到第 3 天就测第 3 天），
   且结果页「再测 30 题」不会退化成从全表 5271 词里随机抽。
   ══════════════════════════════════════════════════════════════ */
console.log("\n== 当天检测 ==");
const selDay = $d("#day");
selDay.value = "2";                                  // 0-based → 第 3 天
selDay.dispatchEvent(new W.Event("change", { bubbles: true }));
await tq();
const day3 = $$d("#content .card .word").map(e => e.textContent.trim());
check("切到第 3 天后渲染 30 张卡", day3.length === 30 && $d("#day").value === "2",
      day3.length + " 张 / value=" + $d("#day").value);

const dqBtn = $d("#dayQuizBtn");
check("头部有「当天检测」按钮", !!dqBtn && /当天检测/.test(dqBtn.textContent),
      dqBtn ? dqBtn.textContent : "(缺 #dayQuizBtn)");

if (dqBtn){
  fireQ(dqBtn, "click");
  await tq();
  check("一键进入全屏答题页（不经过配置弹层）",
        $d("#qscreen").classList.contains("on") && !$d("#cfg").classList.contains("on"));
  check("当天 30 词全考，不是弹层默认的 20 题", txt("#qIdx") === "第 1 题 / 30", txt("#qIdx"));

  const k3 = [];
  for (let i = 0; i < 30; i++){
    k3.push(/看中文写英文/.test(txt("#qBody .qtag")) ? "spell" : "mean");
    fireQ($d("#qSkip"), "click");
    await tq();
    fireQ($d("#qNext"), "click");
    await tq();
  }
  check("当天检测也是混合题型（两种都出现）",
        k3.indexOf("spell") >= 0 && k3.indexOf("mean") >= 0, k3.join(","));
  check("30 题答完进入结果页", txt("#qIdx") === "检测完成", txt("#qIdx"));

  const want3 = day3.slice().sort().join("|");
  const got3 = $$d("#qBody .wrongrow .w").map(e => e.textContent.trim()).sort();
  check("错题集合 == 第 3 天那 30 词（没混进别的天）", got3.join("|") === want3,
        "拿到 " + got3.length + " 词");
  check("结果页标注范围：第 3 天（不是「今日」）", /范围：第 3 天/.test(txt("#qBody .lbl")),
        txt("#qBody .lbl"));

  await fq();
  check("当天 30 词全部进复习库", day3.every(w => rvNow().includes(w)), rvNow().length + " 词在库");

  fireQ($d("#rRetryAll"), "click");
  await tq();
  const backInQuiz = txt("#qIdx") === "第 1 题 / 30";
  check("「再测 30 题」仍是 30 题", backInQuiz, txt("#qIdx"));
  check("「再测 30 题」没把答题页踢回配置面板",
        backInQuiz && $d("#qscreen").classList.contains("on") && !$d("#cfg").classList.contains("on"),
        "qscreen=" + $d("#qscreen").classList.contains("on") + " cfg=" + $d("#cfg").classList.contains("on"));
  if (backInQuiz){
    for (let i = 0; i < 30; i++){
      fireQ($d("#qSkip"), "click");
      await tq();
      fireQ($d("#qNext"), "click");
      await tq();
    }
    const got3b = $$d("#qBody .wrongrow .w").map(e => e.textContent.trim()).sort();
    check("再测 30 题的词仍锁在第 3 天（poolOf 拿到了 cfg.day，没退化成全表随机抽）",
          got3b.join("|") === want3, "拿到 " + got3b.length + " 词");

    fireQ($d("#rClose"), "click");
    await tq();
    check("返回列表后答题页关闭", !$d("#qscreen").classList.contains("on"));
  }
}

/* ══════════════════════════════════════════════════════════════
   答题导航：上一题 / 下一题 / 重新答题（第 10 版）。
   另起实例，理由和下面决战那段一样——主实例跑到这里时状态太脏，
   而本段要断言的是「回退看到的还是不是原来那一题、原来那个结论」，
   得有一个干净的池子和一个已知的复习库。
   A 实例（空库 + 2 个已掌握词）：导航本身、放弃重答、错→对出库
   B 实例（词本来就在库里）：重答对不该把「本来就在库里」的词删掉
   ══════════════════════════════════════════════════════════════ */
console.log("\n== 答题导航 · 上一题 / 下一题 / 重新答题 ==");
const dna = boot({ mastered: ["crew", "abandon"] });
await new Promise(r => dna.window.addEventListener("load", r, { once: true }));
await tick();
const $na = s => dna.window.document.querySelector(s);
const fa = (el, type) => el.dispatchEvent(new dna.window.MouseEvent(type, { bubbles: true }));
const ta = s => ($na(s) ? $na(s).textContent.replace(/\s+/g, " ").trim() : "(缺 " + s + ")");
const tra = () => new Promise(r => setTimeout(r, 40));
const fra = () => new Promise(r => setTimeout(r, 300));
const rvA = () => JSON.parse(dna.window.localStorage.getItem("cet_vocab_review_v1") || "[]");
const openQuizA = async (scope, type) => {         // 走真实入口：检测 → 配置弹层 → 开始
  fa($na("#quizBtn"), "click"); await tra();
  fa($na(`#scopeSegs .seg[data-v="${scope}"]`), "click"); await tra();
  fa($na(`#typeSegs .seg[data-v="${type}"]`), "click"); await tra();
  fa($na("#qStart"), "click"); await tra();
};

await openQuizA("mastered", "mean");
check("2 词的池子出 2 题", ta("#qIdx") === "第 1 题 / 2", ta("#qIdx"));
check("第 1 题没有「上一题」", !$na("#qPrev"));

const w1 = ta("#qBody .qword");
$na("#qi").value = "乱写一串";                     // 故意答错 → 进库，addedByAnswer = true
fa($na("#qSubmit"), "click");
await tra();
check("第 1 题答错", !!$na("#qBody .fb.bad"), ta("#qBody .fb .sub"));
const ans1 = ta("#qBody .fb .ans");                // 攒下正确释义，重答时要写它
await fra();
check("答错 → 该词进复习库", rvA().indexOf(w1) >= 0, JSON.stringify(rvA()));
check("判错时判分页给「重新答题」", !!$na("#qRedo"));
check("第 1 题判分页仍没有「上一题」", !$na("#qPrev"));

fa($na("#qNext"), "click");
await tra();
check("「下一题」到第 2 题", ta("#qIdx") === "第 2 题 / 2", ta("#qIdx"));
check("第 2 题还没答过，显示的是答题页", !!$na("#qi") && !$na("#qBody .fb"));
check("第 2 题有「上一题」", !!$na("#qPrev"));
const w2 = ta("#qBody .qword");
check("两题是两个不同的词", w1 !== w2, w1 + " / " + w2);

/* 回退的关键断言：`quiz.i` 左边全是答过的题，所以退回去看到的是**判分页**，
   而不是一张空白答题页——这正是「结果页不用新增未作答档」的那个前提。 */
fa($na("#qPrev"), "click");
await tra();
check("「上一题」回到第 1 题", ta("#qIdx") === "第 1 题 / 2", ta("#qIdx"));
check("回退看到的是判分页，不是空白答题页", !!$na("#qBody .fb.bad") && !$na("#qi"));
check("回退后还是原来那个词", ta("#qBody .qword") === w1, ta("#qBody .qword"));
check("回退后仍记得你写过的答案", /乱写一串/.test(ta("#qBody .fb .sub")), ta("#qBody .fb .sub"));

fa($na("#qRedo"), "click");
await tra();
check("「重新答题」回到答题页，上一轮的反馈收起来了", !!$na("#qi") && !$na("#qBody .fb"));
check("重新答题时输入框是空的（不是上次那串）", $na("#qi").value === "", $na("#qi").value);
check("重新答题时题号不变", ta("#qIdx") === "第 1 题 / 2", ta("#qIdx"));
await fra();
check("重答途中不提交，复习库一点没动", rvA().indexOf(w1) >= 0, JSON.stringify(rvA()));

$na("#qi").value = ans1;
fa($na("#qSubmit"), "click");
await tra();
check("重答写对 → 判对", !!$na("#qBody .fb.ok"), ta("#qBody .fb .sub"));
check("答对时不再给「重新答题」", !$na("#qRedo"));
check("答对时也不给「我写对了」（本来就对）", !$na("#qAppeal"));
await fra();
check("错 → 对：上一次「顺手入库」的那条被撤销（出库）", rvA().indexOf(w1) < 0, JSON.stringify(rvA()));

fa($na("#qNext"), "click");
await tra();
check("再往前又到第 2 题，仍是一张没答过的答题页", ta("#qIdx") === "第 2 题 / 2" && !!$na("#qi"), ta("#qIdx"));
$na("#qi").value = "又乱写一串";
fa($na("#qSubmit"), "click");
await tra();
check("第 2 题也答错", !!$na("#qBody .fb.bad"), ta("#qBody .fb .sub"));
const ans2 = ta("#qBody .fb .ans");
await fra();

/* 窄屏排布：判分页这一屏是按钮最多的一种（上一题 / 我写对了 / 重新答题 / 下一题 四个）。
   jsdom 没有排版引擎，量不到真实像素，所以这里钉的是那条**结构保证**——
   `.fb` 是 flex-wrap:wrap、按钮是 white-space:nowrap，所以窄屏只会折行，不会横向溢出。
   真实观感（要不要把按钮改小、挪到卡片外面）得在浏览器里看，测试给不了。 */
{
  const row = dna.window.getComputedStyle($na("#qBody .fb"));
  const btn = dna.window.getComputedStyle($na("#qRedo"));
  check("判分页 4 个按钮：按钮组可折行 + 按钮不换行（窄屏不横向溢出）",
        row.flexWrap === "wrap" && btn.whiteSpace === "nowrap",
        row.flexWrap + " / " + btn.whiteSpace);
  check("判分页这一屏确实是 4 个按钮（上一条断言量的就是最坏情况）",
        ["#qPrev", "#qAppeal", "#qRedo", "#qNext"].every(s => !!$na(s)),
        ["#qPrev", "#qAppeal", "#qRedo", "#qNext"].filter(s => !!$na(s)).join(","));
}

/* 重答途中点「上一题」= 放弃重答：本题的旧结论原样留着，不能被清成空白题
   （这是 `quiz.redo` 做成「视图模式」而不是「清 verdict」换来的性质）。 */
fa($na("#qRedo"), "click");
await tra();
check("第 2 题进入重答", !!$na("#qi") && !$na("#qBody .fb"));
fa($na("#qPrev"), "click");
await tra();
check("重答途中「上一题」= 放弃重答，回到第 1 题的判分页",
      ta("#qIdx") === "第 1 题 / 2" && !!$na("#qBody .fb.ok"), ta("#qIdx") + " / " + ta("#qBody .fb"));
fa($na("#qNext"), "click");
await tra();
check("放弃重答后第 2 题的旧结论还在（没被清成空白题）",
      ta("#qIdx") === "第 2 题 / 2" && !!$na("#qBody .fb.bad") && !$na("#qi"),
      ta("#qIdx") + " / " + ta("#qBody .fb"));

fa($na("#qRedo"), "click");
await tra();
$na("#qi").value = ans2;
fa($na("#qSubmit"), "click");
await tra();
check("第 2 题重答写对 → 判对", !!$na("#qBody .fb.ok"), ta("#qBody .fb .sub"));
await fra();
check("两个词都出了库", rvA().length === 0, JSON.stringify(rvA()));
fa($na("#qNext"), "click");
await tra();
check("最后一题答完走到结果页", ta("#qIdx") === "检测完成", ta("#qIdx"));
check("结果页 2 / 2", /^2 \/ 2$/.test(ta("#qBody .big")), ta("#qBody .big"));
check("结果页「没有错题」和空复习库对得上（两处不打架）",
      /0 词/.test(ta("#qBody .res-bk .cnt")) && rvA().length === 0,
      ta("#qBody .res-bk .cnt") + " / 库 " + rvA().length);

console.log("\n== 答题导航 · 重答不误删「本来就在库里」的词 ==");
const dnb = boot({ mastered: ["crew"], review: ["crew"] });
await new Promise(r => dnb.window.addEventListener("load", r, { once: true }));
await tick();
const $nb = s => dnb.window.document.querySelector(s);
const fbb = (el, type) => el.dispatchEvent(new dnb.window.MouseEvent(type, { bubbles: true }));
const tbB = s => ($nb(s) ? $nb(s).textContent.replace(/\s+/g, " ").trim() : "(缺 " + s + ")");
const trB = () => new Promise(r => setTimeout(r, 40));
const frb = () => new Promise(r => setTimeout(r, 300));
const rvB = () => JSON.parse(dnb.window.localStorage.getItem("cet_vocab_review_v1") || "[]");
const openQuizB = async (type) => {
  fbb($nb("#quizBtn"), "click"); await trB();
  fbb($nb('#scopeSegs .seg[data-v="mastered"]'), "click"); await trB();
  fbb($nb(`#typeSegs .seg[data-v="${type}"]`), "click"); await trB();
  fbb($nb("#qStart"), "click"); await trB();
};

await openQuizB("mean");
check("抽到库里的那个词", tbB("#qBody .qword") === "crew", tbB("#qBody .qword"));
$nb("#qi").value = "电脑";                          // 故意答错
fbb($nb("#qSubmit"), "click");
await trB();
const ansB = tbB("#qBody .fb .ans");
await frb();
check("本来就在库里的词，答错后仍在库", rvB().indexOf("crew") >= 0, JSON.stringify(rvB()));
fbb($nb("#qRedo"), "click");
await trB();
$nb("#qi").value = ansB;
fbb($nb("#qSubmit"), "click");
await trB();
check("重答写对 → 判对", !!$nb("#qBody .fb.ok"), tbB("#qBody .fb .sub"));
await frb();
check("重答对也不动「本来就在库里」的词（出库只撤销 addedByAnswer 那一条）",
      rvB().indexOf("crew") >= 0, JSON.stringify(rvB()));

/* 拼写题的对比：第 8 版拿掉了它的申诉入口，但「重新答题」是另一件事——
   它撤销的是「我刚敲错了」，不是「程序判错了」，所以拼写题也该有。 */
fbb($nb("#qNext"), "click");
await trB();
fbb($nb("#rClose"), "click");
await trB();
await openQuizB("spell");
check("拼写题：题干是中文", /看中文写英文/.test(tbB("#qBody .qtag")), tbB("#qBody .qtag"));
$nb("#qi").value = "crcket";
fbb($nb("#qSubmit"), "click");
await trB();
check("拼写题答错不给「我写对了」（第 8 版起）", !$nb("#qAppeal"));
check("拼写题答错照样给「重新答题」", !!$nb("#qRedo"));

/* ══════════════════════════════════════════════════════════════
   决战复习库 · 判分记忆那条路 + **双向齐当场出库**（第 11 版）。
   决战的出题是**随机抽词 + 随机方向**，想测某个具体走向必须把两头都钉死：
   · 库压成已知的一个词（不然抽不中想测的那个）
   · `battle` 种子预置「这个词已经过了哪个方向」→ dirForWord() 必然出另一个方向。
     这是本版新增的存储键，也是让这段从「撞运气」变成确定性的关键
     （旧版这里得先猜题型、撞到拼写就先答对再逼出认义，见 git 里的旧版本）。
   预置的记忆是「人员」——义项「全体人员」的后半截，不记忆的话 meanGrade 只给部分匹配。
   ══════════════════════════════════════════════════════════════ */
console.log("\n== 决战 · 认义方向 + 双向齐当场出库（第 11 版） ==");
const db = boot({ review: ["crew"], mastered: ["crew"], appeals: { crew: ["人员"] },
                  battle: { crew: ["spell"] } });
await new Promise(r => db.window.addEventListener("load", r, { once: true }));
await tick();
const $b = s => db.window.document.querySelector(s);
const fb = (el, type) => el.dispatchEvent(new db.window.MouseEvent(type, { bubbles: true }));
const tb = s => ($b(s) ? $b(s).textContent.replace(/\s+/g, " ").trim() : "(缺 " + s + ")");
const trb = () => new Promise(r => setTimeout(r, 40));
const lsB = k => JSON.parse(db.window.localStorage.getItem(k) || "null");

fb($b("#revBtn"), "click");
await trb();
check("决战的默认数量跟着库里的词数走", $b("#battleNum").value === "1", $b("#battleNum").value);
check("面板上写明「一场里每个词只考一个方向」",
      /一场里每个词只考一个方向/.test(tb("#battleGrp label")), tb("#battleGrp label"));
fb($b("#battleStart"), "click");
await trb();
check("进入决战答题页", /决战复习库/.test(tb("#qIdx")), tb("#qIdx"));
check("决战不显示「复习库」管理面板了", !$b("#rev").classList.contains("on"));
check("已过拼写 → 这场必考另一个方向（认义）", /看英文写中文/.test(tb("#qBody .qtag")), tb("#qBody .qtag"));
check("第 1 题不给「上一题」", !$b("#qPrev"));
check("还没判分，不给「重新答题」", !$b("#qRedo"));
$b("#qi").value = "人员";                          // 不记忆的话这串只算部分匹配 → 判错
fb($b("#qSubmit"), "click");
await trb();
check("决战里同样按记忆判对", !!$b("#qBody .fb.ok"), tb("#qBody .fb .sub"));
check("决战的反馈也点明是按记忆判的", /按你之前确认过的答案判对/.test(tb("#qBody .fb .sub")), tb("#qBody .fb .sub"));
check("决战里按记忆判对时不给「我写对了」", !$b("#qAppeal"));
check("决战里也有「取消这条记忆」", !!$b("#qForget"));
/* 文字链必须压过 .fb button（0,1,1）的盒子样式，否则会变成一个 34px 高、带边框的方块，
   混在「下一词」旁边看不出是附注。同类覆盖问题在 .btn.danger 上出过一次（坑 #15）。 */
{
  const cf = db.window.getComputedStyle($b("#qForget"));
  const cn = db.window.getComputedStyle($b("#qNext"));
  check("「取消这条记忆」是文字链，没被 .fb button 还原成方块按钮",
        cf.height === "auto" && cf.borderTopWidth === "0px" && cn.height === "34px",
        "forget=" + cf.height + "/" + cf.borderTopWidth + " next=" + cn.height);
}
check("双向齐 → 反馈当场点明已移出复习库",
      /两个方向均已通过，已移出复习库/.test(tb("#qBody .fb .sub")), tb("#qBody .fb .sub"));
check("答对且双向齐 → 不再说「还差另一个方向」",
      !/还差另一个方向/.test(tb("#qBody .fb .sub")), tb("#qBody .fb .sub"));
check("最后一道题的按钮是「查看结果」", /查看结果/.test(tb("#qNext")), tb("#qNext"));
check("进度条按「已出库词数」走，不按答对题数", /已出库 1 \/ 1 词/.test(tb("#qIdx")), tb("#qIdx"));
await new Promise(r => setTimeout(r, 300));
check("双向齐 → 当场从复习库落盘里移出",
      (lsB("cet_vocab_review_v1") || []).indexOf("crew") < 0, JSON.stringify(lsB("cet_vocab_review_v1")));
check("双向齐 → 战场记录整条清掉（不留「都过了却还挂着半个方向」的空档）",
      JSON.stringify(lsB("cet_vocab_battle_v1")) === "{}", JSON.stringify(lsB("cet_vocab_battle_v1")));

fb($b("#qForget"), "click");
await trb();
check("决战里取消记忆后反馈改口", /这条记忆已取消/.test(tb("#qBody .fb .sub")), tb("#qBody .fb .sub"));
check("取消后入口自己收起来", !$b("#qForget"));
check("取消记忆不回退判分：本题仍是答对", !!$b("#qBody .fb.ok"));
await new Promise(r => setTimeout(r, 300));
check("决战里取消的记忆也真的从落盘里没了",
      JSON.stringify(lsB("cet_vocab_appeals_v1")) === "{}", JSON.stringify(lsB("cet_vocab_appeals_v1")));

fb($b("#qNext"), "click");
await trb();
check("走完题列进结算页", /决战完成/.test(tb("#qIdx")), tb("#qIdx"));
check("结算页报出库词数", /本场 1 词，出库 1 个/.test(tb("#qBody .res-score .lbl")), tb("#qBody .res-score .lbl"));
check("出库的词不计入「只过一个方向」",
      !/只过一个方向/.test(tb("#qBody .res-score .lbl")), tb("#qBody .res-score .lbl"));
check("结算页的复习库剩余跟着清空", /复习库剩余 0 词/.test(tb("#qBody .split")), tb("#qBody .split"));
check("库空了 → 不给「继续决战」", !$b("#bAgain"));
check("库空了 → 仍给「返回列表」", !!$b("#rClose"));
fb($b("#rClose"), "click");
await trb();
check("返回列表 → 答题页收起", !$b("#qscreen").classList.contains("on"));
check("决战认义这条路没有 JS 运行时错误", db.__errs.length === 0, db.__errs.join(" | "));

/* ══════════════════════════════════════════════════════════════
   决战 · 一场只考一个方向，两个方向**跨场**累计（第 11 版的核心规则）。
   这条规则不靠种子也测得死：第一场考哪个方向确实是随机的，但「第一场过了哪个方向，
   第二场就必须考另一个」是确定的——按 qtag 反推该填什么，两种走向都能自证。
   种子里 battle 为空，走的正是 dirForWord() 的随机分支。
   ══════════════════════════════════════════════════════════════ */
console.log("\n== 决战 · 两个方向跨场累计（第 11 版） ==");
const dk = boot({ review: ["crew"], mastered: ["crew"] });
await new Promise(r => dk.window.addEventListener("load", r, { once: true }));
await tick();
const $k = s => dk.window.document.querySelector(s);
const tk = s => ($k(s) ? $k(s).textContent.replace(/\s+/g, " ").trim() : "(缺 " + s + ")");
const fk = (el, type) => el.dispatchEvent(new dk.window.MouseEvent(type, { bubbles: true }));
const trk = () => new Promise(r => setTimeout(r, 40));
const lsK = k => JSON.parse(dk.window.localStorage.getItem(k) || "null");
/* 库里只有 crew 一个词，按题型反推该填什么：「全体人员」是义项原文，精确命中 */
const ansFor = tag => (/看中文写英文/.test(tag) ? "crew" : "全体人员");

fk($k("#revBtn"), "click");
await trk();
fk($k("#battleStart"), "click");
await trk();
const tag1 = tk("#qBody .qtag");
const dir1 = /看中文写英文/.test(tag1) ? "spell" : "mean";
check("第 1 场的方向是拼写或认义之一", /看中文写英文|看英文写中文/.test(tag1), tag1);
$k("#qi").value = ansFor(tag1);
fk($k("#qSubmit"), "click");
await trk();
check("第 1 场答对 → 只记下一个方向，词还没出库", !!$k("#qBody .fb.ok"), tk("#qBody .fb .sub"));
check("反馈点明还差另一个方向、下一场必考它",
      /这个词还差另一个方向，下一场决战必考它/.test(tk("#qBody .fb .sub")), tk("#qBody .fb .sub"));
check("进度条没动（只过一个方向不算出库）", /已出库 0 \/ 1 词/.test(tk("#qIdx")), tk("#qIdx"));
await new Promise(r => setTimeout(r, 300));
check("第 1 场过后：词仍在复习库",
      (lsK("cet_vocab_review_v1") || []).indexOf("crew") >= 0, JSON.stringify(lsK("cet_vocab_review_v1")));
check("第 1 场过后：只记下过的那个方向",
      JSON.stringify(lsK("cet_vocab_battle_v1")) === JSON.stringify({ crew: [dir1] }),
      JSON.stringify(lsK("cet_vocab_battle_v1")));
fk($k("#qNext"), "click");
await trk();
check("结算页：本场 1 词、出库 0 个", /本场 1 词，出库 0 个/.test(tk("#qBody .res-score .lbl")), tk("#qBody .res-score .lbl"));
check("结算页把「只过一个方向」单列出来",
      /只过一个方向 1 个/.test(tk("#qBody .res-score .lbl")), tk("#qBody .res-score .lbl"));
check("结算页：本场未通过 0 词", /本场未通过 0 词/.test(tk("#qBody .split")), tk("#qBody .split"));
check("词还在库 → 给「继续决战」并提示剩余 1 词", /继续决战剩余 1 词/.test(tk("#bAgain")), tk("#bAgain"));
fk($k("#bAgain"), "click");
await trk();
const tag2 = tk("#qBody .qtag");
check("第 2 场必考另一个方向（上一场过了的那个不再考）",
      dir1 === "spell" ? /看英文写中文/.test(tag2) : /看中文写英文/.test(tag2), tag1 + "  →  " + tag2);
$k("#qi").value = ansFor(tag2);
fk($k("#qSubmit"), "click");
await trk();
check("两个方向都过 → 当场出库",
      /两个方向均已通过，已移出复习库/.test(tk("#qBody .fb .sub")), tk("#qBody .fb .sub"));
check("出库当场反映到进度条", /已出库 1 \/ 1 词/.test(tk("#qIdx")), tk("#qIdx"));
await new Promise(r => setTimeout(r, 300));
check("中途退出（不进结算页）也保住出库结果",
      (lsK("cet_vocab_review_v1") || []).indexOf("crew") < 0, JSON.stringify(lsK("cet_vocab_review_v1")));
check("中途退出后战场记录也清干净",
      JSON.stringify(lsK("cet_vocab_battle_v1")) === "{}", JSON.stringify(lsK("cet_vocab_battle_v1")));
fk($k("#qExit"), "click");
await trk();
check("中途退出 → 答题页收起", !$k("#qscreen").classList.contains("on"));
check("决战跨场累计这条路没有 JS 运行时错误", dk.__errs.length === 0, dk.__errs.join(" | "));

/* ══════════════════════════════════════════════════════════════
   决战 · **拼写方向不认判分记忆**（第 8 版）+ **答错不记方向**（第 11 版）。
   上面那段的预置记忆是认义答案（「人员」），只能走 mean 分支。
   这段反过来：预置一条**拼写形**的记忆——老版本里用户申诉拼写留下的那种纯拉丁串——
   钉住决战里的拼写方向根本不查这张表。这是「存量记忆不清理、但也不再生效」的凭据：
   改版前它会让这里判对，改版后必须判错，而盘里那条记录原样留着。
   种子 `battle:{crew:["mean"]}` 把这一场钉成拼写题（认义已过 → 必考另一个方向）。
   ══════════════════════════════════════════════════════════════ */
console.log("\n== 决战 · 拼写方向不认判分记忆 + 答错不记方向（第 8/11 版） ==");
const dbs = boot({ review: ["crew"], mastered: ["crew"], appeals: { crew: ["crcut"] },
                   battle: { crew: ["mean"] } });
await new Promise(r => dbs.window.addEventListener("load", r, { once: true }));
await tick();
const $s2 = s => dbs.window.document.querySelector(s);
const t2 = s => ($s2(s) ? $s2(s).textContent.replace(/\s+/g, " ").trim() : "(缺 " + s + ")");
const fs2 = (el, type) => el.dispatchEvent(new dbs.window.MouseEvent(type, { bubbles: true }));
const ts2 = () => new Promise(r => setTimeout(r, 40));
const ts2f = () => new Promise(r => setTimeout(r, 300));
const ls2 = k => JSON.parse(dbs.window.localStorage.getItem(k) || "null");

fs2($s2("#revBtn"), "click");
await ts2();
fs2($s2("#battleStart"), "click");
await ts2();
check("认义已过 → 这场必考拼写（同一个词不会两场都考同一方向）",
      /看中文写英文/.test(t2("#qBody .qtag")), t2("#qBody .qtag"));
$s2("#qi").value = "crcut";                        // 预置的存量拼写记忆，逐字相同
fs2($s2("#qSubmit"), "click");
await ts2();
check("决战拼写方向不按记忆判对（存量拼写记忆已失效）", !!$s2("#qBody .fb.bad"), t2("#qBody .fb .sub"));
check("决战拼写方向判错时不给申诉入口", !$s2("#qAppeal"));
check("决战拼写方向也没有「取消这条记忆」", !$s2("#qForget"));
check("拼写判错给「重新答题」（撤的是「我刚敲错了」，不是「程序判错了」）", !!$s2("#qRedo"));
check("答错的反馈说明词仍在复习库、重考要等下一场",
      /这个词仍在复习库，重考要等下一场/.test(t2("#qBody .fb .sub")), t2("#qBody .fb .sub"));
check("答错不冒「还差另一个方向」那句（只有答对才谈方向）",
      !/还差另一个方向/.test(t2("#qBody .fb .sub")), t2("#qBody .fb .sub"));
await ts2f();
check("预置的存量记忆原样留着（不清理，只是不再生效）",
      JSON.stringify(ls2("cet_vocab_appeals_v1")) === '{"crew":["crcut"]}',
      dbs.window.localStorage.getItem("cet_vocab_appeals_v1"));
check("答错不记方向：战场记录仍是种子里的原样",
      JSON.stringify(ls2("cet_vocab_battle_v1")) === '{"crew":["mean"]}',
      dbs.window.localStorage.getItem("cet_vocab_battle_v1"));
check("答错不出库：词仍在复习库",
      (ls2("cet_vocab_review_v1") || []).indexOf("crew") >= 0,
      dbs.window.localStorage.getItem("cet_vocab_review_v1"));
fs2($s2("#qExit"), "click");
await ts2();
check("决战拼写这条路没有 JS 运行时错误", dbs.__errs.length === 0, dbs.__errs.join(" | "));

/* ══════════════════════════════════════════════════════════════
   决战 · 题列导航 + 「一场里每个词只出现一次」（第 11 版）。
   三个词全部预置「只过拼写」→ 这一场三道题**全是认义题**，词头直接印在题干里
   （.qword），于是「一个词一场只考一次」这条能被直接量出来——旧版同一个词会出两次，
   先拼写后认义。答案按 .qword 查表填，抽题顺序被打乱也不影响。
   ══════════════════════════════════════════════════════════════ */
console.log("\n== 决战 · 题列导航 + 一场一词（第 11 版） ==");
const dn = boot({ review: ["crew", "abandon", "zoom"], mastered: ["crew", "abandon", "zoom"],
                  battle: { crew: ["spell"], abandon: ["spell"], zoom: ["spell"] } });
await new Promise(r => dn.window.addEventListener("load", r, { once: true }));
await tick();
const $n = s => dn.window.document.querySelector(s);
const tn = s => ($n(s) ? $n(s).textContent.replace(/\s+/g, " ").trim() : "(缺 " + s + ")");
const fn = (el, type) => el.dispatchEvent(new dn.window.MouseEvent(type, { bubbles: true }));
const tnw = () => new Promise(r => setTimeout(r, 40));
const tnf = () => new Promise(r => setTimeout(r, 300));
const lsN = k => JSON.parse(dn.window.localStorage.getItem(k) || "null");
const CN3 = { crew: "全体人员", abandon: "放弃", zoom: "急速上升" };   // 义项原文，精确命中
const wordNow = () => (($n("#qBody .qword") || {}).textContent || "").trim();
const dirsOf = w => ((lsN("cet_vocab_battle_v1") || {})[w] || []).slice().sort().join(",");

fn($n("#revBtn"), "click");
await tnw();
check("三个词的库 → 数量默认填满 3", $n("#battleNum").value === "3", $n("#battleNum").value);
fn($n("#battleStart"), "click");
await tnw();
check("三个词都只过拼写 → 这一场三道题全是认义题",
      /看英文写中文/.test(tn("#qBody .qtag")), tn("#qBody .qtag"));
const bw1 = wordNow();
check("第 1 题认义题把英文词头印在题干里", !!CN3[bw1], JSON.stringify(bw1));
check("第 1 题不给「上一题」", !$n("#qPrev"));
check("还没判分，不给「重新答题」", !$n("#qRedo"));

$n("#qi").value = "zzz";                            // 必错
fn($n("#qSubmit"), "click");
await tnw();
check("判错 → 给出「重新答题」", !!$n("#qRedo"));
check("认义题判错 → 也给出「我写对了」", !!$n("#qAppeal"));
check("判错后按钮是「下一词」（不是最后一道）", /下一词/.test(tn("#qNext")), tn("#qNext"));
check("判错不记方向：这个词的方向记录还是种子里那一个",
      dirsOf(bw1) === "spell", JSON.stringify(lsN("cet_vocab_battle_v1")));

fn($n("#qRedo"), "click");
await tnw();
check("重新答题 → 回到答题页（有输入框）", !!$n("#qi"));
check("重新答题后「重新答题」按钮收起", !$n("#qRedo"));
check("重新答题后「我写对了」也收起", !$n("#qAppeal"));
check("重新答题不显示旧结论（答题页没有判分块）", !$n("#qBody .fb"));

$n("#qi").value = CN3[bw1];                          // 这一轮填对
fn($n("#qSubmit"), "click");
await tnw();
check("重答改对 → 按新结论判对", !!$n("#qBody .fb.ok"), tn("#qBody .fb .sub"));
check("重答改对 → 两个方向齐，当场出库",
      /两个方向均已通过，已移出复习库/.test(tn("#qBody .fb .sub")), tn("#qBody .fb .sub"));
await tnf();
check("重答改对 → 落盘：这个词出库",
      (lsN("cet_vocab_review_v1") || []).indexOf(bw1) < 0, JSON.stringify(lsN("cet_vocab_review_v1")));
check("重答改对 → 落盘：方向记录整条清掉（出库了就不用再记）",
      (lsN("cet_vocab_battle_v1") || {})[bw1] === undefined, JSON.stringify(lsN("cet_vocab_battle_v1")));

fn($n("#qNext"), "click");
await tnw();
check("第 2 题：进度条已反映第 1 题出库", /已出库 1 \/ 3 词/.test(tn("#qIdx")), tn("#qIdx"));
const bw2 = wordNow();
check("第 2 题换了个词（一场里每个词只出现一次）", !!bw2 && bw2 !== bw1, bw1 + " → " + bw2);

fn($n("#qPrev"), "click");
await tnw();
check("上一题 → 回到第 1 题的判分页（不是空白题）", !!$n("#qBody .fb.ok"), tn("#qBody .fb .sub"));
check("上一题回看时没有输入框", !$n("#qi"));
check("第 1 题上不给「上一题」（回看也不给）", !$n("#qPrev"));
fn($n("#qNext"), "click");
await tnw();
check("从判分页往前翻 → 撞上没答过的题就显示答题页", !!$n("#qi"));
check("翻回来还是第 2 题那个词", wordNow() === bw2, bw2 + " → " + wordNow());

$n("#qi").value = "zzz";                            // 第 2 题答错
fn($n("#qSubmit"), "click");
await tnw();
fn($n("#qNext"), "click");
await tnw();
const bw3 = wordNow();
check("三道题三个词，互不重复", !!bw3 && bw3 !== bw1 && bw3 !== bw2, [bw1, bw2, bw3].join(" / "));
$n("#qi").value = "zzz";                            // 第 3 题也答错（不答就推不到结算页）
fn($n("#qSubmit"), "click");
await tnw();
check("最后一道题的按钮是「查看结果」", /查看结果/.test(tn("#qNext")), tn("#qNext"));
fn($n("#qNext"), "click");
await tnw();
check("结算页：本场 3 词、出库 1 个",
      /本场 3 词，出库 1 个/.test(tn("#qBody .res-score .lbl")), tn("#qBody .res-score .lbl"));
check("结算页：本场未通过 2 词", /本场未通过 2 词/.test(tn("#qBody .split")), tn("#qBody .split"));
check("结算页：复习库剩余 2 词", /复习库剩余 2 词/.test(tn("#qBody .split")), tn("#qBody .split"));
check("还有词 → 给「继续决战剩余 2 词」", /继续决战剩余 2 词/.test(tn("#bAgain")), tn("#bAgain"));
check("决战题列导航这条路没有 JS 运行时错误", dn.__errs.length === 0, dn.__errs.join(" | "));

/* ══════════════════════════════════════════════════════════════
   复习库管理面板。另起一个实例把库压成已知的三词，且故意打乱写入顺序：
   abandon(第 1 天第 1 词) / crew(中段) / zoom(全表最后一个词)——
   列表若按「加入顺序」渲染（zoom|abandon|crew）就会露馅。
   ══════════════════════════════════════════════════════════════ */
console.log("\n== 复习库管理面板 ==");
const rp = boot({ review: ["zoom", "abandon", "crew"], mastered: ["crew"] });
await new Promise(r => rp.window.addEventListener("load", r, { once: true }));
await new Promise(r => setTimeout(r, 80));

const R = rp.window, RD = R.document;
const $r = s => RD.querySelector(s);
const $$r = s => [...RD.querySelectorAll(s)];
const tr = s => ($r(s) ? $r(s).textContent.replace(/\s+/g, " ").trim() : "(缺 " + s + ")");
const rvR = () => JSON.parse(R.localStorage.getItem("cet_vocab_review_v1") || "[]");
const fr = (el, type) => el.dispatchEvent(new R.MouseEvent(type, { bubbles: true }));
const trq = () => new Promise(r => setTimeout(r, 40));
const frq = () => new Promise(r => setTimeout(r, 300));   // saveReview() 也是 220ms 防抖
const rowWords = () => $$r("#revList .revrow .w").map(e => e.textContent.trim().toLowerCase());

const revBtn = $r("#revBtn");
check("头部有「复习库」按钮", !!revBtn && /复习库/.test(revBtn.textContent),
      revBtn ? revBtn.textContent : "(缺 #revBtn)");
check("按钮上不带词数（固定头部里宽度才不会随库大小抖动）",
      !!revBtn && !/\d/.test(revBtn.textContent), revBtn ? revBtn.textContent : "");

fr(revBtn, "click");
await trq();
check("点「复习库」打开管理面板", $r("#rev").classList.contains("on"));
check("面板与遮罩一起出现", $r("#mask").classList.contains("on"));
check("面板标题带当前词数", /复习库 · 3 词/.test(tr("#rev h3")), tr("#rev h3"));

const rowsR = $$r("#revList .revrow");
check("列表行数 == 库里词数", rowsR.length === 3, rowsR.length + " 行");
check("列表按全表原序排（abandon→crew→zoom），不是加入顺序",
      rowWords().join("|") === "abandon|crew|zoom", rowWords().join("|"));
check("每行都有 音标 / 释义 / 第 N 天 / ✕",
      rowsR.length === 3 && rowsR.every(x => x.querySelector(".ipa") && x.querySelector(".cn2") &&
                                             x.querySelector(".d") && x.querySelector(".x")));
check("行标注该词所在的天", /^第 1 天$/.test(rowsR[0].querySelector(".d").textContent.trim()),
      rowsR[0].querySelector(".d").textContent.trim());
check("面板里没有「测复习库」按钮（按需求排除）",
      !$$r("#rev button").some(b => /检测|测复习/.test(b.textContent)),
      $$r("#rev button").map(b => b.textContent.trim()).join(" / "));

const crewRow = rowsR[1];
const crewDay = +/第 (\d+) 天/.exec(crewRow.querySelector(".d").textContent)[1];
fr(crewRow, "click");
await trq();
check("点行 → 关闭面板并收掉遮罩",
      !$r("#rev").classList.contains("on") && !$r("#mask").classList.contains("on"));
check("点行 → 跳到该词所在的那一天", $r("#day").value === String(crewDay - 1),
      "期望 " + (crewDay - 1) + "，实得 " + $r("#day").value);
check("跳过去后那个词就在当页卡片里",
      $$r("#content .card .word").some(e => e.textContent.trim().toLowerCase() === "crew"));

fr(revBtn, "click");
await trq();
fr($$r("#revList .revrow .x")[0], "click");       // 移除 abandon
await trq(); await frq();
check("点 ✕ → 该词出库", rvR().indexOf("abandon") < 0 && rvR().length === 2, rvR().join(","));
check("点 ✕ 后面板不关（方便连着删几个）", $r("#rev").classList.contains("on"));
check("点 ✕ 后列表立刻少一行", rowWords().join("|") === "crew|zoom", rowWords().join("|"));
check("点 ✕ 后标题词数同步", /复习库 · 2 词/.test(tr("#rev h3")), tr("#rev h3"));
check("点 ✕ 后顶栏计数同步", /复习库 2 词/.test(tr("#reviewCnt")), tr("#reviewCnt"));

const clr = $r("#revClear");
fr(clr, "click");
await trq();
check("清空是两段式：第一次点只进入待确认", /再点一次/.test(clr.textContent) && clr.classList.contains("armed"),
      clr.textContent.trim());
await frq();                       // 等过 220ms 防抖窗口，才读得到真实的库内容
check("待确认态下复习库数据一个没少", rvR().length === 2, rvR().join(","));
fr(clr, "click");
await trq(); await frq();
check("第二次点 → 复习库清空", rvR().length === 0, rvR().join(","));
check("清空后显示空状态", /复习库是空的/.test(tr("#revList")), tr("#revList"));
check("清空后「清空复习库」按钮禁用", clr.disabled === true);
check("清空后按钮文案复位", clr.textContent.trim() === "清空复习库", clr.textContent.trim());
check("清空后顶栏计数归零", /复习库 0 词/.test(tr("#reviewCnt")), tr("#reviewCnt"));

fr(revBtn, "click");
await trq();
RD.dispatchEvent(new R.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
await trq();
check("Escape 关闭面板并收掉遮罩",
      !$r("#rev").classList.contains("on") && !$r("#mask").classList.contains("on"));

fr(revBtn, "click");
await trq();
fr($r("#mask"), "click");
await trq();
check("点遮罩关闭面板", !$r("#rev").classList.contains("on"));

const st = $r("#content .card .star");
const stw = st.closest(".card").querySelector(".word").textContent.trim().toLowerCase();
fr(st, "click");
await trq(); await frq();
fr(revBtn, "click");
await trq();
check("卡片 ★ 入库后，面板里立刻能看到这个词", rowWords().includes(stw),
      stw + " / 列表=" + rowWords().join(","));
check("复习库面板无 JS 运行时错误", rp.__errs.length === 0, rp.__errs.slice(0, 3).join(" | "));

console.log("\n== 判分规则（§6.2 / §6.3）==");
check("afterward(s) 接受 afterward", W.spellOK("afterward(s)", "afterward") === true);
check("afterward(s) 接受 afterwards", W.spellOK("afterward(s)", "afterwards") === true);
check("authorize/-ise 接受 authorize", W.spellOK("authorize/-ise", "authorize") === true);
check("authorize/-ise 接受 authorise", W.spellOK("authorize/-ise", "authorise") === true);
check("celsius/-cius 接受 celcius", W.spellOK("celsius/-cius", "celcius") === true);
check("airplane/aeroplane 接受 aeroplane", W.spellOK("airplane/aeroplane", "aeroplane") === true);
check("拼写题大小写与标点不敏感", W.spellOK("crew", "  Crew. ") === true);
check("拼写题不把派生词算对", W.spellOK("create", "creation") === false);
check("拼写题错拼判错", W.spellOK("cricket", "crcket") === false);
/* 拼写变体表（第 8 版新加）。spellAnswers() 只从词头记法展开，而词头记的是英式拼法，
   记法没编码到的合法变体就落在答案集外面（analogue 不认 analog、vigor 不认 vigour）。
   第 7 版靠用户逐次点「我写对了」盖过去；第 8 版拿掉申诉后改由 build_data.py 的
   SPELL_VARIANTS 点名补，所以这两条是判分正确性的一环，不是锦上添花。
   反例用「英美互转规则生成的假词」钉住：four -> for 是实测里最典型的一个，
   防的是有人图省事把规则放开成通用英美互转（那会一次性放进 32 个假词，真词只有 3 个）。 */
check("analogue 认美式拼法 analog（变体表）", W.spellOK("analogue", "analog") === true);
check("vigor 认英式拼法 vigour（变体表）", W.spellOK("vigor", "vigour") === true);
check("变体表没顺带放宽规则：four 不认真假词 for", W.spellOK("four", "for") === false);
/* 源文档错拼的两条回归 pin（第 7 版修）。改 build_data.py 的 TYPO 时先看这两条：
   jail 的英式拼法是 gaol 不是 goal，而 goal「目标」在词表里另有独立词条 */
check("jail 认 gaol（英式拼法）", W.spellOK("jail/gaol", "gaol") === true);
check("jail 不认 goal（那是另一个词）", W.spellOK("jail/gaol", "goal") === false);
check("kilometer 认英式拼法 kilometre", W.spellOK("kilometer/-tre", "kilometre") === true);
check("kilometer 不认版面噪声拼出来的串", W.spellOK("kilometer/-tre", "kitrekin") === false);
check("认义题写任一义项算对", W.meanOK("n. 全体人员, 一群人, 全体队员", "一群人") === true);
check("认义题多个义项逗号隔开也算对", W.meanOK("n. 全体人员, 一群人, 全体队员", "全体人员，队员不完整") === true);
check("认义题去词性前缀与括号", W.meanOK("n. 苹果（水果）, 梨", "苹果") === true);
check("认义题完全不相干判错", W.meanOK("n. 全体人员, 一群人", "电脑") === false);
check("部分匹配（共享 ≥2 连续汉字）判错但带提示", (() => {
  const g = W.meanGrade("n. 全体人员, 一群人", "人员");
  return g.ok === false && !!g.partial && g.partial.item === "全体人员";
})());
check("只共享 1 个字不算部分匹配（阈值 ≥2）", (() => {
  const g = W.meanGrade("n. 爬, 徐行, 蠕动", "爬行");
  return g.ok === false && !g.partial;
})());
/* 义项切分版（2026-10-08）的回归 pin。旧版 meanItems 只剥开头一个词性前缀，中间的
   a./vt. 全粘在义项里——「n. 破产者 a. 破产的」整段粘成一个义项，normCn 后带着字母 a，
   用户写「破产者，破产的」永远精确匹配失败（五张 bug 截图全是这一个根因）。
   新版把词性标记当义项分界：剥掉时补「，」再切分，连写 vt.vi. 一并吃掉。
   这组 pin 用的全是真实词表的释义原文，别换成精简示例——数据形态本身就是 pin 的一部分。 */
check("认义题中间的词性标记也剥掉（bankrupt 案例）", W.meanOK("n. 破产者 a. 破产的", "破产者，破产的") === true);
check("认义题只写词性后面的那个义项也算对", W.meanOK("n. 破产者 a. 破产的", "破产的") === true);
check("认义题照抄屏幕释义（不带词性）判对", W.meanOK("n. 破产者 a. 破产的", "破产者 破产的") === true);
check("认义题义项从词性标记处切开（bait 案例）", W.meanOK("n. 饵 vt. 以饵引诱, 欺负", "饵") === true);
check("认义题三个词性段全部切开（banner 案例）", W.meanOK("n. 旗帜 a. 显著的, 特别好的", "旗帜") === true);
check("认义题 vt. 段独立成义项（bare 案例）", W.meanOK("a. 赤裸的, 缺少的, 无遮蔽的, 坦率的 vt. 使赤裸, 露出", "使赤裸") === true);
check("连写词性 vt.vi. 一并剥掉", W.meanOK("vt.vi. (使)自动化", "自动化") === true);

console.log("\n== 搜索体验 · 历史记的是「那个词」 ==");
/* 自己的实例：历史要在加载前就种进 localStorage，才能连迁移路径一起测。
   种的是「老格式（{q}）与新格式（{w}）混在一起 + 无效项」，验的就是加载时那条清理逻辑 */
const ds = boot({ hist: [
  { q: "Abandon" },          // 老格式，英文搜索串 = 词头（大小写不敏感）→ 迁移
  { q: "放弃" },             // 老格式，中文搜索串对不上词头 → 丢弃
  { w: "crew" },             // 新格式 → 保留
  { w: "zzzznotaword" },     // 词表里没有 → 丢弃
  null, { q: "" },           // 垃圾项 → 丢弃
] });
await new Promise(r => ds.window.addEventListener("load", r, { once: true }));
await tick();
const S = ds.window, DS = S.document;
const $s = x => DS.querySelector(x);
const $$s = x => [...DS.querySelectorAll(x)];
const ts = () => new Promise(r => setTimeout(r, 40));
const fs_ = () => new Promise(r => setTimeout(r, 300));
const fires = (el, t) => el.dispatchEvent(new S.MouseEvent(t, { bubbles: true }));
const histNow = () => JSON.parse(S.localStorage.getItem("cet_vocab_search_hist_v1") || "[]");
const stxt = x => (DS.querySelector(x) ? DS.querySelector(x).textContent.replace(/\s+/g, " ").trim() : "(缺 " + x + ")");
const sSearch = async v => {
  fires($s("#searchBtn"), "click");
  $s("#q").value = v;
  $s("#q").dispatchEvent(new S.Event("input", { bubbles: true }));
  await ts();
};
const sRowFor = name => $$s("#res .row").find(r => r.querySelector(".word, .hw").textContent.trim() === name);

await sSearch("");
check("空查询列出历史", $$s("#res .row.hist").length === 2, "实际 " + $$s("#res .row.hist").length);
const hw = $$s("#res .row.hist").map(r => r.querySelector(".hw").textContent.trim());
check("老格式的英文搜索串迁移成词头、中文搜索串与垃圾项被丢",
      hw.join(",") === "abandon,crew", hw.join(","));
const h0 = $$s("#res .row.hist")[0];
check("历史行带音标", /^\/.+\/$/.test((h0.querySelector(".hipa") || {}).textContent || ""),
      (h0.querySelector(".hipa") || {}).textContent);
check("历史行带词性 + 翻译（就是词典释义原文）",
      /^[a-z]+\.\s*\S/.test(h0.querySelector(".hcn").textContent), h0.querySelector(".hcn").textContent);
check("历史行不再显示搜索串", !h0.querySelector(".hq"));

/* 点历史行 = 直接回到那张词卡（不是拿这个词再搜一遍） */
const h0i = h0.dataset.i;          // 词表第 0 条是 a/an，abandon 在第 2 条，别写死序号
fires(h0, "click");
await ts();
check("点历史行关掉面板", !$s("#panel").classList.contains("on"));
check("点历史行跳到 abandon 那天（第 1 天）", $s("#day").value === "0", $s("#day").value);
check("点历史行高亮的就是那个词卡", !!DS.querySelector('.card[data-i="' + h0i + '"].flash'), "data-i=" + h0i);

/* 搜中文再点结果 → 历史记的是打开的那个词，不是「放弃」这串查询 */
await sSearch("放弃");
check("中文能搜到 abandon", !!sRowFor("abandon"));
fires(sRowFor("abandon"), "click");
await fs_();
const hAfter = histNow();
check("历史落盘存的是词头 {w}，不是搜索串 {q}",
      hAfter.length > 0 && typeof hAfter[0].w === "string" && hAfter[0].q === undefined,
      JSON.stringify(hAfter[0]));
check("搜「放弃」打开 abandon 后，历史里是 abandon 而不是放弃", hAfter[0].w === "abandon", hAfter[0].w);

/* 同一个词，英文搜一次中文搜一次，历史里只该有一条 */
await sSearch("abandon");
fires(sRowFor("abandon"), "click");
await fs_();
check("同义词的两种搜法只留一条历史",
      histNow().filter(x => x.w === "abandon").length === 1,
      JSON.stringify(histNow().map(x => x.w)));

console.log("\n== 搜索体验 · 命中高亮与相关性排序 ==");
await sSearch("abandon");
check("词头命中处包 <mark>", /<mark>abandon<\/mark>/i.test($$s("#res .row")[0].querySelector(".word").innerHTML),
      $$s("#res .row")[0].querySelector(".word").innerHTML);
await sSearch("放弃");
const mrow = sRowFor("abandon");
check("释义命中处包 <mark>", /<mark>放弃<\/mark>/.test(mrow.querySelector(".cn2").innerHTML),
      mrow.querySelector(".cn2").innerHTML);
check("高亮不破坏释义（<mark> 以外的文字照常显示）",
      mrow.querySelector(".cn2").textContent.indexOf("<") < 0, mrow.querySelector(".cn2").textContent);

/* 排序：原先的顺序 = 词表顺序，act 的第 17 位是 abstract（中间含 act），精确词头 act 在第 51 位。
   分档后精确词头必须排第一 —— 这条是这一版真正修的东西，别让它退回去 */
await sSearch("act");
check("精确词头排在「含该串的更长词」之前",
      $$s("#res .row")[0].querySelector(".word").textContent.trim() === "act",
      $$s("#res .row").slice(0, 3).map(r => r.querySelector(".word").textContent.trim()).join(","));
await sSearch("art");
check("精确词头排在「释义里含 art. 的词性前缀」之前",
      $$s("#res .row")[0].querySelector(".word").textContent.trim() === "art",
      $$s("#res .row").slice(0, 3).map(r => r.querySelector(".word").textContent.trim()).join(","));

/* 中文截断：turn 的释义 91 字，「驱赶」落在第 72 字。
   原先一律切前 46 字 —— 用户看到的那一截里根本没有他要找的那个词 */
await sSearch("驱赶");
const trow = sRowFor("turn");
check("超过 46 字的释义不再从中间砍掉命中词",
      !!trow && trow.querySelector(".cn2").textContent.includes("驱赶"),
      trow ? trow.querySelector(".cn2").textContent : "(没搜到 turn)");
check("截断处补省略号", !!trow && /^…/.test(trow.querySelector(".cn2").textContent),
      trow ? trow.querySelector(".cn2").textContent.slice(0, 8) : "");

console.log("\n== 搜索体验 · 清空历史的确认态 ==");
await sSearch("");
fires($s("#histClear"), "click");
await ts();
check("点一下只是进入待确认", $s("#histClear").classList.contains("armed") && $$s("#res .row.hist").length === 2);
fires($s("#histClear"), "click");
await fs_();
check("再点一下才真清空", $$s("#res .row.hist").length === 0 && histNow().length === 0,
      JSON.stringify(histNow()));
check("清空后回到输入提示", /输入关键词/.test(stxt("#res")), stxt("#res").slice(0, 30));

console.log("\n== 搜索体验 · 运行时错误 ==");
check("搜索流程无 JS 运行时错误", ds.__errs.length === 0, ds.__errs.slice(0, 3).join(" | "));

console.log("\n== 检测流程运行时错误 ==");
check("检测流程无 JS 运行时错误", dq.__errs.length === 0, dq.__errs.slice(0, 3).join(" | "));

/* ══════════════════════════════════════════════════════════════
   分区折叠：四级/六级各折各的、每天各折各的，折叠只为「当天检测」服务。
   另起实例的理由：主实例跑到这里时已经翻到第 3 天、复习库塞满了词，
   而这里要测的第一件事恰恰是「默认全展开」这个初始态（坑 #20）。
   ══════════════════════════════════════════════════════════════ */
console.log("\n== 分区折叠 ==");

const df = boot();                                   // 第 1 天，没折过任何东西
await new Promise(r => df.window.addEventListener("load", r, { once: true }));
await tick();
const WF = df.window, DF = WF.document;
const $f = s => DF.querySelector(s);
const $$f = s => [...DF.querySelectorAll(s)];
const tf = () => new Promise(r => setTimeout(r, 40));
const fireF = (el, type) => el.dispatchEvent(new WF.MouseEvent(type, { bubbles: true }));
const foldNow = () => JSON.parse(WF.localStorage.getItem("cet_vocab_fold_v1") || "{}");
const ftxt = s => ($f(s) ? $f(s).textContent.replace(/\s+/g, " ").trim() : "(缺 " + s + ")");
const foldBtn = lv => $f(`.sec-head .fold[data-lv="${lv}"]`);
const c4n = () => $$f(".sec.s4 .card").length, c6n = () => $$f(".sec.s6 .card").length;

check("两个分区各有一个折叠按钮", !!foldBtn("c4") && !!foldBtn("c6"),
      "c4=" + !!foldBtn("c4") + " c6=" + !!foldBtn("c6"));
check("默认都展开", foldBtn("c4").getAttribute("aria-expanded") === "true" &&
                    foldBtn("c6").getAttribute("aria-expanded") === "true");
const day1c4 = c4n(), day1c6 = c6n();
check("第 1 天两个分区卡片齐全", day1c4 + day1c6 === 30 && day1c4 > 0 && day1c6 > 0,
      `四级${day1c4} 六级${day1c6}`);
check("默认没写折叠键", Object.keys(foldNow()).length === 0, JSON.stringify(foldNow()));

/* 折四级：只收起四级，六级原封不动 —— 两个板块独立 */
fireF(foldBtn("c4"), "click");
await tf();
check("折四级后四级卡片全没了（不是藏起来）", c4n() === 0, "还剩 " + c4n() + " 张");
check("折四级不动六级", c6n() === day1c6, "六级 " + c6n() + " / 原 " + day1c6);
check("折叠后标题行留着，才展开得回来", !!foldBtn("c4") && $f(".sec.s4 .sec-head"),
      ftxt(".sec.s4 .sec-head"));
check("aria-expanded 翻成 false", foldBtn("c4").getAttribute("aria-expanded") === "false");
check("四级标题写着「已折叠」", /已折叠/.test(ftxt(".sec.s4 .sec-head")), ftxt(".sec.s4 .sec-head"));
check("六级标题没被标成已折叠", !/已折叠/.test(ftxt(".sec.s6 .sec-head")), ftxt(".sec.s6 .sec-head"));
check("折叠落盘是同步的（没有 save() 那种 220ms 防抖）",
      foldNow()["0"] && foldNow()["0"].c4 === true, JSON.stringify(foldNow()));
check("顶栏补出「可考 N 词」", new RegExp("可考 " + day1c6 + " 词").test(ftxt("#todayMeta")), ftxt("#todayMeta"));

/* 每天各记各的：翻到第 2 天不受第 1 天影响 */
$f("#day").value = "1";
$f("#day").dispatchEvent(new WF.Event("change", { bubbles: true }));
await tf();
check("翻到第 2 天仍是全展开（不串天）",
      foldBtn("c4").getAttribute("aria-expanded") === "true" && c4n() > 0 && !/已折叠/.test(ftxt("#todayMeta")),
      ftxt("#todayMeta"));
$f("#day").value = "0";
$f("#day").dispatchEvent(new WF.Event("change", { bubbles: true }));
await tf();
check("翻回第 1 天还是折着的（状态在内存里也跟着走）",
      foldBtn("c4").getAttribute("aria-expanded") === "false" && c4n() === 0);

/* 6 个板块各记各的：第 1 天折四级，不影响第 1 天折六级 */
fireF(foldBtn("c6"), "click");
await tf();
check("同一天两边可以各自折", foldNow()["0"].c4 === true && foldNow()["0"].c6 === true,
      JSON.stringify(foldNow()));
check("两边都折 → 一张卡都不剩", c4n() + c6n() === 0);
check("两边都折 → 当天检测按钮置灰", $f("#dayQuizBtn").disabled === true, ftxt("#dayQuizBtn"));
check("置灰的按钮说明了原因", /折叠/.test($f("#dayQuizBtn").title), $f("#dayQuizBtn").title);
fireF(foldBtn("c4"), "click");
await tf();
check("只展开一边 → 按钮又可用，且只考那边",
      $f("#dayQuizBtn").disabled === false && c4n() === day1c4 && c6n() === 0,
      `四级${c4n()} 六级${c6n()}`);
check("展开到两边都开时，这一天的折叠键被删干净",
      (fireF(foldBtn("c6"), "click"), true) && (() => { const o = foldNow(); return o["0"] === undefined; })(),
      JSON.stringify(foldNow()));

/* 当天检测：折掉四级就只考六级，题数跟着变，不是固定 30 */
fireF(foldBtn("c4"), "click");                       // 只折四级 → 剩六级
await tf();
const only6 = $$f(".sec.s6 .card .word").map(e => e.textContent.trim()).sort();
check("折四级后六级还有 " + day1c6 + " 张卡", only6.length === day1c6, only6.length + " 张");
fireF($f("#dayQuizBtn"), "click");
await tf();
check("折四级后当天检测题数 == 剩余词数（不再是 30）",
      ftxt("#qIdx") === "第 1 题 / " + day1c6, ftxt("#qIdx"));
const qtypes = [], got6 = [];
for (let i = 0; i < day1c6; i++){
  got6.push(ftxt("#qBody .qword") || ftxt("#qBody .qbig"));
  qtypes.push(/看中文写英文/.test(ftxt("#qBody .qtag")) ? "spell" : "mean");
  fireF($f("#qSkip"), "click"); await tf();
  fireF($f("#qNext"), "click"); await tf();
}
check("折掉四级后考的全是六级词（四级一个没混进来）",
      $$f("#qBody .wrongrow .w").map(e => e.textContent.trim()).sort().join("|") === only6.join("|"),
      $$f("#qBody .wrongrow").length + " 条");
check("结果页标出「仅六级」", /范围：第 1 天 · 仅六级/.test(ftxt("#qBody .lbl")), ftxt("#qBody .lbl"));
fireF($f("#rRetryAll"), "click");
await tf();
check("「再测 N 题」跟着变成剩余词数", ftxt("#qIdx") === "第 1 题 / " + day1c6, ftxt("#qIdx"));
for (let i = 0; i < day1c6; i++){
  fireF($f("#qSkip"), "click"); await tf();
  fireF($f("#qNext"), "click"); await tf();
}
fireF($f("#rClose"), "click");
await tf();
check("答题页关掉了", !$f("#qscreen").classList.contains("on"));

/* 真实边界：第 76 天 30 词全是四级，没有六级分区 */
$f("#day").value = "75";
$f("#day").dispatchEvent(new WF.Event("change", { bubbles: true }));
await tf();
check("全四级的那天不渲染六级分区（也就没有六级折叠按钮）",
      !$f(".sec.s6") && !foldBtn("c6") && c4n() === 30, `四级${c4n()} 六级${c6n()}`);
fireF(foldBtn("c4"), "click");
await tf();
check("把这天唯一的四级折掉 → 当天检测置灰", $f("#dayQuizBtn").disabled === true);
check("这天折光了也还是渲染得出来（不是白屏）", !!$f(".sec.s4 .sec-head") && !!foldBtn("c4"));
fireF(foldBtn("c4"), "click");
await tf();
check("展开回来按钮恢复", $f("#dayQuizBtn").disabled === false && c4n() === 30);

console.log("\n== 分区折叠 · 折叠态是读档来的 ==");
const df2 = boot({ fold: { 4: { c6: true } } });      // 预置：第 5 天收起六级
await new Promise(r => df2.window.addEventListener("load", r, { once: true }));
await tick();
const W2f = df2.window, D2f = W2f.document;
const $2 = s => D2f.querySelector(s);
const $$2 = s => [...D2f.querySelectorAll(s)];
$2("#day").value = "4";
$2("#day").dispatchEvent(new W2f.Event("change", { bubbles: true }));
await new Promise(r => setTimeout(r, 40));
check("预置在第 5 天的折叠态，打开就是折的（证明是读档不是内存）",
      $2('.sec-head .fold[data-lv="c6"]').getAttribute("aria-expanded") === "false" &&
      $$2(".sec.s6 .card").length === 0 && $$2(".sec.s4 .card").length > 0,
      "六级卡 " + $$2(".sec.s6 .card").length + " 张");
check("同一份档里没提到的第 1 天不受影响",
      (() => { $2("#day").value = "0"; $2("#day").dispatchEvent(new W2f.Event("change", { bubbles: true }));
               return $2('.sec-head .fold[data-lv="c6"]').getAttribute("aria-expanded") === "true"; })());
check("坏档不炸页面（天数越界的键直接丢掉）",
      (() => {
        const d3 = boot({ fold: { 9999: { c4: true }, "-1": { c6: true }, "abc": { c4: true } } });
        return d3.window.document.querySelector(".card") !== null;
      })());

console.log("\n== 分区折叠 · 运行时错误 ==");
check("折叠流程无 JS 运行时错误", df.__errs.length === 0, df.__errs.slice(0, 3).join(" | "));

console.log(`\n结果: ${pass} 通过 / ${fail} 失败`);
process.exit(fail ? 1 : 0);
