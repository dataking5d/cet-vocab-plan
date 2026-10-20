# -*- coding: utf-8 -*-
"""ECDICT 音标记法 -> 现代英式 IPA（OALD 风格）

ECDICT 的 `phonetic` 字段是 1980 年代老式英式词典记法，原样显示不能用：

| 它的写法 | 实际是 | 说明 |
|---|---|---|
| `ә` U+04D9 | `ə` U+0259 | **西里尔字母**冒充 IPA，肉眼几乎看不出 |
| `є` U+0454 | `e` | 又一个西里尔字母，专用于 /eə/（SQUARE） |
| `^` | `g` | 编码损坏：`^ɔd`=god、`'^rændtʃaild`=grandchild |
| `i:` `u:` `ɑ:` `ә:` | `iː` `uː` `ɑː` `ɜː` | `:` 当长音符 |
| `ɒ:` | `ɔː` | **记法错误**：`ɒ` 本身是短元音，不该带长音符 |
| `ei` `ai` `au` `әu` `ɒi` | `eɪ` `aɪ` `aʊ` `əʊ` `ɔɪ` | 老式双元音写法 |
| `'` | `ˈ` | 主重音 |
| 词首 `.` 、`,` | `ˌ` | 次重音（不是音节分隔！） |
| 词中 `.` | 无 | 音节分隔，删掉 |
| `. ` `, -` `;` | 断点 | 一个字段塞了多个读音，顺序不固定 |

**本模块只做记法转写，不改任何音素选择**——音素是 ECDICT 的数据，不是推导出来的。
唯一带判断的地方是 `i`/`u` 的宽窄（见 `_narrow`），那里用位置规则，不用词典知识。
"""

import re

# ISO 音标里所有元音字符，用于判断「i/u 后面是不是另一个元音」
_VOWEL_CHARS = "aeiouɪʊəɜæɑɒɔʌ"

# 多字符记号，**最长优先**（3 字符在前），逐个全局替换
_TOKENS = [
    ("iәu", "iəʊ"),                                   # radio: i + әu 跨音节
    # ECDICT 用古拼法把 wh- 词记成 hw-（what=hwɒt、white=hwait），27 个词。
    # 现代英式（OALD）一律 /w/，whole/who/whose 本来就是裸 h，不受影响。
    ("hw", "w"),
    ("ɒ:", "ɔː"), ("ɔ:", "ɔː"), ("ә:", "ɜː"), ("ɑ:", "ɑː"),
    ("i:", "iː"), ("u:", "uː"),
    ("әu", "əʊ"), ("ou", "əʊ"),
    ("ei", "eɪ"), ("ai", "aɪ"), ("au", "aʊ"), ("ɒi", "ɔɪ"),
    ("iә", "ɪə"), ("uә", "ʊə"), ("єә", "eə"), ("eә", "eə"),
]

# 一个读音字段里可能塞了多个读音，这些是分隔符（顺序 = 优先级）
# 注意 `. ` 不在这里：它后面还要过 _pick_british，不能直接取第一段
_VARIANT_SEPS = ("; -", ";", ", -")


def _narrow(ch, rest):
    """`i` / `u` 的宽窄。老式记法不区分，靠位置定：
    词尾或后接元音的 i 是「happy 元音」/i/（happy, studies, radiate），
    其余是 /ɪ/；u 后接元音时是 /u/（graduate），否则 /ʊ/（book）。"""
    if ch == "i":
        if rest[:1] in ("", " ") or re.fullmatch(r"[zd]?", rest):
            return "i"                      # 词尾：happy /ˈhæpi/、studies /ˈstʌdiz/
        if rest[:1] in _VOWEL_CHARS:
            return "i"                      # 后接元音：radiate /ˈreɪdieɪt/
        return "ɪ"
    # u
    if rest[:1] in _VOWEL_CHARS:
        return "u"                          # graduate /ˈgrædʒueɪt/
    return "ʊ"                              # book /bʊk/


def _single(ch, rest):
    """不在任何多字符记号里的单字符"""
    if ch in ("i", "u"):
        return _narrow(ch, rest)
    if ch == "ә":
        return "ə"
    if ch == "є":
        return "e"
    if ch == "ɑ":
        return "ɑː"
    if ch == "ɔ":
        return "ɒ"                          # 裸 ɔ 是 LOT：chopstick /ˈtʃɒpstɪk/
    if ch in ("^", "ɡ"):
        return "g"                          # ^ 是编码损坏的 g；ɡ U+0261 统一成 ASCII
    return ch


