#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从正在运行的 llama-server 镜像英文原版 WebUI 静态资源到 ../webui-en/。

用途：升级 PrismML llama.cpp 运行时（新 bundle 哈希）后，
先跑本脚本刷新 webui-en，再改 apply_zh.py 里的 BUNDLE 常量并重新生成 webui-zh。
"""
import gzip
import os
import pathlib
import re
import urllib.request

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8080").rstrip("/")
OUT = pathlib.Path(__file__).resolve().parent.parent / "webui-en"

seen, queue = set(), []
files = {}


def add(p):
    p = "/" + p.lstrip("./")
    if p not in seen:
        seen.add(p)
        queue.append(p)


def fetch(path):
    req = urllib.request.Request(BASE_URL + path, headers={"Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return data


def main():
    index = fetch("/")
    files["/"] = index
    for m in re.finditer(rb'(?:src|href)="([^"]+)"', index):
        add(m.group(1).decode())
    add("/manifest.webmanifest")
    while queue:
        p = queue.pop(0)
        try:
            data = fetch(p)
        except Exception as e:  # noqa: BLE001
            print("FAIL", p, e)
            continue
        files[p] = data
        text = data.decode("utf-8", "ignore") if p.endswith((".js", ".css", ".html", ".webmanifest")) else ""
        for m in re.finditer(r"[_a-zA-Z0-9./-]*_app/immutable/[A-Za-z0-9_.@/-]+", text):
            add(m.group(0))
        for m in re.finditer(r"assets/[A-Za-z0-9_][A-Za-z0-9_.-]*\.(?:png|jpe?g|svg|woff2?|ttf|webp|ico)", text):
            add("/_app/immutable/" + m.group(0))
        if p.endswith(".webmanifest"):
            for m in re.finditer(r'"src"\s*:\s*"([^"]+)"', text):
                add(m.group(1))

    # 防呆：镜像源必须是英文原版界面。若服务器已经挂了 --path webui-zh，
    # 抓到的是中文版，再跑 apply_zh.py 会"翻译 0 条"。
    index = files.get("/", b"").decode("utf-8", "ignore")
    if 'lang="zh-CN"' in index or "sw disabled" in index:
        raise SystemExit(
            "镜像来源已经是中文界面（服务器启用了 --path webui-zh）。\n"
            "请先临时去掉 --path 重启 llama-server，再运行 mirror_en.py。"
        )

    for p, data in files.items():
        dest = OUT / (p.lstrip("/") if p != "/" else "index.html")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    print(f"mirrored {len(files)} files -> {OUT}")
    bundles = [p for p in files if re.search(r"/bundle\.[A-Za-z0-9_-]+\.js$", p)]
    print("bundle:", bundles[0] if bundles else "NOT FOUND")


if __name__ == "__main__":
    main()
