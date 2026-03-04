# 组件设计参考

> 创建可复用、可配置的 UI 组件

## 目录
- [设计原则](#设计原则)
- [SwiftUI 组件](#swiftui-组件)
- [UIKit 组件](#uikit-组件)

---

## 设计原则

### 1. 单一职责
```swift
// ❌ 错误 - 职责耦合
class UserProfileCard: UIView {
    func loadUserData() { }   // 数据加载
    func updateUI() { }        // UI 更新
    func handleTap() { }       // 交互
}

// ✅ 正确 - 职责分离
struct UserProfile {
    let name: String
    let avatar: URL
}

class UserProfileCard: UIView {
    func configure(with profile: UserProfile) {
        // 只负责 UI 展示
    }
}

class UserProfileViewModel {
    func loadProfile() async throws -> UserProfile {
        // 负责数据加载
    }
}
```

### 2. 配置驱动

```swift
struct CardConfiguration {
    var cornerRadius: CGFloat = 12
    var shadowRadius: CGFloat = 8
    var backgroundColor: UIColor = .systemBackground
    
    static let `default` = CardConfiguration()
}
```

### 3. 提供默认值

```swift
// ✅ 正确 - 可选参数有默认值
struct CustomButton: View {
    let title: String
    var style: Style = .primary
    var size: Size = .medium
    var action: () -> Void
}
```

---

## SwiftUI 组件

### ViewModifier

```swift
struct CardModifier: ViewModifier {
    var cornerRadius: CGFloat = 12
    var shadowRadius: CGFloat = 8
    
    func body(content: Content) -> some View {
        content
            .background(Color(.systemBackground))
            .clipShape(.rect(cornerRadius: cornerRadius))
            .shadow(radius: shadowRadius)
            .padding()
    }
}

extension View {
    func cardStyle(cornerRadius: CGFloat = 12, shadowRadius: CGFloat = 8) -> some View {
        modifier(CardModifier(cornerRadius: cornerRadius, shadowRadius: shadowRadius))
    }
}

// 使用
Text("Hello")
    .cardStyle()
```

### 自定义容器

```swift
struct Card<Content: View>: View {
    let title: String?
    let action: (() -> Void)?
    @ViewBuilder let content: Content
    
    init(
        title: String? = nil,
        action: (() -> Void)? = nil,
        @ViewBuilder content: () -> Content
    ) {
        self.title = title
        self.action = action
        self.content = content()
    }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let title {
                HStack {
                    Text(title).font(.headline)
                    Spacer()
                    if let action {
                        Button("查看更多", action: action)
                    }
                }
            }
            content
        }
        .padding()
        .cardStyle()
    }
}
```

### ButtonStyle

```swift
struct CustomButtonStyle: ButtonStyle {
    enum Style {
        case primary, secondary, destructive
        
        var backgroundColor: Color {
            switch self {
            case .primary: return .blue
            case .secondary: return .gray.opacity(0.2)
            case .destructive: return .red
            }
        }
    }
    
    var style: Style = .primary
    var isLoading: Bool = false
    
    func makeBody(configuration: Configuration) -> some View {
        HStack {
            if isLoading {
                ProgressView()
            } else {
                configuration.label
            }
        }
        .font(.headline)
        .foregroundStyle(.white)
        .frame(maxWidth: .infinity)
        .padding()
        .background(style.backgroundColor)
        .clipShape(.rect(cornerRadius: 8))
        .opacity(configuration.isPressed ? 0.8 : 1.0)
    }
}

extension Button {
    func customStyle(
        style: CustomButtonStyle.Style = .primary,
        isLoading: Bool = false
    ) -> some View {
        buttonStyle(CustomButtonStyle(style: style, isLoading: isLoading))
    }
}
```

---

## UIKit 组件

### 基础控件结构

```swift
final class CustomControl: UIControl {
    // MARK: - Properties
    var value: Int = 0 {
        didSet {
            updateAppearance()
            sendActions(for: .valueChanged)
        }
    }
    
    // MARK: - UI Components
    private lazy var titleLabel: UILabel = {
        let label = UILabel()
        label.font = .systemFont(ofSize: 16, weight: .medium)
        return label
    }()
    
    // MARK: - Initialization
    override init(frame: CGRect) {
        super.init(frame: frame)
        setup()
    }
    
    required init?(coder: NSCoder) {
        super.init(coder: coder)
        setup()
    }
    
    // MARK: - Setup
    private func setup() {
        addSubview(titleLabel)
        setupConstraints()
        updateAppearance()
    }
    
    private func setupConstraints() {
        titleLabel.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            titleLabel.centerXAnchor.constraint(equalTo: centerXAnchor),
            titleLabel.centerYAnchor.constraint(equalTo: centerYAnchor)
        ])
    }
    
    private func updateAppearance() {
        titleLabel.text = "\(value)"
    }
    
    override var intrinsicContentSize: CGSize {
        CGSize(width: 100, height: 44)
    }
}
```

### 可配置组件

```swift
struct CardConfiguration {
    var cornerRadius: CGFloat = 12
    var shadowRadius: CGFloat = 8
    var shadowOpacity: Float = 0.1
    var backgroundColor: UIColor = .systemBackground
}

final class CardView: UIView {
    var configuration: CardConfiguration = CardConfiguration() {
        didSet {
            applyConfiguration()
        }
    }
    
    private let containerView = UIView()
    
    private func applyConfiguration() {
        containerView.backgroundColor = configuration.backgroundColor
        containerView.layer.cornerRadius = configuration.cornerRadius
        containerView.layer.shadowColor = UIColor.black.cgColor
        containerView.layer.shadowOpacity = configuration.shadowOpacity
        containerView.layer.shadowRadius = configuration.shadowRadius
        
        // 优化性能
        containerView.layer.shadowPath = UIBezierPath(
            roundedRect: containerView.bounds,
            cornerRadius: configuration.cornerRadius
        ).cgPath
    }
}
```

---

## 可访问性

### SwiftUI

```swift
struct AccessibleCard: View {
    let title: String
    let description: String
    
    var body: some View {
        VStack(alignment: .leading) {
            Text(title).font(.headline)
            Text(description).font(.body)
        }
        .padding()
        .cardStyle()
        // 合并为单个可访问性元素
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(title), \(description)")
        .accessibilityAddTraits(.isButton)
        // 动态字体
        .dynamicTypeSize(...DynamicTypeSize.xxxLarge)
    }
}
```

### UIKit

```swift
final class AccessibleButton: UIButton {
    override init(frame: CGRect) {
        super.init(frame: frame)
        setupAccessibility()
    }
    
    private func setupAccessibility() {
        isAccessibilityElement = true
        accessibilityTraits = .button
        accessibilityLabel = "提交按钮"
        accessibilityHint = "双击提交表单"
        
        // 动态字体
        titleLabel?.font = UIFont.preferredFont(forTextStyle: .headline)
        titleLabel?.adjustsFontForContentSizeCategory = true
    }
}
```

---

## 组件测试

### SwiftUI Preview

```swift
#Preview("Default") {
    CustomCard(title: "Title", content: "Content")
}

#Preview("Dark Mode") {
    CustomCard(title: "Title", content: "Content")
        .preferredColorScheme(.dark)
}

#Preview("Large Font") {
    CustomCard(title: "Title", content: "Content")
        .environment(\.sizeCategory, .accessibilityExtraExtraExtraLarge)
}
```

### UIKit 快照测试

```swift
import SnapshotTesting

final class CardViewTests: XCTestCase {
    func testDefaultAppearance() {
        let card = CardView()
        card.frame = CGRect(x: 0, y: 0, width: 375, height: 200)
        assertSnapshot(matching: card, as: .image)
    }
    
    func testDarkMode() {
        let card = CardView()
        card.frame = CGRect(x: 0, y: 0, width: 375, height: 200)
        card.overrideUserInterfaceStyle = .dark
        assertSnapshot(matching: card, as: .image)
    }
}
```

---

## 关键原则

1. **单一职责**: 组件只做一件事
2. **配置驱动**: 通过配置对象控制行为
3. **默认值**: 提供合理的默认配置
4. **可访问性**: 支持 VoiceOver、动态字体
5. **可测试**: Preview/快照测试覆盖多种状态
