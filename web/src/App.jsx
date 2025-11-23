import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './LandingPage';
import Login from './Login';
import Dashboard from './Dashboard';
import EditContent from './EditContent';
import './index.css';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={!isLoggedIn ? <Login onLogin={() => setIsLoggedIn(true)} /> : <Navigate to="/dashboard" />} />
        <Route path="/dashboard" element={isLoggedIn ? <Dashboard /> : <Navigate to="/login" />} />
        <Route path="/edit/:id" element={isLoggedIn ? <EditContent /> : <Navigate to="/login" />} />
        <Route path="/view/:id" element={isLoggedIn ? <EditContent /> : <Navigate to="/login" />} />
        <Route path="/signup" element={<div className="p-8 text-center">Signup page coming soon...</div>} />
      </Routes>
    </Router>
  );
}

export default App;
