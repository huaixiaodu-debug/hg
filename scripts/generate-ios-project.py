#!/usr/bin/env python3
"""在本机生成 HGhub 的 iOS Xcode 工程（不需要 macOS）。

做法：用仓库内固化的 Tauri 官方 iOS 模板 + Tauri 自带的真实 pbxproj 样例
（scripts/ios-templates/，离线可用），按 tauri.conf.json / Cargo.toml 参数
实例化到 src-tauri/gen/apple/。最终编译仍在 macOS 上完成：Xcode SDK 与
签名链是 Apple 专有组件。

用法： python scripts/generate-ios-project.py
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DST = ROOT / "src-tauri" / "gen" / "apple"
TEMPLATES = Path(__file__).resolve().parent / "ios-templates"

conf = json.loads((ROOT / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
cargo = (ROOT / "src-tauri" / "Cargo.toml").read_text(encoding="utf-8")
pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

NAME = conf["productName"]
BUNDLE = conf["identifier"]
VERSION = conf["version"]
lib_section = cargo.split("[lib]", 1)[1] if "[lib]" in cargo else cargo
LIB = "lib" + re.search(r'^name\s*=\s*"([^"]+)"', lib_section, re.M).group(1).replace("-", "_") + ".a"

TEXT_FILES = [
    ".gitignore", "ExportOptions.plist", "LaunchScreen.storyboard", "Podfile",
    "project.yml", "Assets.xcassets/Contents.json",
    "Assets.xcassets/AppIcon.appiconset/Contents.json",
    "Sources/{{app.name}}/bindings/bindings.h",
    "Sources/{{app.name}}/main.mm",
    "{{app.name}}.xcodeproj/project.xcworkspace/xcshareddata/WorkspaceSettings.xcsettings",
]


def put(rel: str, text: str) -> None:
    p = DST / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def render(text: str) -> str:
    for k, v in [
        ("{{app.name}}", NAME), ("{{app.stylized-name}}", NAME),
        ("{{app.identifier}}", BUNDLE), ("{{apple.ios-version}}", "15.0"),
        ("{{apple.bundle-version-short}}", VERSION), ("{{apple.bundle-version}}", VERSION),
        ("{{ lib-output-file-name }}", "libapp.a"), ("{{lib-output-file-name}}", "libapp.a"),
        ("{{join ios-valid-archs}}", "arm64, x86_64"), ("{{join file-groups}}", "../../src"),
    ]:
        text = text.replace(k, v)
    text = re.sub(r"\{\{~?#[a-z-]+[^}]*\}\}.*?\{\{~?/[a-z-]+\}\}", "", text, flags=re.S)
    return re.sub(r"\{\{~?[^{}]*\}\}", "", text)


def main() -> None:
    if DST.exists():
        shutil.rmtree(DST)
    for sub in ["Assets.xcassets/AppIcon.appiconset", "Sources/" + NAME + "/bindings",
                NAME + "_iOS", "Externals", "assets",
                NAME + ".xcodeproj/project.xcworkspace/xcshareddata"]:
        (DST / sub).mkdir(parents=True, exist_ok=True)

    for rel in TEXT_FILES:
        put(rel.replace("{{app.name}}", NAME), render((TEMPLATES / rel).read_text(encoding="utf-8")))

    icons = ROOT / "src-tauri" / "icons" / "ios"
    for f in icons.glob("*.png"):
        shutil.copy2(f, DST / "Assets.xcassets" / "AppIcon.appiconset" / f.name)

    dist = ROOT / "dist"
    if dist.exists():
        for item in dist.iterdir():
            target = DST / "assets" / item.name
            shutil.copytree(item, target, dirs_exist_ok=True) if item.is_dir() else shutil.copy2(item, target)

    put(f"{NAME}_iOS/Info.plist", f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>CFBundleName</key><string>{NAME}</string>
\t<key>CFBundleDisplayName</key><string>{NAME}</string>
\t<key>CFBundleShortVersionString</key><string>{VERSION}</string>
\t<key>CFBundleVersion</key><string>{VERSION}</string>
\t<key>CFBundleIdentifier</key><string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
\t<key>LSRequiresIPhoneOS</key><true/>
\t<key>UILaunchStoryboardName</key><string>LaunchScreen</string>
\t<key>UIRequiredDeviceCapabilities</key>
\t<array><string>arm64</string><string>metal</string></array>
\t<key>UISupportedInterfaceOrientations</key>
\t<array>
\t\t<string>UIInterfaceOrientationPortrait</string>
\t\t<string>UIInterfaceOrientationLandscapeLeft</string>
\t\t<string>UIInterfaceOrientationLandscapeRight</string>
\t</array>
\t<key>UISupportedInterfaceOrientations~ipad</key>
\t<array>
\t\t<string>UIInterfaceOrientationPortrait</string>
\t\t<string>UIInterfaceOrientationPortraitUpsideDown</string>
\t\t<string>UIInterfaceOrientationLandscapeLeft</string>
\t\t<string>UIInterfaceOrientationLandscapeRight</string>
\t</array>
</dict>
</plist>
''')
    put(f"{NAME}_iOS/{NAME}_iOS.entitlements", '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>com.apple.security.application-groups</key><array/>
</dict>
</plist>
''')

    pbx = (TEMPLATES / "project.pbxproj.fixture").read_text(encoding="utf-8")
    for a, b in [
        ("libapi_lib.a", LIB), ("api_iOS", f"{NAME}_iOS"),
        ("com.tauri.api", BUNDLE), ("Tauri API", NAME),
        ("/* api */", f"/* {NAME} */"), ('PBXProject "api"', f'PBXProject "{NAME}"'),
        ("path = api;", f"path = {NAME};"),
        ("cargo tauri ios xcode-script", "node ../../../node_modules/.bin/tauri ios xcode-script"),
    ]:
        pbx = pbx.replace(a, b)
    pbx = re.sub(r"^\s*DEVELOPMENT_TEAM = [A-Z0-9]+;\s*$\n", "", pbx, flags=re.M)
    pbx = re.sub(r"^\s*DevelopmentTeam = [A-Z0-9]+;\s*$\n", "", pbx, flags=re.M)
    put(f"{NAME}.xcodeproj/project.pbxproj", pbx)

    files = [p for p in DST.rglob("*") if p.is_file()]
    print(f"generated {len(files)} files under {DST}")
    print(f"bundle id: {BUNDLE} | rust lib: {LIB} | version: {VERSION}")


if __name__ == "__main__":
    main()
