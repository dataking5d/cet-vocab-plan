# -*- coding: utf-8 -*-
"""
从「四六级大纲词汇 六级有星标」docx 抽取干净词表，并补中文释义 + 英式音标。

源文档结构（已探明）：
  - 正文是一条第 a->z 的连续词表，但被拆成「普通段落」+ 21 个嵌入表格
  - 段落部分：每段一个词条，派生词用制表符分隔，行首 ★ 表示六级
  - 表格部分：PDF 转 Word 残留，空格丢失导致单词粘连（goodbye goodness goodsgoose）
             且单元格合并会重复读出内容
  - 两部分的字母区间互补，合起来才完整（单看任一部分都会漏掉 40% 的词）

用法: python build_data.py
输出: out/words.json
"""
import csv, json, re, os, gzip, collections
import docx
import wordninja
import eng_to_ipa as ipa
import cmudict
import ipa_uk

BASE = os.path.dirname(os.path.abspath(__file__))
# 优先用项目内的副本；微信文件夹随时可能被清理，原件只作兜底
SRC = os.path.join(BASE, "data", "源文档 四六级大纲词汇 六级有星标.docx")
if not os.path.exists(SRC):
    raise SystemExit(
        f"找不到源词表：{SRC}\n"
        "请把「四六级大纲词汇 六级有星标.docx」放到 data/ 目录下再运行。"
    )
ECDICT = os.path.join(BASE, "data", "ecdict.csv")
OUT = os.path.join(BASE, "out")
os.makedirs(OUT, exist_ok=True)

STAR = "\u2605"
DIGITS = "0123456789\uff10\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18\uff19"
SEP = re.compile(r"[/()\-'\u2019]")
FW = str.maketrans({"（": "(", "）": ")", "／": "/", "－": "-",
                    "\u2019": "'", "\u2018": "'", "\uff0e": "."})

# 源文档拼写错误 -> 正确拼写（逐一核对了字母序位置后确认）
TYPO = {
    "flase": "false",
    "frier": "fierce",        # 源为 ★frierce；星标挂在第一个 token 上，改完仍保留六级标记
    "comfirm": "confirm",
    "ecocystem": "ecosystem",
    "congraduate": "congratulate",
    "enrol(1)": "enrol(l)",   # OCR 把 l 认成 1
    "enrol(1)ment": "enrol(l)ment",
    # 源文档把 jail 的英式拼法写成了 goal（少一个 a）。goal「目标」在词表里另有独立词条，
    # 不修的话拼写题写 goal 判对、写 gaol 判错——正好反了
    "jail/goal": "jail/gaol",
    # 源文档版面上跟过来一个碎片 " kin"，粘在词头尾部（全表仅此一例）。
    # kin 在源文档里没有独立词条（前后是 kill / kilogram(me)/kilo / kind），是噪声不是丢词，
    # 所以直接删掉而不是 SPLIT 成两条——删了词数仍是 5271
    "kilometer/-tre kin": "kilometer/-tre",
}
# 粘连/误并成一条的，拆成多条
SPLIT = {
    "fuel(l)fulfil": ["fuel(l)", "fulfil"],
    "one oneself": ["one", "oneself"],
}
# 分词残留垃圾（已被上面的 TYPO 修复覆盖，这里兜底）
JUNK = {"ce", "e", "fl", "r", "s"}

# 派生词层的源文档录入错误：派生词在源文档里是词头**后面几格**的内容，
# 上面的 TYPO / SPLIT / JUNK 三张表全都只作用于词头本身，管不到这里，
# 所以这 4 处（全表仅此 4 处）一直潜伏着，直到派生词开始显示释义才暴露。
# 判据：把派生词拿去 ECDICT 查，查不到就是录入错了。
#   - 拼写错 2 处：complete 下的 comletion、compliment 下的 complimetary
#   - 两词粘连 2 处：源文档把两个词挤进同一格（中间只有一个空格），
#     而 ECDICT 查得到的是拆开后的两个真词——`air conditioner` / `baby boomer`
#     这类**不含**在这里，它们本身就是词组，ECDICT 有整条收录，是对的
# 修法要么并入上面的表语义（错拼 -> 改），要么拆开；这里统一成
# 「原样 -> 修正后的列表」，改拼写给一个元素、拆分给两个元素。
DERIV_FIX = {
    "comletion": ["completion"],
    "complimetary": ["complimentary"],
    "habitual habitat": ["habitual", "habitat"],
    "indignation indispensable": ["indignation", "indispensable"],
    # 源文档写 microwavable（少一个 e），ECDICT 收的是 microwaveable——查不到才会
    # 掉进 wordninja 被切碎成 micro|wav|able。对齐 ECDICT 的拼法。
    "microwavable": ["microwaveable"],
}

