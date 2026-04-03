import SwiftUI

struct ExerciseView: View {
    @ObservedObject var viewModel: BreathingViewModel
    @Environment(\.dismiss) var dismiss

    var body: some View {
        ZStack {
            Color(.systemBackground).ignoresSafeArea()

            if viewModel.sessionComplete {
                completionView
            } else {
                exerciseContent
            }
        }
        .onDisappear {
            viewModel.stop()
        }
    }

    // MARK: - Exercise Content

    private var exerciseContent: some View {
        VStack(spacing: 20) {
            // Top bar
            HStack {
                Button("Close") { dismiss() }
                    .foregroundColor(.secondary)
                Spacer()
                if let technique = viewModel.selectedTechnique {
                    Text(technique.name)
                        .font(.subheadline.weight(.medium))
                        .foregroundColor(.cyan)
                }
                Spacer()
                Text(" ") // balance
            }
            .padding(.horizontal)

            if viewModel.isRunning {
                Text("Cycle \(viewModel.currentCycle + 1) / \(viewModel.totalCycles)")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }

            Spacer()

            // Breathing circle
            breathingCircle

            Spacer()

            // Controls
            HStack(spacing: 20) {
                if viewModel.isRunning {
                    Button {
                        viewModel.stop()
                    } label: {
                        Text("Stop")
                            .font(.body.weight(.medium))
                            .foregroundColor(.primary)
                            .padding(.horizontal, 36)
                            .padding(.vertical, 14)
                            .background(Color(.systemGray5))
                            .cornerRadius(30)
                    }
                } else {
                    Button {
                        viewModel.start()
                    } label: {
                        Text("Start")
                            .font(.body.weight(.semibold))
                            .foregroundColor(.black)
                            .padding(.horizontal, 44)
                            .padding(.vertical, 14)
                            .background(Color.cyan)
                            .cornerRadius(30)
                    }

                    Button { dismiss() } label: {
                        Text("Back")
                            .font(.body.weight(.medium))
                            .foregroundColor(.secondary)
                            .padding(.horizontal, 30)
                            .padding(.vertical, 14)
                            .background(Color(.systemGray6))
                            .cornerRadius(30)
                    }
                }
            }
            .padding(.bottom, 40)
        }
    }

    // MARK: - Breathing Circle

    private var breathingCircle: some View {
        ZStack {
            // Background ring
            Circle()
                .stroke(Color(.systemGray5), lineWidth: 3)
                .frame(width: 260, height: 260)

            // Progress ring
            Circle()
                .trim(from: 0, to: viewModel.phaseProgress)
                .stroke(phaseColor, style: StrokeStyle(lineWidth: 3, lineCap: .round))
                .frame(width: 260, height: 260)
                .rotationEffect(.degrees(-90))
                .animation(.linear(duration: 0.1), value: viewModel.phaseProgress)

            // Inner glow circle
            Circle()
                .fill(
                    RadialGradient(
                        colors: [phaseColor.opacity(0.2), phaseColor.opacity(0.02)],
                        center: .center,
                        startRadius: 0,
                        endRadius: 130
                    )
                )
                .frame(width: 250, height: 250)
                .scaleEffect(viewModel.circleScale)
                .animation(.easeInOut(duration: Double(currentStepDuration)), value: viewModel.circleScale)

            // Text content
            VStack(spacing: 6) {
                Text(viewModel.isRunning ? viewModel.currentPhase.rawValue : "Ready")
                    .font(.system(size: 28, weight: .light))
                    .foregroundColor(phaseColor)
                    .textCase(.uppercase)
                    .tracking(2)

                if viewModel.isRunning {
                    Text("\(viewModel.secondsRemaining)")
                        .font(.system(size: 56, weight: .ultraLight).monospacedDigit())
                        .foregroundColor(.primary)
                        .contentTransition(.numericText())
                } else {
                    Text("—")
                        .font(.system(size: 56, weight: .ultraLight))
                        .foregroundColor(.secondary)
                }

                Text(viewModel.currentInstruction)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 180)
            }
        }
    }

    // MARK: - Completion View

    private var completionView: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "checkmark.circle")
                .font(.system(size: 60))
                .foregroundColor(.green.opacity(0.7))

            Text("Session Complete")
                .font(.system(size: 28, weight: .light))
                .foregroundColor(.green.opacity(0.8))

            Text(BreathingViewModel.completionMessages.randomElement() ?? "")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)

            if let technique = viewModel.selectedTechnique {
                Text("\(technique.name) — \(technique.cycles) cycles — \(technique.formattedDuration)")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()

            VStack(spacing: 12) {
                Button {
                    viewModel.sessionComplete = false
                } label: {
                    Text("Do Another")
                        .font(.body.weight(.semibold))
                        .foregroundColor(.black)
                        .padding(.horizontal, 44)
                        .padding(.vertical, 14)
                        .background(Color.cyan)
                        .cornerRadius(30)
                }

                Button { dismiss() } label: {
                    Text("Done")
                        .font(.body)
                        .foregroundColor(.secondary)
                }
            }
            .padding(.bottom, 50)
        }
    }

    // MARK: - Helpers

    private var phaseColor: Color {
        switch viewModel.currentPhase {
        case .inhale: return .cyan
        case .exhale: return .mint
        case .hold: return .purple
        case .rest: return .orange
        }
    }

    private var currentStepDuration: Int {
        guard let technique = viewModel.selectedTechnique,
              viewModel.currentStepIndex < technique.steps.count else { return 1 }
        return technique.steps[viewModel.currentStepIndex].duration
    }
}
