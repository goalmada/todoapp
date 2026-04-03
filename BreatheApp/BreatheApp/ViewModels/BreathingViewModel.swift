import Foundation
import UserNotifications
import Combine

class BreathingViewModel: ObservableObject {
    // Exercise state
    @Published var selectedTechnique: BreathingTechnique?
    @Published var isRunning = false
    @Published var currentCycle = 0
    @Published var currentStepIndex = 0
    @Published var secondsRemaining = 0
    @Published var currentPhase: BreathingPhase = .inhale
    @Published var currentInstruction = ""
    @Published var circleScale: CGFloat = 1.0
    @Published var phaseProgress: Double = 0.0
    @Published var sessionComplete = false

    // Reminder state
    @Published var reminderEnabled = false
    @Published var reminderIntervalMinutes = 60

    let tracker: SessionTracker
    private var timer: Timer?
    private var phaseDuration: Int = 0

    let reminderIntervals = [30, 45, 60, 90, 120]

    init(tracker: SessionTracker) {
        self.tracker = tracker
    }

    // MARK: - Exercise

    func selectTechnique(_ technique: BreathingTechnique) {
        stop()
        selectedTechnique = technique
        sessionComplete = false
        currentCycle = 0
        currentStepIndex = 0
        secondsRemaining = 0
        currentPhase = .inhale
        currentInstruction = "Tap Start when ready"
        circleScale = 1.0
        phaseProgress = 0.0
    }

    func start() {
        guard let technique = selectedTechnique, !isRunning else { return }
        isRunning = true
        sessionComplete = false
        currentCycle = 0
        currentStepIndex = 0
        beginStep()
    }

    func stop() {
        isRunning = false
        timer?.invalidate()
        timer = nil
        circleScale = 1.0
        phaseProgress = 0.0
    }

    private func beginStep() {
        guard let technique = selectedTechnique, isRunning else { return }
        let step = technique.steps[currentStepIndex]

        currentPhase = step.phase
        currentInstruction = step.instruction
        phaseDuration = step.duration
        secondsRemaining = step.duration
        phaseProgress = 0.0

        // Animate circle scale
        withOptionalAnimation {
            switch step.phase {
            case .inhale:
                self.circleScale = 1.15
            case .exhale:
                self.circleScale = 0.85
            case .hold:
                break // keep current scale
            case .rest:
                self.circleScale = 1.0
            }
        }

        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            self?.tick()
        }
    }

    private func tick() {
        guard isRunning else {
            timer?.invalidate()
            return
        }

        secondsRemaining -= 1
        phaseProgress = 1.0 - (Double(secondsRemaining) / Double(phaseDuration))

        if secondsRemaining <= 0 {
            timer?.invalidate()
            advanceStep()
        }
    }

    private func advanceStep() {
        guard let technique = selectedTechnique, isRunning else { return }

        currentStepIndex += 1
        if currentStepIndex >= technique.steps.count {
            currentStepIndex = 0
            currentCycle += 1

            if currentCycle >= technique.cycles {
                completeSession()
                return
            }
        }
        beginStep()
    }

    private func completeSession() {
        isRunning = false
        sessionComplete = true
        timer?.invalidate()
        circleScale = 1.0
        phaseProgress = 0.0

        if let technique = selectedTechnique {
            tracker.recordSession(technique: technique)
        }
    }

    private func withOptionalAnimation(_ body: @escaping () -> Void) {
        // In a real SwiftUI context this would use withAnimation
        body()
    }

    // MARK: - Reminders

    func toggleReminders() {
        reminderEnabled.toggle()

        if reminderEnabled {
            scheduleReminders()
        } else {
            cancelReminders()
        }
    }

    func updateReminderInterval(_ minutes: Int) {
        reminderIntervalMinutes = minutes
        if reminderEnabled {
            cancelReminders()
            scheduleReminders()
        }
    }

    func requestNotificationPermission() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, _ in
            DispatchQueue.main.async {
                if !granted {
                    self.reminderEnabled = false
                }
            }
        }
    }

    private func scheduleReminders() {
        cancelReminders()

        let messages = [
            "Take 2 minutes to reset your nervous system. Your hands and feet will thank you.",
            "Quick breathing break — longer exhales calm your fight-or-flight response.",
            "Your nervous system needs a reset. A few slow exhales will improve your circulation.",
            "Cold hands? Anxious? 2 minutes of extended exhale breathing can help right now.",
            "Pause and breathe. Your vagus nerve activates with each slow exhale.",
            "Breathing reminder: inhale 4, exhale 8. Just a few rounds makes a difference.",
        ]

        // Schedule repeating notifications for the next 12 hours
        let intervalSeconds = TimeInterval(reminderIntervalMinutes * 60)
        let maxNotifications = min(12 * 60 / reminderIntervalMinutes, 60)

        for i in 1...maxNotifications {
            let content = UNMutableNotificationContent()
            content.title = "Time to Breathe"
            content.body = messages[i % messages.count]
            content.sound = .default
            content.categoryIdentifier = "BREATHING_REMINDER"

            let trigger = UNTimeIntervalNotificationTrigger(
                timeInterval: intervalSeconds * Double(i),
                repeats: false
            )

            let request = UNNotificationRequest(
                identifier: "breathing_reminder_\(i)",
                content: content,
                trigger: trigger
            )

            UNUserNotificationCenter.current().add(request)
        }
    }

    private func cancelReminders() {
        let ids = (1...60).map { "breathing_reminder_\($0)" }
        UNUserNotificationCenter.current().removePendingNotificationRequests(withIdentifiers: ids)
    }

    // MARK: - Helpers

    var totalCycles: Int {
        selectedTechnique?.cycles ?? 0
    }

    var phaseColor: String {
        switch currentPhase {
        case .inhale: return "inhale"
        case .exhale: return "exhale"
        case .hold: return "hold"
        case .rest: return "rest"
        }
    }

    static let completionMessages = [
        "Well done. Your vagus nerve is activated. Notice your hands and feet — they should feel slightly warmer.",
        "Session complete. The parasympathetic shift will continue for the next 15-20 minutes.",
        "Great work. Each session builds cumulative vagal tone. Your nervous system is getting better at self-regulating.",
        "Done. Blood vessels in your extremities just dilated. This effect compounds with consistent practice.",
    ]
}