def _segments(s):
    """单段音标 -> 现代 IPA（不含重音符号的处理）

    **一趟最长匹配扫描**，不能拆成「先replace多字符记号、再逐字符」两趟——
    两趟会互相污染：`ɒi`->`ɔɪ` 之后，第二趟的单字符规则又把 `ɔ` 改回 `ɒ`，
    得到 `bɒɪl`；同理 `i:`->`iː` 被改成 `ɪː`、`ɑ:`->`ɑː` 被改成 `ɑːː`。
    """
    rules = sorted(_TOKENS, key=lambda t: -len(t[0]))
    out, i, n = [], 0, len(s)
    while i < n:
        for a, b in rules:
            if s.startswith(a, i):
                out.append(b)
                i += len(a)
                break
        else:
            out.append(_single(s[i], s[i + 1:]))
            i += 1
    return "".join(out)


def _pick_british(parts):
    """多个读音里挑英式的那个。ECDICT 的顺序不固定：
    `dance dæns. dɑ:ns` 美式在前，`cast kɑ:st. kæst` 英式在前。"""
    for x in parts:
        if "ɑ:" in x and any("æ" in y for y in parts if y != x):
            return x                        # BATH 类：有 ɑ: 的那个才是英式
    for x in parts:
        if re.search(r"ɒ(?!:)", x):
            return x                        # cloth: klɒ:θ(错) . klɒθ(对)
    return parts[0]


def transcribe(p):
    """ECDICT `phonetic` 字段 -> 现代英式 IPA。无法识别时返回空串（不编造）。"""
    if not p:
        return ""
    p = p.strip()

    # 0) 尾随的 `,xx-` / `;xx-` 是截断的第二个读音（cigaret = ",si^ә'ret,'si-"、
    #    archaise = "'ɑ:keiaiz,-ki-"），全库有 1400+ 条这种写法。
    #    判据是「片段以 - 收尾」——`,kɔzmә'pɔlitәn`(次重音) 和 `'hænd,buk` 不以 - 收尾，不受影响。
    p = re.sub(r"[,;]\s*[^,;]*-\s*$", "", p).strip()

    # 1) 多读音字段只取第一个读音
    for sep in _VARIANT_SEPS:
        if sep in p:
            p = p.split(sep)[0]
            break
    p = p.strip().rstrip("- ").strip()
    if not p:
        return ""

    # 2) 词首的 `.` 是次重音；词中的 `.` 分两种，靠主重音个数区分
    if p.startswith("."):
        p = "ˌ" + p[1:]
    if "." in p:
        # 音节分隔的判据：没有 `. ` 的，且整段只有 1 个主重音
        # （abbreviation ә.bri:vi'eiʃәn 是音节点；abuse ә'bju:s.ә'bju:z 有两个 '，是两个读音）
        if ". " not in p and p.count("'") + p.count("ˈ") == 1:
            p = p.replace(".", "")
        else:
            parts = [x.strip() for x in re.split(r"\.\s*", p) if x.strip()]
            p = _pick_british(parts) if len(parts) > 1 else parts[0]

    # 3) 多个主重音时，只有最后一个保留 ˈ（afternoon ˌɑːftəˈnuːn）
    if p.count("'") + p.count("ˈ") >= 2:
        k = max(p.rfind("'"), p.rfind("ˈ"))
        p = p[:k].replace("'", "ˌ").replace("ˈ", "ˌ") + p[k:]

    # 4) `,` 是次重音（cosmopolitan ,kɔzmә'pɔlitәn）
    p = p.replace(",", "ˌ")
    p = p.replace("'", "ˈ")

    out = _segments(p)
    return re.sub(r"ˌ+", "ˌ", out).strip()


# 转写后允许出现的字符集合。出现别的字符说明有没考虑到的记法，必须报错而不是照抄
ALLOWED = set("abdefghijklmnoprstuvwzʃʒθðŋtʃdʒɪʊəɜæɑɒɔʌeiouːˈˌ() ")

# 数音节用：元音**组**（双元音算一组，grəʊn 是 1 音节不是 2）
_SYL = re.compile("[aeiouɪʊəɜæɑɒɔʌ]+")


def syllables(ipa):
    return len(_SYL.findall(ipa))
