import Foundation

struct BreathingStep: Identifiable, Codable {
    let id = UUID()
    let phase: BreathingPhase
    let duration: Int
    let instruction: String

    enum CodingKeys: String, CodingKey {
        case phase, duration, instruction
    }
}

enum BreathingPhase: String, Codable {
    case inhale = "Inhale"
    case hold = "Hold"
    case exhale = "Exhale"
    case rest = "Rest"
}

struct BreathingTechnique: Identifiable {
    let id: String
    let name: String
    let description: String
    let steps: [BreathingStep]
    let cycles: Int
    let benefit: String

    var totalDuration: Int {
        steps.reduce(0) { $0 + $1.duration } * cycles
    }

    var formattedDuration: String {
        let mins = totalDuration / 60
        let secs = totalDuration % 60
        if mins > 0 && secs > 0 { return "\(mins)m \(secs)s" }
        if mins > 0 { return "\(mins)m" }
        return "\(secs)s"
    }
}

extension BreathingTechnique {
    static let allTechniques: [BreathingTechnique] = [
        BreathingTechnique(
            id: "calm_exhale",
            name: "Calm Exhale (4-2-8)",
            description: "Extended exhale activates your vagus nerve, shifting your nervous system into rest-and-digest mode. Improves circulation to extremities and reduces anxiety.",
            steps: [
                BreathingStep(phase: .inhale, duration: 4, instruction: "Breathe in slowly through your nose"),
                BreathingStep(phase: .hold, duration: 2, instruction: "Gentle pause"),
                BreathingStep(phase: .exhale, duration: 8, instruction: "Slow, steady exhale through pursed lips"),
            ],
            cycles: 6,
            benefit: "Longest exhale ratio — maximizes vagal tone and calms cold extremities"
        ),
        BreathingTechnique(
            id: "relaxing_478",
            name: "4-7-8 Relaxing Breath",
            description: "Dr. Andrew Weil's technique. The extended hold saturates blood with oxygen, and the long exhale relaxes smooth muscle in blood vessels, warming your hands and feet.",
            steps: [
                BreathingStep(phase: .inhale, duration: 4, instruction: "Inhale quietly through your nose"),
                BreathingStep(phase: .hold, duration: 7, instruction: "Hold your breath gently"),
                BreathingStep(phase: .exhale, duration: 8, instruction: "Exhale completely through your mouth"),
            ],
            cycles: 4,
            benefit: "Natural tranquilizer for the nervous system — do this 2x daily minimum"
        ),
        BreathingTechnique(
            id: "box_extended",
            name: "Extended Box (4-4-6-2)",
            description: "A variation of Navy SEAL box breathing modified with a longer exhale. Balances focus with calm — good for work sessions.",
            steps: [
                BreathingStep(phase: .inhale, duration: 4, instruction: "Steady breath in through the nose"),
                BreathingStep(phase: .hold, duration: 4, instruction: "Hold at the top"),
                BreathingStep(phase: .exhale, duration: 6, instruction: "Slow controlled exhale"),
                BreathingStep(phase: .rest, duration: 2, instruction: "Empty pause before next breath"),
            ],
            cycles: 5,
            benefit: "Great for focus + calm during work — exhale is still longer than the inhale"
        ),
        BreathingTechnique(
            id: "coherent",
            name: "Coherent Breathing (5-5)",
            description: "Breathing at ~6 breaths per minute synchronizes heart rate variability (HRV). Higher HRV = better blood flow regulation and warmer extremities.",
            steps: [
                BreathingStep(phase: .inhale, duration: 5, instruction: "Smooth, even inhale"),
                BreathingStep(phase: .exhale, duration: 5, instruction: "Smooth, even exhale — relax shoulders and jaw"),
            ],
            cycles: 8,
            benefit: "Optimizes heart rate variability — the #1 metric for nervous system health"
        ),
    ]
}