# 拼写题额外认的拼法：词头 -> [额外接受的拼法]。
# 拼写题的答案集由词头记法展开（页面里的 spellAnswers()：词头本身、A(B)C、A/B），
# 词头记的是英式拼法，那些记法没编码到的合法变体就全落在答案集外面。
#
# 「拼写记忆版」曾用判分记忆绕开这件事——用户写变体被判错时点一次「我写对了」，
# 下次就认。整块拿掉了（拼写题答案由 spellAnswers() 唯一确定，申诉本身站不住脚），
# 所以缺口改在这里点名补，而不是留给用户逐次申诉。
#
# 候选不是拍脑袋想的：英美互转规则套到全表 -> 用 data/ecdict.csv 滤掉规则生成的假词
# （如 four -> for），实测真缺口只有下面两个（第三个 aesthetic 是词表自身重复收录，
# 两种拼法本来就都认，不需要补）。
# 值必须是 ecdict.csv 里存在的真词，否则等于把错拼放进答案集——verify_data.py 会断言。
SPELL_VARIANTS = {
    "analogue": ["analog"],
    "vigor": ["vigour"],
}

# 美式拼写回退：英式拼法在 CMUdict 里查不到时换美式（fulfil -> fulfill）
US_SPELL = {"fulfil": "fulfill", "enrol": "enroll", "despatch": "dispatch",
            "yoghurt": "yogurt", "knowhow": "know-how", "appal": "appall",
            "instal": "install", "cigaret": "cigarette", "jewellery": "jewelry"}

DICT = set(gzip.open(
    os.path.join(os.path.dirname(os.path.abspath(wordninja.__file__)),
                 "wordninja", "wordninja_words.txt.gz"), "rt", encoding="utf-8").read().split())

# ECDICT 的全部词形（懒加载，只读一遍 62 MB）。它是分词的第二词典，而且**优先级高于 DICT**：
# wordninja 自带的词表只有约 3 万词，`microwavable` / `quantification` / `reparable` /
# `suppressive` 这类派生词全不在里面，于是被 wordninja.split() 切碎成
# micro|wav|able、quant|if|cation、re|parable——每个碎片恰好都是真词，所以"碎片不是真词"
# 这条检查抓不住它们（源文档写的是对的，是我们切错了）。
# ECDICT 有 77 万词条，这些词都在里面，所以先查它就不会切碎。
# 提前到分词阶段是因为 extract() 跑在 load_ecdict() 之前——那时候 ec 还不存在。
_EC_WORDS = None


