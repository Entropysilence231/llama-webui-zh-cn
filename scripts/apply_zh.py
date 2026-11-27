#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llama.cpp WebUI 简中语言包生成器（适用于新版 SvelteKit UI / prism-b12232+）

原理：不重新编译前端。把官方静态 UI 里的 bundle JS 做「精确字面量替换」
（只在属性、文本节点、模板串等上下文替换英文文案），再生成 webui-zh/ 目录，
llama-server 用 --path 指向它即可。不改任何功能代码，可随时删除回退英文。

翻译词表说明：
  - scripts/upstream_patch_b11344.py 的词表来自
    https://github.com/Yao-Shun-Ya/llama-webui-zh （MIT，Copyright (c) 2026 Yao-Shun-Ya）
  - scripts/extra_zh.json 是针对新版 UI 增补的词表

用法：
  python3 scripts/mirror_en.py          # 1. 从运行中的 llama-server 镜像英文原版
  python3 scripts/apply_zh.py           # 2. 生成 webui-zh/
  llama-server ... --path ./webui-zh    # 3. 启动时挂载
"""
import importlib.util
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(os.environ.get("WEBUI_EN", ROOT / "webui-en"))
DST = Path(os.environ.get("WEBUI_ZH", ROOT / "webui-zh"))
SCRIPTS = Path(__file__).resolve().parent

ATTR_KEYS = [
    "placeholder", "title", "tooltip", "label", "help", "message", "error",
    "note", "description", "buttonText", "srLabel", "confirmText", "cancelText",
    "ariaLabel", '"aria-label"', "triggerTooltip", "disabledTooltip",
    "emptyText", "subtitle",
]
TEXT_HELPERS = ["_r", "gr"]  # Svelte 文本节点 helper（不同构建里名字不同）

# 动态拼接的文案（模板字符串 / 三元里的字面量）
DYNAMIC_RAW = [
    ('`Models - ${EN??""}`', '`模型 - ${EN??""}`'),
    ('`Error ${b(s)??""} - ${EN??""}`', '`错误 ${b(s)??""} - ${EN??""}`'),
    ('pt.activeConversation?.name||"Chat"', 'pt.activeConversation?.name||"对话"'),
    ('`Sort by ${Q}, lowest first`', '`按 ${Q} 升序排序`'),
    ('`Sort by ${Q}, highest order`', '`按 ${Q} 降序排序`'),
    ('`Sort by ${Q}, highest first`', '`按 ${Q} 降序排序`'),
    ('`Stop sorting by ${Q}`', '`取消按 ${Q} 排序`'),
    ('} tokens`', '} 个 token`'),
    ('"Max ${d.toLocaleString()} tokens"', '"最多 ${d.toLocaleString()} 个 token"'),
    ('?"Paused"', '?"已暂停"'),
    ('?"Downloading"', '?"下载中"'),
    ('`Default: ', '`默认：'),
    (' tool${l().tools.length!==1?"s":""}', ' 个工具'),
    (' tool${b(p).tools.length!==1?"s":""}', ' 个工具'),
    (' tools available · Show details', ' 个工具可用 · 显示详情'),
    ('?"Disable":"Enable"', '?"禁用":"启用"'),
    ('?"Enable":"Add"', '?"启用":"添加"'),
    (' MCP Server(s) to access ', ' MCP 服务器来访问 '),
    ('G7t="New chat"', 'G7t="新建对话"'),
    ('z7t="Chat"', 'z7t="对话"'),
    ('i="Reasoning",a="Reasoning...",s="Error",o="Cancelled"', 'i="推理",a="推理中…",s="错误",o="已取消"'),
    (' tokens/s`', ' token/s`'),
]

SW_DISABLE = (
    "<script>(function(){"
    "if('serviceWorker' in navigator){"
    "navigator.serviceWorker.getRegistrations().then(function(rs){"
    "rs.forEach(function(r){r.unregister();});});"
    "navigator.serviceWorker.register=function(){"
    "return Promise.reject(new Error('sw disabled'));};}"
    "if(window.caches){caches.keys().then(function(ks){"
    "ks.forEach(function(k){caches.delete(k);});});}"
    "})();</script>\n"
)

SW_SELFDESTRUCT = (
    "self.addEventListener('install',function(){self.skipWaiting();});\n"
    "self.addEventListener('activate',function(e){e.waitUntil((async function(){\n"
    "try{await self.registration.unregister();}catch(err){}\n"
    "try{var ks=await caches.keys();await Promise.all(ks.map(function(k){return caches.delete(k);}));}catch(err){}\n"
    "})());});\n"
)

report = []


def load_upstream():
    path = SCRIPTS / "upstream_patch_b11344.py"
    spec = importlib.util.spec_from_file_location("upstream_patch", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def detect_bundle():
    env = os.environ.get("BUNDLE")
    if env:
        return env
    bundles = sorted((SRC / "_app/immutable").glob("bundle.*.js"))
    if not bundles:
        sys.exit(f"找不到 {SRC}/_app/immutable/bundle.*.js，请先运行 mirror_en.py")
    return bundles[0].name


def replace_attr(t, en, zh, report, tag):
    n = 0
    for key in ATTR_KEYS:
        for q in ('"', "'"):
            k = f"{key}:{q}{en}{q}"
            c = t.count(k)
            if c:
                t = t.replace(k, f"{key}:{q}{zh}{q}")
                n += c
    if n:
        report.append((tag, en, zh, n))
    return t, n


def replace_template(t, en, zh):
    pat = re.compile(r">(\s*)" + re.escape(en) + r"(\s*)<")
    n = len(pat.findall(t))
    if not n:
        return t, 0
    return pat.sub(lambda m: ">" + m.group(1) + zh + m.group(2) + "<", t), n


def replace_helper(t, en, zh):
    n = 0
    for h in TEXT_HELPERS:
        for q in ('"', "'"):
            k = f"{h}({q}{en}{q})"
            c = t.count(k)
            if c:
                t = t.replace(k, f"{h}({q}{zh}{q})")
                n += c
    return t, n


def replace_escaped(t, en, zh):
    k = '\\"' + en + '\\"'
    c = t.count(k)
    if c:
        t = t.replace(k, '\\"' + zh + '\\"')
    return t, c


def replace_bare(t, en, zh):
    n = 0
    for q in ('"', "'"):
        k = f"{q}{en}{q}"
        c = t.count(k)
        if c:
            t = t.replace(k, f"{q}{zh}{q}")
            n += c
    return t, n


def patch_bundle(t, mapping, tag):
    for en, zh in mapping.items():
        if not en or en == zh:
            continue
        total = 0
        t, n = replace_attr(t, en, zh, report, tag); total += n
        t, n = replace_helper(t, en, zh); total += n
        t, n = replace_template(t, en, zh); total += n
        t, n = replace_escaped(t, en, zh); total += n
        # 长句是唯一的 UI 文案，允许裸引号替换；短词只走上下文，避免误改逻辑值
        if len(en) > 25:
            t, n = replace_bare(t, en, zh); total += n
        # 对象映射值（[enum]:"EN"），用于模态/能力等标签
        for q in ('"', "'"):
            k = f"]:{q}{en}{q}"
            c = t.count(k)
            if c:
                t = t.replace(k, f"]:{q}{zh}{q}"); total += c
        # 其他属性值（key:"EN"）：只对含空格或较长文案生效
        if (" " in en) or len(en) >= 12:
            for q in ('"', "'"):
                k = f":{q}{en}{q}"
                c = t.count(k)
                if c:
                    t = t.replace(k, f":{q}{zh}{q}"); total += c
        # 单引号 JS 模板串里的 HTML 属性 title="EN"
        for attr in ("title", "aria-label", "placeholder", "alt"):
            k = f'{attr}="{en}"'
            c = t.count(k)
            if c:
                t = t.replace(k, f'{attr}="{zh}"'); total += c
        if total == 0:
            report.append(("MISS:" + tag, en, zh, 0))
    return t


def main():
    if not (SRC / "index.html").exists():
        sys.exit(f"找不到 {SRC}/index.html，请先运行：python3 scripts/mirror_en.py")

    U = load_upstream()
    extra = json.load(open(SCRIPTS / "extra_zh.json", encoding="utf-8"))
    bundle = detect_bundle()
    bundle_path = SRC / "_app/immutable" / bundle
    t = bundle_path.read_text(encoding="utf-8")
    orig_len = len(t)
    print(f"bundle: {bundle} ({orig_len} chars)")
    if "新建对话" in t or 'lang="zh-CN"' in (SRC / "index.html").read_text(encoding="utf-8"):
        sys.exit("webui-en/ 里已经是中文了，请用英文原版重新镜像（见 README「手动步骤」）。")

    # 第 0 轮：补充词表里的长句先替换（长句内引用的标签名随后会被换掉）
    long_extra = {k: v for k, v in extra.items() if len(k) >= 30}
    short_extra = {k: v for k, v in extra.items() if len(k) < 30}
    t = patch_bundle(t, long_extra, "EXTRA-LONG")

    # 第一轮：b11344 词表
    t = patch_bundle(t, U.GR, "GR")
    for tag, table in [
        ("LABEL", U.LABEL), ("TITLE", U.TITLE), ("TOOLTIP", U.TOOLTIP),
        ("HELP", U.HELP), ("DESCRIPTION", U.DESCRIPTION),
        ("PLACEHOLDER", U.PLACEHOLDER), ("MESSAGE", U.MESSAGE),
        ("ERROR", U.ERROR), ("NOTE", U.NOTE), ("BTN", U.BTN), ("SR", U.SR),
        ("ARIA", U.ARIA),
    ]:
        t = patch_bundle(t, table, tag)

    for en, zh in U.TEMPLATE.items():
        t, n = replace_template(t, en, zh)
        report.append(("TEMPLATE" if n else "MISS:TEMPLATE", en, zh, n))
    for attr, table in U.SINGLE:
        for en, zh in table.items():
            k = f"{attr}:'{en}'"
            c = t.count(k)
            if c:
                t = t.replace(k, f"{attr}:'{zh}'")
                report.append(("SINGLE", en, zh, c))
    for en, zh in U.PLAIN.items():
        t, n = replace_bare(t, en, zh)
        report.append(("PLAIN" if n else "MISS:PLAIN", en, zh, n))
    for en, zh in U.RAW:
        c = t.count(en)
        if c:
            t = t.replace(en, zh)
            report.append(("RAW", en, zh, c))
        else:
            report.append(("MISS:RAW", en, zh, 0))
    for pat, zh in U.REGEX:
        t, n = re.subn(pat, zh, t)
        if n:
            report.append(("REGEX", pat, zh, n))

    # 第二轮：补充词表（短句）
    t = patch_bundle(t, short_extra, "EXTRA")

    # 第三轮：动态拼接的文案
    for old, new in DYNAMIC_RAW:
        c = t.count(old)
        if c:
            t = t.replace(old, new)
            report.append(("DYNAMIC", old, new, c))
        else:
            report.append(("MISS:DYNAMIC", old, new, 0))
    t, n = re.subn(r' model\$\{[^{}]*\?"":"s"\}', ' 个模型', t)
    report.append(("DYNAMIC-regex", "N model(s)", "N 个模型", n))

    # 输出
    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(SRC, DST)
    (DST / "_app/immutable" / bundle).write_text(t, encoding="utf-8")

    html = (DST / "index.html").read_text(encoding="utf-8")
    if SW_DISABLE not in html:
        html = html.replace("</head>", SW_DISABLE + "</head>", 1)
    html = html.replace('<html lang="en">', '<html lang="zh-CN">')
    (DST / "index.html").write_text(html, encoding="utf-8")

    reset_src = SCRIPTS / "reset.html"
    if reset_src.exists():
        shutil.copyfile(reset_src, DST / "reset.html")
    (DST / "sw.js").write_text(SW_SELFDESTRUCT, encoding="utf-8")

    ok = [r for r in report if not r[0].startswith("MISS")]
    miss = [r for r in report if r[0].startswith("MISS")]
    (ROOT / "report.txt").write_text(
        "".join(f"{r[0]}\t{r[1]}\t{r[2]}\t{r[3]}\n" for r in report), encoding="utf-8"
    )
    print(f"替换成功 {len(ok)} 组，未命中 {len(miss)} 组（未命中多为该版本已删除的旧文案）")
    print(f"bundle: {orig_len} -> {len(t)} chars")
    print(f"\n生成完成：{DST}")
    print(f"启动 llama-server 时加参数：--path {DST}")


if __name__ == "__main__":
    main()
