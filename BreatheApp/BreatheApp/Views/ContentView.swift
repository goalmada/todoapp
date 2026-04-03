import SwiftUI

struct ContentView: View {
    @EnvironmentObject var tracker: SessionTracker
    @StateObject private var viewModel: BreathingViewModel

    init() {
        // Will be replaced by environmentObject tracker in onAppear
        _viewModel = StateObject(wrappedValue: BreathingViewModel(tracker: SessionTracker()))
    }

    @State private var showingExercise = false
    @State private var showingTips = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    // Header
                    headerSection

                    // Reminder bar
                    reminderSection

                    // Daily tracker
                    dailyTrackerSection

                    // Technique cards
                    techniquesSection

                    // Tips button
                    Button {
                        showingTips = true
                    } label: {
                        HStack {
                            Image(systemName: "brain.head.profile")
                            Text("Why this works — the science")
                        }
                        .font(.subheadline)
                        .foregroundColor(Color("warm", bundle: nil).opacity(1))
                        .foregroundColor(.orange)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                    }
                }
                .padding()
            }
            .background(Color(.systemBackground))
            .navigationBarHidden(true)
            .sheet(isPresented: $showingExercise) {
                ExerciseView(viewModel: viewModel)
            }
            .sheet(isPresented: $showingTips) {
                TipsView()
            }
        }
        .onAppear {
            viewModel.tracker.sessionsToday = tracker.sessionsToday
            viewModel.requestNotificationPermission()
        }
    }

    // MARK: - Sections

    private var headerSection: some View {
        VStack(spacing: 6) {
            Text("Breathe")
                .font(.system(size: 34, weight: .light))
                .foregroundColor(.cyan)
            Text("Extended exhale breathing to calm your nervous system")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(.top, 20)
    }

    private var reminderSection: some View {
        VStack(spacing: 12) {
            HStack {
                Image(systemName: viewModel.reminderEnabled ? "bell.fill" : "bell")
                    .foregroundColor(viewModel.reminderEnabled ? .cyan : .secondary)
                Text("Breathing Reminders")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                Spacer()
                Toggle("", isOn: Binding(
                    get: { viewModel.reminderEnabled },
                    set: { _ in viewModel.toggleReminders() }
                ))
                .labelsHidden()
            }

            if viewModel.reminderEnabled {
                HStack {
                    Text("Every")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Picker("Interval", selection: Binding(
                        get: { viewModel.reminderIntervalMinutes },
                        set: { viewModel.updateReminderInterval($0) }
                    )) {
                        ForEach(viewModel.reminderIntervals, id: \.self) { mins in
                            if mins < 60 {
                                Text("\(mins) min").tag(mins)
                            } else if mins == 60 {
                                Text("1 hour").tag(mins)
                            } else {
                                let h = mins / 60
                                let m = mins % 60
                                Text(m > 0 ? "\(h)h \(m)m" : "\(h) hours").tag(mins)
                            }
                        }
                    }
                    .pickerStyle(.segmented)
                }
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }

    private var dailyTrackerSection: some View {
        VStack(spacing: 10) {
            HStack {
                Text("Today's Sessions")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                Spacer()
                Text("\(tracker.sessionsToday) / \(tracker.dailyGoal)")
                    .font(.subheadline.monospacedDigit())
                    .foregroundColor(.secondary)
            }

            HStack(spacing: 6) {
                ForEach(0..<tracker.dailyGoal, id: \.self) { i in
                    Circle()
                        .fill(i < tracker.sessionsToday ? Color.green.opacity(0.7) : Color(.systemGray5))
                        .frame(width: 18, height: 18)
                }
                Spacer()
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }

    private var techniquesSection: some View {
        VStack(spacing: 12) {
            ForEach(BreathingTechnique.allTechniques) { technique in
                TechniqueCard(technique: technique) {
                    viewModel.selectTechnique(technique)
                    showingExercise = true
                }
            }
        }
    }
}

// MARK: - Technique Card

struct TechniqueCard: View {
    let technique: BreathingTechnique
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            VStack(alignment: .leading, spacing: 8) {
                Text(technique.name)
                    .font(.headline)
                    .foregroundColor(.cyan)

                Text(technique.description)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(3)

                // Step badges
                HStack(spacing: 6) {
                    ForEach(technique.steps) { step in
                        StepBadge(step: step)
                    }
                    Text("\(technique.cycles) cycles")
                        .font(.caption2)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color(.systemGray5))
                        .cornerRadius(10)
                        .foregroundColor(.secondary)
                }

                Text(technique.benefit)
                    .font(.caption2)
                    .foregroundColor(.orange)
                    .italic()

                HStack {
                    Spacer()
                    Text(technique.formattedDuration)
                        .font(.caption2)
                        .foregroundColor(.secondary)
                    Image(systemName: "chevron.right")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }
            .padding()
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(.systemGray6))
            .cornerRadius(12)
        }
        .buttonStyle(.plain)
    }
}

struct StepBadge: View {
    let step: BreathingStep

    var color: Color {
        switch step.phase {
        case .inhale: return .cyan
        case .exhale: return .mint
        case .hold: return .purple
        case .rest: return .orange
        }
    }

    var body: some View {
        Text("\(step.phase.rawValue) \(step.duration)s")
            .font(.caption2.weight(.semibold))
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(color.opacity(0.15))
            .foregroundColor(color)
            .cornerRadius(10)
    }
}
