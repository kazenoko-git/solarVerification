import "./LoadingSpinner.css";

interface LoadingSpinnerProps {
  size?: "small" | "medium" | "large";
  message?: string;
}

export default function LoadingSpinner({ 
  size = "medium", 
  message 
}: LoadingSpinnerProps) {
  const sizeMap = {
    small: 24,
    medium: 48,
    large: 64,
  };

  return (
    <div className="loading-container">
      <div className={`spinner spinner-${size}`}>
        <svg
          width={sizeMap[size]}
          height={sizeMap[size]}
          viewBox="0 0 50 50"
          className="spinner-svg"
        >
          <circle
            cx="25"
            cy="25"
            r="20"
            fill="none"
            stroke="#FDB813"
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray="31.4 31.4"
            className="spinner-circle"
          />
        </svg>
      </div>
      {message && <p className="loading-message">{message}</p>}
    </div>
  );
}
