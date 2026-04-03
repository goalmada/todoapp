import SwiftUI

struct TipsView: View {
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    Text("Why extended exhale breathing works")
                        .font(.title3.weight(.light))
                        .foregroundColor(.orange)
                        .padding(.top, 10)

                    ForEach(HealthTip.allTips) { tip in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(tip.title)
                                .font(.subheadline.weight(.medium))
                                .foregroundColor(.cyan)

                            Text(tip.body)
                                .font(.caption)
                                .foregroundColor(.secondary)
                                .lineSpacing(4)
                        }
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                    }
                }
                .padding()
            }
            .navigationTitle("The Science")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}
