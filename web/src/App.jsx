import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './Login';
import Dashboard from './Dashboard';
import EditContent from './EditContent';
import './index.css';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  return (
    <Router>
      <Routes>
        <Route path="/login" element={!isLoggedIn ? <Login onLogin={() => setIsLoggedIn(true)} /> : <Navigate to="/" />} />
        <Route path="/" element={isLoggedIn ? <Dashboard /> : <Navigate to="/login" />} />
        <Route path="/edit/:id" element={isLoggedIn ? <EditContent /> : <Navigate to="/login" />} />
        <Route path="/view/:id" element={isLoggedIn ? <EditContent /> : <Navigate to="/login" />} />
      </Routes>
    </Router>
  );
}

export default App;
