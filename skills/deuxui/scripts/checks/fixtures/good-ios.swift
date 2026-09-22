import SwiftUI

struct SettingsView: View {
    @State private var notify = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        List {
            Section("Account") {
                LabeledContent("Email", value: "keaton@example.com")
                Toggle("Notifications", isOn: $notify)
            }
            Section {
                Button("Continue") { }
                    .frame(minWidth: 44, minHeight: 44)
                    .contentShape(Rectangle())
                Text("Terms apply")
                    .font(.footnote)
                    .foregroundStyle(Color(.secondaryLabel))
                NavigationLink("Details") { DetailView() }
            }
        }
        .listStyle(.insetGrouped)
        .background(Color(.systemGroupedBackground))
        .tint(Color(.tintColor))
        .navigationTitle("Settings")
        .animation(reduceMotion ? nil : .easeOut(duration: 0.2), value: notify)
    }
}

struct RootTabs: View {
    var body: some View {
        TabView {
            SettingsView().tabItem { Label("Settings", systemImage: "gearshape") }
            DetailView().tabItem { Label("Details", systemImage: "doc.text") }
            Text("Me").tabItem { Label("Me", systemImage: "person.crop.circle") }
        }
        .tint(Color(.tintColor))
    }
}

struct HeaderImage: View {
    var body: some View {
        Image(systemName: "photo")
            .resizable()
            .ignoresSafeArea(edges: .top)
    }
}

struct DetailView: View {
    var body: some View {
        ScrollView { Text("detail").font(.body) }
            .background(.ultraThinMaterial)
            .navigationBarTitleDisplayMode(.inline)
    }
}
