# CI/CD 模板参考

## GitHub Actions 完整示例

### 基础构建与测试
```yaml
name: iOS Build & Test

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

env:
  DEVELOPER_DIR: /Applications/Xcode_15.2.app/Contents/Developer

jobs:
  build-and-test:
    runs-on: macos-14
    
    steps:
    - name: Checkout
      uses: actions/checkout@v4
    
    - name: Cache CocoaPods
      uses: actions/cache@v3
      with:
        path: Pods
        key: ${{ runner.os }}-pods-${{ hashFiles('**/Podfile.lock') }}
        restore-keys: |
          ${{ runner.os }}-pods-
    
    - name: Cache SPM
      uses: actions/cache@v3
      with:
        path: .build
        key: ${{ runner.os }}-spm-${{ hashFiles('**/Package.resolved') }}
        restore-keys: |
          ${{ runner.os }}-spm-
    
    - name: Install Dependencies
      run: |
        gem install bundler
        bundle install
        bundle exec pod install
    
    - name: SwiftLint
      run: |
        brew install swiftlint
        swiftlint lint --reporter github-actions-logging
    
    - name: Build
      run: |
        set -o pipefail
        xcodebuild clean build \
          -workspace MyApp.xcworkspace \
          -scheme MyApp \
          -configuration Debug \
          -destination 'platform=iOS Simulator,name=iPhone 15 Pro,OS=17.2' \
          -derivedDataPath build/DerivedData \
          CODE_SIGN_IDENTITY="" \
          CODE_SIGNING_REQUIRED=NO \
          | xcpretty
    
    - name: Test
      run: |
        set -o pipefail
        xcodebuild test \
          -workspace MyApp.xcworkspace \
          -scheme MyApp \
          -destination 'platform=iOS Simulator,name=iPhone 15 Pro,OS=17.2' \
          -derivedDataPath build/DerivedData \
          -enableCodeCoverage YES \
          -resultBundlePath build/TestResults.xcresult \
          | xcpretty
    
    - name: Code Coverage
      run: |
        xcrun xccov view --report build/TestResults.xcresult > coverage.txt
        cat coverage.txt
    
    - name: Upload Test Results
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: test-results
        path: build/TestResults.xcresult
```

