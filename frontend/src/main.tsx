import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import AppLayout from "@/components/AppLayout";
import GuestRoute from "@/components/GuestRoute";
import { Toaster } from "@/components/ui/sonner";
import CategoriesPage from "@/pages/CategoriesPage";
import DashboardPage from "@/pages/DashboardPage";
import FinancePage from "@/pages/FinancePage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";

import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            <GuestRoute>
              <LoginPage />
            </GuestRoute>
          }
        />
        <Route
          path="/register"
          element={
            <GuestRoute>
              <RegisterPage />
            </GuestRoute>
          }
        />
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="categories" element={<CategoriesPage />} />
          <Route path="finance" element={<FinancePage />} />
        </Route>
      </Routes>
      <Toaster />
    </BrowserRouter>
  </StrictMode>,
);
