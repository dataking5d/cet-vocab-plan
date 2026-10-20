# -*- coding: utf-8 -*-
"""交付前数据体检：words.json 内部一致性 + HTML 内嵌数据与 words.json 是否逐字一致"""
import json, re, os, collections
import ipa_uk          # 同目录：ECDICT 老记法 -> 现代英式 IPA

BASE = os.path.dirname(os.path.abspath(__file__))
J = os.path.join(BASE, "out", "words.json")
# 体检对象是本版产物，版名从 build_html.py 的 VERSION 读，改版时不用回来改这里
_ver = re.search(r'^VERSION = "(.+?)"', open(os.path.join(BASE, "build_html.py"),
                                             encoding="utf-8").read(), re.M)
assert _ver, "build_html.py 里找不到 VERSION"
H = os.path.join(BASE, "out", "四六级词汇背诵清单-%s.html" % _ver.group(1))

data = json.load(open(J, encoding="utf-8"))
days, total = data["days"], data["total"]
words = [w for d in days for w in d]

print("总词条 %d  天数 %d  每日 %d" % (total, len(days), data["daySize"]))
assert total == len(words) == sum(len(d) for d in days)

c6 = [w for w in words if w["cet6"]]
print("四级 %d  六级 %d" % (len(words) - len(c6), len(c6)))
sizes = [len(d) for d in days]
print("每日词数 中位 %d  区间 %d-%d  末天 %d" % (
    sorted(sizes)[len(sizes) // 2], min(sizes), max(sizes), sizes[-1]))
s4 = [sum(1 for w in d if not w["cet6"]) for d in days]
s6 = [sum(1 for w in d if w["cet6"]) for d in days]
print("每日四级 中位 %d 区间 %d-%d" % (sorted(s4)[len(s4)//2], min(s4), max(s4)))
print("每日六级 中位 %d 区间 %d-%d" % (sorted(s6)[len(s6)//2], min(s6), max(s6)))

print("有派生词 %d 条  派生词总数 %d" % (
    sum(1 for w in words if w["deriv"]), sum(len(w["deriv"]) for w in words)))

# --- 派生词必须是 {w, cn, ipa} 对象（第 14 版起）---
# 这一版把 deriv 从纯字符串列表升级成对象列表，好让卡片显示派生词的音标与释义。
# 三条断言分别防三种退化：退回字符串（页面只渲染词形，白改）、字段名写错（页面读到 undefined）、
# 派生词与主词同形（去重规则失效，会把主词自己列成它的派生词）。
d_objs = [d for w in words for d in w["deriv"]]
assert d_objs, "派生词列表是空的——数据层没跑出结果？"
bad_type = [(w["w"], d) for w in words for d in w["deriv"] if not isinstance(d, dict)]
assert not bad_type, "派生词不是对象: %s" % bad_type[:5]
miss_key = [(w["w"], d.get("w")) for w in words for d in w["deriv"]
            if not {"w", "cn", "ipa"} <= set(d)]
assert not miss_key, "派生词对象缺字段: %s" % miss_key[:5]
same = [(w["w"], d["w"]) for w in words for d in w["deriv"]
        if d["w"].lower() == w["w"].lower()]
assert not same, "派生词与主词同形: %s" % same[:5]
dv_cn = sum(1 for d in d_objs if d["cn"])
dv_ipa = sum(1 for d in d_objs if d["ipa"])
print("派生词补全 %d/%d 有释义   %d/%d 有音标" % (dv_cn, len(d_objs), dv_ipa, len(d_objs)))
# 覆盖率下限：ECDICT 对派生词的收录率实测很高，掉下来说明查询管线断了而不是数据本就缺
assert dv_cn >= len(d_objs) * 0.9, "派生词释义覆盖率过低: %d/%d" % (dv_cn, len(d_objs))
assert dv_ipa >= len(d_objs) * 0.9, "派生词音标覆盖率过低: %d/%d" % (dv_ipa, len(d_objs))
print("释义缺失 %d  音标缺失 %d: %s" % (
    sum(1 for w in words if not w["cn"]),
    sum(1 for w in words if not w["ipa"]),
    [w["w"] for w in words if not w["ipa"]]))

# --- 音标必须是现代英式（OALD 记法）---
# 1) 只允许 ISO 音标字符集：出现别的说明 ECDICT 的老记法漏转写了
il = [(w["w"], w["ipa"]) for w in words
      if set(w["ipa"]) - ipa_uk.ALLOWED - set("br")]      # r 只出现在 (r) 里
print("音标含非法字符 %d: %s" % (len(il), il[:6]))
assert not il, "有 ECDICT 老记法漏转写"

# 2) 美式记法残留（ʧ ʤ ɹ ɛ ɚ ɝ oʊ 与古拼法 hw）——出现即说明回退到了美式管线
ame = [w["w"] for w in words
       if set(w["ipa"]) & set("ʧʤɹɛɚɝ") or "oʊ" in w["ipa"] or "hw" in w["ipa"]]
print("美式记法残留 %d: %s" % (len(ame), ame[:6]))
assert not ame, "音标里还有美式符号"

# 3) 非儿化：r 只能出现在元音前（允许中间隔着重音符号：ˌɪntərˈækt）
v = "əɪʊɜæɑɒɔʌaeiouːˈˌ"
rho = [w["w"] for w in words if re.search(r"r(?![%s)])" % v, w["ipa"])]
print("儿化残留（r 后不接元音）%d: %s" % (len(rho), rho[:6]))

# 4) 多音节词必须标主重音
ns = [(w["w"], w["ipa"]) for w in words
      if "ˈ" not in w["ipa"] and ipa_uk.syllables(w["ipa"]) >= 2]
print("多音节但无主重音 %d: %s" % (len(ns), ns[:6]))
assert not ns, "多音节词丢了主重音"

# 重复词
low = collections.Counter(w["w"].lower() for w in words)
dup = {k: v for k, v in low.items() if v > 1}
print("重复词条 %d: %s" % (len(dup), list(dup.items())[:8]))

# 字母序倒置（源文档自带，仅统计）
inv = 0
for a, b in zip(words, words[1:]):
    if a["w"][0].lower() > b["w"][0].lower():
        inv += 1
print("相邻字母序倒置 %d 处" % inv)

# 每个词必须有非空 word
bad = [w for w in words if not w.get("w") or not re.search(r"[A-Za-z]", w["w"])]
print("空/非法词条 %d" % len(bad))
assert not bad

# 词头形态：源文档里合法的多词短语只有这几个，其余含空格的都是版面噪声粘进来的碎片
MULTIWORD_OK = {"according to", "air conditioning", "baby boom", "coup (d'état)"}
stray = [w["w"] for w in words if " " in w["w"] and w["w"] not in MULTIWORD_OK]
print("疑似粘连的多词词头 %d: %s" % (len(stray), stray[:6]))
assert not stray, "词头里有版面噪声粘进来的碎片（在 build_data.py 的 TYPO 里点名清掉）"

# 源文档错拼的修正结果：这些词头决定了拼写题认哪些拼法，被回退的话判分就反了
heads = {w["w"] for w in words}
for h in ("jail/gaol", "kilometer/-tre"):
    assert h in heads, "词头 %s 不见了——build_data.py 的 TYPO 是不是被回退了" % h
for h in ("jail/goal", "kilometer/-tre kin"):
    assert h not in heads, "错误词头 %s 又回来了（见 build_data.py 的 TYPO）" % h
print("词头修正就位: jail/gaol、kilometer/-tre；旧错形 jail/goal、kilometer/-tre kin 已消失")

# 拼写变体表：拼写题的答案集由词头记法展开，而词头记的是英式拼法，
# 记法没编码到的合法变体就落在答案集外面（analogue 不认 analog、vigor 不认 vigour）。
# 第 8 版拿掉了「拼写记忆版」的申诉路径，缺口改由这张表点名补，所以它成了判分正确性的一环。
alt = data.get("spellAlt")
assert isinstance(alt, dict), "words.json 缺 spellAlt（build_data.py 的 SPELL_VARIANTS 没烘焙进去）"
for h, vs in alt.items():
    assert h in heads, "spellAlt 的键 %s 不是词表里的词头" % h
    assert vs, "spellAlt[%s] 是空列表" % h
    for v in vs:
        # 页面是 normEn 后查表（只留 a-z），带标点的值会被静默改写，等于写了个没用的条目
        assert re.fullmatch(r"[a-z]+", v), "spellAlt[%s] 的值 %r 不是纯小写字母" % (h, v)
        assert v != h.lower(), "spellAlt[%s] 的值和词头本身重复" % h
# 实测出来的两个真缺口钉住：误删的话拼写题又会把合法变体判错，且没有申诉出口了
assert alt.get("analogue") == ["analog"], alt.get("analogue")
assert alt.get("vigor") == ["vigour"], alt.get("vigor")
print("拼写变体就位 %d 条: %s" % (len(alt), alt))

# HTML 内嵌数据 == words.json
html = open(H, encoding="utf-8").read()
m = re.search(r"const DATA = (\{.*?\});\nconst DAYS", html, re.S)
assert m, "HTML 里找不到 DATA"
embedded = json.loads(m.group(1))
same = embedded == data
print("HTML 内嵌数据与 words.json 一致: %s" % same)
if not same:
    print("  embedded total=%s days=%s / json total=%s days=%s" % (
        embedded.get("total"), len(embedded.get("days", [])), total, len(days)))
    raise SystemExit(1)

print("HTML 大小 %.1f KB" % (os.path.getsize(H) / 1024))
print("体检通过")
