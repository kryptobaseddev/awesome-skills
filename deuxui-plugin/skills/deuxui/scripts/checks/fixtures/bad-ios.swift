import SwiftUI

// Everything here is a real tell from a shipped app, written small.
struct SettingsView: View {
    @State private var notify = false

    var body: some View {
        VStack {
            HStack { Text("Account"); Spacer(); Text("keaton@example.com") }
            HStack { Text("Notifications"); Spacer(); MyToggle(on: $notify) }
            HStack { Text("Appearance"); Spacer(); Text("Light") }
            HStack { Text("Storage"); Spacer(); Text("2.1 GB") }
            HStack { Text("Sign out") }

            Button("Continue") { }
                .frame(width: 32, height: 32)
                .tint(Color(red: 0.2, green: 0.4, blue: 0.9))

            Text("Terms apply")
                .font(.system(size: 9))
                .foregroundColor(Color(red: 0.6, green: 0.6, blue: 0.6))

            Text("Your projects")
                .font(.custom("Satoshi-Bold", size: 17))

            NavigationLink("Details") { DetailView() }
                .transition(.scale)
        }
        .ignoresSafeArea()
        .preferredColorScheme(.light)
        .accentColor(Color(hex: "#FF5A1F"))
        .background(Color.black.opacity(0.4).blur(radius: 18))
        .sheet(isPresented: .constant(true)) { DetailView() }
        .interactiveDismissDisabled()
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct MyToggle: View {
    @Binding var on: Bool
    var body: some View {
        Capsule().fill(on ? Color(red: 0.1, green: 0.8, blue: 0.3) : Color(white: 0.8))
            .onTapGesture { withAnimation(.spring()) { on.toggle() } }
    }
}

struct RootTabs: View {
    var body: some View {
        NavigationStack {
            TabView {
                Text("Home").tabItem { Label("Home", systemImage: "house") }
                Text("Search").tabItem { Label("Search", systemImage: "magnifyingglass") }
                Text("Feed").tabItem { Label("Feed", systemImage: "list.bullet") }
                Text("Chat").tabItem { Label("Chat", systemImage: "message") }
                Text("Files").tabItem { Label("Files", systemImage: "folder") }
                Text("Me").tabItem { Label("Me", systemImage: "person") }
            }
            .navigationBarTitleDisplayMode(.inline)
            .tint(Color(red: 0.9, green: 0.1, blue: 0.1))
        }
    }
}

final class LegacyNav: UINavigationController {
    override func viewDidLoad() {
        super.viewDidLoad()
        interactivePopGestureRecognizer?.isEnabled = false
        navigationBar.prefersLargeTitles = false
    }
}

struct DetailView: View { var body: some View { Text("detail") } }