### App Store 发布
```yaml
name: Deploy to App Store

on:
  push:
    tags:
      - 'v*'

env:
  DEVELOPER_DIR: /Applications/Xcode_15.2.app/Contents/Developer

jobs:
  deploy:
    runs-on: macos-14
    
    steps:
    - name: Checkout
      uses: actions/checkout@v4
    
    - name: Import Certificate
      env:
        CERTIFICATE_BASE64: ${{ secrets.BUILD_CERTIFICATE_BASE64 }}
        P12_PASSWORD: ${{ secrets.P12_PASSWORD }}
        KEYCHAIN_PASSWORD: ${{ secrets.KEYCHAIN_PASSWORD }}
      run: |
        # 创建临时 keychain
        security create-keychain -p "$KEYCHAIN_PASSWORD" build.keychain
        security default-keychain -s build.keychain
        security unlock-keychain -p "$KEYCHAIN_PASSWORD" build.keychain
        security set-keychain-settings -lut 21600 build.keychain
        
        # 导入证书
        echo "$CERTIFICATE_BASE64" | base64 --decode > certificate.p12
        security import certificate.p12 \
          -k build.keychain \
          -P "$P12_PASSWORD" \
          -T /usr/bin/codesign \
          -T /usr/bin/productsign
        
        security set-key-partition-list \
          -S apple-tool:,apple: \
          -s \
          -k "$KEYCHAIN_PASSWORD" \
          build.keychain
    
    - name: Import Provisioning Profile
      env:
        PROVISIONING_PROFILE_BASE64: ${{ secrets.PROVISIONING_PROFILE_BASE64 }}
      run: |
        mkdir -p ~/Library/MobileDevice/Provisioning\ Profiles
        echo "$PROVISIONING_PROFILE_BASE64" | base64 --decode > profile.mobileprovision
        
        # 提取 UUID
        UUID=$(grep -aA1 UUID profile.mobileprovision | grep string | sed -e 's/<string>//' -e 's/<\/string>//' -e 's/^[ \t]*//')
        cp profile.mobileprovision ~/Library/MobileDevice/Provisioning\ Profiles/$UUID.mobileprovision
    
    - name: Install Dependencies
      run: |
        bundle install
        bundle exec pod install
    
    - name: Increment Build Number
      run: |
        BUILD_NUMBER=$(($(date +%Y%m%d)00 + $GITHUB_RUN_NUMBER))
        agvtool new-version -all $BUILD_NUMBER
    
    - name: Archive
      env:
        CODE_SIGN_IDENTITY: ${{ secrets.CODE_SIGN_IDENTITY }}
        DEVELOPMENT_TEAM: ${{ secrets.TEAM_ID }}
        PROVISIONING_PROFILE_SPECIFIER: ${{ secrets.PROVISIONING_PROFILE_NAME }}
      run: |
        xcodebuild archive \
          -workspace MyApp.xcworkspace \
          -scheme MyApp \
          -configuration Release \
          -archivePath build/MyApp.xcarchive \
          -destination 'generic/platform=iOS' \
          CODE_SIGN_IDENTITY="$CODE_SIGN_IDENTITY" \
          DEVELOPMENT_TEAM="$DEVELOPMENT_TEAM" \
          PROVISIONING_PROFILE_SPECIFIER="$PROVISIONING_PROFILE_SPECIFIER"
    
    - name: Export IPA
      env:
        EXPORT_OPTIONS_PLIST: ${{ secrets.EXPORT_OPTIONS_PLIST_BASE64 }}
      run: |
        echo "$EXPORT_OPTIONS_PLIST" | base64 --decode > exportOptions.plist
        xcodebuild -exportArchive \
          -archivePath build/MyApp.xcarchive \
          -exportPath build/IPA \
          -exportOptionsPlist exportOptions.plist
    
    - name: Upload to App Store Connect
      env:
        APP_STORE_CONNECT_API_KEY_ID: ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }}
        APP_STORE_CONNECT_ISSUER_ID: ${{ secrets.APP_STORE_CONNECT_ISSUER_ID }}
        APP_STORE_CONNECT_API_KEY_BASE64: ${{ secrets.APP_STORE_CONNECT_API_KEY_BASE64 }}
      run: |
        echo "$APP_STORE_CONNECT_API_KEY_BASE64" | base64 --decode > AuthKey.p8
        xcrun altool --upload-app \
          --type ios \
          --file build/IPA/*.ipa \
          --apiKey "$APP_STORE_CONNECT_API_KEY_ID" \
          --apiIssuer "$APP_STORE_CONNECT_ISSUER_ID"
    
    - name: Upload dSYM to Firebase
      run: |
        ./Pods/FirebaseCrashlytics/upload-symbols \
          -gsp MyApp/GoogleService-Info.plist \
          -p ios build/MyApp.xcarchive/dSYMs
    
    - name: Cleanup Keychain
      if: always()
      run: |
        security delete-keychain build.keychain
```

## GitLab CI 示例

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

variables:
  LC_ALL: "en_US.UTF-8"
  LANG: "en_US.UTF-8"

cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - Pods/
    - .build/

before_script:
  - bundle install
  - bundle exec pod install

test:
  stage: test
  tags:
    - macos
  script:
    - xcodebuild test 
        -workspace MyApp.xcworkspace 
        -scheme MyApp 
        -destination 'platform=iOS Simulator,name=iPhone 15 Pro'
        -enableCodeCoverage YES
        -resultBundlePath coverage.xcresult
    - xcrun xccov view --report coverage.xcresult
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
    paths:
      - coverage.xcresult

build:
  stage: build
  tags:
    - macos
  only:
    - main
  script:
    - xcodebuild archive
        -workspace MyApp.xcworkspace
        -scheme MyApp
        -configuration Release
        -archivePath build/MyApp.xcarchive
        CODE_SIGN_IDENTITY="$CODE_SIGN_IDENTITY"
        DEVELOPMENT_TEAM="$TEAM_ID"
  artifacts:
    paths:
      - build/MyApp.xcarchive
    expire_in: 1 week

