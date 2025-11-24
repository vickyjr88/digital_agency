import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './LandingPage';
import Login from './Login';
import Signup from './Signup';
import Dashboard from './Dashboard';
import BrandDetails from './BrandDetails';
import CreateBrand from './CreateBrand';
import EditContent from './EditContent';
import './index.css';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(() => !!localStorage.getItem('token'));

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/login" element={!isLoggedIn ? <Login onLogin={() => setIsLoggedIn(true)} /> : <Navigate to="/dashboard" />} />
        <Route path="/dashboard" element={isLoggedIn ? <Dashboard /> : <Navigate to="/login" />} />
        <Route path="/brand/:id" element={isLoggedIn ? <BrandDetails /> : <Navigate to="/login" />} />
        <Route path="/brands/new" element={isLoggedIn ? <CreateBrand /> : <Navigate to="/login" />} />
        <Route path="/edit/:id" element={isLoggedIn ? <EditContent /> : <Navigate to="/login" />} />
        <Route path="/view/:id" element={isLoggedIn ? <EditContent /> : <Navigate to="/login" />} />
      </Routes>
    </Router>
  );
}

export default App;
