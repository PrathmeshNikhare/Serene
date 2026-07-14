"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Dashboard() {
  const router = useRouter();

  // User details from localStorage
  const [userId, setUserId] = useState<string | null>(null);
  const [userName, setUserName] = useState("Friend");
  const [userPersona, setUserPersona] = useState("Exam Warrior/ Teenager");
  const [userAge, setUserAge] = useState(20);
  const [userGender, setUserGender] = useState("Female");
  const [wellnessPoints, setWellnessPoints] = useState(0);

  // Form input states
  const [moodScore, setMoodScore] = useState(5);
  const [sleepHours, setSleepHours] = useState(7.0);
  const [screenTimeHours, setScreenTimeHours] = useState(4.0);
  const [workStudyHours, setWorkStudyHours] = useState(6.0);
  const [selectedStressors, setSelectedStressors] = useState<string[]>([]);
  const [focusedField, setFocusedField] = useState("");
  const [showAllStressors, setShowAllStressors] = useState(false);

  // API loading and response states
  const [loading, setLoading] = useState(false);
  const [predictions, setPredictions] = useState<any>(null);
  const [insights, setInsights] = useState<any>(null);

  const [showNudge, setShowNudge] = useState(false);
  const [nudgePayload, setNudgePayload] = useState<any>(null);


  // Tailored list of stressors per persona
  const getStressorsForPersona = (persona: string) => {
    switch (persona) {
      case "Exam Warrior/ Teenager":
        return ["Exam Anxiety", "Academic Overload", "Fear of Failure", "Peer Pressure", "Social Media", "Sleep Deprivation", "Teen Disconnect"];
      case "Bachelor":
        return ["Time Management", "Financial Pressure", "Dietary Neglect", "Sedentary Lifestyle", "Social Media", "Sleep Deprivation", "Imposter Syndrome"];
      case "Corporate Professional":
        return ["Burnout", "Meeting Fatigue", "Manager Toxicity", "Time Management", "Career-Home Balance", "Imposter Syndrome", "Sedentary Lifestyle"];
      case "Parent of a teenager":
        return ["Teen Disconnect", "Relationship Friction", "Career-Home Balance", "Invisible Load", "Time Management", "Chronic Illness"];
      case "Working Woman":
        return ["Career-Home Balance", "Invisible Load", "Burnout", "Imposter Syndrome", "Relationship Friction", "Dietary Neglect", "Time Management"];
      default:
        return ["Burnout", "Sleep Deprivation", "Time Management", "Social Media", "Academic Overload"];
    }
  };

  // Full list of all 21 stressors supported by the model
  const allModelStressors = [
    "Academic Overload", "Burnout", "Career-Home Balance", "Chronic Illness", "Clinical Anxiety",
    "Depressive Mood", "Dietary Neglect", "Exam Anxiety", "Fear of Failure", "Financial Pressure",
    "Imposter Syndrome", "Invisible Load", "Manager Toxicity", "Meeting Fatigue", "Peer Pressure",
    "Relationship Friction", "Sedentary Lifestyle", "Sleep Deprivation", "Social Media", "Teen Disconnect",
    "Time Management"
  ];

  const displayedStressors = showAllStressors ? allModelStressors : getStressorsForPersona(userPersona);

  useEffect(() => {
    // Read values from localStorage
    const savedUserId = localStorage.getItem("user_id");
    if (!savedUserId) {
      // Redirect to landing page to sign up if not registered
      router.push("/");
      return;
    }

    setUserId(savedUserId);
    setUserName(localStorage.getItem("user_name") || "Friend");
    setUserPersona(localStorage.getItem("user_persona") || "Teenager");
    setUserAge(Number(localStorage.getItem("user_age")) || 20);
    setUserGender(localStorage.getItem("user_gender") || "Female");


    // Load cached predictions/insights if they exist
    const cachedInsights = localStorage.getItem(`insights_${savedUserId}`);
    const cachedPredictions = localStorage.getItem(`predictions_${savedUserId}`);
    if (cachedInsights) {
      try {
        setInsights(JSON.parse(cachedInsights));
      } catch (e) {
        console.error("Error parsing cached insights", e);
      }
    }
    if (cachedPredictions) {
      try {
        setPredictions(JSON.parse(cachedPredictions));
      } catch (e) {
        console.error("Error parsing cached predictions", e);
      }
    }
  }, [router]);


  const handleLogout = () => {
    localStorage.removeItem("user_id");
    localStorage.removeItem("user_name");
    localStorage.removeItem("user_persona");
    localStorage.removeItem("user_age");
    localStorage.removeItem("user_gender");
    router.push("/");
  };

  useEffect(() => {
    const fetchNudge = async () => {
      const userId = localStorage.getItem("user_id");
      if (!userId) return;

      try {
        const res = await fetch(`http://localhost:8000/api/v1/nudge/${userId}`);
        if (res.ok) {
          const json = await res.json();
          if (json.data) {
            setNudgePayload(json.data);
            setShowNudge(true);
          }
        }
      } catch (err) {
        console.error("Failed to fetch nudge:", err);
      }
    };
    // Only fetch after component mounts and we know the user is logged in
    const userId = localStorage.getItem("user_id");
    if (userId) {
      fetchNudge();
    }
  }, []);

  const handleNudgeFeedback = async (accepted: boolean) => {
    const userId = localStorage.getItem("user_id");
    if (!userId || !nudgePayload) return;

    try {
      await fetch(`http://localhost:8000/api/v1/nudge/${userId}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nudge_type: nudgePayload.category,
          nudge_text: nudgePayload.text,
          accepted: accepted
        })
      });
    } catch (err) {
      console.error("Failed to submit feedback:", err);
    }

    // Hide the nudge modal regardless of network success/fail
    setShowNudge(false);
  };

  const toggleStressor = (stressor: string) => {
    if (selectedStressors.includes(stressor)) {
      setSelectedStressors(selectedStressors.filter(s => s !== stressor));
    } else {
      setSelectedStressors([...selectedStressors, stressor]);
    }
  };

  const handleCheckIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId) return;

    setLoading(true);
    try {
      // Step 1: Log the mood and compute ML prediction & SHAP drivers
      const moodResponse = await fetch("http://localhost:8000/api/v1/mood/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          score: Number(moodScore),
          sleep_hours: Number(sleepHours),
          screen_time_hours: Number(screenTimeHours),
          work_study_hours: Number(workStudyHours),
          stressors: selectedStressors
        })
      });

      if (!moodResponse.ok) {
        const errData = await moodResponse.json();
        alert(`Error logging mood: ${errData.detail || "Server error"}`);
        setLoading(false);
        return;
      }

      const moodData = await moodResponse.json();
      setPredictions(moodData);
      localStorage.setItem(`predictions_${userId}`, JSON.stringify(moodData));

      // Step 2: Use predictions result (stress score and drivers) to generate LangGraph agent insights
      const insightsResponse = await fetch("http://localhost:8000/api/v1/insights/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          predicted_stress_score: moodData.predicted_stress_score,
          top_mathematical_drivers: moodData.top_drivers
        })
      });

      if (!insightsResponse.ok) {
        const errData = await insightsResponse.json();
        alert(`Error generating insights: ${errData.detail || "Server error"}`);
        setLoading(false);
        return;
      }

      const insightsData = await insightsResponse.json();
      if (insightsData.status === "success" && insightsData.data) {
        setInsights(insightsData.data);
        localStorage.setItem(`insights_${userId}`, JSON.stringify(insightsData.data));
      } else {
        alert("ML prediction complete, but failed to extract insights list.");
      }
    } catch (err) {
      console.error(err);
      alert("Failed to connect to the backend server. Please make sure it is running.");
    } finally {
      setLoading(false);
    }
  };

  const getMoodLabel = (score: number) => {
    if (score <= 3) return "Struggling 😔";
    if (score <= 6) return "Okay 😐";
    if (score <= 8) return "Good 🙂";
    return "Great! 😄";
  };

  return (
    <div className="app-container" style={{ overflowY: "auto", paddingBottom: "100px" }}>
      {/* Top Welcome Banner */}
      <div
        className="neu-surface rounded-b-[28px] w-full pt-9 px-5 pb-7 text-white"
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: "12px", opacity: 0.6, letterSpacing: "1px", textTransform: "uppercase", color: "var(--muted)" }}>Welcome back</div>
            <h1 style={{ fontSize: "24px", fontWeight: "800", marginTop: "2px" }}>{userName}</h1>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div
              className="neu-pressed px-3.5 py-1.5 rounded-full text-[11px] font-semibold uppercase tracking-wide text-white/70"
            >
              {userPersona}
            </div>
            <button
              onClick={handleLogout}
              className="px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide text-white/40 hover:text-[#FF8F8F] transition-colors cursor-pointer border border-transparent hover:border-[#FF8F8F]/30 hover:bg-red-500/10"
            >
              Logout
            </button>
          </div>
        </div>
      </div>


      {/* Main Layout */}
      <div
        style={{ padding: "32px 16px", width: "100%" }}
        className="flex flex-col gap-8"
      >
        {/* Form Container */}
        <div>
          <div
            className="neu-surface p-6 sm:p-8 rounded-3xl"
          >
            <h2 style={{ fontSize: "18px", fontWeight: "700", marginBottom: "4px" }}>Daily Check-In</h2>
            <p className="text-xs text-white/60 font-serif italic mb-5">
              Log your details to evaluate your stress score
            </p>

            <form onSubmit={handleCheckIn} style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              {/* Mood score slider */}
              <div className="input-group">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="input-label" style={{ marginBottom: "6px", color: "var(--muted)" }}>How is your mood?</span>
                  <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--chart-4)" }}>
                    {moodScore}/10 — {getMoodLabel(moodScore)}
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={moodScore}
                  onChange={(e) => setMoodScore(Number(e.target.value))}
                  className="w-full h-2 neu-pressed rounded-full mt-2 appearance-none accent-white"
                />
              </div>

              {/* Hours Input Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                <div className="input-group" style={{ marginBottom: 0 }}>
                  <div className="input-label" style={{ marginBottom: "6px" }}>Sleep Hours</div>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    max="24"
                    className={`neu-pressed rounded-xl px-3 py-2.5 text-sm w-full outline-none transition-all duration-300 text-white bg-transparent ${focusedField === 'sleep' ? 'ring-2 ring-[var(--chart-3)]' : 'border border-transparent'}`}
                    value={sleepHours}
                    onChange={(e) => setSleepHours(Number(e.target.value))}
                    onFocus={() => setFocusedField('sleep')}
                    onBlur={() => setFocusedField('')}
                    required
                  />
                </div>
                <div className="input-group" style={{ marginBottom: 0 }}>
                  <div className="input-label" style={{ marginBottom: "6px" }}>Screen Time</div>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    max="24"
                    className={`neu-pressed rounded-xl px-3 py-2.5 text-sm w-full outline-none transition-all duration-300 text-white bg-transparent ${focusedField === 'screen' ? 'ring-2 ring-[var(--chart-3)]' : 'border border-transparent'}`}
                    value={screenTimeHours}
                    onChange={(e) => setScreenTimeHours(Number(e.target.value))}
                    onFocus={() => setFocusedField('screen')}
                    onBlur={() => setFocusedField('')}
                    required
                  />
                </div>
              </div>

              <div className="input-group" style={{ marginBottom: 0 }}>
                <div className="input-label" style={{ marginBottom: "6px" }}>Work/Study Hours</div>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  max="24"
                  className={`neu-pressed rounded-xl px-3 py-2.5 text-sm w-full outline-none transition-all duration-300 text-white bg-transparent ${focusedField === 'work' ? 'ring-2 ring-[var(--chart-3)]' : 'border border-transparent'}`}
                  value={workStudyHours}
                  onChange={(e) => setWorkStudyHours(Number(e.target.value))}
                  onFocus={() => setFocusedField('work')}
                  onBlur={() => setFocusedField('')}
                  required
                />
              </div>

              {/* Stressors Multi-select Chips */}
              <div className="input-group" style={{ marginBottom: 0 }}>
                <div className="input-label" style={{ marginBottom: "8px", color: "var(--muted)" }}>Primary Stressors Today</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                  {displayedStressors.map((stressor) => {
                    const isSelected = selectedStressors.includes(stressor);
                    return (
                      <button
                        key={stressor}
                        type="button"
                        onClick={() => toggleStressor(stressor)}
                        className={`px-3 py-1.5 rounded-full text-xs cursor-pointer transition-all duration-150 ${isSelected ? 'bar-gradient-anxiety text-black font-bold' : 'neu-raised text-white/80 font-medium'}`}
                      >
                        {stressor}
                      </button>
                    );
                  })}
                </div>
                <button
                  type="button"
                  onClick={() => setShowAllStressors(!showAllStressors)}
                  className="mt-2.5 bg-transparent border-none text-[var(--chart-3)] text-[11px] font-bold cursor-pointer py-1 inline-block hover:underline"
                >
                  {showAllStressors ? "← Show tailored stressors for my persona" : "Show all stressors →"}
                </button>
              </div>

              <button
                type="submit"
                className="btn-learn-more mt-2 rounded-full p-3.5 flex justify-center items-center w-full font-bold text-black"
                disabled={loading}
              >
                {loading ? (
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span className="splash-orb" style={{ width: "16px", height: "16px", marginBottom: 0, animation: "pulseOrb 1.5s infinite" }}></span>
                    Generating Insights...
                  </div>
                ) : "Check In & Analyze →"}
              </button>
            </form>
          </div>
        </div>

        {/* Results Container */}
        <div className="flex flex-col gap-8" style={{ display: "flex", flexDirection: "column", gap: "32px" }}>
          {/* Prediction Results & SHAP Drivers */}
          {predictions && (
            <div
              className="neu-surface p-6 sm:p-8 rounded-3xl"
            >
              <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "12px", color: "white" }}>Mathematical Stress Metrics</h3>
              <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "16px" }}>
                <div
                  className={`text-2xl font-extrabold w-[60px] h-[60px] rounded-full flex items-center justify-center ${predictions.predicted_stress_score > 60 ? 'bg-red-500/20 text-[#FF8F8F] border border-red-500/30' : 'bg-[#A5F9DF]/20 text-[#A5F9DF] border border-[#A5F9DF]/30'}`}
                >
                  {Math.round(predictions.predicted_stress_score)}%
                </div>
                <div>
                  <div style={{ fontSize: "14px", fontWeight: "600", color: "white" }}>Stress Likelihood Score</div>
                  <div style={{ fontSize: "11px", color: "var(--muted)" }}>Calculated from ML model</div>
                </div>
              </div>

              {Object.keys(predictions.top_drivers || {}).length > 0 && (
                <div>
                  <div style={{ fontSize: "11px", fontWeight: "700", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
                    Key Mathematical Drivers
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    {Object.entries(predictions.top_drivers).map(([driver, val]: [string, any]) => {
                      const cleanDriver = driver.replace("persona_", "").replace("gender_", "");
                      const isPositive = val > 0;
                      return (
                        <div
                          key={driver}
                          className="flex justify-between items-center text-xs px-2.5 py-1.5 neu-pressed rounded-lg text-white"
                        >
                          <span style={{ fontWeight: "500" }}>{cleanDriver}</span>
                          <span className={`font-bold ${isPositive ? 'text-[#FF8F8F]' : 'text-[#A5F9DF]'}`}>
                            {isPositive ? `+${Number(val).toFixed(1)}% stress` : `${Number(val).toFixed(1)}% stress`}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* AI Synthesis Insights */}
          {insights && (
            <div
              className="neu-surface p-6 sm:p-8 rounded-3xl"
            >
              <div style={{ textAlign: "center", marginBottom: "20px" }}>
                <h3 style={{ fontSize: "18px", fontWeight: "800", color: "white", marginBottom: "6px" }}>Clinical Synthesis</h3>

                {insights.error ? (
                  <div
                    style={{
                      padding: "16px",
                      borderRadius: "16px",
                      background: "rgba(255, 143, 143, 0.1)",
                      color: "#FF8F8F",
                      fontSize: "13px",
                      lineHeight: "1.5",
                      textAlign: "left",
                      border: "1px dashed #FF8F8F",
                      marginTop: "12px"
                    }}
                  >
                    <strong>AI Insights Pipeline offline:</strong><br />
                    {insights.error === "Malformed JSON from LLM"
                      ? "The AI model encountered a formatting problem. Please click 'Check In' again to regenerate."
                      : insights.error}
                  </div>
                ) : (
                  <>
                    <p style={{ fontSize: "14px", color: "var(--muted)", padding: "0 10px", lineHeight: "1.4" }}>
                      "{insights.daily_summary}"
                    </p>
                    <div
                      className="mt-3 inline-block bg-[#FCDCA3]/10 px-3.5 py-1.5 rounded-full text-xs font-semibold text-[#FCDCA3] border border-[#FCDCA3]/20"
                    >
                      Core Bottleneck: {insights.core_bottleneck}
                    </div>
                  </>
                )}
              </div>

              {/* Insight cards sliding horizontal layout */}
              {!insights.error && insights.deep_analysis && (
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    justifyContent: "center",
                    gap: "16px",
                    paddingBottom: "12px"
                  }}
                >
                  {insights.deep_analysis.map((insight: any, idx: number) => {
                    const borderColors = ['border-[var(--chart-1)]/40', 'border-[var(--chart-2)]/40', 'border-[var(--chart-3)]/40', 'border-[var(--chart-4)]/40', 'border-[var(--chart-5)]/40'];
                    const textColors = ['text-[var(--chart-1)]', 'text-[var(--chart-2)]', 'text-[var(--chart-3)]', 'text-[var(--chart-4)]', 'text-[var(--chart-5)]'];
                    const bc = borderColors[idx % borderColors.length];
                    const tc = textColors[idx % textColors.length];

                    return (
                      <div
                        key={idx}
                        className={`w-full sm:w-[280px] neu-surface rounded-2xl p-6 flex flex-col border-t-2 ${bc}`}
                      >
                        <div className={`text-[11px] font-bold uppercase tracking-widest ${tc} mb-2`}>
                          {insight.category}
                        </div>
                        <div className="text-[15px] font-bold text-white leading-snug mb-3">
                          {insight.observation}
                        </div>
                        <p className="text-[13px] text-white/70 leading-relaxed mb-6">
                          {insight.clinical_rationale}
                        </p>

                        <div className="mt-auto pt-4 border-t border-white/10">
                          <div className="text-[11px] font-bold text-[var(--chart-3)] uppercase tracking-wider mb-2">
                            Daily Action Step
                          </div>
                          <p className="text-[13px] text-white font-medium leading-relaxed">
                            {insight.action_step}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Empty state: No logs yet */}
          {!insights && !predictions && !loading && (
            <div className="text-center text-white/60 mt-10 p-5 neu-surface rounded-3xl">
              <div style={{ fontSize: "36px", marginBottom: "10px" }}>🧠</div>
              <p className="text-[13px] font-serif italic">
                Please check in on the left to load your personalized stress metrics and AI clinical insights dashboard.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Nudge Modal Overlay */}
      {showNudge && nudgePayload && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-md p-4 transition-opacity duration-300">
          <div className="neu-surface max-w-md w-full rounded-3xl p-8 border border-[var(--chart-2)]/30 shadow-[0_0_50px_rgba(46,204,113,0.15)] relative transform transition-all duration-300 scale-100">

            <div className="text-center mb-6">
              <div className="inline-block bg-[var(--chart-2)]/10 text-[var(--chart-2)] px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest mb-6 border border-[var(--chart-2)]/20">
                Daily Wellness Micro-Step
              </div>
              <h2 className="text-2xl font-black text-white mb-4 tracking-tight">Your Custom Nudge</h2>
              <p className="text-[17px] text-white/90 font-medium leading-relaxed bg-white/5 p-5 rounded-2xl border border-white/10">
                "{nudgePayload.text}"
              </p>
            </div>

            <div className="flex gap-4 mt-8">
              <button
                onClick={() => handleNudgeFeedback(false)}
                className="flex-1 neu-pressed py-3.5 rounded-xl font-bold text-white/50 hover:text-[#FF8F8F] transition-colors border border-transparent hover:border-[#FF8F8F]/30 hover:bg-red-500/10 text-[13px] uppercase tracking-wider"
              >
                Dismiss
              </button>
              <button
                onClick={() => handleNudgeFeedback(true)}
                className="flex-1 neu-pressed py-3.5 rounded-xl font-bold text-[var(--chart-2)] hover:text-white transition-all border border-[var(--chart-2)]/20 hover:border-[var(--chart-2)] hover:bg-[var(--chart-2)]/20 text-[13px] uppercase tracking-wider shadow-[0_0_15px_rgba(46,204,113,0.1)] hover:shadow-[0_0_25px_rgba(46,204,113,0.3)]"
              >
                I'll do this
              </button>
            </div>

          </div>
        </div>
      )}

      {/* Navigation Tab Bar */}
      <div
        className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[480px] h-16 neu-surface flex z-[1000] rounded-t-2xl border-t border-white/10"
      >
        <div
          onClick={() => router.push("/dashboard")}
          className="flex-1 flex flex-col items-center justify-center cursor-pointer text-[var(--chart-3)]"
        >
          <span style={{ fontSize: "20px", textShadow: "0 0 10px rgba(165,206,255,0.5)" }}>📊</span>
          <span className="text-[10px] font-bold mt-0.5">Dashboard</span>
        </div>
        <div
          onClick={() => router.push("/aura-chat")}
          className="flex-1 flex flex-col items-center justify-center cursor-pointer text-white/40 hover:text-white/80 transition-colors"
        >
          <span style={{ fontSize: "20px" }}>✨</span>
          <span className="text-[10px] font-medium mt-0.5">Aura Chat</span>
        </div>
      </div>


    </div>
  );
}
