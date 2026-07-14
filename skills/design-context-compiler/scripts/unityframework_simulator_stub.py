#!/usr/bin/env python3
"""Create and restore an evaluator-only arm64 Simulator UnityFramework ABI stub."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import struct
import subprocess
import sys
import tempfile


SLICE_IDENTIFIER = "ios-arm64-simulator"
FRAMEWORK_NAME = "UnityFramework.framework"
HEADER = r'''#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>
#import <mach-o/loader.h>
typedef struct mach_header_64 MachHeader;
FOUNDATION_EXPORT double UnityFrameworkVersionNumber;
FOUNDATION_EXPORT const unsigned char UnityFrameworkVersionString[];
@protocol UnityFrameworkListener <NSObject>
@optional
- (void)unityDidUnload:(NSNotification *)notification;
- (void)unityDidQuit:(NSNotification *)notification;
@end
@interface UnityAppController : NSObject
@property(nonatomic, strong) UIView *rootView;
@property(nonatomic, strong) UIWindow *window;
@end
@interface UnityFramework : NSObject
- (UnityAppController *)appController;
- (UITextField *)keyboardTextField;
+ (UnityFramework *)getInstance;
- (void)setDataBundleId:(const char *)bundleId;
- (void)runUIApplicationMainWithArgc:(int)argc argv:(char *[])argv;
- (void)runEmbeddedWithArgc:(int)argc argv:(char *[])argv appLaunchOpts:(NSDictionary *)appLaunchOpts;
- (void)unloadApplication;
- (void)quitApplication:(int)exitCode;
- (void)registerFrameworkListener:(id<UnityFrameworkListener>)obj;
- (void)unregisterFrameworkListener:(id<UnityFrameworkListener>)obj;
- (void)showUnityWindow;
- (void)pause:(bool)pause;
- (void)setAbsoluteURL:(const char *)url;
- (void)setExecuteHeader:(const MachHeader *)header;
- (void)sendMessageToGOWithName:(const char *)goName functionName:(const char *)name message:(const char *)msg;
@end
'''
MODULEMAP = '''framework module UnityFramework {
  umbrella header "UnityFramework.h"
  export *
  module * { export * }
}
'''
IMPLEMENTATION = r'''#import "UnityFramework.h"
double UnityFrameworkVersionNumber = 1.0;
const unsigned char UnityFrameworkVersionString[] = "1.0";
__attribute__((noreturn)) static void DCCUnexpectedUnityCall(void) { __builtin_trap(); }
@implementation UnityAppController
@end
@implementation UnityFramework
+ (UnityFramework *)getInstance { DCCUnexpectedUnityCall(); }
- (UnityAppController *)appController { DCCUnexpectedUnityCall(); }
- (UITextField *)keyboardTextField { DCCUnexpectedUnityCall(); }
- (void)setDataBundleId:(const char *)bundleId { DCCUnexpectedUnityCall(); }
- (void)runUIApplicationMainWithArgc:(int)argc argv:(char *[])argv { DCCUnexpectedUnityCall(); }
- (void)runEmbeddedWithArgc:(int)argc argv:(char *[])argv appLaunchOpts:(NSDictionary *)appLaunchOpts { DCCUnexpectedUnityCall(); }
- (void)unloadApplication { DCCUnexpectedUnityCall(); }
- (void)quitApplication:(int)exitCode { DCCUnexpectedUnityCall(); }
- (void)registerFrameworkListener:(id<UnityFrameworkListener>)obj { DCCUnexpectedUnityCall(); }
- (void)unregisterFrameworkListener:(id<UnityFrameworkListener>)obj { DCCUnexpectedUnityCall(); }
- (void)showUnityWindow { DCCUnexpectedUnityCall(); }
- (void)pause:(bool)pause { DCCUnexpectedUnityCall(); }
- (void)setAbsoluteURL:(const char *)url { DCCUnexpectedUnityCall(); }
- (void)setExecuteHeader:(const MachHeader *)header { DCCUnexpectedUnityCall(); }
- (void)sendMessageToGOWithName:(const char *)goName functionName:(const char *)name message:(const char *)msg { DCCUnexpectedUnityCall(); }
@end
'''


class StubError(ValueError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise StubError(f"command failed ({result.returncode}): {command[0]}: {detail}")
    return result


def require_relative(path: str, label: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise StubError(f"{label} must be a checkout-relative path")
    return candidate


def verify_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or sha256(path) != expected:
        raise StubError(f"{label} identity mismatch")


def write_framework_info(path: Path) -> None:
    payload = {
        "CFBundleDevelopmentRegion": "English",
        "CFBundleExecutable": "UnityFramework",
        "CFBundleIdentifier": "com.unity3d.framework",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": "UnityFramework",
        "CFBundlePackageType": "FMWK",
        "CFBundleShortVersionString": "1.0",
        "CFBundleSupportedPlatforms": ["iPhoneSimulator"],
        "CFBundleVersion": "1.0",
        "MinimumOSVersion": "12.0",
        "NSPrincipalClass": "UnityFramework",
        "UIDeviceFamily": [1, 2],
    }
    path.write_bytes(plistlib.dumps(payload, fmt=plistlib.FMT_BINARY, sort_keys=True))


def verify_simulator_macho(path: Path) -> None:
    data = path.read_bytes()
    if len(data) < 32 or struct.unpack_from("<I", data)[0] != 0xFEEDFACF:
        raise StubError("generated stub is not a little-endian 64-bit Mach-O")
    if struct.unpack_from("<I", data, 4)[0] != 0x0100000C:
        raise StubError("generated stub is not an arm64 Mach-O")
    if struct.unpack_from("<I", data, 12)[0] != 6:
        raise StubError("generated stub is not a dynamic library")
    command_count = struct.unpack_from("<I", data, 16)[0]
    command_bytes = struct.unpack_from("<I", data, 20)[0]
    offset = 32
    command_end = offset + command_bytes
    if command_end > len(data):
        raise StubError("generated stub has a truncated load command table")
    has_uuid = False
    has_simulator_platform = False
    for _ in range(command_count):
        if offset + 8 > command_end:
            raise StubError("generated stub has a truncated load command")
        command, size = struct.unpack_from("<II", data, offset)
        if size < 8 or offset + size > command_end:
            raise StubError("generated stub has an invalid load command size")
        if command == 0x1B:
            has_uuid = size >= 24
        elif command == 0x32 and size >= 24:
            has_simulator_platform = struct.unpack_from("<I", data, offset + 8)[0] == 7
        offset += size
    if offset != command_end:
        raise StubError("generated stub load commands do not match sizeofcmds")
    if not has_simulator_platform:
        raise StubError("generated stub is not an iOS Simulator binary")
    if not has_uuid:
        raise StubError("generated stub is missing LC_UUID")


def product_hashes(framework: Path) -> dict[str, str]:
    files = {
        "binary_sha256": framework / "UnityFramework",
        "header_sha256": framework / "Headers/UnityFramework.h",
        "modulemap_sha256": framework / "Modules/module.modulemap",
        "framework_info_sha256": framework / "Info.plist",
    }
    if any(not path.is_file() for path in files.values()):
        raise StubError("generated evaluator dependency product is incomplete")
    return {key: sha256(path) for key, path in files.items()}


def build_product(output: Path, clang: Path, sdk: Path) -> dict[str, str]:
    framework = output / FRAMEWORK_NAME
    headers = framework / "Headers"
    modules = framework / "Modules"
    headers.mkdir(parents=True)
    modules.mkdir(parents=True)
    header = headers / "UnityFramework.h"
    modulemap = modules / "module.modulemap"
    source = output / "UnityFramework.m"
    binary = framework / "UnityFramework"
    header.write_text(HEADER, encoding="utf-8")
    modulemap.write_text(MODULEMAP, encoding="utf-8")
    source.write_text(IMPLEMENTATION, encoding="utf-8")
    write_framework_info(framework / "Info.plist")
    run([
        str(clang), "-target", "arm64-apple-ios12.0-simulator", "-isysroot", str(sdk),
        "-fobjc-arc", "-fblocks", "-dynamiclib", "-framework", "Foundation",
        "-framework", "UIKit", "-I", str(headers),
        "-install_name", "@rpath/UnityFramework.framework/UnityFramework",
        "-current_version", "1.0", "-compatibility_version", "1.0",
        str(source), "-o", str(binary),
    ])
    verify_simulator_macho(binary)
    return product_hashes(framework)


def verify_product(actual: dict[str, str], expected: dict[str, str]) -> None:
    if actual != expected:
        raise StubError("generated evaluator dependency product hash mismatch")


def patch_xcframework_info(path: Path) -> None:
    payload = plistlib.loads(path.read_bytes())
    libraries = payload.get("AvailableLibraries")
    if not isinstance(libraries, list):
        raise StubError("XCFramework AvailableLibraries is invalid")
    if any(item.get("LibraryIdentifier") == SLICE_IDENTIFIER for item in libraries if isinstance(item, dict)):
        raise StubError("arm64 Simulator UnityFramework slice already exists")
    libraries.append({
        "BinaryPath": f"{FRAMEWORK_NAME}/UnityFramework",
        "LibraryIdentifier": SLICE_IDENTIFIER,
        "LibraryPath": FRAMEWORK_NAME,
        "SupportedArchitectures": ["arm64"],
        "SupportedPlatform": "ios",
        "SupportedPlatformVariant": "simulator",
    })
    path.write_bytes(plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=False))


def patch_copy_script(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    variant_anchor = '  "UnityFramework.xcframework/ios-x86_64-simulator")\n    echo "simulator"'
    arch_anchor = '  "UnityFramework.xcframework/ios-x86_64-simulator")\n    echo "x86_64"'
    install_anchor = '"ios-arm64" "ios-x86_64-simulator"'
    if text.count(variant_anchor) != 1 or text.count(arch_anchor) != 1 or text.count(install_anchor) != 1:
        raise StubError("CocoaPods XCFramework copy script shape is not the frozen baseline")
    text = text.replace(
        variant_anchor,
        f'  "UnityFramework.xcframework/{SLICE_IDENTIFIER}")\n    echo "simulator"\n    ;;\n{variant_anchor}',
    )
    text = text.replace(
        arch_anchor,
        f'  "UnityFramework.xcframework/{SLICE_IDENTIFIER}")\n    echo "arm64"\n    ;;\n{arch_anchor}',
    )
    text = text.replace(install_anchor, f'{install_anchor} "{SLICE_IDENTIFIER}"')
    path.write_text(text, encoding="utf-8")


def load_contract(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("mode") != "unityframework-arm64-simulator-stub-v1":
        raise StubError("unsupported evaluator dependency setup mode")
    return payload


def fingerprint(contract: dict) -> dict[str, str]:
    clang = Path(contract["clang"]["path"])
    sdk = Path(contract["sdk"]["path"])
    verify_file(clang, contract["clang"]["sha256"], "clang")
    verify_file(sdk / "SDKSettings.plist", contract["sdk"]["settings_sha256"], "Simulator SDK")
    with tempfile.TemporaryDirectory(prefix="dcc-unity-stub-fingerprint-") as directory:
        first = build_product(Path(directory) / "first", clang, sdk)
        second = build_product(Path(directory) / "second", clang, sdk)
        if first != second:
            raise StubError("evaluator dependency generator is not deterministic")
        return first


def apply(contract: dict, worktree: Path, state: Path) -> dict[str, str]:
    if state.exists():
        raise StubError("dependency setup state already exists")
    xcframework_rel = require_relative(contract["xcframework_path"], "xcframework_path")
    copy_script_rel = require_relative(contract["pod_copy_script_path"], "pod_copy_script_path")
    xcframework = worktree / xcframework_rel
    info = xcframework / "Info.plist"
    copy_script = worktree / copy_script_rel
    verify_file(info, contract["baseline"]["xcframework_info_sha256"], "XCFramework Info.plist")
    verify_file(copy_script, contract["baseline"]["pod_copy_script_sha256"], "CocoaPods copy script")
    state.mkdir(parents=True)
    shutil.copyfile(info, state / "Info.plist")
    shutil.copyfile(copy_script, state / "copy-script.sh")
    try:
        product = fingerprint(contract)
        verify_product(product, contract["product"])
        slice_root = xcframework / SLICE_IDENTIFIER
        if slice_root.exists():
            raise StubError("arm64 Simulator UnityFramework slice path already exists")
        with tempfile.TemporaryDirectory(prefix="dcc-unity-stub-apply-") as directory:
            generated = Path(directory) / SLICE_IDENTIFIER
            verify_product(build_product(generated, Path(contract["clang"]["path"]), Path(contract["sdk"]["path"])), contract["product"])
            shutil.copytree(generated / FRAMEWORK_NAME, slice_root / FRAMEWORK_NAME)
        patch_xcframework_info(info)
        patch_copy_script(copy_script)
        manifest = {
            "original_info_sha256": contract["baseline"]["xcframework_info_sha256"],
            "original_copy_script_sha256": contract["baseline"]["pod_copy_script_sha256"],
            "patched_info_sha256": sha256(info),
            "patched_copy_script_sha256": sha256(copy_script),
            "slice_binary_sha256": sha256(slice_root / FRAMEWORK_NAME / "UnityFramework"),
        }
        (state / "state.json").write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
        return manifest
    except Exception:
        if (state / "Info.plist").is_file():
            shutil.copyfile(state / "Info.plist", info)
        if (state / "copy-script.sh").is_file():
            shutil.copyfile(state / "copy-script.sh", copy_script)
        shutil.rmtree(xcframework / SLICE_IDENTIFIER, ignore_errors=True)
        shutil.rmtree(state, ignore_errors=True)
        raise


def restore(contract: dict, worktree: Path, state: Path) -> dict[str, str]:
    xcframework = worktree / require_relative(contract["xcframework_path"], "xcframework_path")
    info = xcframework / "Info.plist"
    copy_script = worktree / require_relative(contract["pod_copy_script_path"], "pod_copy_script_path")
    manifest_path = state / "state.json"
    if not manifest_path.is_file():
        raise StubError("dependency setup restore state is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sha256(info) != manifest["patched_info_sha256"] or sha256(copy_script) != manifest["patched_copy_script_sha256"]:
        raise StubError("evaluator dependency files changed while capture was running")
    slice_binary = xcframework / SLICE_IDENTIFIER / FRAMEWORK_NAME / "UnityFramework"
    if not slice_binary.is_file() or sha256(slice_binary) != manifest["slice_binary_sha256"]:
        raise StubError("evaluator dependency slice changed while capture was running")
    verify_product(product_hashes(xcframework / SLICE_IDENTIFIER / FRAMEWORK_NAME), contract["product"])
    shutil.copyfile(state / "Info.plist", info)
    shutil.copyfile(state / "copy-script.sh", copy_script)
    shutil.rmtree(xcframework / SLICE_IDENTIFIER)
    verify_file(info, contract["baseline"]["xcframework_info_sha256"], "restored XCFramework Info.plist")
    verify_file(copy_script, contract["baseline"]["pod_copy_script_sha256"], "restored CocoaPods copy script")
    shutil.rmtree(state)
    return {"xcframework_info_sha256": sha256(info), "pod_copy_script_sha256": sha256(copy_script)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("fingerprint", "apply", "restore"))
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--worktree", type=Path)
    parser.add_argument("--state", type=Path)
    args = parser.parse_args()
    try:
        contract = load_contract(args.contract)
        if args.action == "fingerprint":
            result = fingerprint(contract)
        else:
            if args.worktree is None or args.state is None:
                raise StubError("apply/restore require --worktree and --state")
            worktree = args.worktree.resolve()
            if args.action == "apply":
                result = apply(contract, worktree, args.state.resolve())
            else:
                result = restore(contract, worktree, args.state.resolve())
        print(json.dumps({"status": "ready", "action": args.action, "result": result}, sort_keys=True))
        return 0
    except (KeyError, OSError, StubError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