def ec_words():
    """ECDICT 的全部小写词形集合（模块级缓存，只读一遍）。"""
    global _EC_WORDS
    if _EC_WORDS is None:
        _EC_WORDS = set()
        csv.field_size_limit(10 ** 9)
        with open(ECDICT, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                w = r["word"]
                if w:
                    _EC_WORDS.add(w.lower())
    return _EC_WORDS


suspicious = []


# ---------------------------------------------------------------- 词形清洗
def norm(w):
    """全角转半角、去尾部标点、去同形异义编号(patient１ -> patient, check２/cheque -> check/cheque)"""
    w = w.translate(FW).strip().strip(".,;:")
    w = re.sub(r"[0-9%s]+(?=/|$)" % DIGITS, "", w)
    return w.strip()


def tokenize(chunk):
    """切词。含 -/(/' 的形态（high-tech、gray/grey、hono(u)r）整体保留不切。"""
    chunk = chunk.translate(FW).strip()      # 先转半角，否则 toward（s）会被切开
    if not chunk:
        return []
    if chunk.lower() in DICT:
        return [chunk]
    if chunk.lower() in TYPO:                # 整块就是错拼词（flase -> false）
        return [TYPO[chunk.lower()]]
    if chunk.lower() in DERIV_FIX:           # 派生词层的错拼，必须在分词前修
        return list(DERIV_FIX[chunk.lower()])
    if SEP.search(chunk):
        return [chunk]
    # ECDICT 优先于 wordninja：它在 77 万词条里查得到的，就是一个完整单词，
    # 不该再被 wordninja 的 3 万词表切碎（microwavable -> micro|wav|able）。
    # 这一条必须放在 SEP 之后、split 之前——SEP 里的形态（含 - / ( '）本就该整体保留。
    if "." not in chunk and chunk.lower() in ec_words():
        return [chunk]
    pieces = wordninja.split(chunk)
    if len(pieces) <= 1:
        if chunk.lower() not in DICT and chunk.lower() not in ec_words():
            suspicious.append(chunk)
        return pieces
    if any(p.lower() not in DICT and p.lower() not in ec_words() for p in pieces):
        suspicious.append("%s -> %s" % (chunk, "|".join(pieces)))
    return pieces


def tokens_of(piece):
    out = []
    for ch in re.split(r"\s+", piece.strip()):
        if ch:
            out.extend(tokenize(ch))
    return out


def split_star(s):
    """按 ★ 切分；每个 ★ 只标记紧随其后的那一个词"""
    return [(p, i > 0) for i, p in enumerate(s.split(STAR)) if p.strip()]


def cells_dedup(tr):
    """按 w:tc 元素去重，避免合并单元格被重复读出"""
    return ["".join(n.text for n in tc.iter() if n.tag.endswith("}t")).strip()
            for tc in tr.tc_lst]


# ---------------------------------------------------------------- 抽取
def extract():
    d = docx.Document(SRC)
    paras, tables = d.paragraphs, d.tables
    entries = []
    pi = ti = 0

    for child in d.element.body.iterchildren():
        tag = child.tag.split("}")[1]

        if tag == "p":
            t = paras[pi].text.strip(); pi += 1
            if not t:
                continue
            st = t.startswith(STAR)
            raw = (t[len(STAR):] if st else t).replace(STAR, " ")
            parts = [x.strip() for x in re.split(r"\s{2,}", re.sub(r"\t+", "  ", raw)) if x.strip()]
            if not parts:
                continue
            head = norm(parts[0])                      # 段落首项是词头，其余是派生词
            deriv = [norm(x) for x in parts[1:] if norm(x)]
            if head:
                entries.append({"w": head, "cet6": st, "deriv": deriv})

        elif tag == "tbl":
            tb = tables[ti]; ti += 1
            for r in tb.rows:
                cs = cells_dedup(r._tr)
                while cs and cs[-1] == "":
                    cs.pop()
                if not cs:
                    continue
                if cs[0] in ("", STAR):                # 首列是独立的星标列
                    base, hwcell, deriv_cells = (cs[0] == STAR), cs[1], cs[2:]
                    if len(cs) < 2:
                        continue
                else:
                    base, hwcell, deriv_cells = False, cs[0], cs[1:]
                if not hwcell.strip():
                    continue

                for piece, stx in split_star(hwcell):
                    tk = tokens_of(piece)
                    # 该格只切出 1 个词头时，后面几列才确定是它的派生词；粘连格不猜
                    deriv = []
                    if len(tk) == 1:
                        for dc in deriv_cells:
                            for w in tokens_of(dc.replace(STAR, " ")):
                                w = norm(w)
                                if w and re.search(r"[A-Za-z]", w):
                                    deriv.append(w)
                    for k, w0 in enumerate(tk):
                        w = norm(w0)
                        if not w or not re.search(r"[A-Za-z]", w):
                            continue
                        entries.append({"w": w,
                                        "cet6": (stx and k == 0) or (base and k == 0),
                                        "deriv": deriv if k == 0 else []})
    return entries


def clean(entries):
    """修拼写、拆误并、去垃圾、按原文顺序去重"""
    fixed, out, seen, dropped = [], [], {}, []
    for e in entries:
        w = e["w"]
        if w in SPLIT:
            for sub in SPLIT[w]:
                fixed.append({"w": sub, "cet6": e["cet6"], "deriv": []})
            continue
        if w in JUNK and w.lower() not in ("a", "i"):
            dropped.append(w)
            continue
        # 派生词层的修正在这里就地做掉（见 DERIV_FIX 的说明）：
        # 一个原样可能对应 0 个（丢弃）、1 个（改拼写）或 2 个（拆粘连）修正结果。
        dv = []
        for x in e["deriv"]:
            for y in DERIV_FIX.get(x, [x]):
                if y not in dv:
                    dv.append(y)
        fixed.append({"w": TYPO.get(w, w), "cet6": e["cet6"], "deriv": dv})

    for e in fixed:
        k = e["w"].lower()
        if k in seen:
            tgt = out[seen[k]]
            if e["cet6"]:
                tgt["cet6"] = True
            for dv in e["deriv"]:
                if dv not in tgt["deriv"]:
                    tgt["deriv"].append(dv)
        else:
            seen[k] = len(out)
            out.append(e)
    if dropped:
        print("剔除的碎片词: %s" % collections.Counter(dropped))
    return out


# ---------------------------------------------------------------- 词典
def load_ecdict():
    """返回 (小写索引, 原样大小写集合)。后者用来判断专有名词。"""
    csv.field_size_limit(10 ** 9)
    ec, case = {}, set()
    with open(ECDICT, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            w = r["word"]
            if not w:
                continue
            ec.setdefault(w.lower(), r)
            case.add(w)
    return ec, case


def variants(w):
    """查词候选：原形 / 去可选字母括号 / 取斜杠前 / 取斜杠后 / 不同拼写"""
    k = w.lower()
    ys = [k, re.sub(r"\(.*?\)", "", k).strip(), re.sub(r"/.*$", "", k).strip(),
          re.sub(r"^.*/", "", k).strip(), re.sub(r"[^a-z]", "", k)]
    for a, b in (("é", "e"), ("è", "e"), ("ê", "e"), ("á", "a"), ("ó", "o"), ("ü", "u")):
        ys.append(k.replace(a, b))
    out, seen = [], set()
    for y in ys:
        if y and y not in seen:
            seen.add(y); out.append(y)
    return out


def lookup(ec, w):
    for v in variants(w):
        if v in ec:
            return ec[v]
    return None


ACRONYM = {"AIDS", "TV", "BBQ", "OK", "CD", "DVD", "USA", "UK", "UN", "IT", "PC"}
# 源文表格里被整段误大写的普通名词，词典恰好也收了大写形式，只能点名修正
FORCE_LOWER = {"Pole": "pole"}


def canonical_case(w, ec):
    """
    显示大小写。源文表格段落有一批词被转换过程整段大写了（Plastic/Poor/Potato），
    但同一段里也混着真专有名词（Monday/November）。用词典的规范大小写来判：
    词典存小写 -> 还原；词典存大写 -> 保留；词典查不到 -> 按小写处理。
    """
    if not w or w in ACRONYM:
        return w
    if w in FORCE_LOWER:
        return FORCE_LOWER[w]
    if not w[0].isupper():
        return w
    if w.isupper() and len(w) > 1:          # TRUE 这种被整词大写的
        return w.lower()
    r = lookup(ec, w)
    if r is None or (r["word"] or "")[:1].islower():
        return w[0].lower() + w[1:]
    return w


def tidy_translation(t):
    """ECDICT 释义：丢掉 [网络]/[医] 之类标注行，最多留 2 个词性义项"""
    if not t:
        return ""
    t = t.replace("\\n", "\n").replace("\\r", "\n").replace("\r", "\n").replace("\t", " ")
    lines = [l.strip() for l in t.split("\n") if l.strip()]
    keep = [l for l in lines if not re.match(r"^[\[【]", l)] or lines[:1]
    keep = (keep or lines[:1])[:2]
    s = re.sub(r"\s+", " ", " ".join(keep)).strip()
    return s[:90].rstrip("；;，, ") + "…" if len(s) > 90 else s


# ---------------------------------------------------------------- 音标
_CMU = cmudict.dict()
_ARPA = {"AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ",
         "EH": "ɛ", "ER": "ɝ", "EY": "eɪ", "IH": "ɪ", "IY": "i", "OW": "oʊ",
         "OY": "ɔɪ", "UH": "ʊ", "UW": "u",
         "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "F": "f", "G": "ɡ", "HH": "h",
         "JH": "dʒ", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ", "P": "p",
         "R": "ɹ", "S": "s", "SH": "ʃ", "T": "t", "TH": "θ", "V": "v", "W": "w",
         "Y": "j", "Z": "z", "ZH": "ʒ"}


_IPA_VOWELS = set("ɑæʌɔaɛeiɪouəɚɝɜ")
_ARPA_VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
                "IH", "IY", "OW", "OY", "UH", "UW"}
_IPA_VOWEL_RUN = re.compile("[ɑæʌɔaɛeiɪouəɚɝɜ]+")


def _arpa_to_ipa(phones):
    """ARPAbet -> 美式 IPA，重音符号按 CMUdict 的数字标注"""
    out, i = [], 0
    while i < len(phones):
        p = phones[i]
        m = re.fullmatch(r"([A-Z]+)([012]?)", p)
        if not m:
            i += 1; continue
        base, stress = m.group(1), m.group(2)
        if base not in _ARPA:
            i += 1; continue
        if stress in ("1", "2"):
            # 重音符号标在音节首（元音前的辅音串之前），不是元音正前方：
            # abandon 是 əˈbændən，不是 əbˈændən
            j = len(out)
            while j > 0 and out[j - 1][0] not in _IPA_VOWELS:
                j -= 1
            out.insert(j, "ˈ" if stress == "1" else "ˌ")
        sym = _ARPA[base]
        if base == "AH" and stress == "0":
            sym = "ə"
        if base == "ER" and stress == "0":
            sym = "ɚ"
        out.append(sym)
        i += 1
    return "".join(out)


def _single_ipa(w):
    """单个英文词 -> 美式音标；eng_to_ipa 优先（音素更全），退化到 CMUdict"""
    w = w.strip()
    if not w:
        return ""
    cands = [w]
    if w.lower() in US_SPELL:
        cands.append(US_SPELL[w.lower()])
    bare = w.translate(str.maketrans("éèêëáàâäóòôöíìîïúùûüç", "eeeeaaaaooooiiiiuuuuc"))
    if bare != w:                       # cliché 这种带变音符号的，去掉符号再查
        cands.append(bare)
        if bare.lower() in US_SPELL:
            cands.append(US_SPELL[bare.lower()])
    for c in cands:
        try:
            r = ipa.convert(c, keep_punct=False, stress_marks="both")
            if r and "*" not in r:
                return r
        except Exception:
            pass
    for c in cands:
        ph = _CMU.get(c.lower())
        if ph:
            return _arpa_to_ipa(ph[0])
    return ""


def _surface_forms(w):
    """可选字母括号的两种展开：hono(u)r -> honour / honor。

    **先展开式（英式拼法）后省略式**：alumin(i)um 的 aluminium 是 /ˌæljʊˈmɪnɪəm/，
    aluminum 是美式的 /əˈluːmɪnəm/；cigaret(te)/gym(nasium)/photo(graph) 同理，
    词表用的是英式拼法，展开式才是这个词条该有的读音。
    """
    out = [w]
    if "(" in w:
        out.append(re.sub(r"\((.*?)\)", r"\1", w).strip())
        out.append(re.sub(r"\(.*?\)", "", w).strip())
    res, seen = [], set()
    for x in out:
        if x and x not in seen:
            seen.add(x); res.append(x)
    return res


def _cmu_stressed_vowel(phones):
    """CMUdict 音素串里主重音落在第几个元音上（0-based）；没有主重音返回 None"""
    k = -1
    for p in phones:
        m = re.fullmatch(r"([A-Z]+)([012]?)", p)
        if not m or m.group(1) not in _ARPA_VOWELS:
            continue
        k += 1
        if m.group(2) == "1":
            return k
    return None


def _cmu_vowel_count(phones):
    return sum(1 for p in phones
               if re.fullmatch(r"([A-Z]+)([012]?)", p) and
               re.fullmatch(r"([A-Z]+)([012]?)", p).group(1) in _ARPA_VOWELS)


stress_fixed = []


def repair_stress(cur, w):
    """补主重音：eng_to_ipa 对约 70 个词整个丢了 ˈ（它的 stress_marks 开关对这些词无效），
    但它的音素比 CMUdict 完整（arise 在 CMUdict 里是 ER0 AY1 Z，丢了 r）。
    所以保留 eng_to_ipa 的音素，只按 CMUdict 的重音位次把 ˈ 插回去。
    音节数对不上就不动 —— 宁可少一个符号，不可标错位置。"""
    if not cur or "ˈ" in cur or " " in cur or "-" in cur:
        return cur
    ph = _CMU.get(US_SPELL.get(w.lower(), w.lower()))
    if not ph:
        return cur
    si = _cmu_stressed_vowel(ph[0])
    if si is None:
        return cur
    gs = [m.start() for m in _IPA_VOWEL_RUN.finditer(cur)]
    if not gs or si >= len(gs):
        return cur
    # 单音节词按惯例不标重音（/bæk/ 而不是 /ˈbæk/）
    if _cmu_vowel_count(ph[0]) < 2 or len(gs) < 2:
        return cur
    if si > 0 and _cmu_vowel_count(ph[0]) != len(gs):
        return cur            # 两边音节数不一致，位置没法对齐，放弃
    j = gs[si]
    while j > 0 and cur[j - 1] not in _IPA_VOWELS:
        j -= 1
    new = cur[:j] + "ˈ" + cur[j:]
    stress_fixed.append((w, cur, new))
    return new


# ECDICT 有词条但音标本身有缺陷的，逐个点名覆盖（**优先于 ECDICT**）
IPA_FIX = {
    "mammal": "ˈmæməl",              # ECDICT 整个没标主重音
    "deregulate": "diːˈregjʊleɪt",   # ECDICT 记成 di:re^jjleit，^jj 是坏字符
    "ruin": "ˈruːɪn",                # ECDICT 记成 ruin，没标重音
    "well-being": "ˌwelˈbiːɪŋ",      # ECDICT 记成 'welbiiŋ，少了一个 i
    "a/an": "ə",                     # ECDICT 的 a 给的是字母名 /eɪ/，这里是冠词
    # 以下 5 个连字符复合词 ECDICT 没有整条收录，拆成两半拼接后各自单音节、都没重音，
    # 拼出来是 `/brænd njuː/` 这种半成品。复合词该有次重音+主重音，按标准英式补。
    "brand-new": "ˌbrænd ˈnjuː",
    "clear-cut": "ˌklɪəˈkʌt",
    "high-tech": "ˌhaɪ ˈtek",
    "well-known": "ˌwelˈnəʊn",
    "well-off": "ˌwelˈɒf",
    # ECDICT 记法损坏 / 个别音素错的，按 OALD 英式补
    "kilogram(me)/kilo": "ˈkɪləgræm",   # ECDICT 记成 'kilәjgræm，多了个 j
    "laboratory/lab": "ləˈbɒrətri",     # ECDICT 给的是美式 ˈlæbrətəri
    "encyclop(a)edia": "ɪnˌsaɪkləˈpiːdiə",  # 首音节 ECDICT 记成 /en/，应为弱读 /ɪn/
    "fuel(l)": "ˈfjuːəl",               # ECDICT 的 ʊ 应为 uː（OALD 英式）
    "coup (d'état)": "ˌkuː deɪˈtɑː",    # ECDICT 记成 'ku: ˌde'tɑ，de 应是 /deɪ/、末音带长音符
    "celebrity": "səˈlebrəti",          # ECDICT 记成 si'lebrti，第二个 ә 整个丢了
}

# ECDICT 根本没收录的词（现代复合词为主），音标按标准英式填写，**优先于美式回退**
# 这 20 个是仅存的没有英式词典数据来源的词；数值可在 OALD/Cambridge 上核对
IPA_EXTRA = {
    "app": "æp", "barracks": "ˈbærəks", "blog": "blɒg", "customs": "ˈkʌstəmz",
    "cyberspace": "ˈsaɪbəspeɪs", "download": "ˌdaʊnˈləʊd", "freshman": "ˈfreʃmən",
    "hotdog": "ˈhɒtdɒg", "jetlag": "ˈdʒetlæg", "knowhow": "ˈnəʊhaʊ",
    "laptop": "ˈlæptɒp", "mindset": "ˈmaɪndset", "online": "ˌɒnˈlaɪn",
    "podcast": "ˈpɒdkɑːst", "smartphone": "ˈsmɑːtfəʊn", "so-called": "ˌsəʊ ˈkɔːld",
    "telecommunications": "ˌtelɪkəˌmjuːnɪˈkeɪʃnz", "webcast": "ˈwebkɑːst",
    "website": "ˈwebsaɪt", "workforce": "ˈwɜːkfɔːs",
}

# 美式回退时统一字形，免得同一份数据里出现两套写法。
# 只做**无歧义**的对应：ʧ/ʤ 是合字、ɹ 是卷舌 r、ɛ 与 e 是同一个 DRESS 元音、
# oʊ 与 əʊ 是同一个 GOAT、ɚ/ɝ 就是 r 化的 ə/ɜː。
# ɑ（美式 LOT/PALM 合并）和 ɔ 在英式里要分成 ɒ/ɑː/ɔː，分不了，保持原样。
_AME_GLYPH = str.maketrans({"ʧ": "tʃ", "ʤ": "dʒ", "ɹ": "r", "ɛ": "e",
                            "ɚ": "ə", "ɝ": "ɜː"})


def _ame_glyphs(s):
    # oʊ 是两个字符，进不了 translate 表，单独换
    return s.replace("oʊ", "əʊ").translate(_AME_GLYPH)


def _ecdict_phonetic(ec, w):
    """取 ECDICT 的 phonetic 字段原文。依次试：原形 / 去变音符号 / 美式拼法。"""
    bare = w.translate(str.maketrans("éèêëáàâäóòôöíìîïúùûüç",
                                     "eeeeaaaaooooiiiiuuuuc"))
    for c in (w.lower(), bare.lower(), US_SPELL.get(w.lower(), ""),
              US_SPELL.get(bare.lower(), "")):
        r = ec.get(c) if c else None
        if r and (r.get("phonetic") or "").strip():
            return r["phonetic"].strip()
    return ""


def _ipa_one(ec, q):
    """单个英文词 -> 音标。**英式优先**，ECDICT 查不到才回退美式管线。"""
    if q in IPA_EXTRA:
        return IPA_EXTRA[q]
    uk = ipa_uk.transcribe(_ecdict_phonetic(ec, q))
    if uk:
        return uk
    return _ame_glyphs(repair_stress(_single_ipa(q), q))


def safe_ipa(w, ec):
    """可选字母括号/斜杠变体/连字符/词组，逐块转后拼接；查不到返回空串（不编造）

    英式音标来自 ECDICT 的 phonetic 字段（真·英式词典数据，经 ipa_uk 转写）；
    只有 ECDICT 没收录的现代复合词才回退到 eng_to_ipa/CMUdict 的美式结果。
    """
    if not w or not re.search(r"[A-Za-z]", w):
        return ""
    if w in IPA_FIX:
        return IPA_FIX[w]
    for form in _surface_forms(w):
        form = form.split("/")[0].strip()        # analyze/yse 这种斜杠变体，取第一个即可
        if not form:
            continue
        # 整条先查一次：词组（baby boom）和连字符复合词（best-seller）在 ECDICT 里是整条
        # 收录的，拆开查会丢词组重音（ˌbestˈselə 被拆成 best + ˈselə）
        if form in IPA_EXTRA:
            return IPA_EXTRA[form]
        whole = ipa_uk.transcribe(_ecdict_phonetic(ec, form))
        if whole:
            return whole
        words = [x for x in re.split(r"\s+", form) if x.strip()]
        if not words:
            continue
        out, ok = [], True
        for wd in words:
            subs = [q for q in wd.split("-") if q.strip()] if "-" in wd.strip("-") else [wd]
            got = [_ipa_one(ec, q) for q in subs]
            if got and all(got):
                out.append(" ".join(got))
            else:
                ok = False
                break
        if ok and out:
            return " ".join(out)
    return ""


# ---------------------------------------------------------------- 主流程
def main(daysize=30):
    raw = extract()
    words = clean(raw)
    ec, ec_case = load_ecdict()

    for m in words:
        m["w"] = canonical_case(m["w"], ec)
        m["deriv"] = [canonical_case(x, ec) for x in m["deriv"]]
        r = lookup(ec, m["w"])
        m["cn"] = tidy_translation(r["translation"]) if r else ""
        m["ipa"] = safe_ipa(m["w"], ec)
        dv = []
        for x in m["deriv"]:
            x = norm(x)
            if x and x.lower() != m["w"].lower() and len(x) > 1:
                # 同一主词下的派生词去重（按小写，保留先出现的写法）
                if any(d["w"].lower() == x.lower() for d in dv):
                    continue
                # 派生词补释义 + 音标，走的是和主词**完全同一条管线**（lookup -> tidy_translation
                # / safe_ipa），所以两条路的裁剪规则、英式优先、大小写规范化必然一致。
                # 查不到就留空串（不编造），页面那边字段为空时整段不渲染。
                dr = lookup(ec, x)
                dv.append({
                    "w": x,
                    "cn": tidy_translation(dr["translation"]) if dr else "",
                    "ipa": safe_ipa(x, ec),
                })
        m["deriv"] = dv

    # 拼写变体表自检：键必须是词表里真实的词头、值必须是 ECDICT 里存在的真词。
    # 这里失败要当场炸——静默放过等于把错拼放进拼写题答案集，而判分假阳性会污染复习库。
    # 键取词头在 words 里的原样大小写（页面是拿 it.w.w 查表的，不能写成表里那个小写形）。
    head_of = {m["w"].lower(): m["w"] for m in words}
    spell_alt = {}
    for head, alts in SPELL_VARIANTS.items():
        real = head_of.get(head.lower())
        if not real:
            raise SystemExit("SPELL_VARIANTS 的键不是词表里的词头: %s" % head)
        for a in alts:
            if a.lower() not in ec:
                raise SystemExit("SPELL_VARIANTS 的值不是 ECDICT 里的真词: %s -> %s" % (head, a))
        spell_alt[real] = alts
    print("拼写变体 %d 条: %s" % (len(spell_alt), spell_alt))

    miss_tr = [m["w"] for m in words if not m["cn"]]
    miss_ipa = [m["w"] for m in words if not m["ipa"]]
    c6 = sum(1 for m in words if m["cet6"])
    print("总词条 %d  四级 %d  六级 %d" % (len(words), len(words) - c6, c6))
    print("有派生词 %d 条" % sum(1 for m in words if m["deriv"]))
    print("释义缺失 %d: %s" % (len(miss_tr), miss_tr))
    print("音标缺失 %d: %s" % (len(miss_ipa), miss_ipa))
    print("分词存疑 %d: %s" % (len(suspicious), suspicious[:15]))
    print("字母分布:", dict(sorted(collections.Counter(m["w"][0].lower() for m in words).items())))

    days = [words[i:i + daysize] for i in range(0, len(words), daysize)]
    print("天数: %d" % len(days))
    json.dump({"days": days, "daySize": daysize, "total": len(words),
               "spellAlt": spell_alt},
              open(os.path.join(OUT, "words.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("saved ->", os.path.join(OUT, "words.json"))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="抽取词表并补中文释义 + 英式音标")
    ap.add_argument("--daysize", type=int, default=30, help="每天几个词（默认 30）")
    main(ap.parse_args().daysize)
