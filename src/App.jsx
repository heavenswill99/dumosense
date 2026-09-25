import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";

import { AppShell } from "@/components/AppShell";
import { ProtectedRoute } from "@/components/ProtectedRoute";

import Landing from "@/pages/Landing";
import ChooseStart from "@/pages/ChooseStart";
import Register from "@/pages/Register";
import Login from "@/pages/Login";
import PrivacyPromise from "@/pages/PrivacyPromise";
import Consent from "@/pages/Consent";
import ProfileSetup from "@/pages/ProfileSetup";
import ProfileComplete from "@/pages/ProfileComplete";

import Home from "@/pages/app/Home";
import MindGuard from "@/pages/app/MindGuard";
import HealthReserve from "@/pages/app/HealthReserve";
import DumosenseAI from "@/pages/app/DumosenseAI";
import Profile from "@/pages/app/Profile";
import Membership from "@/pages/app/Membership";
import PrivacyCenter from "@/pages/app/PrivacyCenter";
import FamilySharing from "@/pages/app/FamilySharing";

function Shell({ children }) {
  return (
    <ProtectedRoute>
      <AppShell>{children}</AppShell>
    </ProtectedRoute>
  );
}

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/start" element={<ChooseStart />} />
      <Route path="/create-account" element={<Register />} />
      <Route path="/login" element={<Login />} />
      <Route path="/privacy-promise" element={<ProtectedRoute><PrivacyPromise /></ProtectedRoute>} />
      <Route path="/consent" element={<ProtectedRoute><Consent /></ProtectedRoute>} />
      <Route path="/profile-setup" element={<ProtectedRoute><ProfileSetup /></ProtectedRoute>} />
      <Route path="/profile-complete" element={<ProtectedRoute><ProfileComplete /></ProtectedRoute>} />
      <Route path="/app" element={<Shell><Home /></Shell>} />
      <Route path="/app/mindguard" element={<Shell><MindGuard /></Shell>} />
      <Route path="/app/health-reserve" element={<Shell><HealthReserve /></Shell>} />
      <Route path="/app/ai" element={<Shell><DumosenseAI /></Shell>} />
      <Route path="/app/profile" element={<Shell><Profile /></Shell>} />
      <Route path="/app/membership" element={<Shell><Membership /></Shell>} />
      <Route path="/app/privacy" element={<Shell><PrivacyCenter /></Shell>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AppRouter />
        <Toaster position="top-center" />
      </BrowserRouter>
    </div>
  );
}

export default App;