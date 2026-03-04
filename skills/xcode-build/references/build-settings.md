# Build Configuration 最佳实践

## xcconfig 文件管理

### 目录结构
```
Config/
├── Shared.xcconfig           # 所有配置共享
├── Debug.xcconfig
├── Release.xcconfig
├── Staging.xcconfig
└── Targets/
    ├── App.xcconfig
    └── AppTests.xcconfig
```

### Shared.xcconfig
```
// 基础配置
IPHONEOS_DEPLOYMENT_TARGET = 15.0
SWIFT_VERSION = 5.9
TARGETED_DEVICE_FAMILY = 1,2

// 警告设置
GCC_WARN_INHIBIT_ALL_WARNINGS = NO
GCC_TREAT_WARNINGS_AS_ERRORS = YES
SWIFT_TREAT_WARNINGS_AS_ERRORS = YES
CLANG_WARN_DOCUMENTATION_COMMENTS = YES
CLANG_WARN_QUOTED_INCLUDE_IN_FRAMEWORK_HEADER = YES

// SwiftUI Preview
ENABLE_PREVIEWS = YES

// 模块化
DEFINES_MODULE = YES
ALWAYS_EMBED_SWIFT_STANDARD_LIBRARIES = YES
```

### Debug.xcconfig
```
#include "Shared.xcconfig"

// 编译优化
SWIFT_OPTIMIZATION_LEVEL = -Onone
SWIFT_COMPILATION_MODE = singlefile
GCC_OPTIMIZATION_LEVEL = 0
SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG

// 调试符号
DEBUG_INFORMATION_FORMAT = dwarf
GCC_GENERATE_DEBUGGING_SYMBOLS = YES

// 运行时检查
ENABLE_TESTABILITY = YES
ENABLE_NS_ASSERTIONS = YES
ENABLE_STRICT_OBJC_MSGSEND = YES

// 其他
ONLY_ACTIVE_ARCH = YES
VALIDATE_PRODUCT = NO
```

### Release.xcconfig
```
#include "Shared.xcconfig"

// 编译优化
SWIFT_OPTIMIZATION_LEVEL = -O
SWIFT_COMPILATION_MODE = wholemodule
GCC_OPTIMIZATION_LEVEL = s
SWIFT_ACTIVE_COMPILATION_CONDITIONS = RELEASE

// 调试符号
DEBUG_INFORMATION_FORMAT = dwarf-with-dsym
GCC_GENERATE_DEBUGGING_SYMBOLS = YES

// 代码剥离
STRIP_INSTALLED_PRODUCT = YES
COPY_PHASE_STRIP = YES
STRIP_STYLE = non-global
DEAD_CODE_STRIPPING = YES

// 运行时检查
ENABLE_TESTABILITY = NO
ENABLE_NS_ASSERTIONS = NO
VALIDATE_PRODUCT = YES

// 其他
ONLY_ACTIVE_ARCH = NO
```

### Staging.xcconfig
```
#include "Release.xcconfig"

// 覆盖 Bundle ID
PRODUCT_BUNDLE_IDENTIFIER = com.company.app.staging

// 自定义构建标识
STAGING_BUILD = 1

// API 端点
API_BASE_URL = https:/$()/staging.api.company.com
```

### 在项目中应用
1. Project → Info → Configurations
2. 为每个配置选择对应的 xcconfig 文件
3. 在 Build Settings 中不要覆盖 xcconfig 中的值（显示为 green）

## 环境变量注入

### 方法 1: Info.plist + xcconfig
```
// Config/Debug.xcconfig
API_BASE_URL = https:/$()/dev.api.company.com
APP_ENVIRONMENT = Development

// Info.plist
<key>APIBaseURL</key>
<string>$(API_BASE_URL)</string>
<key>AppEnvironment</key>
<string>$(APP_ENVIRONMENT)</string>

// Swift 读取
let apiBaseURL = Bundle.main.object(forInfoDictionaryKey: "APIBaseURL") as! String
```

