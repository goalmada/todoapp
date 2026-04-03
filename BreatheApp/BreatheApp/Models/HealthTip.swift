import Foundation

struct HealthTip: Identifiable {
    let id = UUID()
    let title: String
    let body: String
}

extension HealthTip {
    static let allTips: [HealthTip] = [
        HealthTip(
            title: "Why longer exhales warm your hands & feet",
            body: "When you exhale longer than you inhale, you stimulate the vagus nerve. This shifts your autonomic nervous system from sympathetic (fight-or-flight, which constricts blood vessels in extremities) to parasympathetic (rest-and-digest, which dilates them). More blood flows to your fingers and toes."
        ),
        HealthTip(
            title: "Cold extremities = nervous system signal",
            body: "Cold hands and feet are often caused by vasoconstriction from chronic sympathetic nervous system activation (stress/anxiety). It's your body redirecting blood to vital organs. Extended exhale breathing directly counteracts this."
        ),
        HealthTip(
            title: "The 2x daily minimum",
            body: "Research shows that just 5 minutes of extended-exhale breathing twice daily can measurably improve heart rate variability within 2 weeks. Morning and mid-afternoon are ideal — that's when cortisol naturally spikes."
        ),
        HealthTip(
            title: "Nose breathing matters",
            body: "Breathing through your nose produces nitric oxide, a vasodilator that opens blood vessels and improves circulation. Mouth breathing skips this. Always inhale through your nose during these exercises."
        ),
        HealthTip(
            title: "The vagus nerve connection",
            body: "The vagus nerve runs from your brainstem to your gut. Long exhales increase vagal tone, which lowers heart rate, reduces inflammation, improves digestion, and relaxes smooth muscle in blood vessel walls, allowing more blood to reach your extremities."
        ),
        HealthTip(
            title: "Breathing before meals",
            body: "Doing 2 minutes of extended-exhale breathing before eating shifts your body into parasympathetic mode, improving digestion and nutrient absorption. Your body can't properly digest in fight-or-flight mode."
        ),
        HealthTip(
            title: "Stack it with movement",
            body: "After a breathing session, gently shake your hands and feet for 30 seconds. The combination of vasodilation from breathing + mechanical movement pumps blood into extremities faster."
        ),
    ]
}