deploy:
  stage: deploy
  tags:
    - macos
  only:
    - tags
  dependencies:
    - build
  script:
    - xcodebuild -exportArchive
        -archivePath build/MyApp.xcarchive
        -exportPath build/IPA
        -exportOptionsPlist exportOptions.plist
    - bundle exec fastlane upload_to_testflight
```

## Fastlane 完整配置

### Fastfile
```ruby
default_platform(:ios)

platform :ios do
  
  before_all do
    ensure_git_status_clean unless ENV['CI']
    cocoapods
  end
  
  desc "Run all tests"
  lane :test do
    scan(
      workspace: "MyApp.xcworkspace",
      scheme: "MyApp",
      devices: ["iPhone 15 Pro"],
      code_coverage: true,
      result_bundle: true,
      output_directory: "./fastlane/test_output"
    )
  end
  
  desc "Build for testing in simulator"
  lane :build_for_testing do
    run_tests(
      workspace: "MyApp.xcworkspace",
      scheme: "MyApp",
      build_for_testing: true,
      destination: "platform=iOS Simulator,name=iPhone 15 Pro"
    )
  end
  
  desc "Run tests on pre-built app"
  lane :test_without_building do
    run_tests(
      workspace: "MyApp.xcworkspace",
      scheme: "MyApp",
      test_without_building: true,
      destination: "platform=iOS Simulator,name=iPhone 15 Pro"
    )
  end
  
  desc "Build development app"
  lane :build_dev do
    match(type: "development")
    gym(
      workspace: "MyApp.xcworkspace",
      scheme: "MyApp",
      configuration: "Debug",
      export_method: "development",
      clean: true
    )
  end
  
  desc "Build and upload to TestFlight"
  lane :beta do
    ensure_git_branch(branch: 'main')
    
    # 证书和配置文件
    match(type: "appstore", readonly: true)
    
    # 递增 Build Number
    increment_build_number(
      build_number: latest_testflight_build_number + 1
    )
    
    # 构建
    gym(
      workspace: "MyApp.xcworkspace",
      scheme: "MyApp",
      configuration: "Release",
      export_method: "app-store",
      clean: true,
      output_directory: "./build",
      include_symbols: true,
      include_bitcode: false
    )
    
    # 上传到 TestFlight
    upload_to_testflight(
      skip_waiting_for_build_processing: true,
      changelog: changelog_from_git_commits(
        between: [ENV['GIT_PREVIOUS_SUCCESSFUL_COMMIT'] || "HEAD^^^^^", "HEAD"],
        pretty: "- %s"
      )
    )
    
    # 上传 dSYM 到 Firebase
    upload_symbols_to_crashlytics
    
    # 提交版本号变更
    commit_version_bump(
      message: "chore: bump build number to #{lane_context[SharedValues::BUILD_NUMBER]}"
    )
    push_to_git_remote
  end
  
  desc "Deploy to App Store"
  lane :release do
    ensure_git_branch(branch: 'main')
    
    # 证书和配置文件
    match(type: "appstore", readonly: true)
    
    # 弹出版本号输入
    version = prompt(text: "Enter version number: ")
    increment_version_number(version_number: version)
    
    # 构建
    gym(
      workspace: "MyApp.xcworkspace",
      scheme: "MyApp",
      configuration: "Release",
      export_method: "app-store",
      clean: true
    )
    
    # 上传到 App Store
    upload_to_app_store(
      submit_for_review: false,
      automatic_release: false,
      skip_metadata: false,
      skip_screenshots: false,
      precheck_include_in_app_purchases: false
    )
    
    # 打 Git Tag
    add_git_tag(
      tag: "v#{version}",
      message: "Release v#{version}"
    )
    push_git_tags
    
    # Slack 通知
    slack(
      message: "🎉 MyApp v#{version} has been uploaded to App Store!",
      success: true
    )
  end
  
  desc "Upload dSYM to Firebase Crashlytics"
  lane :upload_dsym do
    upload_symbols_to_crashlytics(
      gsp_path: "./MyApp/GoogleService-Info.plist",
      binary_path: "./Pods/FirebaseCrashlytics/upload-symbols"
    )
  end
  
  desc "Create screenshots for all devices"
  lane :screenshots do
    snapshot(
      workspace: "MyApp.xcworkspace",
      scheme: "MyAppUITests",
      devices: [
        "iPhone 15 Pro Max",
        "iPhone 15 Pro",
        "iPhone SE (3rd generation)",
        "iPad Pro (12.9-inch) (6th generation)"
      ],
      languages: ["en-US", "zh-Hans"],
      output_directory: "./fastlane/screenshots"
    )
  end
  
  after_all do |lane|
    notification(
      subtitle: "Fastlane finished",
      message: "Successfully executed lane: #{lane}"
    )
  end
  
  error do |lane, exception|
    slack(
      message: "❌ Lane #{lane} failed: #{exception.message}",
      success: false
    )
  end
  