### 方法 2: 编译时生成 Swift 文件
```bash
# Build Phase: Run Script (在 Compile Sources 之前)
cat > "${SRCROOT}/Generated/BuildConfig.swift" << EOF
// Auto-generated, do not edit
struct BuildConfig {
    static let apiBaseURL = "${API_BASE_URL}"
    static let environment = "${CONFIGURATION}"
}
EOF
```

### 方法 3: Swift Package Manager
```swift
// Package.swift - 定义编译条件
let package = Package(
    name: "MyApp",
    targets: [
        .target(
            name: "MyApp",
            swiftSettings: [
                .define("DEBUG", .when(configuration: .debug)),
                .define("STAGING", .when(configuration: .release)),
            ]
        )
    ]
)

// 代码中使用
#if DEBUG
let apiBaseURL = "https://dev.api.company.com"
#elseif STAGING
let apiBaseURL = "https://staging.api.company.com"
#else
let apiBaseURL = "https://api.company.com"
#endif
```

## Build Settings 深度配置

### 警告和错误
```
// 推荐启用的警告
CLANG_WARN_BLOCK_CAPTURE_AUTORELEASING = YES
CLANG_WARN_BOOL_CONVERSION = YES
CLANG_WARN_COMMA = YES
CLANG_WARN_CONSTANT_CONVERSION = YES
CLANG_WARN_DEPRECATED_OBJC_IMPLEMENTATIONS = YES
CLANG_WARN_EMPTY_BODY = YES
CLANG_WARN_ENUM_CONVERSION = YES
CLANG_WARN_INFINITE_RECURSION = YES
CLANG_WARN_INT_CONVERSION = YES
CLANG_WARN_NON_LITERAL_NULL_CONVERSION = YES
CLANG_WARN_OBJC_IMPLICIT_RETAIN_SELF = YES
CLANG_WARN_OBJC_LITERAL_CONVERSION = YES
CLANG_WARN_RANGE_LOOP_ANALYSIS = YES
CLANG_WARN_STRICT_PROTOTYPES = YES
CLANG_WARN_SUSPICIOUS_MOVE = YES
CLANG_WARN_UNREACHABLE_CODE = YES
GCC_WARN_64_TO_32_BIT_CONVERSION = YES
GCC_WARN_ABOUT_RETURN_TYPE = YES
GCC_WARN_UNDECLARED_SELECTOR = YES
GCC_WARN_UNINITIALIZED_AUTOS = YES
GCC_WARN_UNUSED_FUNCTION = YES
GCC_WARN_UNUSED_VARIABLE = YES
```

### Swift 编译器标志
```
// Debug
OTHER_SWIFT_FLAGS = -Xfrontend -warn-long-function-bodies=100 -Xfrontend -warn-long-expression-type-checking=100

// 严格并发检查 (Swift 6 准备)
SWIFT_STRICT_CONCURRENCY = complete

// 启用即将推出的功能
OTHER_SWIFT_FLAGS = $(inherited) -enable-upcoming-feature StrictConcurrency
```

### 链接优化
```
// 死代码消除
DEAD_CODE_STRIPPING = YES

// 链接时优化 (LTO) - 减小包体，增加编译时间
LLVM_LTO = YES_THIN  // monolithic 更激进但更慢

// 去除未使用的符号
STRIP_STYLE = non-global
STRIPFLAGS = -x
```

### App Thinning
```
// Asset Catalog 按需资源
ENABLE_ON_DEMAND_RESOURCES = YES

// Bitcode (已废弃)
ENABLE_BITCODE = NO

// 编译选项
ASSETCATALOG_COMPILER_OPTIMIZATION = space
```

## 多 Target 配置

### 主 App vs Extensions 共享配置
```
// Shared.xcconfig
MARKETING_VERSION = 2.1.0
CURRENT_PROJECT_VERSION = 42
IPHONEOS_DEPLOYMENT_TARGET = 15.0

// App.xcconfig
#include "Shared.xcconfig"
PRODUCT_BUNDLE_IDENTIFIER = com.company.app
INFOPLIST_FILE = MyApp/Info.plist

// Extension.xcconfig
#include "Shared.xcconfig"
PRODUCT_BUNDLE_IDENTIFIER = com.company.app.widget
INFOPLIST_FILE = Widget/Info.plist
IPHONEOS_DEPLOYMENT_TARGET = 16.0  // Widget 需要更高版本
```

