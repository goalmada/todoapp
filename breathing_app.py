from flask import Flask, render_template, jsonify

app = Flask(__name__)


TECHNIQUES = {
    "calm_exhale": {
        "name": "Calm Exhale (4-2-8)",
        "description": "Extended exhale activates your vagus nerve, shifting your nervous system into rest-and-digest mode. This improves circulation to your extremities and reduces anxiety.",
        "steps": [
            {"phase": "Inhale", "duration": 4, "instruction": "Breathe in slowly through your nose"},
            {"phase": "Hold", "duration": 2, "instruction": "Gentle pause"},
            {"phase": "Exhale", "duration": 8, "instruction": "Slow, steady exhale through pursed lips"},
        ],
        "cycles": 6,
        "benefit": "Longest exhale ratio — maximizes vagal tone and calms cold extremities",
    },
    "relaxing_478": {
        "name": "4-7-8 Relaxing Breath",
        "description": "Dr. Andrew Weil's technique. The extended hold saturates blood with oxygen, and the long exhale dumps CO2 and relaxes smooth muscle in blood vessels, warming your hands and feet.",
        "steps": [
            {"phase": "Inhale", "duration": 4, "instruction": "Inhale quietly through your nose"},
            {"phase": "Hold", "duration": 7, "instruction": "Hold your breath gently"},
            {"phase": "Exhale", "duration": 8, "instruction": "Exhale completely through your mouth with a whoosh"},
        ],
        "cycles": 4,
        "benefit": "Natural tranquilizer for the nervous system — do this 2x daily minimum",
    },
    "box_extended": {
        "name": "Extended Box Breathing (4-4-6-2)",
        "description": "A variation of Navy SEAL box breathing modified with a longer exhale. Balances focus with calm — good for work sessions.",
        "steps": [
            {"phase": "Inhale", "duration": 4, "instruction": "Steady breath in through the nose"},
            {"phase": "Hold", "duration": 4, "instruction": "Hold at the top"},
            {"phase": "Exhale", "duration": 6, "instruction": "Slow controlled exhale"},
            {"phase": "Rest", "duration": 2, "instruction": "Empty pause before next breath"},
        ],
        "cycles": 5,
        "benefit": "Great for focus + calm during work — the exhale is still longer than the inhale",
    },
    "coherent": {
        "name": "Coherent Breathing (5-5 with exhale focus)",
        "description": "Breathing at ~6 breaths per minute synchronizes heart rate variability (HRV). Higher HRV = better blood flow regulation and warmer extremities.",
        "steps": [
            {"phase": "Inhale", "duration": 5, "instruction": "Smooth, even inhale"},
            {"phase": "Exhale", "duration": 5, "instruction": "Smooth, even exhale — relax your shoulders and jaw"},
        ],
        "cycles": 8,
        "benefit": "Optimizes heart rate variability — the #1 metric for nervous system health",
    },
}

HEALTH_TIPS = [
    {
        "title": "Why longer exhales warm your hands & feet",
        "body": "When you exhale longer than you inhale, you stimulate the vagus nerve. This shifts your autonomic nervous system from sympathetic (fight-or-flight, which constricts blood vessels in extremities) to parasympathetic (rest-and-digest, which dilates them). More blood flows to your fingers and toes.",
    },
    {
        "title": "Cold extremities = nervous system signal",
        "body": "Cold hands and feet are often caused by vasoconstriction from chronic sympathetic nervous system activation (stress/anxiety). It's your body redirecting blood to vital organs. Extended exhale breathing directly counteracts this by activating the parasympathetic branch.",
    },
    {
        "title": "The 2x daily minimum",
        "body": "Research shows that just 5 minutes of extended-exhale breathing twice daily can measurably improve heart rate variability within 2 weeks. Set reminders for morning and mid-afternoon — these are when cortisol naturally spikes.",
    },
    {
        "title": "Nose breathing matters",
        "body": "Breathing through your nose produces nitric oxide, a vasodilator that opens blood vessels and improves circulation. Mouth breathing skips this. Always inhale through your nose during these exercises.",
    },
    {
        "title": "The vagus nerve connection",
        "body": "The vagus nerve runs from your brainstem to your gut. Long exhales increase vagal tone, which lowers heart rate, reduces inflammation, improves digestion, and — critically — relaxes the smooth muscle in blood vessel walls, allowing more blood to reach your extremities.",
    },
    {
        "title": "Breathing before meals",
        "body": "Doing 2 minutes of extended-exhale breathing before eating shifts your body into parasympathetic mode, improving digestion and nutrient absorption. Your body can't properly digest in fight-or-flight mode.",
    },
    {
        "title": "Stack it with movement",
        "body": "After a breathing session, gently shake your hands and feet for 30 seconds. The combination of vasodilation from breathing + mechanical movement pumps blood into extremities faster.",
    },
]


@app.route("/")
def index():
    return render_template(
        "breathing.html", techniques=TECHNIQUES, health_tips=HEALTH_TIPS
    )


@app.route("/api/techniques")
def get_techniques():
    return jsonify(TECHNIQUES)


@app.route("/api/tips")
def get_tips():
    return jsonify(HEALTH_TIPS)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