end
```

### Matchfile
```ruby
git_url("https://github.com/company/certificates.git")
git_branch("main")

storage_mode("git")

type("development") # development, appstore, adhoc, enterprise

app_identifier(["com.company.app", "com.company.app.staging"])
username("developer@company.com")

team_id("TEAM_ID")
```

### Appfile
```ruby
app_identifier("com.company.app")
apple_id("developer@company.com")
team_id("TEAM_ID")

for_platform :ios do
  for_lane :beta do
    app_identifier("com.company.app")
  end
  
  for_lane :release do
    app_identifier("com.company.app")
  end
end
```

## Jenkins Pipeline

```groovy
pipeline {
    agent { label 'macos' }
    
    environment {
        DEVELOPER_DIR = '/Applications/Xcode_15.2.app/Contents/Developer'
        FASTLANE_SKIP_UPDATE_CHECK = '1'
        FASTLANE_HIDE_CHANGELOG = '1'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Install Dependencies') {
            steps {
                sh '''
                    gem install bundler
                    bundle install
                    bundle exec pod install
                '''
            }
        }
        
        stage('Lint') {
            steps {
                sh 'swiftlint lint --reporter junit > swiftlint.xml'
            }
            post {
                always {
                    junit 'swiftlint.xml'
                }
            }
        }
        
        stage('Test') {
            steps {
                sh '''
                    bundle exec fastlane test
                '''
            }
            post {
                always {
                    junit 'fastlane/test_output/*.junit'
                    publishHTML([
                        reportDir: 'fastlane/test_output',
                        reportFiles: 'report.html',
                        reportName: 'Test Report'
                    ])
                }
            }
        }
        
        stage('Build') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    bundle exec fastlane beta
                '''
            }
        }
        
        stage('Archive Artifacts') {
            steps {
                archiveArtifacts artifacts: 'build/*.ipa', fingerprint: true
                archiveArtifacts artifacts: 'build/*.dSYM.zip', fingerprint: true
            }
        }
    }
    
    post {
        success {
            slackSend(
                color: 'good',
                message: "Build succeeded: ${env.JOB_NAME} ${env.BUILD_NUMBER}"
            )
        }
        failure {
            slackSend(
                color: 'danger',
                message: "Build failed: ${env.JOB_NAME} ${env.BUILD_NUMBER}"
            )
        }
        always {
            cleanWs()
        }
    }
}
```

## Secrets 管理

### GitHub Actions Secrets
需要配置的 Secrets:
```
BUILD_CERTIFICATE_BASE64        # p12 证书 base64 编码
P12_PASSWORD                     # p12 密码
KEYCHAIN_PASSWORD                # 临时 keychain 密码
PROVISIONING_PROFILE_BASE64      # 配置文件 base64 编码
PROVISIONING_PROFILE_NAME        # 配置文件名称
CODE_SIGN_IDENTITY               # 签名身份 "Apple Distribution: ..."
TEAM_ID                          # 开发团队 ID
EXPORT_OPTIONS_PLIST_BASE64      # exportOptions.plist base64 编码
APP_STORE_CONNECT_API_KEY_ID     # App Store Connect API Key ID
APP_STORE_CONNECT_ISSUER_ID      # Issuer ID
APP_STORE_CONNECT_API_KEY_BASE64 # .p8 文件 base64 编码
```

### 创建 Base64 编码
```bash
# 证书
base64 -i certificate.p12 | pbcopy

# 配置文件
base64 -i profile.mobileprovision | pbcopy

# API Key
base64 -i AuthKey_XXXXXX.p8 | pbcopy
```
