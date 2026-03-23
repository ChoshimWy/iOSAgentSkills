# MV 模式参考

这份参考用于判断一个 SwiftUI 功能是否应保持简单 MV，还是确实需要引入 view model。

## 默认立场
- 默认采用 MV：视图是状态表达和界面编排层，不是业务逻辑容器。
- 在考虑 view model 之前，先用好 `@State`、`@Environment`、`@Query`、`.task`、`.task(id:)` 和 `onChange`。
- 业务逻辑归 service、model 或 domain type，不归 `body`。
- 屏幕变大时，先拆小视图，再考虑是否真的需要多一层 view model。

## 什么情况下不要引入 view model
以下情况通常不值得加 view model：
- 只是镜像本地视图状态。
- 只是包一层已经能从 `@Environment` 拿到的依赖。
- 只是重复 `@Query`、`@State` 或 `Binding` 已经能表达的数据流。
- 只是因为 `body` 太长，其实应先拆子视图。
- 只是承载一次性异步加载逻辑，而这类逻辑本来就能放在 `.task` 和本地状态里。

## 什么情况下可以接受 view model
满足以下任一条件时，可以考虑：
- 用户明确要求。
- 代码库该功能已经统一采用 view model。
- 页面需要长生命周期的引用类型状态，且不适合只放在 service 中。
- 需要桥接非 SwiftUI API。
- 多个视图共享同一份展示层状态，而这份状态又不适合建成全局环境对象。

即便如此，也应让 view model 小、明确、尽量非可选。

## 推荐模式：本地状态 + Environment

```swift
struct FeedView: View {
    @Environment(BlueSkyClient.self) private var client

    enum ViewState {
        case loading
        case error(String)
        case loaded([Post])
    }

    @State private var viewState: ViewState = .loading

    var body: some View {
        List {
            switch viewState {
            case .loading:
                ProgressView("Loading feed...")
            case .error(let message):
                ErrorStateView(message: message, retryAction: { await loadFeed() })
            case .loaded(let posts):
                ForEach(posts) { post in
                    PostRowView(post: post)
                }
            }
        }
        .task { await loadFeed() }
    }

    private func loadFeed() async {
        do {
            let posts = try await client.getFeed()
            viewState = .loaded(posts)
        } catch {
            viewState = .error(error.localizedDescription)
        }
    }
}
```

为什么这种方式更优：
- 状态离渲染它的 UI 很近。
- 依赖直接来自 `@Environment`，而不是额外 wrapper。
- 视图负责界面编排，真正工作仍在 service。

## 推荐模式：用生命周期 modifier 做轻量编排

```swift
.task(id: searchText) {
    guard !searchText.isEmpty else {
        results = []
        return
    }
    await searchFeed(query: searchText)
}

.onChange(of: isInSearch, initial: false) {
    guard !isInSearch else { return }
    Task { await fetchSuggestedFeed() }
}
```

这类本地、轻量的 orchestration 不应默认上升为 view model。

## SwiftData 说明
SwiftData 本身就是把数据流留在视图附近的有力理由。

```swift
struct BookListView: View {
    @Query private var books: [Book]
    @Environment(\.modelContext) private var modelContext

    var body: some View {
        List {
            ForEach(books) { book in
                BookRowView(book: book)
                    .swipeActions {
                        Button("Delete", role: .destructive) {
                            modelContext.delete(book)
                        }
                    }
            }
        }
    }
}
```

除非功能有明确额外需求，否则不要再加一个手动镜像相同状态的 view model。

## 测试建议
- 优先测试 service、业务规则、状态变换和异步流程。
- 视图层使用 preview 或更高层级 UI 测试验证。
- 不要为了“更好测试”而给简单 SwiftUI 视图硬加 view model。

## 重构清单
- 去掉只包装环境依赖或本地状态的 view model。
- 如果本地状态足够，去掉可选或延迟初始化 view model。
- 把业务逻辑从 `body` 中抽离到 service / model。
- 把视图保持为 UI 状态、导航和交互的薄协调层。
- 大视图优先拆小，再考虑是否增加新抽象层。

## 结论
在现代 SwiftUI 中，view model 应该是例外，不是默认。

默认栈通常是：
- `@State` 负责本地状态。
- `@Environment` 负责共享依赖。
- `@Query` 负责 SwiftData 集合。
- 生命周期 modifier 负责轻量编排。
- service 与 model 负责业务逻辑。
