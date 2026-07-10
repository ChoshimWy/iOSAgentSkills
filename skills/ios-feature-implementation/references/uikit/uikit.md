# UIKit 开发参考

## ViewController 结构
始终按此顺序组织代码：
1. `// MARK: - Properties`
2. `// MARK: - UI Components` (lazy var / let)
3. `// MARK: - Lifecycle` (viewDidLoad, viewWillAppear...)
4. `// MARK: - Setup` (setupUI, setupConstraints, setupBindings)
5. `// MARK: - Public Methods`
6. `// MARK: - Private Methods`
7. `// MARK: - Actions` (@objc func)
8. Protocol conformance 在 extension 中

## viewDidLoad 调用顺序
```swift
override func viewDidLoad() {
    super.viewDidLoad()
    setupUI()          // 添加子视图
    setupConstraints() // 设置约束
    setupBindings()    // 绑定数据
    loadData()         // 加载数据
}
```

## 布局规则
- Swift 的纯代码 UIKit 布局，默认使用 **SnapKit**；Objective-C 的纯代码 UIKit 布局，默认使用 **Masonry**
- 先检查目标 target 的依赖和同目录既有约束写法；库未集成时不得静默新增依赖
- 保持既有页面的布局系统；不要为统一风格改写无关的原生约束，也不要在同一页面混用多套约束 DSL
- 优先 `UIStackView` 减少约束
- SnapKit / Masonry 不可用、系统 API 特殊要求或既有局部约定明确时，手动约束用 `NSLayoutConstraint.activate([])` 批量激活
- 复杂列表用 `UICollectionViewCompositionalLayout` + `DiffableDataSource`

### SnapKit 约束示例
```swift
private func setupConstraints() {
    titleLabel.snp.makeConstraints { make in
        make.top.equalTo(view.safeAreaLayoutGuide).offset(16)
        make.leading.trailing.equalToSuperview().inset(20)
    }

    contentView.snp.makeConstraints { make in
        make.top.equalTo(titleLabel.snp.bottom).offset(12)
        make.leading.trailing.equalToSuperview()
        make.bottom.lessThanOrEqualTo(view.safeAreaLayoutGuide)
    }
}
```

## UI 组件创建模式
```swift
private lazy var titleLabel: UILabel = {
    let label = UILabel()
    label.font = .systemFont(ofSize: 16, weight: .semibold)
    label.textColor = .label
    // 使用 SnapKit 时无需设置 translatesAutoresizingMaskIntoConstraints
    return label
}()
```

### SnapKit 常用约束模式
```swift
// 居中
view.snp.makeConstraints { make in
    make.center.equalToSuperview()
    make.size.equalTo(CGSize(width: 100, height: 100))
}

// 填充父视图
view.snp.makeConstraints { make in
    make.edges.equalToSuperview()
}

// 填充（带边距）
view.snp.makeConstraints { make in
    make.edges.equalToSuperview().inset(16)
}

// 相对其他视图
view2.snp.makeConstraints { make in
    make.top.equalTo(view1.snp.bottom).offset(8)
    make.leading.trailing.equalTo(view1)
}
```

### Masonry 约束示例（Objective-C）
```objc
- (void)setupConstraints {
    [self.titleLabel mas_makeConstraints:^(MASConstraintMaker *make) {
        make.top.equalTo(self.view.mas_safeAreaLayoutGuideTop).offset(16);
        make.leading.trailing.equalTo(self.view).inset(20);
    }];

    [self.contentView mas_makeConstraints:^(MASConstraintMaker *make) {
        make.top.equalTo(self.titleLabel.mas_bottom).offset(12);
        make.leading.trailing.equalTo(self.view);
        make.bottom.lessThanOrEqualTo(self.view.mas_safeAreaLayoutGuideBottom);
    }];
}
```

## Cell 复用
- 实现 `prepareForReuse()` 清理旧状态
- 图片 reuse 时设 nil 并取消旧请求
- 用 `UICollectionView.CellRegistration` (现代 API)

## SwiftUI 混用
- UIKit 中嵌 SwiftUI: `UIHostingController(rootView: SwiftUIView())`
- SwiftUI 中嵌 UIKit: 实现 `UIViewRepresentable` 协议
