"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  const [showSplash, setShowSplash] = useState(true);
  const [isRegister, setIsRegister] = useState(true);
  
  // Registration and Login common fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  
  // Registration only fields
  const [name, setName] = useState("");
  const [age, setAge] = useState(20);
  const [gender, setGender] = useState("Female");
  const [persona, setPersona] = useState("Exam Warrior/ Teenager");
  
  const [focusedField, setFocusedField] = useState("");
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowSplash(false);
    }, 2000);
    return () => clearTimeout(timer);
  }, []);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, persona, age: Number(age), gender }),
      });
      
      if (res.ok) {
        const data = await res.json();
        // Save user ID, name and email to local storage
        localStorage.setItem("user_id", data.id);
        localStorage.setItem("user_name", name || "Friend");
        localStorage.setItem("user_email", data.email);
        localStorage.setItem("user_persona", data.persona);
        localStorage.setItem("user_gender", data.gender);
        localStorage.setItem("user_age", String(data.age));
        
        // Auto-login to generate a token
        const loginRes = await fetch("http://localhost:8000/api/v1/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        
        if (loginRes.ok) {
          const loginData = await loginRes.json();
          localStorage.setItem("access_token", loginData.access_token);
        }
        
        alert("Welcome to Serene! Account created successfully.");
        router.push("/dashboard");
      } else {
        const errorData = await res.json();
        alert(`Error: ${errorData.detail}`);
      }
    } catch (err) {
      console.error(err);
      alert("Registration failed. Please check if your backend server is running.");
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      
      if (res.ok) {
        const data = await res.json();
        // Save token and metadata from updated Token response
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("user_id", data.user_id);
        localStorage.setItem("user_name", data.email.split("@")[0]); // derive username from email for greeting
        localStorage.setItem("user_email", data.email);
        localStorage.setItem("user_persona", data.persona || "Teenager");
        localStorage.setItem("user_gender", data.gender || "Female");
        localStorage.setItem("user_age", String(data.age));
        
        alert("Welcome back to Serene!");
        router.push("/dashboard");
      } else {
        const errorData = await res.json();
        alert(`Error: ${errorData.detail}`);
      }
    } catch (err) {
      console.error(err);
      alert("Login failed. Please check if your backend server is running.");
    } finally {
      setLoading(false);
    }
  };

  if (showSplash) {
    return (
      <div className="app-container">
        <div className="s-splash">
          <div className="splash-orb"></div>
          <div className="splash-name">Serene</div>
          <div className="splash-tagline">Your mind deserves care</div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container" style={{ overflowY: "auto", display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh", padding: "24px 16px" }}>
      <div className="s-signup" style={{ width: "100%", maxWidth: "480px", background: "white", borderRadius: "24px", boxShadow: "0 10px 32px rgba(15, 28, 20, 0.05)", border: "1px solid rgba(15, 28, 20, 0.04)", padding: "32px 24px", minHeight: "auto", height: "auto" }}>
        <div className="signup-title">
          {isRegister ? "Create your space" : "Welcome back"}
        </div>
        <div className="signup-sub">
          {isRegister ? "A safe, private place just for you." : "Sign in to continue your reflections."}
        </div>

        {isRegister ? (
          /* REGISTRATION FORM */
          <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', flex: 1, gap: '4px' }}>
            <div className="input-group">
              <div className="input-label">Your name</div>
              <input 
                type="text" 
                className={`input-field ${focusedField === 'name' ? 'focused' : ''}`}
                placeholder="Namrata" 
                value={name}
                onChange={(e) => setName(e.target.value)}
                onFocus={() => setFocusedField('name')}
                onBlur={() => setFocusedField('')}
                required
              />
            </div>
            <div className="input-group">
              <div className="input-label">Email</div>
              <input 
                type="email" 
                className={`input-field ${focusedField === 'email' ? 'focused' : ''}`} 
                placeholder="namrata@gmail.com" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onFocus={() => setFocusedField('email')}
                onBlur={() => setFocusedField('')}
                required
              />
            </div>
            <div className="input-group">
              <div className="input-label">Password</div>
              <input 
                type="password" 
                className={`input-field ${focusedField === 'password' ? 'focused' : ''}`} 
                placeholder="••••••••" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onFocus={() => setFocusedField('password')}
                onBlur={() => setFocusedField('')}
                required
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div className="input-group">
                <div className="input-label">Age</div>
                <input 
                  type="number" 
                  className={`input-field ${focusedField === 'age' ? 'focused' : ''}`} 
                  min="13"
                  max="100"
                  value={age}
                  onChange={(e) => setAge(Number(e.target.value))}
                  onFocus={() => setFocusedField('age')}
                  onBlur={() => setFocusedField('')}
                  required
                />
              </div>
              <div className="input-group">
                <div className="input-label">Gender</div>
                <select 
                  className="input-field"
                  value={gender}
                  onChange={(e) => setGender(e.target.value)}
                >
                  <option value="Female">Female</option>
                  <option value="Male">Male</option>
                  <option value="Non-binary">Non-binary</option>
                </select>
              </div>
            </div>

            <div className="input-group">
              <div className="input-label">Persona</div>
              <select 
                className="input-field"
                value={persona}
                onChange={(e) => setPersona(e.target.value)}
              >
                <option value="Exam Warrior/ Teenager">Exam Warrior / Teenager</option>
                <option value="Bachelor">Bachelor</option>
                <option value="Corporate Professional">Corporate Professional</option>
                <option value="Parent of a teenager">Parent of a teenager</option>
                <option value="Working Woman">Working Woman</option>
              </select>
            </div>

            <button 
              type="submit" 
              className="btn-primary" 
              style={{ marginTop: '16px' }}
              disabled={loading}
            >
              {loading ? "Registering..." : "Create Account →"}
            </button>
            
            <button 
              type="button"
              className="btn-secondary"
              onClick={() => setIsRegister(false)}
            >
              Already have an account? Log In
            </button>
          </form>
        ) : (
          /* LOGIN FORM */
          <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', flex: 1, gap: '4px' }}>
            <div className="input-group">
              <div className="input-label">Email</div>
              <input 
                type="email" 
                className={`input-field ${focusedField === 'email' ? 'focused' : ''}`} 
                placeholder="namrata@gmail.com" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onFocus={() => setFocusedField('email')}
                onBlur={() => setFocusedField('')}
                required
              />
            </div>
            <div className="input-group">
              <div className="input-label">Password</div>
              <input 
                type="password" 
                className={`input-field ${focusedField === 'password' ? 'focused' : ''}`} 
                placeholder="••••••••" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onFocus={() => setFocusedField('password')}
                onBlur={() => setFocusedField('')}
                required
              />
            </div>

            <button 
              type="submit" 
              className="btn-primary" 
              style={{ marginTop: '16px' }}
              disabled={loading}
            >
              {loading ? "Logging In..." : "Log In →"}
            </button>
            
            <button 
              type="button"
              className="btn-secondary"
              onClick={() => setIsRegister(true)}
            >
              Don't have an account? Sign Up
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
