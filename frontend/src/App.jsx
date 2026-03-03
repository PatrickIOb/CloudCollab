import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider } from "@/auth/AuthContext"
import RequireAuth from "@/auth/RequireAuth"
import TopNav from "@/components/TopNav"

import Home from "@/pages/Home"
import Login from "@/pages/Login"
import CompletedProjects from "@/pages/CompletedProjects"
import ActiveProjects from "@/pages/ActiveProjects"
import Player from "@/pages/Player"

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <TopNav />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />

          <Route path="/projects/completed" element={<CompletedProjects />} />

          <Route
            path="/projects/active"
            element={
              <RequireAuth>
                <ActiveProjects />
              </RequireAuth>
            }
          />

          <Route path="/projects/:id/player" element={<Player />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
