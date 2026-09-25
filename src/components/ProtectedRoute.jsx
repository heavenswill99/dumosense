import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { CoreMark } from "@/components/CoreMark";

function FullScreenLoader() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background">
      <CoreMark state="sensing" size={56} />
      <p className="text-sm text-muted-foreground">Preparing your intelligence…</p>
    </div>
  );
}

export function ProtectedRoute({ children }) {
  const { user } = useAuth();
  if (user === undefined) return <FullScreenLoader />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default ProtectedRoute;
