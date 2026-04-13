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
- 纯代码布局，优先使用 **SnapKit** 作为约束布局工具
- 优先 `UIStackView` 减少约束
- SnapKit 不可用时，手动约束用 `NSLayoutConstraint.activate([])` 批量激活
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

## Cell 复用
- 实现 `prepareForReuse()` 清理旧状态
- 图片 reuse 时设 nil 并取消旧请求
- 用 `UICollectionView.CellRegistration` (现代 API)

## SwiftUI 混用
- UIKit 中嵌 SwiftUI: `UIHostingController(rootView: SwiftUIView())`
- SwiftUI 中嵌 UIKit: 实现 `UIViewRepresentable` 协议
