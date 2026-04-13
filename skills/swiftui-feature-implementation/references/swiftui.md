# SwiftUI 开发参考

> 完整的 SwiftUI 开发最佳实践，涵盖状态管理、现代 API、性能优化、动画和布局

## 目录
- [状态管理](#状态管理)
- [现代 API](#现代-api)
- [视图组合](#视图组合)
- [列表与性能](#列表与性能)
- [导航](#导航)
- [动画](#动画)
- [布局](#布局)
- [预览](#预览)

---

## 状态管理

### 属性包装器选择指南

| 包装器 | 使用场景 | 说明 |
|--------|---------|------|
| `@State` | View 内部拥有的状态 | **必须** `private` |
| `@Binding` | 子视图需要**修改**父状态 | 不用于只读 |
| `@Bindable` | 注入的 `@Observable` 对象需要绑定 | iOS 17+ |
| `let` | 只读值从父传入 | 最简单 |
| `var` | 只读值，通过 `.onChange()` 响应 | 响应式读取 |

**遗留 API（iOS 17 之前）：**
| 包装器 | 使用场景 | 说明 |
|--------|---------|------|
| `@StateObject` | View 拥有 `ObservableObject` | 用 `@State` + `@Observable` 替代 |
| `@ObservedObject` | 注入的 `ObservableObject` | 不要内联创建 |

### @State（必须 private）

```swift
// ✅ 正确
@State private var isExpanded = false
@State private var selectedTab = 0

// ❌ 错误 - 不是 private
@State var count = 0  // 会被父 View 初始值覆盖！
```

**为什么 private？** 明确该状态由 View 拥有，防止父 View 传初始值（会被忽略）。

### iOS 17+ @Observable（首选）

**优先使用 `@Observable` 而非 `ObservableObject`。**

```swift
@Observable
@MainActor  // 必须标注，确保线程安全
final class DataModel {
    var name = "Some Name"
    var count = 0
}

struct MyView: View {
    @State private var model = DataModel()  // 用 @State，不是 @StateObject

    var body: some View {
        VStack {
            TextField("Name", text: $model.name)
            Stepper("Count: \(model.count)", value: $model.count)
        }
    }
}
```

### @Binding（仅用于修改）

```swift
// ✅ 正确 - 子视图需要修改
struct ToggleView: View {
    @Binding var isOn: Bool
    
    var body: some View {
        Button("Toggle") {
            isOn.toggle()  // 修改父状态
        }
    }
}

// ❌ 错误 - 只读不需要 @Binding
struct DisplayView: View {
    @Binding var text: String  // 浪费！应该用 let
    
    var body: some View {
        Text(text)  // 只读
    }
}

// ✅ 正确 - 只读用 let
struct DisplayView: View {
    let text: String
    
    var body: some View {
        Text(text)
    }
}
```

### @Bindable（iOS 17+）

用于注入的 `@Observable` 对象需要创建绑定时：

```swift
@Observable
@MainActor
final class Settings {
    var username = ""
    var notificationsEnabled = true
}

struct SettingsView: View {
    @Bindable var settings: Settings  // 注入的对象
    
    var body: some View {
        Form {
            TextField("Username", text: $settings.username)  // 需要 $
            Toggle("Notifications", isOn: $settings.notificationsEnabled)
        }
    }
}
```

### 不要把传入值声明为 @State

```swift
// ❌ 错误 - @State 只接受初始值，后续更新会被忽略！
struct ItemView: View {
    @State var item: Item  // 父 View 传入的值变化不会反映！
}

// ✅ 正确 - 用 let
struct ItemView: View {
    let item: Item
}

// ✅ 正确 - 需要修改用 @Binding
struct ItemView: View {
    @Binding var item: Item
}
```

---

## 现代 API

### 样式和外观

```swift
// ✅ 现代 API
Text("Hello")
    .foregroundStyle(.primary)  // 支持层级样式、渐变、材质

Image("photo")
    .clipShape(.rect(cornerRadius: 12))  // 明确、支持所有形状

// ❌ 已废弃
Text("Hello")
    .foregroundColor(.primary)

Image("photo")
    .cornerRadius(12)  // 已废弃
```

### 导航

```swift
// ✅ 现代 - NavigationStack + 类型安全
NavigationStack {
    List(items) { item in
        NavigationLink(value: item) {
            Text(item.name)
        }
    }
    .navigationDestination(for: Item.self) { item in
        DetailView(item: item)
    }
}

// ❌ 遗留 - NavigationView
NavigationView {
    List(items) { item in
        NavigationLink(destination: DetailView(item: item)) {
            Text(item.name)
        }
    }
}
```

### Tabs（iOS 18+）

```swift
// ✅ 现代 - Tab API
TabView {
    Tab("Home", systemImage: "house") {
        HomeView()
    }
    Tab("Search", systemImage: "magnifyingglass") {
        SearchView()
    }
}

// ❌ 遗留 - tabItem()
TabView {
    HomeView()
        .tabItem { Label("Home", systemImage: "house") }
}
```

### 其他现代 API

```swift
// ✅ Button 而非 onTapGesture（除非需要位置/次数）
Button("Tap me") { action() }

// ✅ .onChange 双参数版本
.onChange(of: searchText) { oldValue, newValue in
    performSearch(newValue)
}

// ✅ .task 自动取消异步任务
.task {
    await loadData()
}

// ✅ .task(id:) 值变化时重启任务
.task(id: userID) {
    await loadUser(id: userID)
}

// ✅ .sheet(item:) 而非 .sheet(isPresented:)
.sheet(item: $selectedItem) { item in
    DetailView(item: item)
}
```

---

## 视图组合

### 保持 View body 简单

```swift
// ✅ 正确 - 提取为子视图
var body: some View {
    VStack {
        HeaderView()
        ContentView()
        FooterView()
    }
}

// ❌ 错误 - body 太长
var body: some View {
    VStack {
        HStack {
            Image(systemName: "person")
            Text("Profile")
            Spacer()
            Button("Edit") { }
        }
        // ... 50 行代码 ...
    }
}
```

### 用修饰符而非条件视图

```swift
// ✅ 正确 - 保持视图身份
Circle()
    .fill(isSelected ? Color.blue : Color.gray)
    .scaleEffect(isSelected ? 1.2 : 1.0)

// ❌ 错误 - 破坏视图身份，动画不流畅
if isSelected {
    Circle().fill(Color.blue).scaleEffect(1.2)
} else {
    Circle().fill(Color.gray)
}
```

### 分离业务逻辑

```swift
// ✅ 正确 - 逻辑在 ViewModel
struct LoginView: View {
    @State private var viewModel = LoginViewModel()
    
    var body: some View {
        Button("Login") {
            viewModel.login()  // 调用方法
        }
    }
}

// ❌ 错误 - 内联业务逻辑
Button("Login") {
    // 10 行登录逻辑
    let credentials = ...
    networkService.login(credentials)
    ...
}
```

---

## 列表与性能

### ForEach 必须用稳定 ID

```swift
// ✅ 正确 - Identifiable
extension User: Identifiable {
    var id: String { userId }
}

ForEach(users) { user in
    UserRow(user: user)
}

// ✅ 正确 - keyPath
ForEach(users, id: \.userId) { user in
    UserRow(user: user)
}

// ❌ 错误 - 使用 indices（动态内容）
ForEach(users.indices, id: \.self) { index in
    UserRow(user: users[index])  // 删除时会崩溃！
}
```

### 避免内联过滤

```swift
// ❌ 错误 - 每次更新都重新过滤
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

### 只传递需要的值

```swift
// ✅ 正确 - 传递具体值
ForEach(users) { user in
    UserRow(name: user.name, avatar: user.avatar)
}

// ❌ 错误 - 传递整个对象（可能有不需要的依赖）
ForEach(users) { user in
    UserRow(user: user)  // user 的所有属性变化都会触发更新
}
```

### 热路径优化

```swift
// ❌ 错误 - 滚动时频繁更新
.onPreferenceChange(ScrollOffsetKey.self) { offset in
    currentOffset = offset  // 每帧都触发！
}

// ✅ 正确 - 只在跨阈值时更新
.onPreferenceChange(ScrollOffsetKey.self) { offset in
    let shouldShow = offset.y > 100
    if shouldShow != showHeader {
        showHeader = shouldShow  // 只在状态变化时更新
    }
}
```

---

## 导航

### NavigationStack（iOS 16+）

```swift
@Observable
@MainActor
final class Router {
    var path = NavigationPath()
    
    func navigate(to destination: Destination) {
        path.append(destination)
    }
    
    func popToRoot() {
        path = NavigationPath()
    }
}

enum Destination: Hashable {
    case detail(Item)
    case settings
}

// 使用
NavigationStack(path: $router.path) {
    HomeView()
        .navigationDestination(for: Destination.self) { destination in
            switch destination {
            case .detail(let item):
                DetailView(item: item)
            case .settings:
                SettingsView()
            }
        }
}
.environment(router)
```

### Sheet 管理

```swift
// ✅ 正确 - Sheet 内部处理 dismiss
struct AddItemSheet: View {
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            Form { /* ... */ }
                .navigationTitle("Add Item")
                .toolbar {
                    Button("Cancel") { dismiss() }
                    Button("Save") {
                        saveItem()
                        dismiss()
                    }
                }
        }
    }
}

// 使用
.sheet(item: $presentedItem) { item in
    AddItemSheet(item: item)
}
```

---

## 动画

### 使用 value 参数

```swift
// ✅ 正确 - 指定触发值
Rectangle()
    .frame(width: isExpanded ? 200 : 100)
    .animation(.spring, value: isExpanded)

// ❌ 错误 - 已废弃，会动画所有变化
Rectangle()
    .frame(width: isExpanded ? 200 : 100)
    .animation(.spring)  // 废弃！
```

### 隐式 vs 显式动画

```swift
// 隐式 - 特定值变化时动画
.animation(.spring, value: isExpanded)

// 显式 - 事件驱动动画
Button("Toggle") {
    withAnimation(.spring) {
        isExpanded.toggle()
    }
}
```

### 动画修饰符位置

```swift
// ✅ 正确 - 动画在被动画属性之后
Rectangle()
    .frame(width: size)
    .foregroundStyle(color)
    .animation(.default, value: animateTrigger)

// ❌ 错误 - 动画太早
Rectangle()
    .animation(.default, value: animateTrigger)
    .frame(width: size)  // 不会被动画！
```

---

## 布局

### 避免硬编码尺寸

```swift
// ✅ 正确 - 相对布局
.frame(maxWidth: .infinity)
.padding()

// ❌ 错误 - 硬编码
.frame(width: UIScreen.main.bounds.width - 40)
```

### GeometryReader 替代方案

```swift
// ✅ 优先 - containerRelativeFrame
Text("Hello")
    .containerRelativeFrame(.horizontal) { length, _ in
        length * 0.8
    }

// ⚠️ 备选 - GeometryReader（最后选择）
GeometryReader { geometry in
    Text("Hello")
        .frame(width: geometry.size.width * 0.8)
}
```

---

## 预览

```swift
#Preview("Default") {
    CardView(title: "Title", content: "Content")
}

#Preview("Dark Mode") {
    CardView(title: "Title", content: "Content")
        .preferredColorScheme(.dark)
}

#Preview("Large Font") {
    CardView(title: "Title", content: "Content")
        .environment(\.sizeCategory, .accessibilityExtraExtraExtraLarge)
}

#Preview("Loading State") {
    CardView(title: "Title", content: "Content", isLoading: true)
}
```

---

## 关键原则总结

1. **状态管理**：iOS 17+ 优先 `@Observable`，`@State` 必须 `private`
2. **现代 API**：用 `foregroundStyle()`、`NavigationStack`、`Tab` API
3. **性能**：传递具体值、稳定 ID、避免热路径冗余更新
4. **视图组合**：保持 body 简单、用修饰符而非条件视图
5. **动画**：用 `value:` 参数、修饰符在属性之后
6. **布局**：相对布局、避免 `UIScreen.main.bounds`
