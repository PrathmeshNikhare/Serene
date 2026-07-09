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
        style={{
          background: "linear-gradient(160deg, var(--night) 0%, var(--slate) 100%)",
          padding: "36px 20px 28px",
          color: "white",
          borderRadius: "0 0 28px 28px",
          boxShadow: "0 4px 20px rgba(15, 28, 20, 0.15)",
          maxWidth: "1200px",
          margin: "0 auto"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: "12px", opacity: 0.6, letterSpacing: "1px", textTransform: "uppercase" }}>Welcome back</div>
            <h1 style={{ fontSize: "24px", fontWeight: "800", marginTop: "2px" }}>{userName}</h1>
          </div>
          <div 
            style={{
              background: "rgba(255, 255, 255, 0.15)",
              border: "1px solid rgba(255, 255, 255, 0.2)",
              padding: "6px 14px",
              borderRadius: "100px",
              fontSize: "11px",
              fontWeight: "600",
              textTransform: "uppercase",
              letterSpacing: "0.5px"
            }}
          >
            {userPersona}
          </div>
        </div>
      </div>

      {/* Main Responsive Grid */}
      <div 
        style={{ padding: "24px 16px", maxWidth: "1200px", margin: "0 auto" }}
        className="grid grid-cols-1 md:grid-cols-12 gap-6"
      >
        {/* Left Column: Form */}
        <div className="md:col-span-5">
          <div 
            style={{
              background: "white",
              padding: "20px",
              borderRadius: "24px",
              boxShadow: "0 4px 16px rgba(0, 0, 0, 0.03)",
              border: "1px solid rgba(0, 0, 0, 0.04)"
            }}
          >
            <h2 style={{ fontSize: "18px", fontWeight: "700", marginBottom: "4px" }}>Daily Check-In</h2>
            <p style={{ fontSize: "12px", color: "var(--mist)", fontFamily: "Literata, serif", fontStyle: "italic", marginBottom: "20px" }}>
              Log your details to evaluate your stress score
            </p>

            <form onSubmit={handleCheckIn} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {/* Mood score slider */}
              <div className="input-group" style={{ marginBottom: "8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="input-label" style={{ marginBottom: "6px" }}>How is your mood?</span>
                  <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--sage)" }}>
                    {moodScore}/10 — {getMoodLabel(moodScore)}
                  </span>
                </div>
                <input 
                  type="range" 
                  min="1" 
                  max="10" 
                  value={moodScore} 
                  onChange={(e) => setMoodScore(Number(e.target.value))}
                  style={{ width: "100%", height: "6px", accentColor: "var(--sage)", background: "#e2e8f0", borderRadius: "10px", marginTop: "8px" }}
                />
              </div>

              {/* Hours Input Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div className="input-group" style={{ marginBottom: 0 }}>
                  <div className="input-label" style={{ marginBottom: "6px" }}>Sleep Hours</div>
                  <input 
                    type="number" 
                    step="0.5" 
                    min="0" 
                    max="24"
                    className={`input-field ${focusedField === 'sleep' ? 'focused' : ''}`}
                    style={{ padding: "10px 12px", fontSize: "14px", borderRadius: "10px" }}
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
                    className={`input-field ${focusedField === 'screen' ? 'focused' : ''}`}
                    style={{ padding: "10px 12px", fontSize: "14px", borderRadius: "10px" }}
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
                  className={`input-field ${focusedField === 'work' ? 'focused' : ''}`}
                  style={{ padding: "10px 12px", fontSize: "14px", borderRadius: "10px" }}
                  value={workStudyHours}
                  onChange={(e) => setWorkStudyHours(Number(e.target.value))}
                  onFocus={() => setFocusedField('work')}
                  onBlur={() => setFocusedField('')}
                  required
                />
              </div>

              {/* Stressors Multi-select Chips */}
              <div className="input-group" style={{ marginBottom: 0 }}>
                <div className="input-label" style={{ marginBottom: "8px" }}>Primary Stressors Today</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                  {displayedStressors.map((stressor) => {
                    const isSelected = selectedStressors.includes(stressor);
                    return (
                      <button
                        key={stressor}
                        type="button"
                        onClick={() => toggleStressor(stressor)}
                        style={{
                          padding: "6px 12px",
                          borderRadius: "100px",
                          fontSize: "12px",
                          fontWeight: isSelected ? "600" : "500",
                          cursor: "pointer",
                          border: "1.5px solid",
                          borderColor: isSelected ? "var(--sage)" : "rgba(0, 0, 0, 0.08)",
                          background: isSelected ? "var(--sage-pale)" : "white",
                          color: isSelected ? "var(--sage)" : "var(--slate)",
                          transition: "all 0.15s ease"
                        }}
                      >
                        {stressor}
                      </button>
                    );
                  })}
                </div>
                <button
                  type="button"
                  onClick={() => setShowAllStressors(!showAllStressors)}
                  style={{
                    marginTop: "10px",
                    background: "none",
                    border: "none",
                    color: "var(--sage)",
                    fontSize: "11px",
                    fontWeight: "700",
                    cursor: "pointer",
                    padding: "4px 0",
                    display: "inline-block",
                    textDecoration: "underline"
                  }}
                >
                  {showAllStressors ? "← Show tailored stressors for my persona" : "Show all stressors →"}
                </button>
              </div>

              <button 
                type="submit" 
                className="btn-primary" 
                style={{ marginTop: "8px", borderRadius: "12px", padding: "14px", background: "var(--night)", display: "flex", justifyContent: "center", alignItems: "center" }}
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

        {/* Right Column: Results */}
        <div className="md:col-span-7 flex flex-col gap-6" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Prediction Results & SHAP Drivers */}
          {predictions && (
            <div 
              style={{
                background: "white",
                padding: "20px",
                borderRadius: "24px",
                boxShadow: "0 4px 16px rgba(0, 0, 0, 0.03)",
                border: "1px solid rgba(0, 0, 0, 0.04)"
              }}
            >
              <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "12px" }}>Mathematical Stress Metrics</h3>
              <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "16px" }}>
                <div 
                  style={{
                    fontSize: "24px",
                    fontWeight: "800",
                    width: "60px",
                    height: "60px",
                    borderRadius: "50%",
                    background: predictions.predicted_stress_score > 0.6 ? "rgba(196, 114, 74, 0.1)" : "rgba(107, 158, 120, 0.1)",
                    color: predictions.predicted_stress_score > 0.6 ? "var(--terra)" : "var(--sage)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center"
                  }}
                >
                  {Math.round(predictions.predicted_stress_score * 100)}%
                </div>
                <div>
                  <div style={{ fontSize: "14px", fontWeight: "600" }}>Stress Likelihood Score</div>
                  <div style={{ fontSize: "11px", color: "var(--mist)" }}>Calculated from XGBoost ML model</div>
                </div>
              </div>

              {Object.keys(predictions.top_drivers || {}).length > 0 && (
                <div>
                  <div style={{ fontSize: "11px", fontWeight: "700", color: "var(--mist)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
                    Key Mathematical Drivers
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    {Object.entries(predictions.top_drivers).map(([driver, val]: [string, any]) => {
                      const cleanDriver = driver.replace("persona_", "").replace("gender_", "");
                      const isPositive = val > 0;
                      return (
                        <div 
                          key={driver} 
                          style={{
                            display: "flex", 
                            justifyContent: "space-between", 
                            alignItems: "center", 
                            fontSize: "12px", 
                            padding: "6px 10px", 
                            background: "var(--cream)", 
                            borderRadius: "8px"
                          }}
                        >
                          <span style={{ fontWeight: "500" }}>{cleanDriver}</span>
                          <span style={{ fontWeight: "700", color: isPositive ? "var(--terra)" : "var(--sage)" }}>
                            {isPositive ? `+${Math.round(val * 100)}% stress` : `${Math.round(val * 100)}% stress`}
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
              style={{
                background: "white",
                padding: "20px",
                borderRadius: "24px",
                boxShadow: "0 4px 16px rgba(0, 0, 0, 0.03)",
                border: "1px solid rgba(0, 0, 0, 0.04)"
              }}
            >
              <div style={{ textAlign: "center", marginBottom: "20px" }}>
                <h3 style={{ fontSize: "18px", fontWeight: "800", color: "var(--night)", marginBottom: "6px" }}>Clinical Synthesis</h3>
                
                {insights.error ? (
                  <div 
                    style={{
                      padding: "16px",
                      borderRadius: "16px",
                      background: "rgba(196, 114, 74, 0.08)",
                      color: "var(--terra)",
                      fontSize: "13px",
                      lineHeight: "1.5",
                      textAlign: "left",
                      border: "1px dashed var(--terra)",
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
                    <p style={{ fontSize: "14px", color: "var(--slate)", padding: "0 10px", lineHeight: "1.4" }}>
                      "{insights.daily_summary}"
                    </p>
                    <div 
                      style={{
                        marginTop: "12px",
                        display: "inline-block",
                        background: "rgba(196, 114, 74, 0.1)",
                        color: "var(--terra)",
                        padding: "6px 14px",
                        borderRadius: "100px",
                        fontSize: "12px",
                        fontWeight: "600"
                      }}
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
                    gap: "14px",
                    overflowX: "auto",
                    paddingBottom: "12px",
                    scrollSnapType: "x mandatory",
                    WebkitOverflowScrolling: "touch"
                  }}
                >
                  {insights.deep_analysis.map((insight: any, idx: number) => (
                    <div 
                      key={idx}
                      style={{
                        flex: "0 0 260px",
                        scrollSnapAlign: "start",
                        background: "var(--cream)",
                        borderRadius: "20px",
                        padding: "16px",
                        border: "1px solid rgba(0,0,0,0.02)",
                        boxShadow: "0 2px 8px rgba(0,0,0,0.01)",
                        display: "flex",
                        flexDirection: "column",
                        gap: "8px"
                      }}
                    >
                      <div style={{ fontSize: "10px", fontWeight: "700", color: "var(--sage)", textTransform: "uppercase", letterSpacing: "1px" }}>
                        {insight.category}
                      </div>
                      <div style={{ fontSize: "14px", fontWeight: "700", color: "var(--night)", lineHeight: "1.2" }}>
                        {insight.observation}
                      </div>
                      <p style={{ fontSize: "12px", color: "var(--slate)", lineHeight: "1.4", opacity: 0.85 }}>
                        {insight.clinical_rationale}
                      </p>
                      
                      <div style={{ marginTop: "auto", paddingTop: "12px", borderTop: "1px solid rgba(0, 0, 0, 0.05)" }}>
                        <div style={{ fontSize: "11px", fontWeight: "700", color: "var(--terra)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                          Daily Action Step
                        </div>
                        <p style={{ fontSize: "12px", color: "var(--night)", fontWeight: "500", marginTop: "2px" }}>
                          {insight.action_step}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Empty state: No logs yet */}
          {!insights && !predictions && !loading && (
            <div style={{ textAlign: "center", color: "var(--mist)", marginTop: "40px", padding: "20px", background: "white", borderRadius: "24px", border: "1px solid rgba(0,0,0,0.04)", boxShadow: "0 4px 16px rgba(0, 0, 0, 0.03)" }}>
              <div style={{ fontSize: "36px", marginBottom: "10px" }}>🌿</div>
              <p style={{ fontSize: "13px", fontFamily: "Literata, serif", fontStyle: "italic" }}>
                Please check in on the left to load your personalized stress metrics and AI clinical insights dashboard.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Navigation Tab Bar */}
      <div 
        style={{
          position: "fixed",
          bottom: 0,
          left: "50%",
          transform: "translateX(-50%)",
          width: "100%",
          maxWidth: "480px",
          height: "64px",
          background: "white",
          borderTop: "1px solid rgba(0, 0, 0, 0.06)",
          display: "flex",
          zIndex: 1000,
          borderRadius: "16px 16px 0 0",
          boxShadow: "0 -4px 16px rgba(0, 0, 0, 0.04)"
        }}
      >
        <div 
          onClick={() => router.push("/dashboard")}
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            color: "var(--sage)"
          }}
        >
          <span style={{ fontSize: "20px" }}>🏡</span>
          <span style={{ fontSize: "10px", fontWeight: "600", marginTop: "2px" }}>Dashboard</span>
        </div>
        <div 
          onClick={() => router.push("/aura-chat")}
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            color: "var(--mist)"
          }}
        >
          <span style={{ fontSize: "20px" }}>✨</span>
          <span style={{ fontSize: "10px", fontWeight: "500", marginTop: "2px" }}>Aura Chat</span>
        </div>
      </div>
    </div>
  );
}
