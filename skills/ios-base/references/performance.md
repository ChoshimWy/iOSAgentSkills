# 性能优化参考

> SwiftUI 和 UIKit 性能优化最佳实践

## 目录
- [SwiftUI 性能](#swiftui-性能)
- [UIKit 性能](#uikit-性能)
- [图片优化](#图片优化)
- [网络优化](#网络优化)
- [启动优化](#启动优化)
- [缓存策略](#缓存策略)
- [内存优化](#内存优化)

---

## SwiftUI 性能

### 1. 避免冗余状态更新

```swift
// ❌ 错误 - 每次都触发更新
.onReceive(publisher) { value in
    self.currentValue = value
}

// ✅ 正确 - 只在值变化时更新
.onReceive(publisher) { value in
    if self.currentValue != value {
        self.currentValue = value
    }
}
```

### 2. 热路径优化

```swift
// ❌ 错误 - 滚动时持续触发
.onPreferenceChange(ScrollOffsetKey.self) { offset in
    shouldShowTitle = offset.y <= -32
}

// ✅ 正确 - 只在跨阈值时更新
.onPreferenceChange(ScrollOffsetKey.self) { offset in
    let shouldShow = offset.y <= -32
    if shouldShow != shouldShowTitle {
        shouldShowTitle = shouldShow
    }
}
```

### 3. 只传递需要的值

```swift
// ❌ 错误 - 传递整个对象
@Observable
@MainActor
final class AppConfig {
    var theme: Theme
    var fontSize: CGFloat
    var notifications: Bool
}

struct SettingsView: View {
    @State private var config = AppConfig()
    
    var body: some View {
        ThemeSelector(config: config)  // 所有属性变化都触发更新
    }
}

// ✅ 正确 - 传递具体值
struct SettingsView: View {
    @State private var config = AppConfig()
    
    var body: some View {
        ThemeSelector(theme: config.theme)  // 只在 theme 变化时更新
    }
}
```

### 4. ForEach 稳定 ID

```swift
// ❌ 错误 - 不稳定 ID
ForEach(items.indices, id: \.self) { index in
    ItemRow(item: items[index])  // 删除时崩溃
}

// ✅ 正确 - Identifiable
extension Item: Identifiable {
    var id: String { itemID }
}

ForEach(items) { item in
    ItemRow(item: item)
}
```

### 5. 避免内联过滤

```swift
// ❌ 错误 - 每次 body 执行都过滤
ForEach(items.filter { $0.isEnabled }) { item in
    ItemRow(item: item)
}

// ✅ 正确 - 预过滤并缓存
@State private var enabledItems: [Item] = []

var body: some View {
    ForEach(enabledItems) { item in
        ItemRow(item: item)
    }
    .onChange(of: items) { _, newItems in
        enabledItems = newItems.filter { $0.isEnabled }
    }
}
```

### 6. View body 保持纯净

```swift
// ❌ 错误 - body 中做计算
var body: some View {
    let processedData = heavyComputation(rawData)  // 每次重绘都计算！
    return List(processedData) { ... }
}

// ✅ 正确 - 用 computed property 或缓存
@State private var processedData: [Data] = []

var body: some View {
    List(processedData) { ... }
        .onChange(of: rawData) { _, newData in
            processedData = heavyComputation(newData)
        }
}
```

---

## UIKit 性能

### 1. Cell 复用

```swift
// ✅ 正确 - 复用 Cell
override func viewDidLoad() {
    super.viewDidLoad()
    tableView.register(CustomCell.self, forCellReuseIdentifier: "CustomCell")
}

func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
    let cell = tableView.dequeueReusableCell(withIdentifier: "CustomCell", for: indexPath) as! CustomCell
    cell.configure(with: items[indexPath.row])
    return cell
}
```

### 2. 异步图片加载

```swift
class ImageCell: UITableViewCell {
    private var imageLoadTask: Task<Void, Never>?
    
    func configure(with imageURL: URL) {
        imageView?.image = nil
        
        imageLoadTask?.cancel()
        imageLoadTask = Task {
            do {
                let (data, _) = try await URLSession.shared.data(from: imageURL)
                guard !Task.isCancelled else { return }
                
                await MainActor.run {
                    imageView?.image = UIImage(data: data)
                }
            } catch {
                // 处理错误
            }
        }
    }
    
    override func prepareForReuse() {
        super.prepareForReuse()
        imageLoadTask?.cancel()
        imageView?.image = nil
    }
}
```

### 3. 视图层级优化

```swift
// ❌ 错误 - 深层嵌套
view.addSubview(containerView)
containerView.addSubview(innerContainer)
innerContainer.addSubview(contentView)
contentView.addSubview(label)

// ✅ 正确 - 扁平化
view.addSubview(containerView)
containerView.addSubview(label)

// 或用 UIStackView
let stackView = UIStackView(arrangedSubviews: [label1, label2, label3])
stackView.axis = .vertical
view.addSubview(stackView)
```

### 4. 约束性能

```swift
// ❌ 慢 - 逐个激活
label.topAnchor.constraint(equalTo: view.topAnchor).isActive = true
label.leadingAnchor.constraint(equalTo: view.leadingAnchor).isActive = true

// ✅ 快 - 批量激活
NSLayoutConstraint.activate([
    label.topAnchor.constraint(equalTo: view.topAnchor),
    label.leadingAnchor.constraint(equalTo: view.leadingAnchor)
])
```

### 5. Shadow 优化

```swift
// ❌ 慢 - 每帧计算 shadow
view.layer.shadowColor = UIColor.black.cgColor
view.layer.shadowOpacity = 0.3
view.layer.shadowRadius = 4

// ✅ 快 - 预定义 shadowPath
view.layer.shadowPath = UIBezierPath(
    roundedRect: view.bounds,
    cornerRadius: 8
).cgPath
view.layer.shadowColor = UIColor.black.cgColor
view.layer.shadowOpacity = 0.3
view.layer.shadowRadius = 4
```

---

## 图片优化

### 图片降采样

图片内存占用 = 宽 × 高 × 4 bytes（RGBA）。直接加载大图会导致内存暴涨。

```swift
// ❌ 错误 - 加载完整大图（例如 4000×3000 的图片占用 ~46MB）
let image = UIImage(contentsOfFile: imagePath)
imageView.image = image  // ImageView 只有 100×100

// ✅ 正确 - 降采样到显示尺寸
func downsample(imageAt url: URL, to targetSize: CGSize) -> UIImage? {
    let options: [CFString: Any] = [
        kCGImageSourceShouldCache: false,
        kCGImageSourceCreateThumbnailFromImageAlways: true,
        kCGImageSourceCreateThumbnailWithTransform: true,
        kCGImageSourceThumbnailMaxPixelSize: max(targetSize.width, targetSize.height)
    ]
    
    guard let imageSource = CGImageSourceCreateWithURL(url as CFURL, nil),
          let image = CGImageSourceCreateThumbnailAtIndex(imageSource, 0, options as CFDictionary) else {
        return nil
    }
    
    return UIImage(cgImage: image)
}

// 使用
let thumbnail = downsample(imageAt: imageURL, to: imageView.bounds.size)
imageView.image = thumbnail
```

### 异步图片加载（UIKit）

```swift
class ImageCell: UITableViewCell {
    private var imageLoadTask: Task<Void, Never>?
    
    func configure(with imageURL: URL) {
        imageView?.image = nil
        
        // 取消旧任务
        imageLoadTask?.cancel()
        
        imageLoadTask = Task {
            do {
                let (data, _) = try await URLSession.shared.data(from: imageURL)
                guard !Task.isCancelled else { return }
                
                // 降采样
                if let image = downsample(data: data, to: imageView?.bounds.size ?? .zero) {
                    await MainActor.run {
                        imageView?.image = image
                    }
                }
            } catch {
                // 处理错误
            }
        }
    }
    
    override func prepareForReuse() {
        super.prepareForReuse()
        imageLoadTask?.cancel()
        imageView?.image = nil
    }
}
```

### SwiftUI 异步图片

```swift
struct AsyncImageView: View {
    let url: URL
    let size: CGSize
    
    var body: some View {
        AsyncImage(url: url) { phase in
            switch phase {
            case .empty:
                ProgressView()
            case .success(let image):
                image
                    .resizable()
                    .aspectRatio(contentMode: .fill)
            case .failure:
                Image(systemName: "photo")
            @unknown default:
                EmptyView()
            }
        }
        .frame(width: size.width, height: size.height)
    }
}
```

---

## 网络优化

### 1. 并发请求去重

防止相同 URL 的重复请求：

```swift
actor RequestDeduplicator {
    private var inFlightRequests: [URL: Task<Data, Error>] = [:]
    
    func data(from url: URL) async throws -> Data {
        // 如果已有进行中的请求，直接返回
        if let existingTask = inFlightRequests[url] {
            return try await existingTask.value
        }
        
        // 创建新任务
        let task = Task<Data, Error> {
            defer { 
                Task { await removeTask(for: url) }
            }
            let (data, _) = try await URLSession.shared.data(from: url)
            return data
        }
        
        inFlightRequests[url] = task
        return try await task.value
    }
    
    private func removeTask(for url: URL) {
        inFlightRequests[url] = nil
    }
}

// 使用
let deduplicator = RequestDeduplicator()

Task {
    let data = try await deduplicator.data(from: url)
}
```

### 2. URLCache 配置

```swift
let cache = URLCache(
    memoryCapacity: 20 * 1024 * 1024,   // 20 MB
    diskCapacity: 100 * 1024 * 1024,     // 100 MB
    diskPath: "myAppCache"
)
URLCache.shared = cache

// 配置 URLRequest
var request = URLRequest(url: url)
request.cachePolicy = .returnCacheDataElseLoad
request.setValue("gzip", forHTTPHeaderField: "Accept-Encoding")
```

### 3. 请求取消

```swift
class DataService {
    private var loadTask: Task<[Item], Error>?
    
    func loadItems() async throws -> [Item] {
        // 取消旧请求
        loadTask?.cancel()
        
        let task = Task<[Item], Error> {
            let (data, _) = try await URLSession.shared.data(from: url)
            try Task.checkCancellation()  // 检查是否被取消
            return try JSONDecoder().decode([Item].self, from: data)
        }
        
        loadTask = task
        return try await task.value
    }
    
    func cancel() {
        loadTask?.cancel()
    }
}
```

---

## 启动优化

### 分级加载策略

```swift
@main
struct MyApp: App {
    init() {
        // 🔴 首屏必须 - 同步执行
        configureAppearance()
        initializeDatabase()
        
        // 🟡 首帧后执行 - 不阻塞启动
        DispatchQueue.main.async {
            self.preloadCriticalData()
            self.registerNotifications()
        }
        
        // 🟢 低优先级 - 延迟执行
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            self.cleanupOldCache()
            self.checkForUpdates()
        }
    }
    
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
```

### 主线程保护

```swift
// ❌ 错误 - 阻塞主线程
func loadUserProfile() {
    let data = try! Data(contentsOf: fileURL)  // 同步 I/O！
    let profile = try! JSONDecoder().decode(UserProfile.self, from: data)
    self.profile = profile
}

// ✅ 正确 - 后台执行
func loadUserProfile() async {
    do {
        let data = try await URLSession.shared.data(from: fileURL).0
        let profile = try JSONDecoder().decode(UserProfile.self, from: data)
        
        await MainActor.run {
            self.profile = profile  // UI 更新回主线程
        }
    } catch {
        // 处理错误
    }
}
```

### Prefetching

```swift
class ListViewController: UIViewController, UICollectionViewDataSourcePrefetching {
    override func viewDidLoad() {
        super.viewDidLoad()
        collectionView.prefetchDataSource = self
    }
    
    func collectionView(_ collectionView: UICollectionView, prefetchItemsAt indexPaths: [IndexPath]) {
        // 预加载即将显示的 cell 数据
        for indexPath in indexPaths {
            let item = items[indexPath.row]
            Task {
                await imageCache.load(url: item.imageURL)
            }
        }
    }
    
    func collectionView(_ collectionView: UICollectionView, cancelPrefetchingForItemsAt indexPaths: [IndexPath]) {
        // 取消预加载
        for indexPath in indexPaths {
            let item = items[indexPath.row]
            imageCache.cancel(url: item.imageURL)
        }
    }
}
```

---

## 缓存策略

### NSCache 基础

```swift
class ImageCache {
    private let cache = NSCache<NSURL, UIImage>()
    
    init() {
        cache.countLimit = 100        // 最多 100 个对象
        cache.totalCostLimit = 50 * 1024 * 1024  // 50 MB
    }
    
    func image(for url: URL) -> UIImage? {
        cache.object(forKey: url as NSURL)
    }
    
    func setImage(_ image: UIImage, for url: URL) {
        let cost = image.size.width * image.size.height * 4  // 估算内存占用
        cache.setObject(image, forKey: url as NSURL, cost: Int(cost))
    }
}
```

### 缓存策略

```swift
enum CacheStrategy {
    case cacheFirst      // 优先缓存，缓存失效才请求网络
    case networkFirst    // 优先网络，失败才用缓存
    case cacheAndRefresh // 先返回缓存，同时刷新网络数据
}

actor DataCache<T: Codable> {
    private let cache = NSCache<NSString, CacheEntry>()
    private let maxAge: TimeInterval
    
    init(maxAge: TimeInterval = 3600) {
        self.maxAge = maxAge
    }
    
    func get(for key: String, strategy: CacheStrategy, fetch: () async throws -> T) async throws -> T {
        switch strategy {
        case .cacheFirst:
            if let cached = getCached(for: key) {
                return cached
            }
            let data = try await fetch()
            set(data, for: key)
            return data
            
        case .networkFirst:
            do {
                let data = try await fetch()
                set(data, for: key)
                return data
            } catch {
                if let cached = getCached(for: key) {
                    return cached
                }
                throw error
            }
            
        case .cacheAndRefresh:
            let cached = getCached(for: key)
            
            Task {
                let data = try await fetch()
                set(data, for: key)
            }
            
            if let cached {
                return cached
            }
            
            return try await fetch()
        }
    }
    
    private func getCached(for key: String) -> T? {
        guard let entry = cache.object(forKey: key as NSString) else {
            return nil
        }
        
        if Date().timeIntervalSince(entry.timestamp) > maxAge {
            cache.removeObject(forKey: key as NSString)
            return nil
        }
        
        return entry.value as? T
    }
    
    private func set(_ value: T, for key: String) {
        let entry = CacheEntry(value: value, timestamp: Date())
        cache.setObject(entry, forKey: key as NSString)
    }
}

private class CacheEntry: NSObject {
    let value: Any
    let timestamp: Date
    
    init(value: Any, timestamp: Date) {
        self.value = value
        self.timestamp = timestamp
    }
}
```

---

## 内存优化

### 1. 弱引用和循环引用

```swift
// ❌ 错误 - 循环引用
class ViewController: UIViewController {
    var closure: (() -> Void)?
    
    override func viewDidLoad() {
        super.viewDidLoad()
        closure = {
            self.doSomething()  // 强引用 self
        }
    }
}

// ✅ 正确 - weak self
override func viewDidLoad() {
    super.viewDidLoad()
    closure = { [weak self] in
        guard let self else { return }
        self.doSomething()
    }
}
```

### 2. Delegate 必须 weak

```swift
// ✅ 正确
protocol CustomDelegate: AnyObject {
    func didUpdate()
}

class CustomView: UIView {
    weak var delegate: CustomDelegate?
}
```

### 3. Timer 和观察者清理

```swift
class ViewController: UIViewController {
    private var timer: Timer?
    private var observer: NSObjectProtocol?
    
    deinit {
        timer?.invalidate()
        if let observer {
            NotificationCenter.default.removeObserver(observer)
        }
    }
}
```

---

## 性能分析工具

### Instruments
- **Time Profiler**: 找出耗时函数（CPU 性能）
- **Allocations**: 查看内存分配（内存增长）
- **Leaks**: 检测内存泄漏
- **Core Animation**: 渲染性能、帧率分析
- **SwiftUI**: SwiftUI 视图性能分析
- **App Launch**: 启动性能分析

### 深度 Profiling / Benchmark
- `measure(metrics:)`、`XCTApplicationLaunchMetric`、`xcrun xctrace`、Instruments 模板选择和 trace 证据分析统一切到 `ios-performance`。
- 本文档只保留常规性能守则，不再承担专门的性能分析与测试工作流。

### SwiftUI Debug
```swift
// 查看视图重绘
let _ = Self._printChanges()

// Debug 模式追踪
._printChanges()
```

---

## 关键原则

1. **SwiftUI**: 传递具体值、稳定 ID、避免热路径冗余更新、保持 body 纯净
2. **UIKit**: Cell 复用、异步加载、扁平视图层级、批量约束、shadowPath
3. **图片**: 降采样到显示尺寸、计算内存占用（宽×高×4）、prepareForReuse 取消任务
4. **网络**: 并发去重、配置 URLCache、支持请求取消、gzip 压缩
5. **启动**: 首屏同步、首帧后 async、低优先级 asyncAfter、主线程保护
6. **缓存**: NSCache（自动内存管理）、设置 countLimit/totalCostLimit、选择合适策略
7. **内存**: weak self、弱引用 delegate、清理 timer/observer
8. **工具**: 用 Instruments 分析性能瓶颈