### 共享 Framework 配置
```
// Framework.xcconfig
PRODUCT_NAME = MyFramework
DEFINES_MODULE = YES
SKIP_INSTALL = NO
BUILD_LIBRARY_FOR_DISTRIBUTION = YES  // ABI 稳定性
VERSIONING_SYSTEM = apple-generic
DYLIB_COMPATIBILITY_VERSION = 1
DYLIB_CURRENT_VERSION = 1
INSTALL_PATH = @rpath
LD_RUNPATH_SEARCH_PATHS = $(inherited) @executable_path/Frameworks @loader_path/Frameworks
```

## 构建性能优化

### 并行编译
```
// Build Settings
SWIFT_ENABLE_BATCH_MODE = YES  // 批量编译多个文件

// 命令行
xcodebuild -jobs $(sysctl -n hw.ncpu)  # 使用所有 CPU 核心
```

### 增量编译优化
```
// 避免触发全量重编译
// 1. 不修改 public header
// 2. 使用 @_spi 替代 internal
// 3. 分离接口和实现

@_spi(Internal) public func helperMethod() { }
```

### 编译时间分析
```
// Build Settings
OTHER_SWIFT_FLAGS = -Xfrontend -debug-time-function-bodies -Xfrontend -debug-time-compilation

// 命令行构建后
grep -r "took" build.log | sort -t. -k1 -n | tail -20
```

### DerivedData 优化
```bash
# 移动到更快的磁盘
defaults write com.apple.dt.Xcode IDECustomDerivedDataLocation -string "/Volumes/SSD/DerivedData"

# 定期清理
rm -rf ~/Library/Developer/Xcode/DerivedData/*
```

## 包体积优化

### Asset Catalog 优化
```
// Build Settings
ASSETCATALOG_COMPILER_OPTIMIZATION = space
ASSETCATALOG_COMPILER_GENERATE_ASSET_SYMBOLS = YES  // 类型安全的资源访问

// 启用 App Thinning
COMPRESS_PNG_FILES = YES
REMOVE_TEXT_METADATA_FROM_PNGS = YES
```

### 资源压缩
```bash
# Build Phase: Run Script (Archive 前)
if [ "${CONFIGURATION}" = "Release" ]; then
    # 压缩图片
    find "${TARGET_BUILD_DIR}/${UNLOCALIZED_RESOURCES_FOLDER_PATH}" -name "*.png" -exec pngquant --ext .png --force 256 {} \;
    
    # 去除 PDF 元数据
    find "${TARGET_BUILD_DIR}/${UNLOCALIZED_RESOURCES_FOLDER_PATH}" -name "*.pdf" -exec exiftool -all= -overwrite_original {} \;
fi
```

### 依赖瘦身
```
// CocoaPods - 移除架构
post_install do |installer|
  installer.pods_project.targets.each do |target|
    target.build_configurations.each do |config|
      config.build_settings['EXCLUDED_ARCHS[sdk=iphonesimulator*]'] = 'arm64'  # 模拟器不需要 arm64
    end
  end
end
```

### 代码剥离
```
// Build Settings
SWIFT_OPTIMIZATION_LEVEL = -Osize  # 大小优化而非速度
GCC_OPTIMIZATION_LEVEL = s

DEPLOYMENT_POSTPROCESSING = YES
STRIP_INSTALLED_PRODUCT = YES
STRIP_SWIFT_SYMBOLS = YES

// 移除调试符号（dSYM 单独保存）
COPY_PHASE_STRIP = YES
```

## 安全配置

### 代码签名强化
```
// Build Settings
CODE_SIGN_INJECT_BASE_ENTITLEMENTS = NO  // 禁止注入基础 entitlement
ENABLE_HARDENED_RUNTIME = YES             // macOS 强化运行时

// Entitlements
<key>com.apple.security.get-task-allow</key>
<false/>  <!-- Release 必须为 false -->
```

