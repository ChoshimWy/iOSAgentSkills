# 导航架构参考

> UIKit Coordinator Pattern 和 SwiftUI NavigationStack 导航架构指南

## 目录
- [UIKit: Coordinator Pattern](#uikit-coordinator-pattern)
- [SwiftUI: NavigationStack + Router](#swiftui-navigationstack--router)
- [深度链接](#深度链接)

---

## UIKit: Coordinator Pattern

### 核心概念

Coordinator 将导航逻辑从 ViewController 分离：
- ViewController 不知道其他 ViewController
- 导航流程集中管理
- 支持深度链接和复杂场景

### 基础协议

```swift
protocol Coordinator: AnyObject {
    var childCoordinators: [Coordinator] { get set }
    var navigationController: UINavigationController { get set }
    
    func start()
}

extension Coordinator {
    func addChild(_ coordinator: Coordinator) {
        childCoordinators.append(coordinator)
    }
    
    func removeChild(_ coordinator: Coordinator) {
        childCoordinators.removeAll { $0 === coordinator }
    }
}
```

### App Coordinator

```swift
final class AppCoordinator: Coordinator {
    var childCoordinators: [Coordinator] = []
    var navigationController: UINavigationController
    private let window: UIWindow
    
    init(window: UIWindow) {
        self.window = window
        self.navigationController = UINavigationController()
    }
    
    func start() {
        window.rootViewController = navigationController
        window.makeKeyAndVisible()
        
        if AuthService.shared.isLoggedIn {
            showMain()
        } else {
            showAuth()
        }
    }
    
    private func showMain() {
        let coordinator = MainCoordinator(navigationController: navigationController)
        addChild(coordinator)
        coordinator.start()
    }
}
```

### Feature Coordinator

```swift
final class HomeCoordinator: Coordinator {
    var childCoordinators: [Coordinator] = []
    var navigationController: UINavigationController
    weak var parentCoordinator: MainCoordinator?
    
    init(navigationController: UINavigationController) {
        self.navigationController = navigationController
    }
    
    func start() {
        let viewModel = HomeViewModel()
        viewModel.coordinator = self
        let vc = HomeViewController(viewModel: viewModel)
        navigationController.setViewControllers([vc], animated: false)
    }
    
    func showDetail(item: Item) {
        let viewModel = DetailViewModel(item: item)
        viewModel.coordinator = self
        let vc = DetailViewController(viewModel: viewModel)
        navigationController.pushViewController(vc, animated: true)
    }
}
```

### ViewModel 集成

```swift
@MainActor
final class HomeViewModel {
    weak var coordinator: HomeCoordinator?
    
    func didSelectItem(_ item: Item) {
        coordinator?.showDetail(item: item)
    }
}
```

### 内存管理

```swift
// ❌ 错误：循环引用
class HomeViewModel {
    var coordinator: HomeCoordinator?  // 应该是 weak
}

// ✅ 正确
class HomeViewModel {
    weak var coordinator: HomeCoordinator?
}
```

---

## SwiftUI: NavigationStack + Router

### Router 对象

```swift
@Observable
@MainActor
final class Router {
    var path = NavigationPath()
    
    func navigate(to destination: Destination) {
        path.append(destination)
    }
    
    func pop() {
        path.removeLast()
    }
    
    func popToRoot() {
        path = NavigationPath()
    }
}

enum Destination: Hashable {
    case detail(Item)
    case settings
    case profile(User)
}
```

### 使用示例

```swift
@main
struct MyApp: App {
    @State private var router = Router()
    
    var body: some Scene {
        WindowGroup {
            NavigationStack(path: $router.path) {
                HomeView()
                    .navigationDestination(for: Destination.self) { destination in
                        switch destination {
                        case .detail(let item):
                            DetailView(item: item)
                        case .settings:
                            SettingsView()
                        case .profile(let user):
                            ProfileView(user: user)
                        }
                    }
            }
            .environment(router)
        }
    }
}
```

### View 中使用

```swift
struct HomeView: View {
    @Environment(Router.self) var router
    let items: [Item]
    
    var body: some View {
        List(items) { item in
            Button(item.name) {
                router.navigate(to: .detail(item))
            }
        }
    }
}
```

### Sheet/FullScreenCover

```swift
struct ContentView: View {
    @State private var presentedItem: Item?
    
    var body: some View {
        List {
            // ...
        }
        .sheet(item: $presentedItem) { item in
            DetailSheet(item: item)
        }
    }
}

struct DetailSheet: View {
    @Environment(\.dismiss) var dismiss
    let item: Item
    
    var body: some View {
        NavigationStack {
            DetailView(item: item)
                .navigationTitle(item.name)
                .toolbar {
                    Button("Close") { dismiss() }
                }
        }
    }
}
```

---

## 深度链接

### UIKit Coordinator

```swift
extension AppCoordinator {
    func handle(deepLink: DeepLink) {
        guard AuthService.shared.isLoggedIn else {
            pendingDeepLink = deepLink
            return
        }
        
        switch deepLink {
        case .item(let id):
            navigateToItem(id: id)
        case .settings:
            navigateToSettings()
        }
    }
    
    private func navigateToItem(id: String) {
        Task {
            do {
                let item = try await ItemService.shared.fetchItem(id: id)
                await MainActor.run {
                    // 导航到详情页
                }
            } catch {
                // 处理错误
            }
        }
    }
}
```

### SwiftUI Router

```swift
extension Router {
    func handle(url: URL) {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: true) else {
            return
        }
        
        switch components.path {
        case "/item":
            if let id = components.queryItems?.first(where: { $0.name == "id" })?.value {
                navigate(to: .detail(Item(id: id)))
            }
        case "/settings":
            navigate(to: .settings)
        default:
            break
        }
    }
}

// 使用
.onOpenURL { url in
    router.handle(url: url)
}
```

---

## 最佳实践

### 何时使用 Coordinator
- ✅ UIKit 中型以上项目（5+ 屏幕）
- ✅ 复杂导航流程（多分支、条件导航）
- ✅ 需要深度链接支持
- ❌ 简单项目（2-3 屏幕线性流程）
- ❌ 纯 SwiftUI 项目（用 NavigationStack + Router）

### SwiftUI 导航原则
- 优先 `NavigationStack` 而非 `NavigationView`
- 用 `navigationDestination(for:)` 实现类型安全
- 复杂流程用 Router 对象管理 `NavigationPath`
- Sheet/FullScreenCover 内部处理 `dismiss()`
- 避免嵌套 `NavigationStack`
