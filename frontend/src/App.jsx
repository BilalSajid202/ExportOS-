import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Register from './pages/Register';
import Team from './pages/Team';
import Products from './pages/Products';
import Inventory from './pages/Inventory';
import Deals from './pages/Deals';
import Inquiries from './pages/Inquiries';
import Copilot from './pages/Copilot';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Auth Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected App Routes */}
          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<Dashboard />} />
            <Route path="/copilot" element={<Copilot />} />
            <Route path="/copilot/:dealId" element={<Copilot />} />
            <Route path="/inquiries" element={<Inquiries />} />
            <Route path="/deals" element={<Deals />} />
            <Route path="/deals/:dealId" element={<Deals />} />
            <Route path="/products" element={<Products />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/inventory/:productId" element={<Inventory />} />
            <Route path="/team" element={<Team />} />
          </Route>

          {/* Catch-all fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
