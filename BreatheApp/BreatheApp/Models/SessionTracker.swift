import Foundation

class SessionTracker: ObservableObject {
    @Published var sessionsToday: Int = 0
    @Published var sessionHistory: [SessionRecord] = []

    let dailyGoal = 6

    private let sessionsKey = "breathingSessions"
    private let historyKey = "breathingHistory"

    struct SessionRecord: Codable, Identifiable {
        let id: UUID
        let date: Date
        let techniqueId: String
        let techniqueName: String
        let durationSeconds: Int

        init(techniqueId: String, techniqueName: String, durationSeconds: Int) {
            self.id = UUID()
            self.date = Date()
            self.techniqueId = techniqueId
            self.techniqueName = techniqueName
            self.durationSeconds = durationSeconds
        }
    }

    init() {
        loadToday()
        loadHistory()
    }

    func recordSession(technique: BreathingTechnique) {
        sessionsToday += 1
        let record = SessionRecord(
            techniqueId: technique.id,
            techniqueName: technique.name,
            durationSeconds: technique.totalDuration
        )
        sessionHistory.insert(record, at: 0)
        saveToday()
        saveHistory()
    }

    var progress: Double {
        min(Double(sessionsToday) / Double(dailyGoal), 1.0)
    }

    private func loadToday() {
        let data = UserDefaults.standard.dictionary(forKey: sessionsKey)
        let today = dateString(Date())
        if let stored = data, stored["date"] as? String == today {
            sessionsToday = stored["count"] as? Int ?? 0
        } else {
            sessionsToday = 0
        }
    }

    private func saveToday() {
        let today = dateString(Date())
        UserDefaults.standard.set(["date": today, "count": sessionsToday], forKey: sessionsKey)
    }

    private func loadHistory() {
        guard let data = UserDefaults.standard.data(forKey: historyKey),
              let records = try? JSONDecoder().decode([SessionRecord].self, from: data) else {
            return
        }
        // Keep last 30 days
        let cutoff = Calendar.current.date(byAdding: .day, value: -30, to: Date()) ?? Date()
        sessionHistory = records.filter { $0.date > cutoff }
    }

    private func saveHistory() {
        if let data = try? JSONEncoder().encode(sessionHistory) {
            UserDefaults.standard.set(data, forKey: historyKey)
        }
    }

    private func dateString(_ date: Date) -> String {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        return f.string(from: date)
    }
}
