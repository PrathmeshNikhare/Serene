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
      <div className="flex justify-center items-center h-screen bg-[var(--background)]">
        <div className="text-center">
          <div className="mx-auto mb-8" style={{ background: "linear-gradient(135deg, var(--chart-1), var(--chart-2))", width: "80px", height: "80px", borderRadius: "50%", filter: "blur(24px)", opacity: 0.8 }}></div>
          <div className="text-5xl font-black text-white tracking-tight mb-3 relative z-10" style={{ marginTop: "-90px" }}>Serene</div>
          <div className="text-xs font-bold text-white/50 tracking-widest uppercase mt-4">Your mind deserves care</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-center items-center min-h-screen bg-[var(--background)] px-4 py-8">
      <div className="neu-surface w-full max-w-[480px] rounded-[2rem] p-8 sm:p-10 border-t border-white/10">
        <div className="text-3xl font-black text-white mb-2 tracking-tight">
          {isRegister ? "Create your space" : "Welcome back"}
        </div>
        <div className="text-sm text-white/50 mb-10 font-medium">
          {isRegister ? "A safe, private place just for you." : "Sign in to continue your reflections."}
        </div>

        {isRegister ? (
          /* REGISTRATION FORM */
          <form onSubmit={handleRegister} className="flex flex-col gap-5">
            <div>
              <div className="text-[11px] font-bold text-white/40 uppercase tracking-widest mb-2">Your name</div>
              <input 
                type="text" 
                className={`neu-pressed rounded-xl px-4 py-3.5 text-sm w-full outline-none transition-all duration-300 text-white bg-transparent ${focusedField === 'name' ? 'ring-2 ring-[var(--chart-2)]' : ''}`}
                placeholder="Namrata" 
                value={name}
                onChange={(e) => setName(e.target.value)}
                onFocus={() => setFocusedField('name')}
                onBlur={() => setFocusedField('')}
                required
              />
            </div>
            <div>
              <div className="text-[11px] font-bold text-white/40 uppercase tracking-widest mb-2">Email</div>
              <input 
                type="email" 
                className={`neu-pressed rounded-xl px-4 py-3.5 text-sm w-full outline-none transition-all duration-300 text-white bg-transparent ${focusedField === 'email' ? 'ring-2 ring-[var(--chart-2)]' : ''}`}
                placeholder="namrata@gmail.com" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onFocus={() => setFocusedField('email')}
                onBlur={() => setFocusedField('')}
                required
              />
            </div>
            <div>
              <div className="text-[11px] font-bold text-white/40 uppercase tracking-widest mb-2">Password</div>
              <input 
                type="password" 
                className={`neu-pressed rounded-xl px-4 py-3.5 text-sm w-full outline-none transition-all duration-300 text-white bg-transparent ${focusedField === 'password' ? 'ring-2 ring-[var(--chart-2)]' : ''}`}
                placeholder="••••••••" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onFocus={() => setFocusedField('password')}
                onBlur={() => setFocusedField('')}
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-[11px] font-bold text-white/40 uppercase tracking-widest mb-2">Age</div>
                <input 
                  type="number" 
                  className={`neu-pressed rounded-xl px-4 py-3.5 text-sm w-full outline-none transition-all duration-300 text-white bg-transparent ${focusedField === 'age' ? 'ring-2 ring-[var(--chart-2)]' : ''}`}
                  min="13"
                  max="100"
                  value={age}
                  onChange={(e) => setAge(Number(e.target.value))}
                  onFocus={() => setFocusedField('age')}
                  onBlur={() => setFocusedField('')}
                  required
                />
              </div>
              <div>
                <div className="text-[11px] font-bold text-white/40 uppercase tracking-widest mb-2">Gender</div>
                <select 
                  className="neu-pressed rounded-xl px-4 py-3.5 text-sm w-full outline-none transition-all duration-300 text-white bg-transparent appearance-none cursor-pointer"
                  value={gender}
                  onChange={(e) => setGender(e.target.value)}
                  style={{ backgroundImage: `url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='rgba(255,255,255,0.4)' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e")`, backgroundRepeat: "no-repeat", backgroundPosition: "right 1rem center", backgroundSize: "1em" }}
                >
                  <option value="Female" className="bg-[#0f1115] text-white">Female</option>
                  <option value="Male" className="bg-[#0f1115] text-white">Male</option>
                  <option value="Non-binary" className="bg-[#0f1115] text-white">Non-binary</option>
                </select>
              </div>
            </div>

            <div>
              <div className="text-[11px] font-bold text-white/40 uppercase tracking-widest mb-2">Persona</div>
              <select 
                className="neu-pressed rounded-xl px-4 py-3.5 text-sm w-full outline-none transition-all duration-300 text-white bg-transparent appearance-none cursor-pointer"
                value={persona}
                onChange={(e) => setPersona(e.target.value)}
                style={{ backgroundImage: `url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='rgba(255,255,255,0.4)' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e")`, backgroundRepeat: "no-repeat", backgroundPosition: "right 1rem center", backgroundSize: "1em" }}
              >
                <option value="Exam Warrior/ Teenager" className="bg-[#0f1115] text-white">Exam Warrior / Teenager</option>
                <option value="Bachelor" className="bg-[#0f1115] text-white">Bachelor</option>
                <option value="Corporate Professional" className="bg-[#0f1115] text-white">Corporate Professional</option>
                <option value="Parent of a teenager" className="bg-[#0f1115] text-white">Parent of a teenager</option>
                <option value="Working Woman" className="bg-[#0f1115] text-white">Working Woman</option>
              </select>
            </div>

            <button 
              type="submit" 
              className="mt-6 neu-pressed rounded-full py-4 w-full font-bold text-white tracking-widest uppercase transition-all duration-300 hover:text-[var(--chart-2)] border border-white/5 hover:border-[var(--chart-2)]/30 hover:bg-[var(--chart-2)]/5"
              disabled={loading}
            >
              {loading ? "Registering..." : "Create Account"}
            </button>
            
            <button 
              type="button"
              className="mt-2 text-sm font-semibold text-white/40 hover:text-white transition-colors"
              onClick={() => setIsRegister(false)}
            >
              Already have an account? Log In
            </button>
          </form>
        ) : (
          /* LOGIN FORM */
          <form onSubmit={handleLogin} className="flex flex-col gap-5">
            <div>
              <div className="text-[11px] font-bold text-white/40 uppercase tracking-widest mb-2">Email</div>
              <input 
                type="email" 
                className={`neu-pressed rounded-xl px-4 py-3.5 text-sm w-full outline-none transition-all duration-300 text-white bg-transparent ${focusedField === 'email' ? 'ring-2 ring-[var(--chart-2)]' : ''}`}
                placeholder="namrata@gmail.com" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onFocus={() => setFocusedField('email')}
                onBlur={() => setFocusedField('')}
                required
              />
            </div>
            <div>
              <div className="text-[11px] font-bold text-white/40 uppercase tracking-widest mb-2">Password</div>
              <input 
                type="password" 
                className={`neu-pressed rounded-xl px-4 py-3.5 text-sm w-full outline-none transition-all duration-300 text-white bg-transparent ${focusedField === 'password' ? 'ring-2 ring-[var(--chart-2)]' : ''}`}
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
              className="mt-6 neu-pressed rounded-full py-4 w-full font-bold text-white tracking-widest uppercase transition-all duration-300 hover:text-[var(--chart-2)] border border-white/5 hover:border-[var(--chart-2)]/30 hover:bg-[var(--chart-2)]/5"
              disabled={loading}
            >
              {loading ? "Logging In..." : "Log In"}
            </button>
            
            <button 
              type="button"
              className="mt-2 text-sm font-semibold text-white/40 hover:text-white transition-colors"
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