### App Transport Security
```xml
<!-- Info.plist -->
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <false/>
    <key>NSExceptionDomains</key>
    <dict>
        <key>example.com</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <true/>
            <key>NSIncludesSubdomains</key>
            <true/>
        </dict>
    </dict>
</dict>
```

### 隐私配置
```
// Build Settings - 禁用隐私敏感的分析功能
CLANG_ANALYZER_LOCALIZABILITY_NONLOCALIZED = YES

// Info.plist - 必需的隐私声明
<key>NSCameraUsageDescription</key>
<string>需要访问相机以拍摄照片</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>需要访问相册以选择图片</string>
```

## 调试配置

### LLDB 断点命令
```bash
# .lldbinit
command alias bd breakpoint disable
command alias be breakpoint enable
command alias bl breakpoint list
command alias bp breakpoint set

# 自动导入
settings set target.load-cwd-lldbinit true
```

### 运行时参数
```
// Scheme → Run → Arguments → Arguments Passed On Launch
-com.apple.CoreData.SQLDebug 1         // Core Data SQL 日志
-com.apple.CoreData.ConcurrencyDebug 1 // 并发调试

// Environment Variables
OS_ACTIVITY_MODE = disable             // 禁用系统日志噪音
IDEPreferLogStreaming = YES            // Xcode 控制台流式输出
```

### 性能测试配置
```
// Build Settings for Profiling
GCC_GENERATE_TEST_COVERAGE_FILES = YES
GCC_INSTRUMENT_PROGRAM_FLOW_ARCS = YES

// 或用 Scheme → Profile
// 编辑 Profile scheme → Build Configuration → Release
```

## 版本管理

### 自动化版本号
```bash
# Build Phase: Run Script
if [ $CONFIGURATION = "Release" ]; then
    # Marketing Version 从 Git Tag 读取
    VERSION=$(git describe --tags --abbrev=0 2>/dev/null | sed 's/v//')
    if [ -n "$VERSION" ]; then
        /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "${INFOPLIST_FILE}"
    fi
    
    # Build Number = 提交次数
    BUILD_NUMBER=$(git rev-list --count HEAD)
    /usr/libexec/PlistBuddy -c "Set :CFBundleVersion $BUILD_NUMBER" "${INFOPLIST_FILE}"
fi
```

### agvtool 使用
```bash
# 启用自动版本管理
xcrun agvtool bump -all                # 递增 Build Number
xcrun agvtool new-version 1.2.0        # 设置 Marketing Version
xcrun agvtool new-version -all 42      # 设置 Build Number
xcrun agvtool what-version             # 查看当前版本
```

## Troubleshooting

### 清理构建缓存
```bash
# 完全清理
rm -rf ~/Library/Developer/Xcode/DerivedData
rm -rf ~/Library/Caches/com.apple.dt.Xcode
xcodebuild clean -workspace MyApp.xcworkspace -scheme MyApp

# 重置包管理器
pod deintegrate && pod install
swift package reset && swift package resolve
```

### 常见构建错误

#### Code Signing 错误
```bash
# 检查可用身份
security find-identity -v -p codesigning

# 检查配置文件
security cms -D -i profile.mobileprovision

# 匹配证书和配置文件
/usr/libexec/PlistBuddy -c 'Print :Entitlements:application-identifier' /dev/stdin <<< \
  $(security cms -D -i profile.mobileprovision)
```

#### Module Not Found
```
// 解决方案
1. Product → Clean Build Folder
2. 检查 Framework Search Paths
3. 确认 Target Dependencies
4. swift package reset
```

#### Duplicate Symbol
```
// 检查重复文件
grep -r "duplicate symbol" build.log

// 排除重复资源
Build Settings → EXCLUDED_SOURCE_FILE_NAMES = DuplicateFile.swift
```

### 构建日志分析
```bash
# 生成详细日志
xcodebuild ... | tee build.log | xcpretty

# 分析编译时间
awk '/CompileSwift/ {print $8, $NF}' build.log | sort -n

# 查找警告
grep "warning:" build.log | sort | uniq -c

# 统计错误
grep "error:" build.log | wc -l
```
