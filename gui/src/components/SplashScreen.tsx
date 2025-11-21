import { useEffect, useState } from "react";
import "./SplashScreen.css";

interface SplashScreenProps {
  onComplete: () => void;
}

export default function SplashScreen({ onComplete }: SplashScreenProps) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setTimeout(onComplete, 300);
          return 100;
        }
        return prev + 3;
      });
    }, 40);

    return () => clearInterval(interval);
  }, [onComplete]);

  return (
    <div className="splash-screen">
      <div className="splash-content">
        <div className="solar-icon">
          <svg viewBox="0 0 200 200" width="120" height="120">
            <circle cx="100" cy="100" r="40" fill="#FDB813" />
            {[...Array(12)].map((_, i) => (
              <line
                key={i}
                x1="100"
                y1="100"
                x2="100"
                y2="30"
                stroke="#FDB813"
                strokeWidth="4"
                strokeLinecap="round"
                transform={`rotate(${i * 30} 100 100)`}
                style={{
                  animation: `ray-pulse 1.5s ease-in-out infinite`,
                  animationDelay: `${i * 0.1}s`,
                }}
              />
            ))}
          </svg>
        </div>
        <h1 className="splash-title">Helioscope</h1>
        <p className="splash-subtitle">AI-Powered Solar Panel Detection</p>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <p className="splash-status">Initializing YOLO models...</p>
      </div>
    </div>
  );
}
