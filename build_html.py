# -*- coding: utf-8 -*-
"""
把 out/words.json 渲染成单文件 HTML 背诵清单（数据内嵌，双击即可用，无需联网）。

**一个版本一个产物。** TEMPLATE 就是「本版」的完整页面源码——要加功能就直接改它，
改完把 VERSION 换成新版的名字（名字 = 这一版新加的功能），再跑一次就得到一个新文件，
旧版原样留着。版本沿革记在 VERSION_LOG.md。

功能：每日清单（四级/六级分块，两块可各自折叠）、勾选已掌握 + 本地进度、深浅色主题、
      点击朗读、天数跳转、全表搜索、搜索历史、复习库、抽题检测、当天检测、数据同步、判分记忆、
      决战分场（每个词一场只考一个方向，两个方向跨场累计，都过才出库）。

用法: python build_html.py
输出: out/四六级词汇背诵清单-<VERSION>.html
"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "out", "words.json")

# 本版的名字：这一版新加了什么功能，就叫什么版（见 VERSION_LOG.md）
VERSION = "派生词条版"
DST = os.path.join(BASE, "out", "四六级词汇背诵清单-%s.html" % VERSION)

TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>四六级词汇 · 每日30词</title>
<style>
:root{
  color-scheme: light;
  --bg:#f6f6f3; --surface:#ffffff; --surface-2:#f0f0ec; --surface-3:#e9e9e4;
  --text:#1b1d21; --text-2:#5a6069; --text-3:#8d939c;
  --line:#e4e4df; --line-2:#d8d8d2;
  --cet4:#3a6ea5; --cet4-bg:#eaf1f9;
  --cet6:#a8622a; --cet6-bg:#faf0e6;
  --ok:#3d8b5f; --ok-bg:#e9f4ee;
  --star:#d99a1f; --star-bg:#fdf4e0;
  --bad:#c0503f; --bad-bg:#fbeeec;
  --accent:#3a6ea5;
  --shadow:0 1px 2px rgba(20,22,26,.04), 0 4px 14px rgba(20,22,26,.05);
  --radius:14px;
  /* 键帽侧面：uiverse elijahgummer/sweet-rabbit-5 的回弹靠这几层堆出立体侧面。
     浅色主题顶面是白的，侧面逐层压暗。 */
  --key-hi:#fff; --key-1:#f4f4f1; --key-2:#e9e9e4; --key-3:#d9d9d2;
  --key-sh:rgba(20,22,26,.10);
  /* ✓ 的描边/硬投影色与勾色：uiverse andrew-demchenk0/rotten-catfish-34 */
  --tick-line:#3a3d42; --tick-ck:#fff;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --bg:#141619; --surface:#1c1f24; --surface-2:#23272d; --surface-3:#2b3038;
    --text:#e7e9ec; --text-2:#a5abb4; --text-3:#767d87;
    --line:#2a2f36; --line-2:#343a42;
    --cet4:#7fb0e0; --cet4-bg:#1d2a38;
    --cet6:#dda06a; --cet6-bg:#33261a;
    --ok:#6fc194; --ok-bg:#1b2d24;
    --star:#e8b951; --star-bg:#332a15;
    --bad:#e08c7c; --bad-bg:#3a221e;
    --accent:#7fb0e0;
    --shadow:0 1px 2px rgba(0,0,0,.3), 0 4px 14px rgba(0,0,0,.22);
    /* 深色主题同理但方向相反：顶面 #1c1f24，侧面逐层压到近黑，顶边留一道亮线 */
    --key-hi:#2b3038; --key-1:#16191d; --key-2:#111316; --key-3:#0b0c0e;
    --key-sh:rgba(0,0,0,.55);
    --tick-line:#c2c8d0; --tick-ck:#15181c;
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --bg:#141619; --surface:#1c1f24; --surface-2:#23272d; --surface-3:#2b3038;
  --text:#e7e9ec; --text-2:#a5abb4; --text-3:#767d87;
  --line:#2a2f36; --line-2:#343a42;
  --cet4:#7fb0e0; --cet4-bg:#1d2a38;
  --cet6:#dda06a; --cet6-bg:#33261a;
  --ok:#6fc194; --ok-bg:#1b2d24;
  --star:#e8b951; --star-bg:#332a15;
  --bad:#e08c7c; --bad-bg:#3a221e;
  --accent:#7fb0e0;
  --shadow:0 1px 2px rgba(0,0,0,.3), 0 4px 14px rgba(0,0,0,.22);
  --key-hi:#2b3038; --key-1:#16191d; --key-2:#111316; --key-3:#0b0c0e;
  --key-sh:rgba(0,0,0,.55);
  --tick-line:#c2c8d0; --tick-ck:#15181c;
}
/* -webkit-tap-highlight-color：安卓/微信 WebView 默认是 rgba(51,181,229,.4)（Holo 蓝）。
   它由合成器画在页面之上、不受 backdrop-filter 模糊影响，所以点「检测」时弹层已经把背景糊掉了，
   按钮上那块蓝还是锐利的。纯装饰，关掉不影响任何功能。 */
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;padding:0}
body{
  background:var(--bg); color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB",
              "Microsoft YaHei","Noto Sans CJK SC",sans-serif;
  font-size:15px; line-height:1.6;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:940px;margin:0 auto;padding:0 16px 72px}

/* ---------- 顶栏 ---------- */
header{
  position:sticky; top:0; z-index:40;
  background:var(--bg);
  background:color-mix(in srgb, var(--bg) 88%, transparent);
  -webkit-backdrop-filter:saturate(180%) blur(14px);
  backdrop-filter:saturate(180%) blur(14px);
  border-bottom:1px solid var(--line);
  margin:0 -16px 0; padding:10px 16px 0;
}
.head-row{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.brand{font-weight:650;font-size:15px;letter-spacing:.2px;white-space:nowrap}
.brand small{font-weight:400;color:var(--text-3);margin-left:8px;font-size:12.5px}
.spacer{flex:1}
.iconbtn{
  border:1px solid var(--line-2); background:var(--surface); color:var(--text-2);
  width:32px;height:32px;border-radius:9px;cursor:pointer;font-size:14px;
  display:inline-flex;align-items:center;justify-content:center;
  transition:.16s ease;
}
.iconbtn:hover{background:var(--surface-2);color:var(--text);border-color:var(--line-2)}
.topbtn{
  border:1px solid var(--line-2); background:var(--surface); color:var(--text);
  height:32px;padding:0 12px;border-radius:9px;cursor:pointer;font-size:13px;
  font-family:inherit;white-space:nowrap;transition:.16s ease;
}
.topbtn:hover:not(:disabled){background:var(--surface-2);border-color:var(--line-2)}
.topbtn:disabled{opacity:.4;cursor:default}
.bar{height:4px;background:var(--surface-3);border-radius:99px;overflow:hidden;margin:9px 0 0}
.bar>i{display:block;height:100%;width:0;background:var(--ok);border-radius:99px;transition:width .35s cubic-bezier(.4,0,.2,1)}
.head-meta{display:flex;justify-content:space-between;gap:10px;font-size:12px;color:var(--text-3);padding:5px 1px 8px}
.hm-r{display:inline-flex;align-items:center;gap:7px}
.hm-sep{opacity:.5}
.head-meta b{font-weight:600;color:var(--star);font-variant-numeric:tabular-nums}

/* ---------- 搜索长条（整行 40px，替代原 32px 图标按钮） ---------- */
.searchwrap{position:relative;padding:8px 0 10px}
.searchbar{
  display:flex;align-items:center;gap:9px;width:100%;height:40px;padding:0 13px;
  border:1px solid var(--line-2);border-radius:11px;background:var(--surface);
  transition:.16s ease;
}
.searchbar:focus-within{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 15%,transparent)}
.sbtn{
  flex:0 0 auto;border:0;background:transparent;padding:0;margin:0;cursor:pointer;
  width:22px;height:22px;display:inline-flex;align-items:center;justify-content:center;
  color:var(--text-3);transition:.16s ease;
}
.sbtn svg{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round}
.sbtn:hover{color:var(--text)}
.searchbar input{
  flex:1;min-width:0;border:0;background:transparent;outline:none;color:var(--text);
  font-size:14.5px;font-family:inherit;
}
.searchbar input::placeholder{color:var(--text-3)}

/* ---------- 天导航 ---------- */
nav{display:flex;align-items:center;gap:8px;margin:14px 0 6px;flex-wrap:wrap}
.navbtn{
  border:1px solid var(--line-2); background:var(--surface); color:var(--text);
  height:36px;padding:0 14px;border-radius:10px;cursor:pointer;font-size:14px;
  font-family:inherit; transition:.16s ease;
}
.navbtn:hover:not(:disabled){background:var(--surface-2)}
.navbtn:disabled{opacity:.4;cursor:default}
select#day{
  appearance:none; border:1px solid var(--line-2); background:var(--surface); color:var(--text);
  height:36px;padding:0 30px 0 12px;border-radius:10px;font-size:14px;font-family:inherit;cursor:pointer;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'><path d='M2 4.5 6 8.5 10 4.5' fill='none' stroke='%238d939c' stroke-width='1.6' stroke-linecap='round'/></svg>");
  background-repeat:no-repeat; background-position:right 11px center;
}
.today{font-size:13px;color:var(--text-3);margin-left:auto}

/* ---------- 分区 ---------- */
.sec{margin-top:22px}
.sec-head{display:flex;align-items:center;gap:9px;margin:0 0 10px 2px}
.dot{width:8px;height:8px;border-radius:99px}
.dot.c4{background:var(--cet4)} .dot.c6{background:var(--cet6)}
.sec-head h2{font-size:14px;font-weight:600;margin:0;letter-spacing:.3px}
/* flex:1 只给每日清单里那个带折叠按钮的 h2 —— 结果页的 .sec-head 结构一样但没按钮，
   跟着撑开会把它后面的 .cnt 顶到最右边去（「错题 … 5 词」变成两端对齐） */
.sec-head h2.fh{flex:1;min-width:0}
.sec-head .cnt{font-size:12.5px;color:var(--text-3);font-variant-numeric:tabular-nums}
/* 折叠：标题行整行可点（h2 撑满、按钮再撑满 h2），所以点哪儿都行。
   结果页那两个 .sec-head 里没有 .fold，不受影响。 */
.sec-head .fold{
  display:flex;align-items:center;gap:9px;width:100%;
  background:none;border:0;margin:-4px -6px;padding:4px 6px;border-radius:9px;
  font:inherit;letter-spacing:inherit;color:inherit;text-align:left;cursor:pointer;transition:.16s ease;
}
.sec-head .fold:hover{background:var(--surface-2)}
.sec-head .fold:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.chev{
  width:0;height:0;flex:none;margin-left:2px;color:var(--text-3);
  border-left:5px solid currentColor;border-top:4.5px solid transparent;border-bottom:4.5px solid transparent;
  transition:transform .18s ease;
}
.fold[aria-expanded="true"] .chev{transform:rotate(90deg)}

/* ---------- 词卡 ---------- */
.card{
  display:flex;align-items:flex-start;gap:12px;
  background:var(--surface); border:1px solid var(--line);
  border-radius:var(--radius); padding:13px 15px 13px 16px; margin-bottom:8px;
  box-shadow:var(--shadow); transition:.18s ease; position:relative; overflow:hidden;
}
.card::before{
  content:""; position:absolute; left:0; top:0; bottom:0; width:3px;
  background:var(--cet4); opacity:.85;
}
.card.c6::before{background:var(--cet6)}
.card:hover{border-color:var(--line-2)}
.card.done{background:var(--surface-2);box-shadow:none}
.card.done::before{background:var(--ok)}
.card.done .word{color:var(--text-3);text-decoration:line-through;text-decoration-thickness:1px;text-decoration-color:var(--text-3)}
.card.done .ipa,.card.done .cn,.card.done .deriv{opacity:.5}
.card.flash{animation:flash 1.5s ease}
@keyframes flash{0%,55%{background:var(--ok-bg);border-color:var(--ok)}100%{}}

.body{flex:1;min-width:0}
.line1{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;margin-bottom:2px}
.word{
  font-size:18.5px;font-weight:600;letter-spacing:.1px;cursor:pointer;
  border-bottom:1px dotted transparent; transition:.15s;
}
.word:hover{border-bottom-color:currentColor;color:var(--accent)}
.ipa{
  font-family:"SF Mono",ui-monospace,Consolas,"Courier New",monospace;
  font-size:12.5px;color:var(--text-3);letter-spacing:.1px;white-space:nowrap;
}
.cn{font-size:14px;color:var(--text-2);overflow-wrap:break-word}
.deriv{
  margin-top:7px;font-size:12.5px;color:var(--text-3);
  display:flex;flex-direction:column;gap:2px;align-items:flex-start;
}
.deriv b{font-weight:500;color:var(--text-3);opacity:.8;margin-right:1px}
/* 派生词从「一排 pill」改成「一行一条」：补上音标与释义后每条会长很多，
   横排 pills 会把卡片挤爆（2444 个派生词里释义最长的接近 90 字）。 */
.deriv .dv{
  display:flex;flex-wrap:wrap;align-items:baseline;gap:0 6px;
  line-height:1.5;
}
.deriv .dv-w{font-weight:500;color:var(--text-2)}
.deriv .dv-ipa{
  font-family:"SF Mono",ui-monospace,Consolas,"Courier New",monospace;
  font-size:11.5px;color:var(--text-3);white-space:nowrap;letter-spacing:.1px;
}
.deriv .dv-cn{color:var(--text-3);overflow-wrap:break-word}

/* ---------- 卡片右侧控件：★ 复习库 · ✓ 已掌握 ---------- */
.ctl{flex:0 0 auto;display:flex;align-items:center;gap:7px;padding-top:1px}
.star{
  width:30px;height:30px;border:0;background:transparent;cursor:pointer;padding:0;
  display:inline-flex;align-items:center;justify-content:center;
  border-radius:8px;transition:.16s ease;
}
/* 星形取自 uiverse andrew-demchenk0/light-lionfish-40（它常态是实心灰、选中亮黄）。
   这里只留形状：常态空心描边、选中才实心填充 —— 30 行列表里 30 个实心灰星太吵，
   而且「空↔实」的状态差异比「灰↔金」更好扫。 */
.star svg{width:20px;height:20px;fill:none;stroke:var(--text-3);stroke-width:1.5;
  stroke-linejoin:round;transition:.16s ease}
.star:hover{background:var(--star-bg)}
.star:hover svg{stroke:var(--star);transform:scale(1.1)}
.star[aria-pressed="true"] svg{fill:var(--star);stroke:var(--star)}
.star:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.card.inreview{border-color:color-mix(in srgb,var(--star) 45%,var(--line))}

/* ---------- 勾选 ---------- */
.tick{flex:0 0 auto;padding-top:2px}
.tick input{position:absolute;opacity:0;width:0;height:0}
/* 方框 + 错位硬投影取自 uiverse andrew-demchenk0/rotten-catfish-34，
   原版投影是 4px，30 行列表里太重，收到 2px 保留贴纸味。颜色走主题变量。 */
.tick label{
  display:flex;align-items:center;justify-content:center;
  width:26px;height:26px;border-radius:6px;cursor:pointer;
  border:2px solid var(--tick-line);background:var(--surface);
  box-shadow:2px 2px 0 var(--tick-line);
  transition:background .16s ease,border-color .16s ease;
}
.tick label:hover{background:var(--surface-2)}
.tick label::after{
  content:"";width:6px;height:11px;
  border:solid var(--tick-ck);border-width:0 2px 2px 0;
  opacity:0;transform:rotate(45deg) scale(.6);
  transition:.16s cubic-bezier(.4,0,.2,1);
}
.tick input:checked + label{background:var(--ok);border-color:var(--ok)}
.tick input:checked + label::after{opacity:1;transform:rotate(45deg) scale(1)}
.tick input:focus-visible + label{outline:2px solid var(--accent);outline-offset:2px}

/* ---------- 搜索结果下拉（绝对定位，不推挤内容） ---------- */
.panel{
  position:absolute;left:0;right:0;top:52px;z-index:50;
  background:var(--surface);border:1px solid var(--line-2);border-radius:12px;
  box-shadow:0 12px 34px rgba(0,0,0,.16);display:none;overflow:hidden;
}
.panel.on{display:block}
.res{max-height:min(52vh,420px);overflow-y:auto;padding:6px}
.res .row{
  display:flex;align-items:baseline;gap:10px;padding:9px 12px;border-radius:9px;cursor:pointer;
}
.res .row:hover,.res .row.sel{background:var(--surface-2)}
.res .row .d{font-size:12px;color:var(--text-3);margin-left:auto;white-space:nowrap}
.res .row .cn2{font-size:12.5px;color:var(--text-3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:290px}
/* 命中高亮用字色而不是黄底：深浅两套主题下都不需要另配背景色，
   也和这个页面「只有强调色一种彩」的克制一致 */
.res mark{background:transparent;color:var(--accent);font-weight:600}
.empty{padding:26px;text-align:center;color:var(--text-3);font-size:14px}

/* ---------- 搜索历史（空查询时展示在结果面板里） ---------- */
.res-head{
  display:flex;align-items:center;justify-content:space-between;gap:10px;
  padding:8px 12px 6px;font-size:12px;color:var(--text-3);letter-spacing:.2px;
}
.hclear{
  flex:0 0 auto;border:0;background:transparent;color:var(--text-3);
  font-size:12px;font-family:inherit;cursor:pointer;padding:3px 8px;border-radius:7px;transition:.16s;
}
.hclear:hover{color:var(--bad);background:var(--bad-bg)}
.hclear.armed{color:var(--bad);font-weight:600;background:var(--bad-bg)}
.res .row.hist{align-items:center;gap:9px}
.hic{flex:0 0 auto;width:16px;height:16px;display:inline-flex;align-items:center;justify-content:center;color:var(--text-3)}
.hic svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round}
/* 历史行显示的是「那个词」本身（词头 + 音标 + 释义），不是当初敲进去的搜索串 */
.hw{
  flex:0 1 auto;min-width:0;font-size:14.5px;font-weight:600;color:var(--text);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.hipa{
  flex:0 0 auto;font-family:"SF Mono",ui-monospace,Consolas,"Courier New",monospace;
  font-size:11.5px;color:var(--text-3);letter-spacing:.1px;white-space:nowrap;
}
.hcn{
  flex:1;min-width:0;font-size:12.5px;color:var(--text-3);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.hx{
  flex:0 0 auto;width:26px;height:26px;padding:0;border:0;border-radius:7px;
  background:transparent;color:var(--text-3);font-size:12px;line-height:1;font-family:inherit;
  display:inline-flex;align-items:center;justify-content:center;cursor:pointer;transition:.16s;
}
.hx:hover{background:var(--bad-bg);color:var(--bad)}

/* ---------- 弹层（检测配置） ---------- */
.mask{position:fixed;inset:0;background:rgba(12,14,17,.45);z-index:80;display:none;
  backdrop-filter:blur(3px)}
.mask.on{display:block}
.dialog{
  position:fixed;left:50%;top:11vh;transform:translateX(-50%);
  width:min(460px,calc(100vw - 28px));max-height:80vh;z-index:90;
  background:var(--surface);border:1px solid var(--line-2);border-radius:16px;
  box-shadow:0 18px 50px rgba(0,0,0,.22);display:none;flex-direction:column;overflow:hidden;
}
.dialog.on{display:flex}
.dialog h3{margin:0;padding:17px 19px 13px;font-size:16px;font-weight:650}
.dialog .grp{padding:0 19px 15px}
.dialog .grp>label{display:block;font-size:12.5px;color:var(--text-3);margin-bottom:7px;letter-spacing:.3px}
.segs{display:flex;gap:7px}
.seg{
  flex:1;height:38px;border:1px solid var(--line-2);background:var(--surface);
  border-radius:10px;cursor:pointer;font-size:13.5px;font-family:inherit;color:var(--text-2);
  transition:.16s;padding:0 6px;white-space:nowrap;
}
.seg:hover{background:var(--surface-2)}
.seg.on{background:var(--cet4-bg);border-color:var(--cet4);color:var(--cet4);font-weight:600}
.numin{display:flex;align-items:center;gap:10px}
.numin input{
  width:104px;height:38px;border:1px solid var(--line-2);border-radius:10px;
  background:var(--surface);color:var(--text);font-size:15px;font-family:inherit;
  padding:0 12px;outline:none;font-variant-numeric:tabular-nums;
}
.numin input:focus{border-color:var(--accent)}
.numin span{font-size:12.5px;color:var(--text-3);line-height:1.5}
.qempty{
  margin:0 19px 15px;padding:10px 13px;border-radius:10px;background:var(--star-bg);
  border:1px solid color-mix(in srgb,var(--star) 40%,transparent);
  color:var(--text-2);font-size:13px;display:none;line-height:1.6;
}
.dialog .foot{display:flex;gap:9px;padding:14px 19px 18px;border-top:1px solid var(--line);background:var(--surface-2)}
.btn{
  flex:1;height:42px;border-radius:11px;border:1px solid var(--line-2);background:var(--surface);
  color:var(--text);font-size:14.5px;font-family:inherit;cursor:pointer;transition:.16s;
}
.btn:hover:not(:disabled){background:var(--surface-3)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
.btn.primary:hover:not(:disabled){filter:brightness(1.07)}
.btn:disabled{opacity:.45;cursor:default}
.btn.danger{color:var(--bad);border-color:color-mix(in srgb,var(--bad) 35%,var(--line-2))}
/* :not(.armed) 不能省：这条是 0,4,0，比下面的 .btn.danger.armed（0,3,0）高，
   会把它盖成浅底 + 白字（白字来自 .armed），待确认的按钮就成了隐形按钮。
   触屏上尤其致命——点一下会留下粘住的 :hover，正好落在待确认那一刻。 */
.btn.danger:hover:not(:disabled):not(.armed){background:var(--bad-bg);border-color:var(--bad)}
.btn.danger.armed{background:var(--bad);border-color:var(--bad);color:#fff;font-weight:600}

/* ---------- 复习库管理面板（复用 .dialog 骨架） ---------- */
.dialog h3 .cnt{font-size:12.5px;font-weight:500;color:var(--text-3);font-variant-numeric:tabular-nums}
.revlist{flex:1;overflow-y:auto;padding:2px 12px 12px;min-height:64px}
.revrow{display:flex;align-items:baseline;gap:9px;padding:8px 9px;border-radius:9px;cursor:pointer}
.revrow:hover{background:var(--surface-2)}
.revrow .w{font-weight:600;font-size:15px;white-space:nowrap}
.revrow .ipa{font-size:12px;color:var(--text-3);white-space:nowrap}
.revrow .cn2{flex:1;font-size:12.5px;color:var(--text-3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.revrow .d{font-size:12px;color:var(--text-3);white-space:nowrap}
.revrow .x{
  flex:0 0 auto;align-self:center;width:32px;height:32px;padding:0;border:0;border-radius:8px;
  background:transparent;color:var(--text-3);font-size:14px;line-height:1;font-family:inherit;
  cursor:pointer;transition:.16s;
}
.revrow .x:hover{background:var(--bad-bg);color:var(--bad)}
/* 决战复习库：主按钮独占一行，清空 / 关闭第二行平分，窄屏不挤 */
#rev .foot{flex-wrap:wrap}
#battleStart{flex:1 1 100%}
#battleNum:disabled{opacity:.45}
/* 数量区与滚动列表之间固定分隔（滚动容器的 padding-bottom 会随滚动走，贴不住） */
#battleGrp{border-top:1px solid var(--line);padding:13px 19px 15px}
/* 一行塞不下「词 + 音标 + 释义 + 天 + ✕」。释义在这里是认出这个词的唯一线索，
   音标不是（点进卡片就有），所以窄屏让音标让位——否则释义被挤到只剩两个汉字，
   渲染出来是噪音。释义本身仍按设计省略号截断。 */
@media (max-width:380px){
  .revrow .ipa{display:none}
}

/* ---------- 答题页（全屏） ---------- */
.qscreen{position:fixed;inset:0;z-index:120;background:var(--bg);overflow-y:auto;display:none}
.qscreen.on{display:block}
.qwrap{max-width:620px;margin:0 auto;padding:24px 16px 64px}
.qtop{display:flex;align-items:center;gap:12px;font-size:13px;color:var(--text-3);margin-bottom:20px}
.qtop .idx{font-variant-numeric:tabular-nums;font-weight:600;color:var(--text-2);white-space:nowrap}
.qprog{flex:1;height:4px;background:var(--surface-3);border-radius:99px;overflow:hidden}
.qprog>i{display:block;height:100%;width:0;background:var(--accent);border-radius:99px;transition:width .3s}
.qexit{
  border:1px solid var(--line-2);background:var(--surface);color:var(--text-2);
  height:30px;padding:0 11px;border-radius:9px;cursor:pointer;font-size:12.5px;
  font-family:inherit;white-space:nowrap;
}
.qexit:hover{background:var(--surface-2)}
.qcard{
  background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:30px 26px;box-shadow:var(--shadow);
}
.qtag{
  display:inline-block;font-size:11.5px;padding:2px 9px;border-radius:6px;
  background:var(--surface-2);color:var(--text-3);border:1px solid var(--line);margin-bottom:16px;
}
.qcn{font-size:21px;line-height:1.75;font-weight:500;word-break:break-word}
.qen{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.qword{font-size:34px;font-weight:600;letter-spacing:-.4px;line-height:1.25;word-break:break-word}
.say{width:34px;height:34px;border:1px solid var(--line-2);background:var(--surface);
  border-radius:9px;cursor:pointer;font-size:14px;line-height:1;transition:.16s}
.say:hover{background:var(--surface-2)}
.qhint{font-size:12.5px;color:var(--text-3);margin-top:16px;line-height:1.7}
.qin{display:flex;gap:9px;margin-top:20px;flex-wrap:wrap}
.qin input{
  flex:1;min-width:140px;height:48px;border:1px solid var(--line-2);border-radius:12px;background:var(--surface);
  color:var(--text);font-size:18px;font-family:inherit;padding:0 15px;outline:none;transition:.16s;
}
.qin input:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 15%,transparent)}
.qin button{
  height:48px;padding:0 20px;border-radius:12px;border:1px solid var(--line-2);
  background:var(--surface);color:var(--text);font-size:14px;font-family:inherit;cursor:pointer;
  white-space:nowrap;
}
.qin button:hover{background:var(--surface-3)}
.qin button.primary{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
.fb{
  margin-top:18px;border-radius:12px;padding:15px 17px;border:1px solid;display:flex;
  align-items:flex-start;gap:12px;flex-wrap:wrap;
}
.fb.ok{background:var(--ok-bg);border-color:color-mix(in srgb,var(--ok) 35%,transparent)}
.fb.bad{background:var(--bad-bg);border-color:color-mix(in srgb,var(--bad) 35%,transparent)}
.fb .mark{font-size:17px;font-weight:700;line-height:1.35}
.fb.ok .mark{color:var(--ok)} .fb.bad .mark{color:var(--bad)}
.fb .txt{flex:1;min-width:150px;font-size:14px}
.fb .txt .ans{font-weight:650;font-size:16px}
.fb .txt .sub{font-size:12.5px;color:var(--text-3);margin-top:3px;line-height:1.7}
.fb .txt .part{font-size:12.5px;color:var(--bad);margin-top:6px;line-height:1.7}
/* 判分记忆的撤销入口：文字链样式，不是按钮盒子。
   下面这两条的特异度（0,4,0 / 0,5,0）必须压过 .fb button（0,1,1）和 .fb button:hover（0,2,1），
   否则会被还原成 34px 高、带边框的方块，混在「下一题」旁边看不出是附注。 */
.fb .txt .recall{font-size:12.5px;color:var(--text-3);margin-top:6px;line-height:1.7}
.fb .txt .recall .forget{
  height:auto;padding:0;border:0;background:none;color:inherit;align-self:auto;
  font-size:12.5px;font-family:inherit;text-decoration:underline;
  text-underline-offset:3px;cursor:pointer;white-space:normal;
}
.fb .txt .recall .forget:hover{background:none;color:var(--text)}
.fb button{
  align-self:center;height:34px;padding:0 13px;border-radius:9px;
  border:1px solid var(--line-2);background:var(--surface);color:var(--text);
  font-size:13px;font-family:inherit;cursor:pointer;white-space:nowrap;
}
.fb button:hover{background:var(--surface-3)}

/* ---------- 结果页 ---------- */
.res-score{
  background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:28px 24px;box-shadow:var(--shadow);text-align:center;margin-bottom:16px;
}
.res-score .big{font-size:42px;font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:-1px;line-height:1.15}
.res-score .big em{font-style:normal;font-size:19px;color:var(--text-3);font-weight:500}
.res-score .lbl{font-size:13px;color:var(--text-3);margin-top:6px;line-height:1.9}
.res-score .split{
  display:flex;align-items:center;justify-content:center;gap:14px;flex-wrap:wrap;
  margin-top:16px;padding-top:15px;border-top:1px solid var(--line);font-size:13px;color:var(--text-2);
}
.res-score .split b{font-variant-numeric:tabular-nums;font-weight:650;color:var(--text)}
.res-score .split .sep{width:1px;height:15px;background:var(--line-2)}
.rbtns{display:flex;gap:9px;flex-wrap:wrap}
.rbtns .btn{flex:1 1 150px;height:44px}
.res-bk{margin-top:26px}
.res-bk .cnt{font-variant-numeric:tabular-nums}
.wrongrow{
  display:flex;align-items:baseline;gap:10px;padding:10px 14px;background:var(--surface);
  border:1px solid var(--line);border-radius:11px;margin-bottom:7px;flex-wrap:wrap;
}
.wrongrow .w{font-weight:600;font-size:16px}
.wrongrow .mt{
  font-size:11px;padding:1px 7px;border-radius:5px;background:var(--surface-2);
  border:1px solid var(--line);color:var(--text-3);white-space:nowrap;align-self:center;
}
.wrongrow .you{font-size:12.5px;color:var(--bad)}
.wrongrow .cn2{
  font-size:12.5px;color:var(--text-3);margin-left:auto;text-align:right;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:46%;
}
.rhint{font-size:12.5px;color:var(--text-3);margin-top:12px;line-height:1.7}

.hint{text-align:center;color:var(--text-3);font-size:12px;margin-top:26px;line-height:1.9}
kbd{font-family:inherit;background:var(--surface-2);border:1px solid var(--line);
  border-radius:5px;padding:1px 5px;font-size:11.5px}

@media (max-width:560px){
  .wrap{padding:0 12px 60px}
  header{margin:0 -12px 0;padding:9px 12px 0}
  .word{font-size:17px}
  .cn{font-size:13.5px}
  .card{padding:12px 12px 12px 14px;gap:9px}
  .today{width:100%;margin-left:0}
  .seg{font-size:12.5px}
  .qcard{padding:22px 18px}
  .qcn{font-size:18px}
  .qword{font-size:28px}
  .res-score .big{font-size:36px}
}
/* ---------- 实体动作按钮的键帽回弹 ----------
   取自 uiverse elijahgummer/sweet-rabbit-5：原版用 8 层 box-shadow 堆出键帽的立体侧面，
   :active 时整体下沉、侧面被压扁，于是有「按下去」的手感。
   这里把各层偏移改成由 --kc（键帽深度）推导，一套规则适配所有尺寸的按钮。
   只给真正「按下去会做事」的按钮。不加的：.seg 分段选择器（并排的扁平分段，
   加立体侧面会变成一排小砖）、.iconbtn/.sbtn/.say（没底色的纯图标，加了像悬浮）、
   以及卡片上的 ★/✓（它们有各自选定的设计）。
   放在样式表末尾是为了盖住上面各家族自己写的 transition。 */
.btn,.topbtn,.navbtn,.qexit,.qin button,.fb button{
  --kc:5px;
  box-shadow:
    inset 0 1px 0 var(--key-hi),
    0 calc(var(--kc) * .2) 0 var(--key-1),
    0 calc(var(--kc) * .4) 0 var(--key-2),
    0 calc(var(--kc) * .6) 0 var(--key-3),
    0 calc(var(--kc) * .8) 0 var(--key-3),
    0 var(--kc) 0 var(--key-3),
    0 var(--kc) calc(var(--kc) * 1.2) var(--key-sh);
  transition:translate .15s ease,box-shadow .15s ease,
    background .16s ease,border-color .16s ease,filter .16s ease;
}
/* 矮按钮（≤36px）用浅一点的键帽：5px 的侧面压在 30px 高的按钮上像块砖 */
.topbtn,.qexit,.fb button{--kc:3px}
/* 主按钮是实心蓝的，侧面再用中性灰会像贴了块别的颜色，改成由 --accent 往下压 */
.btn.primary,.qin button.primary{
  --key-hi:color-mix(in srgb,var(--accent) 88%,#fff);
  --key-1:color-mix(in srgb,var(--accent) 86%,#000);
  --key-2:color-mix(in srgb,var(--accent) 72%,#000);
  --key-3:color-mix(in srgb,var(--accent) 58%,#000);
}
.btn:active:not(:disabled),.topbtn:active,.navbtn:active:not(:disabled),
.qexit:active,.qin button:active,.fb button:active{
  translate:0 calc(var(--kc) * .8);
  box-shadow:
    inset 0 1px 0 var(--key-hi),
    0 calc(var(--kc) * .2) 0 var(--key-1),
    0 calc(var(--kc) * .2) calc(var(--kc) * .4) var(--key-sh);
}

/* ---------- 触摸设备：关掉「粘住」的 hover ----------
   手机没有鼠标指针，:hover 不会因为「移开」而取消——点一下之后浏览器会一直挂着它，
   直到你点别的地方。于是 ★ 会永远留着金色的 hover 描边 + 淡黄底，看着像选中了，
   实际 aria-pressed 还是 false。产物里 17 条 :hover 全部没有 @media (hover:hover) 守卫，
   这里统一重置回常态。

   为什么用「末尾覆盖」而不是把那 17 条包进 @media (hover:hover)：`.res .row:hover,.res .row.sel`
   是两种选择器混写，包起来会把选中态一起干掉。

   :not(.on)/:not(.primary)/:not(.sel)/:not(.armed) 不是多余的——本块在样式表末尾，
   与选中态同优先级时会盖掉选中态（`.seg:hover` 和 `.seg.on` 都是 0,2,0），
   加 :not 让选中态根本不被这条规则匹配。

   .armed 是同类问题的另一半：触屏点一下会留下粘住的 :hover，而「再点一次确认」
   恰恰就发生在这一下之后——被盖掉的话浅底配白字，按钮等于隐形。 */
@media (hover:none){
  .iconbtn:hover{background:var(--surface);color:var(--text-2)}
  .topbtn:hover:not(:disabled){background:var(--surface)}
  .sec-head .fold:hover{background:transparent}
  .sbtn:hover{color:var(--text-3)}
  .navbtn:hover:not(:disabled){background:var(--surface)}
  .card:hover{border-color:var(--line)}
  .word:hover{border-bottom-color:transparent;color:inherit}
  .star:hover{background:transparent}
  .star:hover svg{stroke:var(--text-3);transform:none}
  .tick label:hover{background:var(--surface)}
  .res .row:hover:not(.sel){background:transparent}
  .hclear:hover{background:transparent;color:var(--text-3)}
  .hx:hover{background:transparent;color:var(--text-3)}
  .seg:hover:not(.on){background:var(--surface)}
  .btn:hover:not(:disabled):not(.armed){background:var(--surface)}
  .btn.primary:hover:not(:disabled){background:var(--accent);filter:none}
  .qexit:hover{background:var(--surface)}
  .say:hover{background:var(--surface)}
  .qin button:hover:not(.primary){background:var(--surface)}
  .fb button:hover{background:var(--surface)}
}

@media print{
  header,nav,.tick,.ctl,.star,.searchwrap,.topbtn,.hint,
  .qscreen,.dialog,.mask{display:none!important}
  body{background:#fff}
  .card{break-inside:avoid;box-shadow:none;border-color:#ddd}
}

/* 尊重系统「减少动态效果」：把 21 处 transition 和 flash 高亮动画压成瞬时。
   只改时长、不改终态——进度条宽度、选中态、flash 结束后的底色照常抵达，功能不受影响。 */
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{
    transition-duration:.01ms!important;
    animation-duration:.01ms!important;
    animation-iteration-count:1!important;
    scroll-behavior:auto!important;
  }
}

/* ══════════ 数据同步（头部 ⇅ 图标按钮 → 自己的弹层） ══════════
   作用域一律收在 #sync 里，避免碰到 #cfg / #rev 两个既有弹层。 */
#sync .syncscroll{flex:1;overflow-y:auto;min-height:0}
#syncBox{
  width:100%;box-sizing:border-box;height:96px;resize:vertical;display:block;
  border:1px solid var(--line-2);border-radius:10px;background:var(--surface-2);
  color:var(--text-2);font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:11px;line-height:1.55;padding:9px 11px;outline:none;transition:.16s;
}
#syncBox:focus{border-color:var(--accent)}
#syncBox::placeholder{color:var(--text-3)}
#sync .syncrow{display:flex;gap:8px}
#sync .syncrow .btn{flex:1;height:36px;font-size:13px;--kc:3px}
#sync .syncmsg{
  font-size:12.5px;line-height:1.65;color:var(--text-3);
  padding:9px 11px;border-radius:9px;background:var(--surface-2);
}
#sync .syncmsg.ok{color:var(--ok);background:var(--ok-bg)}
#sync .syncmsg.bad{color:var(--bad);background:var(--bad-bg)}
#sync .syncmsg b{font-variant-numeric:tabular-nums}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="head-row">
      <div class="brand">四六级词汇 · 每日 30 词<small id="totalLabel"></small></div>
      <div class="spacer"></div>
      <button class="iconbtn" id="themeBtn" title="切换深浅色" aria-label="切换主题">&#9788;</button>
      <button class="iconbtn" id="syncBtn" title="导出 / 导入学习数据" aria-label="数据同步">&#8645;</button>
      <button class="topbtn" id="quizBtn" title="抽题检测">&#9635; 检测</button>
      <button class="topbtn" id="dayQuizBtn" title="检测当前这一天的 30 词">&#9745; 当天检测</button>
      <button class="topbtn" id="revBtn" title="管理复习库：查看 / 移除 / 清空">&#9733; 复习库</button>
    </div>
    <div class="bar"><i id="barFill"></i></div>
    <div class="head-meta">
      <span id="progAll">已掌握 0 / 0</span>
      <span class="hm-r">
        <span id="progDay"></span>
        <span class="hm-sep">·</span>
        <span id="reviewCnt">复习库 <b>0</b> 词</span>
      </span>
    </div>

    <div class="searchwrap">
      <div class="searchbar">
        <button class="sbtn" id="searchBtn" title="搜索单词（/）" aria-label="搜索" type="button">
          <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>
        </button>
        <input id="q" placeholder="输入英文或中文搜索…" autocomplete="off" spellcheck="false">
        <kbd>/</kbd>
      </div>
      <div class="panel" id="panel">
        <div class="res" id="res"></div>
      </div>
    </div>
  </header>

  <nav>
    <button class="navbtn" id="prev">‹ 上一天</button>
    <select id="day" aria-label="选择天数"></select>
    <button class="navbtn" id="next">下一天 ›</button>
    <span class="today" id="todayMeta"></span>
  </nav>

  <main id="content"></main>

  <div class="hint">
    <kbd>←</kbd> <kbd>→</kbd> 切换天 &nbsp;·&nbsp; <kbd>/</kbd> 搜索 &nbsp;·&nbsp; 点单词朗读
    &nbsp;·&nbsp; ★ 加入复习库 &nbsp;·&nbsp; ✓ 标记已掌握
    <br>进度与复习库自动保存在本机浏览器
  </div>
</div>

<!-- ══════════ 检测配置 ══════════ -->
<div class="mask" id="mask"></div>
<div class="dialog" id="cfg">
  <h3>开始检测</h3>
  <div class="grp">
    <label>抽取范围</label>
    <div class="segs" id="scopeSegs">
      <button class="seg on" type="button" data-v="review">复习库（0）</button>
      <button class="seg" type="button" data-v="all">全部（0）</button>
      <button class="seg" type="button" data-v="mastered">已掌握（0）</button>
    </div>
  </div>
  <div class="grp">
    <label>题目数量</label>
    <div class="numin">
      <input type="number" id="qNum" value="20" min="1" max="200" inputmode="numeric">
      <span id="qNumHint">题</span>
    </div>
  </div>
  <div class="grp">
    <label>题型</label>
    <div class="segs" id="typeSegs">
      <button class="seg on" type="button" data-v="spell">看中文写英文</button>
      <button class="seg" type="button" data-v="mean">看英文写中文</button>
      <button class="seg" type="button" data-v="mixed">混合</button>
    </div>
  </div>
  <div class="qempty" id="qEmpty"></div>
  <div class="foot">
    <button class="btn" type="button" id="qCancel">取消</button>
    <button class="btn primary" type="button" id="qStart">开始</button>
  </div>
</div>

<!-- ══════════ 复习库管理（复用 .dialog 骨架，与检测配置共用一块 #mask） ══════════ -->
<div class="dialog" id="rev">
  <h3>复习库 <span class="cnt" id="revTotal"></span></h3>
  <div class="revlist" id="revList"></div>
  <div class="grp" id="battleGrp">
    <label>决战数量（从库中随机抽取；一场里每个词只考一个方向，两个方向都通过才出库）</label>
    <div class="numin">
      <input type="number" id="battleNum" value="1" min="1" inputmode="numeric">
      <span id="battleNumHint"></span>
    </div>
  </div>
  <div class="foot">
    <button class="btn primary" type="button" id="battleStart">决战复习库</button>
    <button class="btn danger" type="button" id="revClear">清空复习库</button>
    <button class="btn" type="button" id="revClose">关闭</button>
  </div>
</div>

<!-- ══════════ 数据同步（导出 / 导入合并） ══════════
     两台设备的 localStorage 互相独立，靠一段 JSON 手工搬运。与 #cfg / #rev 共用 #mask。
     搬的是「操作日志」，不是当前的集合——详见脚本里的「操作日志」那一段。 -->
<div class="dialog" id="sync">
  <h3>数据同步</h3>
  <div class="syncscroll">
    <div class="grp">
      <label>导出 &mdash;&mdash; 在本机生成一份数据，拿到另一台设备导入</label>
      <div class="syncrow">
        <button class="btn" type="button" id="syncCopy">复制到剪贴板</button>
        <button class="btn" type="button" id="syncDl">下载 .json</button>
      </div>
    </div>
    <div class="grp">
      <textarea id="syncBox" spellcheck="false"
        placeholder="导出的数据会出现在这里；也可以把另一台设备的数据粘贴进来"></textarea>
    </div>
    <div class="grp">
      <label>导入 &mdash;&mdash; 与本机数据合并（已掌握 / 复习库 / 判分记忆，各按最后一次操作为准）</label>
      <div class="syncrow">
        <button class="btn" type="button" id="syncPaste">从剪贴板粘贴</button>
        <button class="btn" type="button" id="syncPick">选择文件</button>
        <input type="file" id="syncFile" accept=".json,application/json" hidden>
      </div>
    </div>
    <div class="grp"><div class="syncmsg" id="syncMsg"></div></div>
  </div>
  <div class="foot">
    <button class="btn danger" type="button" id="syncApply">导入并合并</button>
    <button class="btn" type="button" id="syncClose">关闭</button>
  </div>
</div>

<!-- ══════════ 答题 / 结果（全屏） ══════════ -->
<div class="qscreen" id="qscreen">
  <div class="qwrap">
    <div class="qtop">
      <span class="idx" id="qIdx"></span>
      <span class="qprog"><i id="qBar"></i></span>
      <button class="qexit" type="button" id="qExit">退出</button>
    </div>
    <div id="qBody"></div>
  </div>
</div>

<script>
const DATA = __DATA__;
const DAYS = DATA.days;
const ALL = DAYS.flat();
const TOTAL = ALL.length;

/* ---------- 进度存储 ---------- */
const KEY = "cet_vocab_mastered_v1";
let mastered = new Set();
try { mastered = new Set(JSON.parse(localStorage.getItem(KEY) || "[]")); } catch (e) {}
let saveTimer = null;
function save(){
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    try { localStorage.setItem(KEY, JSON.stringify([...mastered])); } catch (e) {}
  }, 220);
}

/* ---------- 复习库存储 ----------
   ★ 与 ✓ 互不干扰：★ 记「这次没想起来」，✓ 记「这个词我过了」。
   两个键都是 Set<小写词头>，共用 keyOf，零迁移。 */
const RKEY = "cet_vocab_review_v1";
let review = new Set();
try { review = new Set(JSON.parse(localStorage.getItem(RKEY) || "[]")); } catch (e) {}
let rSaveTimer = null;
function saveReview(){
  clearTimeout(rSaveTimer);
  rSaveTimer = setTimeout(() => {
    try { localStorage.setItem(RKEY, JSON.stringify([...review])); } catch (e) {}
  }, 220);
}

/* ---------- 分区折叠 ----------
   每天各记各的、四级/六级各记各的：「第 3 天收起四级」既不影响第 4 天，
   也不影响同一天收起六级。两边都展开时把这一天整个删掉，所以展开态不留痕迹。

   用途只有一个：喂给「当天检测」。收起哪边，当天检测就只考没收起的那边。
   配置弹层里的「复习库 / 全部 / 已掌握」是跨全表的范围，和当前这页显示什么无关，不受影响。

   键里的天序号是位置量（和 cet_vocab_day 一样），换 --daysize 重建后天的划分会变，
   已折叠的天会跟着错位。这是「这一页显示成什么样」的视图状态，不是挂在词上的进度，
   所以既不像 mastered/review 那样按词头存，也不跟着导出走（折叠态两次都没进过导出格式）。 */
const FKEY = "cet_vocab_fold_v1";
let fold = {};
try {
  const raw = JSON.parse(localStorage.getItem(FKEY) || "{}");
  for (const k in raw){
    const d = +k, v = raw[k];
    if (d >= 0 && d < DAYS.length && v && typeof v === "object" && (v.c4 || v.c6))
      fold[d] = { c4: !!v.c4, c6: !!v.c6 };
  }
} catch (e) {}
function foldOf(day){ return fold[day] || { c4: false, c6: false }; }
function isFolded(day, isC6){ const f = foldOf(day); return isC6 ? f.c6 : f.c4; }
function toggleFold(day, isC6){
  const f = foldOf(day);
  if (isC6) f.c6 = !f.c6; else f.c4 = !f.c4;
  if (f.c4 || f.c6) fold[day] = f; else delete fold[day];
  try { localStorage.setItem(FKEY, JSON.stringify(fold)); } catch (e) {}
  render();
}

/* ---------- 战场记录（决战已通过的方向） ----------
   形如 {"abandon": ["spell"]}：键 = 小写词头（同 mastered / review），值 = 已通过的方向。
   「一场决战里每个词只考一个方向，两个方向跨场累计」要成立，就必须把「哪个方向过了」
   记在词上——只放在内存里的话，中途退出或换个晚上再来，上一场过的方向就没了。

   只在「过了一个方向、还没双向通过」时才有条目：双向通过当场出库，条目同时删掉，
   所以这张表永远只有半场的词，是小的。

   它是**进度**不是视图状态（对比折叠态）：挂在词上而不是挂在页上，换 --daysize 重建后
   照样能用，也因此跟着导出走（格式 ver 3）。 */
const BKEY = "cet_vocab_battle_v1";
const BTYPES = ["spell", "mean"];
let battlePass = {};                      // { 词头小写: ["spell", ...] }
try {
  const raw = JSON.parse(localStorage.getItem(BKEY) || "{}");
  if (raw && typeof raw === "object" && !Array.isArray(raw))
    Object.keys(raw).forEach(k => {
      const list = [...new Set((Array.isArray(raw[k]) ? raw[k] : []).filter(x => BTYPES.indexOf(x) >= 0))];
      if (list.length && list.length < BTYPES.length) battlePass[k] = list;   // 双向齐的条目不该存在
    });
} catch (e) {}
function saveBattle(){
  try { localStorage.setItem(BKEY, JSON.stringify(battlePass)); } catch (e) {}
}
function passedDirs(k){ return battlePass[k] || []; }
/* 记/撤一个方向。撤空了就把整条删掉，表里不留空壳 */
function setDirPassed(k, type, on){
  const cur = new Set(passedDirs(k));
  if (on) cur.add(type); else cur.delete(type);
  if (cur.size) battlePass[k] = BTYPES.filter(t => cur.has(t));   // 固定按 BTYPES 顺序，导出可比
  else delete battlePass[k];
  saveBattle();
}
function battleCount(){ return Object.keys(battlePass).length; }

/* ---------- 主题 ---------- */
const tBtn = document.getElementById("themeBtn");
function applyTheme(t){
  if (t) document.documentElement.setAttribute("data-theme", t);
  else document.documentElement.removeAttribute("data-theme");
  const dark = t === "dark" || (!t && matchMedia("(prefers-color-scheme: dark)").matches);
  tBtn.innerHTML = dark ? "&#9790;" : "&#9788;";
}
let theme = null;
try { theme = localStorage.getItem("cet_vocab_theme") || null; } catch (e) {}
applyTheme(theme);
tBtn.onclick = () => {
  const dark = document.documentElement.getAttribute("data-theme") === "dark" ||
               (!document.documentElement.getAttribute("data-theme") &&
                matchMedia("(prefers-color-scheme: dark)").matches);
  theme = dark ? "light" : "dark";
  try { localStorage.setItem("cet_vocab_theme", theme); } catch (e) {}
  applyTheme(theme);
};
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (!theme) applyTheme(null); });

/* ---------- 朗读 ---------- */
let voice = null;
function pickVoice(){
  const vs = speechSynthesis.getVoices() || [];
  voice = vs.find(v => /en[-_]US/i.test(v.lang)) || vs.find(v => /^en/i.test(v.lang)) || null;
}
if ("speechSynthesis" in window){ pickVoice(); speechSynthesis.onvoiceschanged = pickVoice; }
function say(text){
  if (!("speechSynthesis" in window)) return;
  const clean = text.replace(/\(.*?\)/g, "").split("/")[0].replace(/[^A-Za-z' \-]/g, " ").trim();
  if (!clean) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(clean);
  u.lang = "en-US"; u.rate = .9;
  if (voice) u.voice = voice;
  speechSynthesis.speak(u);
}

/* ---------- 渲染一天 ---------- */
let cur = 0;
const content = document.getElementById("content");
const esc = s => s.replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const keyOf = w => w.w.toLowerCase();

/* 派生词一行一条：词形 + 音标 + 释义。数据层从第 14 版起存成 {w, cn, ipa} 对象；
   旧 words.json 里还是纯字符串，这里兼容两种形态（字符串只渲染词形）——重建数据前
   页面照样能开，不会因为字段缺失整块不渲染。 */
function derivHTML(w){
  const list = w.deriv;
  if (!list || !list.length) return "";
  const rows = list.map(d => {
    const o = (typeof d === "string") ? { w: d } : (d || {});
    const nm = esc(o.w || "");
    const ipa = o.ipa ? '<span class="dv-ipa">/' + esc(o.ipa) + "/</span>" : "";
    const cn = o.cn ? '<span class="dv-cn">' + esc(o.cn) + "</span>" : "";
    return '<span class="dv"><span class="dv-w">' + nm + "</span>" + ipa + cn + "</span>";
  }).join("");
  return '<div class="deriv"><b>派生</b>' + rows + "</div>";
}

function cardHTML(w, idx){
  const done = mastered.has(keyOf(w));
  const inrev = review.has(keyOf(w));
  const dv = derivHTML(w);
  return '<div class="card' + (w.cet6 ? " c6" : "") + (done ? " done" : "") + (inrev ? " inreview" : "")
       +   '" data-i="' + idx + '">'
       +   '<div class="body">'
       +     '<div class="line1">'
       +       '<span class="word" data-say="' + esc(w.w) + '">' + esc(w.w) + "</span>"
       +       (w.ipa ? '<span class="ipa">/' + esc(w.ipa) + "/</span>" : "")
       +     "</div>"
       +     '<div class="cn">' + esc(w.cn || "—") + "</div>"
       +     dv
       +   "</div>"
       +   '<div class="ctl">'
       +     '<button class="star" type="button" aria-pressed="' + (inrev ? "true" : "false")
       +       '" aria-label="复习库" title="' + (inrev ? "从复习库移除" : "加入复习库") + '">'
       +       '<svg viewBox="0 0 24 24"><path d="M9.362,9.158c0,0-3.16,0.35-5.268,0.584c-0.19,0.023-0.358,0.15-0.421,0.343s0,0.394,0.14,0.521 c1.566,1.429,3.919,3.569,3.919,3.569c-0.002,0-0.646,3.113-1.074,5.19c-0.036,0.188,0.032,0.387,0.196,0.506 c0.163,0.119,0.373,0.121,0.538,0.028c1.844-1.048,4.606-2.624,4.606-2.624s2.763,1.576,4.604,2.625 c0.168,0.092,0.378,0.09,0.541-0.029c0.164-0.119,0.232-0.318,0.195-0.505c-0.428-2.078-1.071-5.191-1.071-5.191 s2.353-2.14,3.919-3.566c0.14-0.131,0.202-0.332,0.14-0.524s-0.23-0.319-0.42-0.341c-2.108-0.236-5.269-0.586-5.269-0.586 s-1.31-2.898-2.183-4.83c-0.082-0.173-0.254-0.294-0.456-0.294s-0.375,0.122-0.453,0.294C10.671,6.26,9.362,9.158,9.362,9.158z"/></svg>'
       +     "</button>"
       +     '<div class="tick"><input type="checkbox" id="k' + idx + '"' + (done ? " checked" : "") + ">"
       +       '<label for="k' + idx + '"></label></div>'
       +   "</div>"
       + "</div>";
}

function render(){
  const day = DAYS[cur];
  const base = cur * DATA.daySize;              // 全表连续序号，避免每次 indexOf 全表查找
  const c4 = [], c6 = [];
  day.forEach((w, j) => (w.cet6 ? c6 : c4).push([w, base + j]));
  let html = "";
  const sec = (list, cls, title) => {
    if (!list.length) return "";                  // 这天没有这个级别的词 → 整块不出现，也就没得折
    const lv = cls === "s6" ? "c6" : "c4";
    const folded = isFolded(cur, lv === "c6");
    // 折叠时卡片一张都不渲染（不是藏起来），标题行留着好展开回来
    return '<section class="sec ' + cls + '">'
         + '<div class="sec-head"><span class="dot ' + lv + '"></span>'
         +   '<h2 class="fh"><button class="fold" type="button" data-lv="' + lv + '"'
         +     ' aria-expanded="' + (folded ? "false" : "true") + '" aria-controls="secbody-' + lv + '"'
         +     ' title="' + (folded ? "展开" : "收起") + title + '（当天检测只考没收起的那边）">'
         +     title + '<span class="cnt">' + list.length + " 词" + (folded ? " · 已折叠" : "") + "</span>"
         +     '<span class="chev"></span>'
         +   "</button></h2></div>"
         + '<div class="secbody" id="secbody-' + lv + '">'
         + (folded ? "" : list.map(([w, i]) => cardHTML(w, i)).join(""))
         + "</div></section>";
  };
  html += sec(c4, "s4", "四级词汇");
  html += sec(c6, "s6", "六级词汇");
  content.innerHTML = html;

  document.getElementById("day").value = cur;
  document.getElementById("prev").disabled = cur === 0;
  document.getElementById("next").disabled = cur === DAYS.length - 1;
  const testable = dayTestable();
  document.getElementById("todayMeta").textContent =
    "第 " + (cur + 1) + " 天 / 共 " + DAYS.length + " 天 · 本页 " + day.length + " 词"
    + (testable < day.length ? " · 可考 " + testable + " 词" : "");
  try { localStorage.setItem("cet_vocab_day", cur); } catch (e) {}
  updateProgress();
  syncDayQuizBtn();
}

/* 这一天折完之后还剩多少词可考。挂机提示和「当天检测」按钮共用，免得两处算法走偏 */
function dayTestable(){ return poolOf("today", cur).length; }
function syncDayQuizBtn(){
  const n = dayTestable(), b = document.getElementById("dayQuizBtn");
  b.disabled = n === 0;
  b.title = n ? "检测当前这一天的 " + n + " 词"
              : "本页的词已全部被折叠，没有可考的词";
}

function updateProgress(){
  const day = DAYS[cur];
  const dDone = day.filter(w => mastered.has(keyOf(w))).length;
  document.getElementById("progAll").textContent = "已掌握 " + mastered.size + " / " + TOTAL;
  document.getElementById("progDay").textContent = "本日 " + dDone + " / " + day.length;
  document.getElementById("barFill").style.width = (TOTAL ? mastered.size / TOTAL * 100 : 0) + "%";
  document.getElementById("reviewCnt").innerHTML = "复习库 <b>" + review.size + "</b> 词";
}

/* 把复习库状态同步到当前已渲染的卡片上（★ 与 .inreview） */
function syncCards(){
  content.querySelectorAll(".card").forEach(c => {
    const k = keyOf(wordOfIndex(+c.dataset.i));
    const on = review.has(k);
    c.classList.toggle("inreview", on);
    const b = c.querySelector(".star");
    if (b){
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.title = on ? "从复习库移除" : "加入复习库";
    }
  });
  updateProgress();
}

/* ---------- 交互 ---------- */
content.addEventListener("click", e => {
  const f = e.target.closest(".fold");
  if (f){ toggleFold(cur, f.dataset.lv === "c6"); return; }   // toggleFold 里会重新 render
  const star = e.target.closest(".star");
  if (star){
    const card = star.closest(".card");
    const k = keyOf(wordOfIndex(+card.dataset.i));
    const on = !review.has(k);           // 再点一次 = 出库
    setReview(k, on);                    // 记一条加入 / 移出（真正变化才记）
    star.setAttribute("aria-pressed", on ? "true" : "false");
    star.title = on ? "从复习库移除" : "加入复习库";
    card.classList.toggle("inreview", on);
    saveReview(); updateProgress();
    return;
  }
  const word = e.target.closest(".word");
  if (word) say(word.dataset.say);
});
const wordOfIndex = i => DATA.days[Math.floor(i / DATA.daySize)][i % DATA.daySize];
// 用 change 而不是 click：点 <label> 时事件目标是 label，click 处理器不会触发
content.addEventListener("change", e => {
  const cb = e.target.closest('input[type="checkbox"]');
  if (!cb) return;
  const card = cb.closest(".card");
  const w = wordOfIndex(+card.dataset.i);
  setMastered(keyOf(w), cb.checked);     // 打 ✓ = 加入、取消 ✓ = 移出，各记一条
  card.classList.toggle("done", cb.checked);
  save(); updateProgress();
});

const sel = document.getElementById("day");
DAYS.forEach((d, i) => {
  const o = document.createElement("option");
  o.value = i;
  o.textContent = "第 " + (i + 1) + " 天（" + d.length + " 词）";
  sel.appendChild(o);
});
sel.onchange = () => { cur = +sel.value; render(); window.scrollTo({ top: 0, behavior: "smooth" }); };
document.getElementById("prev").onclick = () => { if (cur > 0){ cur--; render(); window.scrollTo({top:0,behavior:"smooth"}); } };
document.getElementById("next").onclick = () => { if (cur < DAYS.length - 1){ cur++; render(); window.scrollTo({top:0,behavior:"smooth"}); } };
document.getElementById("totalLabel").textContent = TOTAL + " 词 · " + DAYS.length + " 天";

/* ---------- 搜索（常驻 40px 长条 + 浮层结果，不推挤内容） ---------- */
const panel = document.getElementById("panel");
const q = document.getElementById("q"), res = document.getElementById("res");
let selIdx = -1, hits = [];

/* ---------- 搜索历史（本机持久化；记录「打开过的那个词」，最多 20 条） ----------
   存的是词头（小写）而不是当初敲进去的搜索串：搜「放弃」和搜 abandon 打开的是同一张卡片，
   历史里就该只有 abandon 一条，显示它的音标/词性/释义——而不是两串查询词。
   和 mastered / review 一样存词头而非序号，换 --daysize 重建后照样能用。 */
const HKEY = "cet_vocab_search_hist_v1", HIST_MAX = 20;
const HEAD = new Map();                       // 小写词头 -> ALL 下标
ALL.forEach((w, i) => { const k = keyOf(w); if (!HEAD.has(k)) HEAD.set(k, i); });
let hist = [];                                // [{w: 小写词头, t: 时间戳}]
try {
  const _h = JSON.parse(localStorage.getItem(HKEY) || "[]");
  if (Array.isArray(_h)) hist = _h.map(x => {
    if (!x) return null;
    // v1 老记录存的是搜索串（{q}）。英文搜索串多半就是词头，能对上就留；中文搜索串对不上，丢掉
    const k = typeof x.w === "string" ? x.w
            : (typeof x.q === "string" ? x.q.trim().toLowerCase() : "");
    if (!k || !HEAD.has(k)) return null;
    return { w: k, t: typeof x.t === "number" ? x.t : 0 };
  }).filter(Boolean).slice(0, HIST_MAX);
} catch (e) {}
/* 历史里能落到词卡上的那些（词头在本版词表里找不到的会被跳过） */
function histRows(){
  const out = [];
  hist.forEach(h => { const i = HEAD.get(h.w); if (i !== undefined) out.push({ w: h.w, i: i }); });
  return out;
}
let hTimer = null;
function saveHist(){
  clearTimeout(hTimer);
  hTimer = setTimeout(() => { try { localStorage.setItem(HKEY, JSON.stringify(hist)); } catch (e) {} }, 220);
}
function addHist(i){
  const w = ALL[i];
  if (!w) return;
  const k = keyOf(w);
  hist = hist.filter(x => x.w !== k);          // 已存在则提到最前
  hist.unshift({ w: k, t: Date.now() });
  if (hist.length > HIST_MAX) hist.length = HIST_MAX;
  saveHist();
}
function delHist(k){
  hist = hist.filter(x => x.w !== k);
  saveHist();
}

function openSearch(){
  panel.classList.add("on");
  q.value = ""; q.focus(); doSearch("");
}
function closeSearch(){
  panel.classList.remove("on");
  // 收起后焦点还留在输入框里，键盘快捷键会被 typing 判断吃掉
  if (document.activeElement && document.activeElement !== document.body) document.activeElement.blur();
}
document.getElementById("searchBtn").onclick = openSearch;
const HIST_ICON = '<span class="hic"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7.5V12l3 2"/></svg></span>';
let qstr = "";                                 // 当前查询串，供高亮与截窗用

/* 命中高亮：逐段 esc 再包 <mark>——整串 esc 会把标签一起转义掉，整串不 esc 又会把用户输入当 HTML。
   用 indexOf 而不是正则：查询串里的 . * ( ) 不必再操心转义。 */
function hl(text, query){
  text = text || "";
  if (!query) return esc(text);
  const tl = text.toLowerCase(), ql = query.toLowerCase();
  let out = "", from = 0, at;
  while ((at = tl.indexOf(ql, from)) >= 0){
    out += esc(text.slice(from, at)) + "<mark>" + esc(text.slice(at, at + ql.length)) + "</mark>";
    from = at + ql.length;
  }
  return out + esc(text.slice(from));
}
/* 中文释义截断：以命中处为中心开窗，两端补省略号。
   原先一律切前 46 字——实测 333 个词的释义长过 46 字（最长 91，如 turn / pitch），
   命中词落在后半段时，用户看到的那一截里根本没有他要找的字。 */
const CN_WIN = 46;
function cnSnippet(cn, query){
  cn = cn || "";
  if (cn.length <= CN_WIN) return cn;
  const at = query ? cn.toLowerCase().indexOf(query.toLowerCase()) : -1;
  if (at < 0) return cn.slice(0, CN_WIN);
  let s = Math.max(0, at - ((CN_WIN - query.length) >> 1));
  if (s + CN_WIN > cn.length) s = cn.length - CN_WIN;
  return (s > 0 ? "…" : "") + cn.slice(s, s + CN_WIN) + (s + CN_WIN < cn.length ? "…" : "");
}
function resultsHTML(){
  return hits.map((i, n) => {
    const w = ALL[i];
    return '<div class="row' + (n === 0 ? " sel" : "") + '" data-i="' + i + '">'
         + '<span class="word" style="font-size:15px">' + hl(w.w, qstr) + "</span>"
         + '<span class="cn2">' + hl(cnSnippet(w.cn, qstr), qstr) + "</span>"
         + '<span class="d">第 ' + (Math.floor(i / DATA.daySize) + 1) + " 天</span></div>";
  }).join("");
}
function historyHTML(rows){
  return '<div class="res-head"><span>搜索历史 · 点一下回到那个词</span>'
    + '<button class="hclear" type="button" id="histClear">清空</button></div>'
    + rows.map((r, n) => {
        const w = ALL[r.i];
        return '<div class="row hist' + (n === 0 ? " sel" : "") + '" data-i="' + r.i + '">'
        + HIST_ICON + '<span class="hw">' + esc(w.w) + "</span>"
        + (w.ipa ? '<span class="hipa">/' + esc(w.ipa) + "/</span>" : "")
        + '<span class="hcn">' + esc(w.cn || "") + "</span>"
        + '<button class="hx" type="button" data-del="' + esc(r.w)
        + '" title="删除这条记录" aria-label="删除这条搜索记录">&#10005;</button></div>';
      }).join("");
}
/* 相关性分档。原先「凑够 300 条就停」有两个毛病：常见词上直接截断，
   而且结果顺序完全等于词表顺序——搜 abandon 时 abandonable 排在 abandon 前面。
   现在先全表扫一遍打分，再排序取前 300。同档内保持词表原序（显式按 i 兜底，
   不依赖 sort 是否稳定）。 */
const RES_MAX = 300;
function doSearch(s){
  s = (s || "").trim();
  qstr = s;
  hits = [];
  if (s){
    const sl = s.toLowerCase();
    const scored = [];
    for (let i = 0; i < ALL.length; i++){
      const w = ALL[i];
      const hw = w.w.toLowerCase(), cn = (w.cn || "").toLowerCase();
      let sc = 0;
      if (hw === sl) sc = 1000;              // 词头完全相同
      else if (hw.indexOf(sl) === 0) sc = 600;   // 词头前缀
      else if (hw.indexOf(sl) >= 0) sc = 400;    // 词头中间
      else if (cn === sl) sc = 300;              // 释义完全相同
      else if (cn.indexOf(sl) >= 0) sc = 200;    // 释义里出现
      if (sc) scored.push({ i: i, sc: sc });
    }
    scored.sort((a, b) => b.sc - a.sc || a.i - b.i);
    hits = scored.slice(0, RES_MAX).map(x => x.i);
    selIdx = hits.length ? 0 : -1;
    res.innerHTML = hits.length ? resultsHTML() : '<div class="empty">没有匹配的单词</div>';
  } else {
    const rows = histRows();
    selIdx = rows.length ? 0 : -1;
    res.innerHTML = rows.length ? historyHTML(rows) : '<div class="empty">输入关键词开始搜索</div>';
  }
}
let hcTimer = null;
function disarmClearHist(){
  clearTimeout(hcTimer);
  const b = document.getElementById("histClear");
  if (b){ b.classList.remove("armed"); b.textContent = "清空"; }
}
/* 清空历史：两段式确认，与复习库清空一致，防误触 */
function clearHistClick(){
  const b = document.getElementById("histClear");
  if (!b) return;
  if (!b.classList.contains("armed")){
    b.classList.add("armed"); b.textContent = "确认清空？";
    clearTimeout(hcTimer);
    hcTimer = setTimeout(disarmClearHist, 3000);
    return;
  }
  hist = []; saveHist(); doSearch("");
}
q.oninput = () => { panel.classList.add("on"); doSearch(q.value); };
q.onfocus = () => { panel.classList.add("on");
  if (!q.value.trim() && !res.querySelector(".row")) doSearch("");
};
q.onkeydown = e => {
  if (e.key === "ArrowDown"){ e.preventDefault(); moveSel(1); }
  else if (e.key === "ArrowUp"){ e.preventDefault(); moveSel(-1); }
  else if (e.key === "Enter"){
    const rows = res.querySelectorAll(".row");
    const r = rows[Math.max(selIdx, 0)];
    if (!r) return;
    const i = +r.dataset.i;
    addHist(i);                       // 历史行的回车也算「又用了一次」，提到最前
    goto(i);
  }
};
function moveSel(d){
  const rows = res.querySelectorAll(".row");
  if (!rows.length) return;
  selIdx = (selIdx + d + rows.length) % rows.length;
  rows.forEach((r, n) => r.classList.toggle("sel", n === selIdx));
  if (rows[selIdx]) rows[selIdx].scrollIntoView({ block: "nearest" });
}
res.onclick = e => {
  if (e.target.closest("#histClear")){ clearHistClick(); return; }
  const x = e.target.closest(".hx");
  if (x){ delHist(x.dataset.del); doSearch(""); q.focus(); return; }
  const r = e.target.closest(".row");
  if (!r) return;
  const i = +r.dataset.i;
  addHist(i);                        // 只有真正跳到词卡才入历史（复习库面板的「跳过去」不算）
  goto(i);
};
function goto(i){
  if (!(i >= 0 && i < ALL.length)) return;
  cur = Math.floor(i / DATA.daySize);
  q.value = ""; hits = []; selIdx = -1;
  closeSearch(); render();
  const card = content.querySelector('.card[data-i="' + i + '"]');
  if (card){ card.scrollIntoView({ block: "center", behavior: "smooth" }); card.classList.add("flash"); }
}
// 点到搜索区外就收起下拉
document.addEventListener("click", e => {
  if (!e.target.closest || !e.target.closest(".searchwrap")) panel.classList.remove("on");
});

/* ══════════ 判分规则（spec §6） ══════════ */
const normEn = s => s.toLowerCase().replace(/[^a-z]/g, "");
const normCn = s => s.replace(/[\s,.。，、；;:：!！?？"'“”‘’()（）]/g, "");

/* ══════════ 判分记忆（申诉过的答案） ══════════
   用户点过「我写对了」的中文答案记在这里，下次写同一串就直接判对，不再重复报错。

   只服务**认义题（英译汉）**：一个英文词可以有好几种说得通的中文写法
   （「放弃」/「遗弃」/「放弃遗弃」），判错未必是用户错，所以给一个人工出口。
   拼写题不走这条路——拼写题的答案集由 spellAnswers() 唯一确定（「显示所有汉语后，
   唯一一个英语答案也确定了」），「我写对了」在那里没有立足点；词头记法没编码到的
   合法变体改由 build_data.py 的 SPELL_VARIANTS 点名补进答案集，不留给用户逐次申诉。
   **第 7 版曾让拼写题也记**（那时是 `normAns(type)` 按题型选规范化函数），第 8 版整块删除。

   只记答案本身（规范化后逐字相同才算），不做任何模糊——判分上的假阳性会污染复习库，
   那是用户判断该重背哪些词的唯一依据；模糊的余地留给「我写对了」这个按钮，人是最终裁定者。
   误判风险趋近于零：这串字只有用户自己敲得出来。

   键是小写词头（同 mastered / review），所以换 --daysize 重建后照样能用。 */
const AKEY = "cet_vocab_appeals_v1";
let appeals = {};                        // { 词头小写: [规范化后的答案, ...] }
try {
  const raw = JSON.parse(localStorage.getItem(AKEY) || "{}");
  if (raw && typeof raw === "object" && !Array.isArray(raw))
    Object.keys(raw).forEach(k => {
      if (Array.isArray(raw[k])){
        const list = raw[k].filter(x => typeof x === "string" && x);
        if (list.length) appeals[k] = list;
      }
    });
} catch (e) {}
let aSaveTimer = null;
function saveAppeals(){
  clearTimeout(aSaveTimer);
  aSaveTimer = setTimeout(() => {
    try { localStorage.setItem(AKEY, JSON.stringify(appeals)); } catch (e) {}
  }, 220);
}
/* 认义答案的规范化：去空格、去中英标点。「放弃, 遗弃」和「放弃遗弃」算同一串。
   第 7 版这里还有一层按题型分的 normAns(type)（拼写题走 normEn），第 8 版拼写申诉
   拿掉后就没有第二种来源了，直接传 normCn。 */
/* 记一条。返回 false = 没记（空答案 / 只有标点 / 这个词已经记过同一串） */
function rememberAnswer(k, input, norm){
  const a = norm((input || "").trim());
  if (!a) return false;
  const list = appeals[k] || (appeals[k] = []);
  if (list.indexOf(a) >= 0) return false;      // 已经有同一条 → 不记，也不刷新时间戳
  list.push(a);
  opSet(aKey(k, a), true);                     // 判分记忆的对象是「词头 + 这一条答案」
  saveAppeals();
  return true;
}
/* 查一条。命中返回当初存下的那串（反馈里回显用），否则 null */
function acceptedAnswer(k, input, norm){
  const a = norm((input || "").trim());
  if (!a) return null;
  const list = appeals[k];
  return list && list.indexOf(a) >= 0 ? a : null;
}
/* 忘掉一条。返回是否真删掉了 */
function forgetAnswer(k, a){
  const list = appeals[k];
  const i = list ? list.indexOf(a) : -1;
  if (i < 0) return false;
  list.splice(i, 1);
  if (!list.length) delete appeals[k];
  opSet(aKey(k, a), false);                    // 取消的是这一条答案，同词的其它答案不动
  saveAppeals();
  return true;
}
function apCount(o){ let n = 0; Object.keys(o).forEach(k => { n += o[k].length; }); return n; }

/* ══════════ 操作日志（数据同步搬的就是它） ══════════
   三样进度（已掌握 / 复习库 / 判分记忆）的每一次「加入 / 移出」在这里留一条，
   **同步搬的是这份日志，不是当前的集合**。只搬集合的话移出就丢了：
   对面的旧状态会把这边刚出库的词救回来。

   每个对象只保留时间更晚的那一次操作：更晚的加入压过更早的移出，更晚的移出压过更早的加入。
   移出之后又加入，同步后要回来。所以既不是并集，也不是「移出过就永久拉黑」。

   对象粒度：
     · 已掌握 / 复习库 —— 一个小写词头一条（前缀 m: / r:）
     · 判分记忆       —— 一个「小写词头 + 规范化后的那一条答案」一条（前缀 a:，词头与答案用 \n 隔）
       同一个词的不同答案互不影响。

   只在状态**真正变化**时记：已经在库里再答错、同一条判分记忆再记一次，都不刷新时间戳
   （记了就会压过另一台更晚的操作）。时间一律 Date.now()——设备时钟严重不准时快的那台会赢，
   这是接受的取舍，不做向量钟。 */
const OKEY = "cet_vocab_ops_v1";
const K_M = "m:", K_R = "r:", K_A = "a:";      // 已掌握 / 复习库 / 判分记忆
const ASEP = "\n";                             // 判分记忆的键里，词头与答案的分隔
const AP_MAX = 20;                             // 每个词最多保留 20 条仍生效的答案
let ops = {};                                  // { 对象键: {op: "add"|"del", t: 时间戳} }
let oSaveTimer = null;
function saveOps(){
  clearTimeout(oSaveTimer);
  oSaveTimer = setTimeout(() => { try { localStorage.setItem(OKEY, JSON.stringify(ops)); } catch (e) {} }, 220);
}
function aKey(k, a){ return K_A + k + ASEP + a; }
/* 记一次操作。返回是否真记了——状态没变就不记，也不刷新时间戳 */
function opSet(key, on, t){
  const cur = ops[key];
  if (cur && cur.op === (on ? "add" : "del")) return false;
  ops[key] = { op: on ? "add" : "del", t: (typeof t === "number" ? t : Date.now()) };
  saveOps();
  return true;
}
function opOn(key){ const o = ops[key]; return !!o && o.op === "add"; }
/* 三样进度的唯一入口：先记日志，再把派生集合改到一致。返回是否真的变了 */
function setMastered(k, on){
  if (!opSet(K_M + k, on)) return false;
  if (on) mastered.add(k); else mastered.delete(k);
  save(); return true;
}
function setReview(k, on, t){
  if (!opSet(K_R + k, on, t)) return false;
  if (on) review.add(k); else review.delete(k);
  saveReview(); return true;
}
/* 清空复习库 = 当时库里每一个词各写一条移出（同一个时间戳），
   不是一个全局水位——水位会把另一台更晚才加入的词也清掉 */
function clearReview(){
  const t = Date.now();
  [...review].forEach(k => setReview(k, false, t));
}
/* 合并两份日志：同一对象只留时间戳更大的那条；时间戳相同而一加一移时**算加入**（平局不丢）。
   这里没有任何「本机优先 / 导入方优先」的偏向，两边对向同步的结果必须一样 */
function mergeOps(base, list){
  const out = {};
  for (const k in base) out[k] = { op: base[k].op, t: base[k].t };
  (list || []).forEach(o => {
    if (!o || typeof o.k !== "string") return;
    if (o.op !== "add" && o.op !== "del") return;
    if (typeof o.t !== "number" || !isFinite(o.t)) return;
    const c = out[o.k];
    if (!c || o.t > c.t || (o.t === c.t && o.op === "add")) out[o.k] = { op: o.op, t: o.t };
  });
  return out;
}
/* 日志 -> 三个派生集合。mastered / review / appeals 永远由它重算，界面只读它们 */
function rebuildFromOps(map){
  const m = new Set(), r = new Set(), list = [];
  Object.keys(map).forEach(k => {
    if (map[k].op !== "add") return;
    const kind = k.slice(0, 2);
    if (kind === K_M) m.add(k.slice(2));
    else if (kind === K_R) r.add(k.slice(2));
    else if (kind === K_A){
      const i = k.indexOf(ASEP, 2);
      if (i > 2) list.push({ w: k.slice(2, i), a: k.slice(i + 1), t: map[k].t });
    }
  });
  // 同一词下的答案按加入时间排（时间戳相同就按答案排），保证两台设备导出的数据逐字相同
  list.sort((x, y) => (x.t - y.t) || (x.a < y.a ? -1 : x.a > y.a ? 1 : 0));
  const byWord = {};
  list.forEach(x => { (byWord[x.w] || (byWord[x.w] = [])).push(x); });
  const ap = {};
  Object.keys(byWord).forEach(w => {
    const arr = byWord[w];
    // 每个词最多 20 条仍生效的答案，超过时留加入时间最新的 20 条（日志本身不动）
    ap[w] = (arr.length > AP_MAX ? arr.slice(arr.length - AP_MAX) : arr).map(x => x.a);
  });
  return { mastered: m, review: r, appeals: ap };
}
function deriveCounts(map){
  const d = rebuildFromOps(map);
  return { m: d.mastered.size, r: d.review.size, a: apCount(d.appeals) };
}
/* 导出用的日志：按键排序，同一份数据两次导出逐字相同（「来回导两次结果不变」的前提） */
function opsList(map){ return Object.keys(map).sort().map(k => ({ k: k, op: map[k].op, t: map[k].t })); }

/* 读日志；没有就说明是升级后第一次打开 —— 把库里现有成员各记一条「加入」，时间戳一律 0。
   用 0 而不是迁移时的 Date.now()：后打开新版本的那台会把残留成员盖成新的加入，
   把另一台升级后已经记下的移出冲掉（那台的移出时间戳必然大于 0，但用「现在」就等于凭空变晚，
   早晚关系全乱）。代价是「更新前已经移出、另一台却还留着的词」第一次同步仍会回来——认了。
   不在库里的词不补移出：那等于凭空制造一条「本机删过」的记录。 */
(function loadOps(){
  ops = {};
  let raw = null, ok = false;
  try { raw = localStorage.getItem(OKEY); } catch (e) {}
  if (raw !== null){
    try {
      const p = JSON.parse(raw);
      if (p && typeof p === "object" && !Array.isArray(p)){
        Object.keys(p).forEach(k => {
          const o = p[k];
          if (o && (o.op === "add" || o.op === "del") && typeof o.t === "number" && isFinite(o.t))
            ops[k] = { op: o.op, t: o.t };
        });
        ok = true;                      // 哪怕是个空对象也认：清空过的库本来就该是空的
      }
    } catch (e) {}
  }
  if (!ok){
    mastered.forEach(k => { ops[K_M + k] = { op: "add", t: 0 }; });
    review.forEach(k => { ops[K_R + k] = { op: "add", t: 0 }; });
    Object.keys(appeals).forEach(k => { appeals[k].forEach(a => { ops[aKey(k, a)] = { op: "add", t: 0 }; }); });
    try { localStorage.setItem(OKEY, JSON.stringify(ops)); } catch (e) {}
  }
  const d = rebuildFromOps(ops);
  mastered = d.mastered; review = d.review; appeals = d.appeals;
})();

/* 拼写题答案集——只从词头 w.w 展开，派生词不进答案集（题干带词性前缀，本就排除了派生词） */
function spellAnswers(head){
  const set = new Set();
  const add = x => { const n = normEn(x); if (n) set.add(n); };
  add(head);                                             // 1. 基础
  const m = /^(.*?)\((.*?)\)(.*)$/.exec(head);            // 2. A(B)C → A+C、A+B+C
  if (m){ add(m[1] + m[3]); add(m[1] + m[2] + m[3]); }
  const k = head.indexOf("/");                            // 3. A/B
  if (k >= 0){
    const A = head.slice(0, k), B = head.slice(k + 1);
    add(A);
    if (B.charAt(0) === "-") add(A.slice(0, A.length - B.length + 1) + B.slice(1));
    else add(B);
  }
  /* 4. 点名补的拼写变体（analogue 认 analog、vigor 认 vigour）。
     上面三种记法都是从词头字符串推出来的，而词头记的是英式拼法，推不出的合法变体
     就永远落在答案集外面。第 7 版拿判分记忆让用户逐次申诉盖过去，第 8 版把那条路
     整块删了，缺口改由 build_data.py 的 SPELL_VARIANTS 在数据层点名补——所以这里
     查的是 DATA.spellAlt（它跟着 words.json 一起嵌进页面，verify_data.py 会断言两边相等）。
     别把这里改成通用英美互转规则：实测那会放进 32 个假词（four -> for），真词只有 3 个。 */
  const extra = (DATA.spellAlt || {})[head];
  if (extra) extra.forEach(add);
  return set;
}

/* 认义题义项表：剥掉全部词性标记（不只开头那个）→ 去括号内容 → 按 [,，;；、] 切分 */
function meanItems(cn){
  let s = (cn || "");
  s = s.replace(/[（(][^）)]*[）)]/g, "");
  /* 词性标记本身就是义项分界——`n. 破产者 a. 破产的` 两个义项之间只有空格没有逗号，
     所以剥词性时补一个「，」顶上再切分，连写记法（vt.vi.）也一并吃掉。
     旧版只剥开头一个前缀，中间的 a./vt. 全留在义项里：「破产者 a. 破产的」整段粘成
     一个义项，normCn 后带着字母 a，用户写「破产者，破产的」（normCn 后没有 a）
     永远精确匹配失败——2026-09-27 五张 bug 截图（bait/banner/bare/bankrupt×2）
     全是这一个根因。白名单是全表 5271 词实测出来的词性标记全集（无大写形式）。 */
  s = s.replace(/(^|[\s,，;；、])((?:abbr|adj|adv|aux|art|conj|interj|prep|pron|pref|num|pl|vt|vi|n|v|int|a)\.)+(?=\s|$)/g,
                (m, p1) => p1 + "，");
  return s.split(/[,，;；、]/).map(x => x.trim()).filter(Boolean);
}

/* 最长公共子串长度 */
function lcsLen(a, b){
  if (!a || !b) return 0;
  let best = 0, prev = new Array(b.length + 1).fill(0);
  for (let i = 1; i <= a.length; i++){
    const cur = new Array(b.length + 1).fill(0);
    for (let j = 1; j <= b.length; j++){
      if (a.charAt(i - 1) === b.charAt(j - 1)){
        cur[j] = prev[j - 1] + 1;
        if (cur[j] > best) best = cur[j];
      }
    }
    prev = cur;
  }
  return best;
}

/* 认义题判分：输入含分隔符就拆开，任一义项命中即对；判错时找「部分匹配」 */
const PARTIAL_MIN = 2;   // spec §6.4：共享 ≥2 个连续汉字才算部分匹配
function meanGrade(cn, input){
  const items = meanItems(cn);
  const normed = items.map(normCn).filter(Boolean);
  const cands = [];
  const whole = normCn(input);
  if (whole) cands.push(whole);
  input.split(/[,，;；、\s]+/).forEach(p => {
    const n = normCn(p);
    if (n && cands.indexOf(n) < 0) cands.push(n);
  });
  for (let i = 0; i < normed.length; i++){
    if (cands.indexOf(normed[i]) >= 0) return { ok: true, hit: items[i], partial: null };
  }
  let best = null;
  for (let c = 0; c < cands.length; c++){
    for (let i = 0; i < normed.length; i++){
      const L = lcsLen(cands[c], normed[i]);
      if (L >= PARTIAL_MIN && (!best || L > best.len)) best = { item: items[i], len: L };
    }
  }
  return { ok: false, hit: null, partial: best };
}

/* 测试与复用入口（等价于页面内的判分路径） */
function spellOK(head, input){ return spellAnswers(head).has(normEn(input)); }
function meanOK(cn, input){ return meanGrade(cn, input).ok; }

/* ══════════ 检测：配置 → 逐题作答 → 结果 ══════════ */
const SCOPES = { review: { label: "复习库" }, all: { label: "全部" }, mastered: { label: "已掌握" } };
/* 结果页范围文案。当天检测不在 SCOPES 里（它不进配置弹层），自带天数 */
/* 折叠态是现算的，不是开局快照：结果页的「再测 N 题」本来就按 poolOf 现算池子，
   文案跟着现算才对得上。答题页是全屏的，做题期间折不了，所以两者不会打架。 */
const scopeLabel = c => {
  if (c.scope !== "today") return SCOPES[c.scope].label;
  const f = foldOf(c.day);
  const only = f.c4 && !f.c6 ? " · 仅六级" : (f.c6 && !f.c4 ? " · 仅四级" : "");
  return "第 " + (c.day + 1) + " 天" + only;
};
const TYPES  = { spell: "看中文写英文", mean: "看英文写中文", mixed: "混合" };
const TTAG   = { spell: "拼写", mean: "认义" };

const mask = document.getElementById("mask"), cfgBox = document.getElementById("cfg");
const scopeSegs = document.getElementById("scopeSegs"), typeSegs = document.getElementById("typeSegs");
const qNum = document.getElementById("qNum"), qNumHint = document.getElementById("qNumHint");
const qEmpty = document.getElementById("qEmpty"), qStart = document.getElementById("qStart");
const qscreen = document.getElementById("qscreen"), qBody = document.getElementById("qBody");
const qIdx = document.getElementById("qIdx"), qBar = document.getElementById("qBar");

const CFG = { scope: "review", type: "spell" };   // 题数只从输入框读，默认 20
let quiz = null;        // { items, i, cfg, t0 }

function poolOf(scope, day){
  if (scope === "review")   return ALL.filter(w => review.has(keyOf(w)));
  if (scope === "mastered") return ALL.filter(w => mastered.has(keyOf(w)));
  if (scope === "today")    return (DAYS[day] || []).filter(w => !isFolded(day, w.cet6)); // 头部「当天检测」用，day 来自 cfg
  return ALL.slice();
}

function openCfg(){ refreshCfg(); mask.classList.add("on"); cfgBox.classList.add("on"); }
function closeCfg(){
  mask.classList.remove("on"); cfgBox.classList.remove("on");
  if (document.activeElement && document.activeElement !== document.body) document.activeElement.blur();
}
function refreshCfg(){
  const pool = poolOf(CFG.scope);
  const max = Math.min(pool.length, 200);          // 上限 = min(范围内词数, 200)
  const counts = { review: review.size, all: TOTAL, mastered: mastered.size };
  scopeSegs.querySelectorAll(".seg").forEach(b => {
    b.textContent = SCOPES[b.dataset.v].label + "（" + counts[b.dataset.v] + "）";
    b.classList.toggle("on", b.dataset.v === CFG.scope);
  });
  typeSegs.querySelectorAll(".seg").forEach(b => b.classList.toggle("on", b.dataset.v === CFG.type));
  qNum.max = String(Math.max(max, 1));
  const raw = qNum.value.trim();
  if (raw !== ""){
    let v = parseInt(raw, 10);
    if (isNaN(v) || v < 1) v = 1;
    if (max >= 1 && v > max) v = max;
    qNum.value = String(v);
  }
  qNumHint.textContent = max >= 1
    ? "题 · 范围内共 " + pool.length + " 词，最多可抽 " + max + " 题"
    : "题 · 范围内没有可抽的词";
  const empty = pool.length === 0;
  qStart.disabled = empty;
  qEmpty.style.display = empty ? "block" : "none";
  qEmpty.textContent = CFG.scope === "review"
    ? "复习库是空的，先背几天或选其它范围"
    : "这个范围内还没有词，换个范围试试";
}

document.getElementById("quizBtn").onclick = openCfg;
document.getElementById("qCancel").onclick = closeCfg;
mask.onclick = () => { closeCfg(); closeRev(); closeSync(); };   // 三个弹层共用一块遮罩，同时只开一个
scopeSegs.addEventListener("click", e => {
  const b = e.target.closest(".seg"); if (!b) return;
  CFG.scope = b.dataset.v; qNum.value = "20"; refreshCfg();
});
typeSegs.addEventListener("click", e => {
  const b = e.target.closest(".seg"); if (!b) return;
  CFG.type = b.dataset.v; refreshCfg();
});
qNum.oninput = refreshCfg;
qNum.onchange = refreshCfg;
qStart.onclick = () => {
  const pool = poolOf(CFG.scope);
  const max = Math.min(pool.length, 200);
  if (!max) return;
  const n = Math.min(Math.max(parseInt(qNum.value, 10) || 20, 1), max);
  closeCfg();
  startQuiz(buildItems(pool, n, CFG.type), { scope: CFG.scope, type: CFG.type, count: n });
};

/* 头部「当天检测」：一键考当前翻到的那天（DAYS[cur]）没被折叠的那些词，全考 + 洗牌 + 混合题型，
   绕过配置弹层。cfg.day 记下当时是哪一天，供结果页标注与「再测 N 题」定位。
   这天是哪几个词由 poolOf("today", cur) 现算——用户折起哪边，这里就不考哪边。 */
document.getElementById("dayQuizBtn").onclick = () => {
  const pool = poolOf("today", cur);
  if (!pool.length) return;                       // 按钮同时也被 syncDayQuizBtn 置灰
  startQuiz(buildItems(pool, pool.length, "mixed"),
            { scope: "today", type: "mixed", count: pool.length, day: cur });
};

/* ══════════ 复习库管理面板 ══════════
   出库只由用户手动操作（卡片 ★ / 这里）——检测答对不再自动移出，
   所以库只会按用户的意愿收缩，不会自己漏词。 */
const revBox = document.getElementById("rev");
const revList = document.getElementById("revList");
const revTotal = document.getElementById("revTotal");
const revClear = document.getElementById("revClear");
let revTimer = null;

/* 按全表原序（= 天序）返回库里词的下标，和词表本身的顺序一致 */
function revIdx(){
  const out = [];
  for (let i = 0; i < ALL.length; i++) if (review.has(keyOf(ALL[i]))) out.push(i);
  return out;
}
function disarmClear(){
  clearTimeout(revTimer); revTimer = null;
  revClear.classList.remove("armed");
  revClear.textContent = "清空复习库";
}
function renderRev(){
  const idx = revIdx();
  revTotal.textContent = "· " + idx.length + " 词";
  revClear.disabled = !idx.length;
  disarmClear();
  battleGrp.style.display = idx.length ? "block" : "none";
  battleStartBtn.disabled = !idx.length;
  battleNum.disabled = !idx.length;
  battleNum.max = String(Math.max(idx.length, 1));
  battleNum.value = String(idx.length);
  battleNumHint.textContent = idx.length
    ? "词 · 随机抽取，两个方向跨场累计，都通过才出库"
    : "";
  revList.innerHTML = idx.length ? idx.map(i => {
    const w = ALL[i];
    return '<div class="revrow" data-i="' + i + '">'
         + '<span class="w">' + esc(w.w) + "</span>"
         + (w.ipa ? '<span class="ipa">/' + esc(w.ipa) + "/</span>" : "")
         + '<span class="cn2">' + esc(w.cn || "—") + "</span>"
         + '<span class="d">第 ' + (Math.floor(i / DATA.daySize) + 1) + " 天</span>"
         + '<button class="x" type="button" data-del="' + i
         + '" title="从复习库移除" aria-label="从复习库移除">&#10005;</button></div>';
  }).join("") : '<div class="empty">复习库是空的 · 在卡片上点 ★ 加入</div>';
}
function openRev(){
  renderRev();
  mask.classList.add("on"); revBox.classList.add("on");
}
function closeRev(){
  revBox.classList.remove("on"); disarmClear();
  if (!cfgBox.classList.contains("on")) mask.classList.remove("on");
}
document.getElementById("revBtn").onclick = openRev;
document.getElementById("revClose").onclick = closeRev;
revList.addEventListener("click", e => {
  const x = e.target.closest(".x");
  if (x){                                          // 移除后不关面板，方便连着清几个
    setReview(keyOf(ALL[+x.dataset.del]), false);
    saveReview(); syncCards(); renderRev();
    return;
  }
  const row = e.target.closest(".revrow");
  if (row){ closeRev(); goto(+row.dataset.i); }     // 跳过去看原卡片
});
/* 两段式确认，不用 confirm()——jsdom 不实现它，用它这条路径就成了测试盲区 */
revClear.onclick = () => {
  if (!revClear.classList.contains("armed")){
    revClear.classList.add("armed");
    revClear.textContent = "再点一次，清空 " + review.size + " 词";
    revTimer = setTimeout(disarmClear, 3000);
    return;
  }
  clearReview(); syncCards(); renderRev();
};

/* ══════════ 决战复习库 ══════════
   从复习库随机抽 N 个词进入决战。**一场就是一张一次性题列：每个词恰好一题、只考一个方向**
   （第 11 版起），所以同一个词在一场里最多出现一次——「汉译英 + 英译汉」两个方向
   分摊在至少两场里累计，都通过了才出库。

   · 方向怎么定：这个词两个方向都没过 → 随机；已经过了一个 → 必考另一个
   · 答对 → 记下「这个方向过了」（落盘 cet_vocab_battle_v1）
   · 两个方向都过 → **当场移出复习库**，战场记录同时删掉。这是决战唯一的出库路径
   · 答错 / 跳过 → 什么都不记，词仍在库里；重考要等**下一场**，不是同场再来一次
   · 题列走和检测同一套导航模型（上一题 / 重新答题，见 renderQuestion 上面那段）。
     区别只在「答对」的账：检测是「进不进复习库」，决战是「记哪个方向」

   第 10 版曾明确不给决战加导航，理由是「随机抽词、无固定顺序、同一个词反复出现，
   回退到上一题在那里没有对应物」。第 11 版把出题改成题列之后那条理由就不成立了。 */
const BTAG = { spell: "汉译英", mean: "英译汉" };
const battleGrp = document.getElementById("battleGrp");
const battleNum = document.getElementById("battleNum");
const battleNumHint = document.getElementById("battleNumHint");
const battleStartBtn = document.getElementById("battleStart");
let battle = null;

function shuffleArr(a){
  for (let i = a.length - 1; i > 0; i--){
    const j = Math.floor(Math.random() * (i + 1));
    const t = a[i]; a[i] = a[j]; a[j] = t;
  }
  return a;
}
function battleCur(){ return battle ? battle.items[battle.i] : null; }
/* 一个词这场考哪个方向：过了一个就必考另一个，两个都没过就随机。
   两个都过的词早就出库了，不会出现在题列里。 */
function dirForWord(k){
  const done = passedDirs(k);
  return done.length === 1 ? BTYPES.filter(t => done.indexOf(t) < 0)[0]
                           : (Math.random() < 0.5 ? "spell" : "mean");
}
function buildBattleItems(words){
  return words.map(w => ({
    w: w, type: dirForWord(keyOf(w)),
    verdict: null, input: "", skipped: false, partial: null,
    cleared: false, appealed: false, recalled: null, remembered: false
  }));
}
function startBattle(words){
  battle = { items: buildBattleItems(words), i: 0, n: words.length,
             answered: 0, redo: false, t0: Date.now() };
  closeRev();
  mask.classList.remove("on");
  qscreen.classList.add("on");
  renderBattleQuestion();
}
battleStartBtn.onclick = () => {
  const idx = revIdx();
  if (!idx.length) return;
  let n = parseInt(battleNum.value, 10);
  if (isNaN(n) || n < 1) n = 1;
  if (n > idx.length) n = idx.length;
  startBattle(shuffleArr(idx.map(i => ALL[i])).slice(0, n));
};
/* 进度条按「已经出库了几个词」走——出库是这场唯一的结果，只过了一个方向不算数。
   直接查 review 而不是另记一个计数器：重答把某个词放回库里时，这个数字会跟着退回去。 */
function battleHead(){
  let done = 0;
  battle.items.forEach(it => { if (!review.has(keyOf(it.w))) done++; });
  qIdx.textContent = "决战复习库 · 已出库 " + done + " / " + battle.n + " 词";
  qBar.style.width = (done / battle.n * 100) + "%";
}
function renderBattleQuestion(){
  const it = battleCur();
  if (!it){ battle.i = battle.items.length; finishBattle(); return; }
  battle.answered++;
  battleHead();
  const ph = it.type === "spell" ? "输入英文…" : "输入中文意思…";
  const hint = it.type === "spell"
    ? "回车提交 · 一场里每个词只考一个方向，两个方向都通过后才出库 · 拼不出可跳过（视为未通过）"
    : "写出任意一个义项即可，多个义项用逗号隔开也算对 · 一场里每个词只考一个方向";
  qBody.innerHTML = '<div class="qcard">' + stemHTML(it, "决战复习库")
    + '<div class="qin"><input id="qi" placeholder="' + ph + '" autocomplete="off" spellcheck="false">'
    + '<button class="primary" type="button" id="qSubmit">提交</button>'
    + '<button type="button" id="qSkip">跳过</button>'
    // 第 1 题没有上一题；重答中也给——点它就是放弃重答（不提交则旧结论不变）
    + (battle.i > 0 ? '<button type="button" id="qPrev">上一题</button>' : "")
    + "</div>"
    + '<div class="qhint">' + hint + "</div></div>";
  const box = document.getElementById("qi");
  if (box) box.focus();
}
function battleJudge(it){
  const txt = (it.input || "").trim();
  it.recalled = null;
  if (!txt) return { ok: false, partial: null };
  // 拼写题不查判分记忆（和 grade() 一致）。注意 !txt 守卫必须留在最前面：
  // 空串去查表是白查，而且空答案的结果必须始终是 {ok:false, partial:null}
  if (it.type === "spell") return { ok: spellAnswers(it.w.w).has(normEn(txt)), partial: null };
  const a = acceptedAnswer(keyOf(it.w), txt, normCn);
  if (a){ it.recalled = a; return { ok: true, partial: null }; }
  const g = meanGrade(it.w.cn, txt);
  return { ok: g.ok, partial: g.partial || null };
}
/* 记账。决战里「答错」没有任何副作用（词本来就在库里），所以判错时不需要撤账；
   「答对」的账唯一可能被推翻的路径是重答，而重答只在判错时给（battleRedo 的守卫）。
   两头一夹：battleApply 只会被调用一次，不需要 battleUnapply 那样的镜像函数。
   注意这跟检测不一样——检测判错会顺手把词塞进复习库，所以那边必须能撤。 */
function battleApply(it){
  if (it.verdict !== "ok") return;              // 答错不记账：词本来就在库里，重考要等下一场
  const k = keyOf(it.w);
  setDirPassed(k, it.type, true);
  if (passedDirs(k).length === BTYPES.length){  // 两个方向齐了 → 出库（决战唯一的出库路径）
    setReview(k, false); delete battlePass[k]; saveBattle(); syncCards();
    it.cleared = true;
  }
}
/* 下面两个守卫里的 `&& !battle.redo` 不能省，理由同 submitAnswer：
   重答期间 verdict 还是上一轮的结论，只看 verdict 会把「重新答题」当成已作答挡掉。 */
function battleSubmit(){
  const it = battleCur();
  if (!it || (it.verdict && !battle.redo)) return;
  const box = document.getElementById("qi");
  it.input = box ? box.value.trim() : "";
  it.skipped = false;
  battle.redo = false;
  const g = battleJudge(it);
  it.verdict = g.ok ? "ok" : "bad";
  it.partial = g.partial;
  battleApply(it);
  renderBattleFeedback();
}
function battleSkip(){
  const it = battleCur();
  if (!it || (it.verdict && !battle.redo)) return;
  it.input = ""; it.skipped = true;
  battle.redo = false;
  it.verdict = "bad"; it.partial = null;
  battleApply(it);
  renderBattleFeedback();
}
function battleAppeal(){
  const it = battleCur();
  if (!it || it.verdict !== "bad") return;
  if (it.type === "spell") return;      // 拼写题没有申诉入口（按钮也不渲染），这行是兜底
  const k = keyOf(it.w);
  it.verdict = "ok"; it.appealed = true; it.partial = null;
  it.remembered = rememberAnswer(k, it.input, normCn);
  battleApply(it);                      // 改判为对 → 走正常记账（可能就此出库）
  renderBattleFeedback();
}
function renderBattleFeedback(){
  const it = battleCur();
  battleHead();
  const ok = it.verdict === "ok";
  const ans = it.type === "spell" ? it.w.w : (it.w.cn || "—");
  const raw = it.skipped ? "" : it.input;
  let sub;
  if (ok){
    const dir = it.type === "spell" ? "汉译英通过" : "英译汉通过";
    if (it.recalled) sub = "按你之前确认过的答案判对";
    else if (it.forgotten) sub = "这条记忆已取消 · 下次写这个答案会正常判错";
    else sub = it.type === "mean" ? "你写的是「" + esc(raw) + "」· " + dir : dir;
    if (it.remembered) sub += " · 已记住这个答案";
    sub += it.cleared ? " · 两个方向均已通过，已移出复习库"
                      : " · 这个词还差另一个方向，下一场决战必考它";
  } else {
    sub = "你写的是「" + (raw ? esc(raw) : "（跳过）") + "」· " + BTAG[it.type]
        + "未通过，这个词仍在复习库，重考要等下一场";
  }
  const extra = !ok && it.type === "mean" && it.partial
    ? '<div class="part">你写的「' + esc(raw) + '」与义项「' + esc(it.partial.item)
      + '」部分匹配 · 如果是同义表达，点「我写对了」</div>'
    : ok && it.recalled
    ? '<div class="recall">这句是你之前确认过的答案 · 不想再自动判对？'
      + '<button type="button" class="forget" id="qForget">取消这条记忆</button></div>'
    : "";
  const last = battle.i === battle.items.length - 1;
  qBody.innerHTML = '<div class="qcard">' + stemHTML(it, "决战复习库")
    + '<div class="fb ' + (ok ? "ok" : "bad") + '">'
    +   '<span class="mark">' + (ok ? "&#10003;" : "&#10007;") + "</span>"
    +   '<div class="txt"><span class="ans">' + esc(ans) + '</span><div class="sub">' + sub + "</div>" + extra + "</div>"
    +   (battle.i > 0 ? '<button type="button" id="qPrev">上一题</button>' : "")
    // 拼写题不给申诉按钮：答案集唯一确定，「我写对了」没有立足点（第 8 版起）
    +   (ok || it.type === "spell" ? "" : '<button type="button" id="qAppeal">我写对了</button>')
    // 重答只在判错时给，和检测一致（答对时重答的唯一效果是把自己改错）
    +   (ok ? "" : '<button type="button" id="qRedo">重新答题</button>')
    +   '<button type="button" id="qNext">' + (last ? "查看结果" : "下一词") + "</button>"
    + "</div></div>";
}
function battleNext(){
  if (!battle) return;
  battle.redo = false;
  battle.i++;
  if (battle.i >= battle.items.length){ finishBattle(); return; }
  battleShowCurrent();
}
/* 回退：`battle.i` 左边恒为已作答的题（往前走必须先把当前这题提交或跳过），
   所以退回去撞上的永远是判分页，不会是空白题——和检测的 prevQuestion 同一条性质。 */
function battlePrev(){
  if (!battle || battle.i <= 0) return;
  battle.redo = false;
  battle.i--;
  renderBattleFeedback();
}
/* 重新答题：不清 verdict，只把这一题重新显示成答题页。什么都不用重置——
   用户不提交就退出的话旧结论原样生效；而重答只可能从「判错」出发（上一轮没记任何账），
   提交后按新结论正常记一次就是全部。 */
function battleRedo(){
  const it = battleCur();
  if (!it || it.verdict !== "bad") return;   // 按钮本来就不渲染（答对时不给），这行是兜底
  battle.redo = true;
  renderBattleQuestion();
}
function battleShowCurrent(){
  const it = battleCur();
  if (!it) return;
  if (it.verdict) renderBattleFeedback(); else renderBattleQuestion();
}
/* 走完题列 = 本场决战结束。出库在每道题答对那一刻就已经当场做了，这里只负责结算页——
   所以「走到底」和「中途退出」的差别只是有没有看到这张结算页，已通过的记录两边都已落盘。 */
function finishBattle(){
  renderBattleResult();
}
function battleTimeTxt(){
  const sec = Math.max(1, Math.round((Date.now() - battle.t0) / 1000));
  return sec >= 60 ? Math.floor(sec / 60) + " 分 " + (sec % 60) + " 秒" : sec + " 秒";
}
function renderBattleResult(){
  const n = battle.n, items = battle.items;
  const wrongs = items.filter(it => it.verdict === "bad");
  const cleared = items.filter(it => !review.has(keyOf(it.w)));                     // 本场出库的
  const half = items.filter(it => it.verdict === "ok" && review.has(keyOf(it.w)));  // 只过了一个方向
  qIdx.textContent = "决战完成";
  qBar.style.width = "100%";
  let html = '<div class="res-score">'
    + '<div class="big">' + cleared.length + "<em> / " + n + " 词</em></div>"
    + '<div class="lbl">本场 ' + n + " 词，出库 " + cleared.length + " 个（两个方向均已通过）"
    + (half.length ? " &nbsp;·&nbsp; 只过一个方向 " + half.length + " 个，下一场必考另一个" : "")
    + " &nbsp;·&nbsp; 共答 " + battle.answered + " 题 &nbsp;·&nbsp; 用时 " + battleTimeTxt() + "</div>"
    + '<div class="split">'
    +   "<span>复习库剩余 <b>" + review.size + "</b> 词</span>"
    +   '<span class="sep"></span><span>本场未通过 <b>' + wrongs.length + "</b> 词</span>"
    + "</div></div>";
  html += '<div class="rbtns">';
  if (review.size) html += '<button class="btn primary" type="button" id="bAgain">继续决战剩余 ' + review.size + " 词</button>";
  html += '<button class="btn' + (review.size ? "" : " primary") + '" type="button" id="rClose">返回列表</button></div>';
  html += '<div class="res-bk"><div class="sec-head"><span class="dot" style="background:var(--bad)"></span>'
    + '<h2>本场未通过（词仍在复习库，下一场可再考）</h2><span class="cnt">' + wrongs.length + " 词</span></div>";
  html += wrongs.length
    ? wrongs.map(it => '<div class="wrongrow"><span class="mt">' + BTAG[it.type] + "</span>"
        + '<span class="w">' + esc(it.w.w) + "</span>"
        + '<span class="you">' + (it.input ? "你写：" + esc(it.input) : "跳过未答") + "</span>"
        + '<span class="cn2">' + esc(it.w.cn || "") + "</span></div>").join("")
    : '<div class="empty" style="padding:14px">本场没有答错的题</div>';
  html += "</div>";
  qBody.innerHTML = html;
}
function battleAgain(){
  if (!battle) return;
  const idx = revIdx();
  if (!idx.length){ exitBattle(); return; }
  startBattle(idx.map(i => ALL[i]));
}
function exitBattle(){
  battle = null;
  qscreen.classList.remove("on");
  syncCards();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function buildItems(pool, n, type){
  const p = pool.slice();
  for (let i = p.length - 1; i > 0; i--){            // 无放回随机抽 N 个
    const j = Math.floor(Math.random() * (i + 1));
    const t = p[i]; p[i] = p[j]; p[j] = t;
  }
  return p.slice(0, n).map(w => ({
    w: w,
    type: type === "mixed" ? (Math.random() < 0.5 ? "spell" : "mean") : type,
    verdict: null, input: "", skipped: false, appealed: false,
    partial: null, addedByAnswer: false, recalled: null, remembered: false
  }));
}

function startQuiz(items, cfg){
  if (!items.length) return;
  quiz = { items: items, i: 0, cfg: cfg, t0: Date.now(), redo: false };
  qscreen.classList.add("on");
  renderQuestion();
}

function quizHead(){
  const n = quiz.items.length;
  qIdx.textContent = "第 " + (quiz.i + 1) + " 题 / " + n;
  qBar.style.width = ((quiz.i + 1) / n * 100) + "%";
}
function stemHTML(it, prefix){
  const tag = (prefix ? prefix + " · " : "") + (it.w.cet6 ? "六级词汇" : "四级词汇") + " · " + TYPES[it.type];
  if (it.type === "spell")
    return '<span class="qtag">' + tag + '</span><div class="qcn">' + esc(it.w.cn || "—") + "</div>";
  return '<span class="qtag">' + tag + '</span><div class="qen"><span class="qword">' + esc(it.w.w)
       + '</span><button class="say" type="button" data-say="' + esc(it.w.w) + '" title="朗读" aria-label="朗读单词">&#128266;</button></div>';
}

/* 答题页的导航模型（第 10 版）：
   `quiz.i` 左边恒为已作答的题——只能靠「提交 / 跳过」往前推，所以「上一题」回看时
   撞上的永远是判分页，不会是空白题。结果页因此不需要新增「未作答」这一档。
   `quiz.redo` 是**视图模式**不是数据状态：点「重新答题」不清 verdict，
   只是把这一题重新显示成答题页。误点零损失（不提交就什么都没变），
   而本题的旧结论一直挂着——重答途中点「上一题」就是放弃重答，旧结论照旧生效。
   重答也是 `grade()` 唯一会被同一题调用第二次的路径，「出库」那段就靠这个前提。 */
function renderQuestion(){
  const it = quiz.items[quiz.i];
  quizHead();
  const ph = it.type === "spell" ? "输入英文…" : "输入中文意思…";
  const hint = it.type === "spell"
    ? "回车提交 · 拼不出来可以跳过"
    : "写出任意一个义项即可 · 多个义项用逗号隔开也算对 · 想不起来可跳过";
  qBody.innerHTML = '<div class="qcard">' + stemHTML(it)
    + '<div class="qin"><input id="qi" placeholder="' + ph + '" autocomplete="off" spellcheck="false">'
    + '<button class="primary" type="button" id="qSubmit">提交</button>'
    + '<button type="button" id="qSkip">跳过</button>'
    // 第 1 题没有上一题；重答中也给——点它就是放弃重答（不提交则旧结论不变）
    + (quiz.i > 0 ? '<button type="button" id="qPrev">上一题</button>' : "")
    + "</div>"
    + '<div class="qhint">' + hint + "</div></div>";
  const box = document.getElementById("qi");
  if (box) box.focus();
}

function renderFeedback(){
  const it = quiz.items[quiz.i];
  quizHead();
  const ok = it.verdict === "ok";
  const last = quiz.i === quiz.items.length - 1;
  const ans = it.type === "spell" ? it.w.w : (it.w.cn || "—");
  const raw = it.skipped ? "" : it.input;
  let sub;
  if (ok){
    if (it.recalled) sub = "按你之前确认过的答案判对";
    else if (it.forgotten) sub = "这条记忆已取消 · 下次写这个答案会正常判错";
    else if (it.appealed) sub = "已改判为答对 · 不计入错题" + (it.remembered ? " · 已记住这个答案" : "");
    else if (it.type === "spell") sub = "答对";
    else sub = "你写的是「" + esc(raw) + "」· 命中义项";
  } else {
    sub = "你写的是「" + (raw ? esc(raw) : "（跳过）") + "」· 已加入复习库";
  }
  const extra = !ok && it.type === "mean" && it.partial
    ? '<div class="part">你写的「' + esc(raw) + '」与义项「' + esc(it.partial.item)
      + '」部分匹配 · 如果是同义表达，点「我写对了」</div>'
    : ok && it.recalled
    ? '<div class="recall">这句是你之前确认过的答案 · 不想再自动判对？'
      + '<button type="button" class="forget" id="qForget">取消这条记忆</button></div>'
    : "";
  qBody.innerHTML = '<div class="qcard">' + stemHTML(it)
    + '<div class="fb ' + (ok ? "ok" : "bad") + '">'
    +   '<span class="mark">' + (ok ? "&#10003;" : "&#10007;") + "</span>"
    +   '<div class="txt"><span class="ans">' + esc(ans) + '</span><div class="sub">' + sub + "</div>" + extra + "</div>"
    +   (quiz.i > 0 ? '<button type="button" id="qPrev">上一题</button>' : "")
    // 拼写题不给申诉按钮：答案集唯一确定，「我写对了」没有立足点（第 8 版起）
    +   (ok || it.type === "spell" ? "" : '<button type="button" id="qAppeal">我写对了</button>')
    // 重答只在判错时给：答对时重答的唯一效果是把自己改错，没有动机（跳过＝判错，也给）
    +   (ok ? "" : '<button type="button" id="qRedo">重新答题</button>')
    +   '<button type="button" id="qNext">' + (last ? "查看结果" : "下一题") + "</button>"
    + "</div></div>";
}

function grade(it){
  const k = keyOf(it.w);
  const txt = (it.input || "").trim();
  let ok = false, partial = null;
  it.recalled = null;
  if (txt){
    // 拼写题不查判分记忆：它的答案集已由 spellAnswers() 唯一确定（含 spellAlt 点名的变体）。
    // 认义题才查——中文写法本来就不唯一，申诉是正当的。
    if (it.type === "spell") ok = spellAnswers(it.w.w).has(normEn(txt));
    else {
      const a = acceptedAnswer(k, txt, normCn);
      if (a){ ok = true; it.recalled = a; }
      else { const g = meanGrade(it.w.cn, txt); ok = g.ok; partial = g.partial || null; }
    }
  }
  it.partial = partial;
  if (ok){
    it.verdict = "ok";                     // 答对不出库：出库只由用户手动操作（★ / 管理面板）
    // 例外二（第 10 版起）：「重新答题」把同一题判了第二次，上一次判错时顺手入库的那条要撤销。
    // 判据和 appeal() 逐字相同（addedByAnswer），所以这不是新的自动出库路径——
    // 非重答时一题只判一次（verdict 一设，submitAnswer/skipAnswer 就挡掉了），
    // addedByAnswer 恒为 false，这段根本不会执行。本来就在库里的词不受影响。
    if (it.addedByAnswer && review.has(k)){
      setReview(k, false); it.addedByAnswer = false;
    }
  } else {
    it.verdict = "bad";                    // 答错 → 进库
    // 本来就在库里的词再答错：不记（状态没变），否则会把时间戳推后压过另一台更晚的移出
    if (!review.has(k)){ setReview(k, true); it.addedByAnswer = true; }
  }
  syncCards();
}

/* 下面两个守卫里的 `&& !quiz.redo` 不能省：重答期间 verdict 还是上一轮的结论，
   只看 verdict 会把它当成「已作答」直接挡掉，等于「重新答题」按钮点了没反应。 */
function submitAnswer(){
  const it = quiz && quiz.items[quiz.i];
  if (!it || (it.verdict && !quiz.redo)) return;
  const box = document.getElementById("qi");
  it.input = box ? box.value.trim() : "";
  it.skipped = false;
  quiz.redo = false;
  grade(it);
  renderFeedback();
}
function skipAnswer(){
  const it = quiz && quiz.items[quiz.i];
  if (!it || (it.verdict && !quiz.redo)) return;
  it.input = ""; it.skipped = true;
  quiz.redo = false;
  grade(it);
  renderFeedback();
}
function appeal(){
  const it = quiz && quiz.items[quiz.i];
  if (!it || it.verdict !== "bad") return;
  if (it.type === "spell") return;      // 拼写题没有申诉入口（按钮也不渲染），这行是兜底
  const k = keyOf(it.w);
  it.verdict = "ok"; it.appealed = true; it.partial = null;
  it.remembered = rememberAnswer(k, it.input, normCn);
  // 只撤销「本次答错顺手入库」那一条——那是个已被推翻的误判。
  // 本来就躺在库里的词不受影响：出库只由用户手动操作。
  if (it.addedByAnswer && review.has(k)){
    setReview(k, false); it.addedByAnswer = false;
  }
  syncCards();
  renderFeedback();
}
/* 就地撤销一条判分记忆。只忘掉记忆，本题已判对的结论不动——
   把判分回退成错会让「刚才还对、点一下变错」这种反直觉的事发生，代价比留一次误判大。 */
function forgetRecalled(){
  const it = battle ? battleCur() : (quiz && quiz.items[quiz.i]);
  if (!it || !it.recalled) return;
  forgetAnswer(keyOf(it.w), it.recalled);
  it.recalled = null; it.forgotten = true;
  if (battle) renderBattleFeedback(); else renderFeedback();
}
/* 前进/后退都要按「这一题答过没有」分派，不能一律 renderQuestion()：
   上一题回看之后往前翻，翻到的可能是**已经答过**的题（该显示判分页），
   也可能是从没走到过的下一题（该显示答题页）。详见 renderQuestion 上面那段模型说明。 */
function showCurrent(){
  if (quiz.items[quiz.i].verdict) renderFeedback(); else renderQuestion();
}
function nextQuestion(){
  if (!quiz) return;
  quiz.redo = false;
  if (quiz.i < quiz.items.length - 1){ quiz.i++; showCurrent(); }
  else renderResult();
}
/* 上一题。只可能在 i>0 时被调用（按钮不渲染），而 i-1 必然是答过的——
   因为往前走必须先把当前这题提交或跳过，所以这里不需要再判 verdict。 */
function prevQuestion(){
  if (!quiz || quiz.i <= 0) return;
  quiz.redo = false;
  quiz.i--;
  renderFeedback();
}
/* 重新答题：不清 verdict，只把这一题重新显示成答题页。所以这个函数什么都不用重置——
   verdict / input / partial / skipped 全留着，一旦用户不提交就退出，旧结论原样生效；
   提交时 submitAnswer() 会重新填 input、grade() 会重算 partial 和 verdict。
   addedByAnswer 更不能动：它扛着复习库的账，出库那段在 grade() 里。 */
function redoQuestion(){
  const it = quiz && quiz.items[quiz.i];
  if (!it || it.verdict !== "bad") return;    // 按钮本来就不渲染（答对时不给），这行是兜底
  quiz.redo = true;
  renderQuestion();
}

function renderResult(){
  const items = quiz.items;
  const st = { n: items.length, ok: 0, spell: { n: 0, ok: 0 }, mean: { n: 0, ok: 0 } };
  items.forEach(it => {
    const t = it.type === "spell" ? st.spell : st.mean;
    t.n++;
    if (it.verdict === "ok"){ st.ok++; t.ok++; }
  });
  const wrong = items.filter(it => it.verdict === "bad");
  const sec = Math.max(1, Math.round((Date.now() - quiz.t0) / 1000));
  const timeTxt = sec >= 60 ? Math.floor(sec / 60) + " 分 " + (sec % 60) + " 秒" : sec + " 秒";
  const acc = st.n ? Math.round(st.ok / st.n * 100) : 0;

  let html = '<div class="res-score">'
    + '<div class="big">' + st.ok + "<em> / " + st.n + "</em></div>"
    + '<div class="lbl">正确率 ' + acc + "% &nbsp;·&nbsp; 用时 " + timeTxt
    + " &nbsp;·&nbsp; 范围：" + scopeLabel(quiz.cfg)
    + " &nbsp;·&nbsp; 题型：" + TYPES[quiz.cfg.type] + "</div>"
    + '<div class="split">'
    +   "<span>看中文写英文 <b>" + st.spell.ok + " / " + st.spell.n + "</b></span>"
    +   '<span class="sep"></span>'
    +   "<span>看英文写中文 <b>" + st.mean.ok + " / " + st.mean.n + "</b></span>"
    + "</div></div>";

  // 答对不再自动出库，这里明说一句，否则用户会以为答对的词已经离开复习库了
  html += '<div class="rhint">答对的词仍留在复习库，不会自动移出 · 点顶部「★ 复习库」可随时管理</div>';

  html += '<div class="rbtns">';
  if (wrong.length) html += '<button class="btn" type="button" id="rRetryWrong">只重测这 ' + wrong.length + " 个错词</button>";
  html += '<button class="btn primary" type="button" id="rRetryAll">再测 ' + quiz.cfg.count + " 题</button>";
  html += '<button class="btn" type="button" id="rClose">返回列表</button></div>';

  html += '<div class="res-bk"><div class="sec-head"><span class="dot" style="background:var(--bad)"></span>'
    + '<h2>错题（已全部加入复习库）</h2><span class="cnt">' + wrong.length + " 词</span></div>";
  html += wrong.length
    ? wrong.map(it => '<div class="wrongrow"><span class="mt">' + TTAG[it.type] + "</span>"
        + '<span class="w">' + esc(it.w.w) + "</span>"
        + '<span class="you">你写：' + (it.input ? esc(it.input) : "—") + "</span>"
        + '<span class="cn2">' + esc(it.w.cn || "") + "</span></div>").join("")
    : '<div class="empty" style="padding:14px">这次没有错题</div>';
  html += "</div>";

  qIdx.textContent = "检测完成";
  qBar.style.width = "100%";
  qBody.innerHTML = html;
  syncCards();
}

function retryWrong(){
  if (!quiz) return;
  const items = quiz.items.filter(it => it.verdict === "bad").map(it => ({
    w: it.w, type: it.type, verdict: null, input: "", skipped: false,
    appealed: false, partial: null, addedByAnswer: false, recalled: null, remembered: false
  }));
  if (!items.length) return;
  startQuiz(items, quiz.cfg);
}
function retryAll(){
  if (!quiz) return;
  const cfg = quiz.cfg;
  const pool = poolOf(cfg.scope, cfg.day);   // 当天检测必须带上 day，否则池子为空
  const n = Math.min(cfg.count, pool.length, 200);
  if (!n){                       // 范围已经被清空，回到配置面板
    CFG.scope = cfg.scope; CFG.type = cfg.type;
    exitQuiz(); openCfg(); return;
  }
  startQuiz(buildItems(pool, n, cfg.type), cfg);
}
function exitQuiz(){
  quiz = null;
  qscreen.classList.remove("on");
  syncCards();
  window.scrollTo({ top: 0, behavior: "smooth" });
}
document.getElementById("qExit").onclick = () => { if (battle) exitBattle(); else exitQuiz(); };

qBody.addEventListener("click", e => {
  const t = e.target;
  if (battle){
    if (t.closest("#qSubmit")) return battleSubmit();
    if (t.closest("#qSkip")) return battleSkip();
    if (t.closest("#qPrev")) return battlePrev();
    if (t.closest("#qRedo")) return battleRedo();
    if (t.closest("#qNext")) return battleNext();
    if (t.closest("#qAppeal")) return battleAppeal();
    if (t.closest("#qForget")) return forgetRecalled();
    if (t.closest("#bAgain")) return battleAgain();
    if (t.closest("#rClose")) return exitBattle();
    const bsay = t.closest(".say");
    if (bsay) say(bsay.dataset.say);
    return;
  }
  if (t.closest("#qSubmit")) return submitAnswer();
  if (t.closest("#qSkip")) return skipAnswer();
  if (t.closest("#qPrev")) return prevQuestion();
  if (t.closest("#qRedo")) return redoQuestion();
  if (t.closest("#qNext")) return nextQuestion();
  if (t.closest("#qAppeal")) return appeal();
  if (t.closest("#qForget")) return forgetRecalled();
  if (t.closest("#rRetryWrong")) return retryWrong();
  if (t.closest("#rRetryAll")) return retryAll();
  if (t.closest("#rClose")) return exitQuiz();
  const s = t.closest(".say");
  if (s) say(s.dataset.say);
});
qBody.addEventListener("keydown", e => {
  if (e.key === "Enter" && e.target && e.target.id === "qi"){
    e.preventDefault();
    if (battle) battleSubmit(); else submitAnswer();
  }
});

/* ---------- 键盘 ---------- */
document.addEventListener("keydown", e => {
  if (qscreen.classList.contains("on") && (quiz || battle)){
    if (e.key === "Escape"){ if (battle) exitBattle(); else exitQuiz(); }
    return;
  }
  const typing = /^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName);
  if (e.key === "Escape"){ closeSearch(); closeCfg(); closeRev(); closeSync(); document.activeElement.blur(); return; }
  if (e.key === "/" && !typing){ e.preventDefault(); openSearch(); return; }
  if (typing) return;
  if (e.key === "ArrowLeft" && cur > 0){ cur--; render(); window.scrollTo({top:0,behavior:"smooth"}); }
  if (e.key === "ArrowRight" && cur < DAYS.length - 1){ cur++; render(); window.scrollTo({top:0,behavior:"smooth"}); }
});

/* ══════════ 数据同步（导出 / 导入合并） ══════════
   手机与电脑各有一份互不相干的 localStorage，只能靠一段 JSON 手工搬。
   搬「已掌握」「复习库」「判分记忆」的操作日志 + 「战场记录」——主题 / 当前天 / 搜索历史 /
   折叠态是本机偏好，不搬。存的是小写词头而不是下标，所以换了 --daysize 重建的清单也能对上；
   对不上的词头在导入时静默丢掉，不会灌进一个不存在的词。

   导入是「按操作日志合并」，不是覆盖也不是并集：
     · 覆盖会丢另一边的进度（手机用一点、电脑用一点时必然丢）
     · 并集会把复习库里已经移出的词救回来（另一台还留着旧状态）
     · 「加入取并集再减去历史上所有移出」是永久拉黑——出库或取消 ★ 之后又答错、又点 ★ 要能回来
   规则只有一条：**每个对象只保留时间更晚的那一次操作**（时间戳相同而一加一移时算加入，平局不丢）。
   两边对向同步的结果必须一样，所以没有「导入方优先 / 本机优先」这种规定。

   格式版本 1 = 只有 mastered / review；版本 2 起多一个 appeals；版本 3 起多一个 battle
   （决战已通过的方向）；**同一版起导出必带完整操作日志 ops**。旧版仍收：
   文件里没有日志时，把文件里有的词当成「导出那一刻仍是加入」，ts 用文件里的 ISO 时间
   （没有就用导入当时），文件里没有的词不当成移出。 */
const SYNC_APP = "cet-vocab-plan", SYNC_VER = 3;
const SYNC_VERS = [1, 2, 3];    // 认得的导出格式版本
const SYNC_TIP = "先从本机导出一份，拿到另一台设备导入并合并。";
const syncDlg = document.getElementById("sync");
const syncBox = document.getElementById("syncBox");
const syncMsg = document.getElementById("syncMsg");
const syncApply = document.getElementById("syncApply");
const syncFile = document.getElementById("syncFile");
let syncParsed = null;      // 解析通过、等待导入的那份数据；null = 无
let syncTimer = null;

/* 提示行。html 里的动态内容只有数字和本机词数，没有任何来自导入文件的原样字符串 */
function syncSay(html, cls){
  syncMsg.className = "syncmsg" + (cls ? " " + cls : "");
  syncMsg.innerHTML = html;
}
/* 撤销「再点一次」的待确认态；按钮能不能点只跟 syncParsed 走 */
function disarmSync(){
  clearTimeout(syncTimer); syncTimer = null;
  syncApply.classList.remove("armed");
  syncApply.textContent = "导入并合并";
  syncApply.disabled = !syncParsed;
}
function syncMine(){
  return "已掌握 <b>" + mastered.size + "</b> 词、复习库 <b>" + review.size
       + "</b> 词、判分记忆 <b>" + apCount(appeals) + "</b> 条、决战过半场 <b>"
       + battleCount() + "</b> 词";
}
function syncExported(txt){        // 导出后收口：文本框换成本机数据，丢弃上一条待导入结果
  syncBox.value = txt;
  syncParsed = null; disarmSync();
}
function buildSync(){
  return JSON.stringify({
    app: SYNC_APP, ver: SYNC_VER, ts: new Date().toISOString(), total: TOTAL,
    mastered: [...mastered].sort(), review: [...review].sort(), appeals: appeals,
    battle: battlePass,
    // 同步真正搬的是这份日志。上面的三个集合是给人看的、也是给还没升级的那台兜底用的
    ops: opsList(ops)
  });
}
function parseSync(raw){
  let o;
  try { o = JSON.parse(raw); } catch (e) { return { err: "不是合法的 JSON 文本" }; }
  if (!o || typeof o !== "object" || Array.isArray(o)) return { err: "这不是本词表的导出数据" };
  if (o.app !== SYNC_APP) return { err: "这不是本词表的导出文件（缺少 app 标记）" };
  if (SYNC_VERS.indexOf(o.ver) < 0) return { err: "导出文件的版本不认识，无法导入" };
  const strs = v => (Array.isArray(v) ? v : []).filter(x => typeof x === "string");
  const known = new Set(ALL.map(keyOf));
  const incoming = [];                    // 待合并的操作日志
  let drop = 0;
  /* 对象键 -> 词头。取不出词头就是坏键，丢 */
  const wordOfOp = k => {
    const kind = k.slice(0, 2);
    if (kind === K_M || kind === K_R) return k.slice(2);
    if (kind !== K_A) return null;
    const i = k.indexOf(ASEP, 2);
    return i > 2 ? k.slice(2, i) : null;
  };
  const keep = e => {                     // 对不上本机词表的词头静默丢掉，不写进一个不存在的词
    const w = wordOfOp(e.k);
    if (!w || !known.has(w.toLowerCase())){ drop++; return; }
    incoming.push({ k: e.k, op: e.op, t: e.t });
  };
  /* 1. 文件里有完整日志 → 直接拿日志来合并 */
  const log = [];
  if (Array.isArray(o.ops))
    o.ops.forEach(e => {
      if (!e || typeof e.k !== "string") return;
      if (e.op !== "add" && e.op !== "del") return;
      if (typeof e.t !== "number" || !isFinite(e.t)) return;
      log.push({ k: e.k, op: e.op, t: e.t });
    });
  const hasLog = log.length > 0;
  if (hasLog){
    log.forEach(keep);
  } else {
    /* 2. 文件里没有日志（ver 1 / 2，或还没升级的那台导出的 ver 3）——
       文件里有的词当成「导出那一刻仍是加入」，ts 用文件里的 ISO 时间（没有就用导入当时）；
       文件里没有的词一个都不当移出，否则等于拿一份旧文件把本机的新进度删掉。 */
    const ts = (typeof o.ts === "string" && isFinite(Date.parse(o.ts))) ? Date.parse(o.ts) : Date.now();
    const seed = (list, kind) => strs(list).forEach(s => {
      const k = s.toLowerCase();
      if (!known.has(k)){ drop++; return; }
      incoming.push({ k: kind + k, op: "add", t: ts });
    });
    seed(o.mastered, K_M);
    seed(o.review, K_R);
    if (o.appeals && typeof o.appeals === "object" && !Array.isArray(o.appeals))
      Object.keys(o.appeals).forEach(key => {
        const k = key.toLowerCase();
        if (!known.has(k)){ drop++; return; }
        strs(o.appeals[key]).filter(x => x.trim())
          .forEach(a => incoming.push({ k: aKey(k, a), op: "add", t: ts }));
      });
  }
  /* 战场记录：键是词头、值是已通过的方向数组。ver 1 / 2 没有这个字段，当空处理。
     双向都齐的条目直接丢掉——双向齐就等于该出库了，留一张「都过了却还在库里」的
     记录只会让下一场又把这个词抽出来。 */
  const bt = {}; let bdrop = 0;
  if (o.battle && typeof o.battle === "object" && !Array.isArray(o.battle)){
    Object.keys(o.battle).forEach(raw => {
      const k = raw.toLowerCase();
      if (!known.has(k)){ bdrop++; return; }
      const list = [...new Set(strs(o.battle[raw]).filter(x => BTYPES.indexOf(x) >= 0))];
      if (list.length && list.length < BTYPES.length) bt[k] = BTYPES.filter(t => list.indexOf(t) >= 0);
    });
  }
  return { ops: incoming, battle: bt, drop: drop + bdrop, total: o.total, legacy: !hasLog };
}
/* 解读文本框当前内容：通过 → 启用按钮并预告**合并后**的词数；不通过 → 停用按钮，本机数据不动 */
function checkSync(){
  const raw = syncBox.value.trim();
  if (!raw){ syncParsed = null; disarmSync(); syncSay(SYNC_TIP); return; }
  const p = parseSync(raw);
  if (p.err){ syncParsed = null; disarmSync(); syncSay(p.err + " &middot; 本机数据未改动", "bad"); return; }
  syncParsed = p; disarmSync();
  const now = { m: mastered.size, r: review.size, a: apCount(appeals) };
  const after = deriveCounts(mergeOps(ops, p.ops));       // 预告的是合并结果，不是导入方那一边的数
  let s = "将 <b>按最后一次操作合并</b> &middot; 已掌握 <b>" + now.m + " &rarr; " + after.m
        + "</b>，复习库 <b>" + now.r + " &rarr; " + after.r
        + "</b>，判分记忆 <b>" + now.a + " &rarr; " + after.a
        + "</b> 条，决战过半场 <b>" + battleCount() + " &rarr; " + Object.keys(p.battle).length
        + "</b> 词"
        + "<br>复习库以最后一次加入或移出为准，不是整份替换";
  if (p.legacy) s += "<br>这份文件里没有操作日志，按文件里的成员当成「导出时仍是加入」合并";
  if (p.total !== TOTAL)
    s += "<br>导出方清单共 <b>" + (typeof p.total === "number" ? p.total : "?")
       + "</b> 词，本机 <b>" + TOTAL + "</b> 词 &mdash;&mdash; 不是同一份清单，只导入两边都有的词";
  if (p.drop) s += "<br>另有 <b>" + p.drop + "</b> 个词不在本机清单里，已跳过";
  syncSay(s);
}
function applySync(){
  if (!syncParsed) return;
  if (!syncApply.classList.contains("armed")){     // 两段式确认，和「清空复习库」同一套做法
    syncApply.classList.add("armed");
    syncApply.textContent = "确认合并";
    syncTimer = setTimeout(disarmSync, 3000);
    return;
  }
  // 先并日志，再由日志重算三个派生集合——顺序不能反，反了就是覆盖
  ops = mergeOps(ops, syncParsed.ops);
  const d = rebuildFromOps(ops);
  mastered = d.mastered;
  review = d.review;
  appeals = d.appeals;
  battlePass = syncParsed.battle;
  // 丢掉挂起的防抖写入（含日志那条），直接落盘——不丢的话 220ms 后那次会把刚合并进来的值又写回去
  clearTimeout(saveTimer); clearTimeout(rSaveTimer); clearTimeout(aSaveTimer); clearTimeout(oSaveTimer);
  try {
    localStorage.setItem(KEY, JSON.stringify([...mastered]));
    localStorage.setItem(RKEY, JSON.stringify([...review]));
    localStorage.setItem(AKEY, JSON.stringify(appeals));
    localStorage.setItem(BKEY, JSON.stringify(battlePass));   // saveBattle() 不带防抖，这里直接写
    localStorage.setItem(OKEY, JSON.stringify(ops));
  } catch (e) {}
  disarmSync();
  render(); renderRev();                              // ✓ / ★ / 进度条 / 复习库面板一起刷新
  syncSay("已合并到本机 &middot; " + syncMine(), "ok");
}
function openSync(){ checkSync(); mask.classList.add("on"); syncDlg.classList.add("on"); }
function closeSync(){
  syncDlg.classList.remove("on"); disarmSync();
  if (!cfgBox.classList.contains("on") && !revBox.classList.contains("on")) mask.classList.remove("on");
}
document.getElementById("syncBtn").onclick = openSync;
document.getElementById("syncClose").onclick = closeSync;
syncApply.onclick = applySync;
syncBox.oninput = checkSync;
document.getElementById("syncCopy").onclick = () => {
  const txt = buildSync();
  syncExported(txt);
  const sum = "本机 " + syncMine();
  const cl = navigator.clipboard;
  if (cl && cl.writeText)
    cl.writeText(txt).then(
      () => syncSay(sum + " &middot; 已复制，去另一台设备粘贴", "ok"),
      () => syncSay(sum + " &middot; 浏览器不肯自动复制，请手动全选上面的文本", ""));
  else
    syncSay(sum + " &middot; 这个环境不支持自动复制，请手动全选上面的文本", "");
};
document.getElementById("syncDl").onclick = () => {
  const txt = buildSync(), sum = "本机 " + syncMine();
  syncExported(txt);
  let url = null;
  try {
    url = URL.createObjectURL(new Blob([txt], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "cet-vocab-" + new Date().toISOString().slice(0, 10) + ".json";
    document.body.appendChild(a); a.click(); a.remove();
    syncSay(sum + " &middot; 已下载，传到另一台设备用「选择文件」导入", "ok");
  } catch (e) {
    syncSay(sum + " &middot; 这个环境不支持下载，改用「复制到剪贴板」", "bad");
  }
  if (url) setTimeout(() => { try { URL.revokeObjectURL(url); } catch (e) {} }, 1000);
};
document.getElementById("syncPaste").onclick = () => {
  const cl = navigator.clipboard;
  if (!cl || !cl.readText){
    syncSay("这个环境读不了剪贴板，请手动粘贴到上面的框里", "bad"); return;
  }
  cl.readText().then(
    t => { syncBox.value = t; checkSync(); },
    () => syncSay("浏览器不肯读剪贴板，请手动粘贴到上面的框里", "bad"));
};
document.getElementById("syncPick").onclick = () => syncFile.click();
syncFile.onchange = () => {
  const f = syncFile.files && syncFile.files[0];
  if (f){
    const rd = new FileReader();
    rd.onload = () => { syncBox.value = String(rd.result || ""); checkSync(); };
    rd.onerror = () => { syncParsed = null; disarmSync(); syncSay("这个文件读不出来", "bad"); };
    rd.readAsText(f);
  }
  syncFile.value = "";        // 同一个文件连选两次也要能再次触发 change
};

/* ---------- 启动 ---------- */
try { const s = +localStorage.getItem("cet_vocab_day"); if (s >= 0 && s < DAYS.length) cur = s; } catch (e) {}
render();
</script>
</body>
</html>
"""


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    # 整份原样嵌入（含 total），保证 HTML 与 words.json 数据逐字一致
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.replace("__DATA__", payload)
    # 显式写 CRLF：不依赖 Windows 文本模式的行尾翻译，换个平台跑也是同一份字节
    with open(DST, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(html)
    print("saved -> %s  (%.1f MB)" % (DST, os.path.getsize(DST) / 1048576))


if __name__ == "__main__":
    main()
