
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Upload from './pages/Upload'
import Dashboard from './pages/Dashboard'
import ManualExpense from './pages/ManualExpense'
import Trends from './pages/Trends'
import Alerts from './pages/Alerts'
import Search from './pages/Search'
import './App.css'

const links = [
  { to: '/', label: 'Upload', icon: '↥', end: true },
  { to: '/dashboard', label: 'Dashboard', icon: '▦' },
  { to: '/manual', label: 'Add Expense', icon: '+' },
  { to: '/trends', label: 'Trends', icon: '↗' },
  { to: '/alerts', label: 'Alerts', icon: '◇' },
  { to: '/search', label: 'Search', icon: '⌕' }
]

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="navbar">
          <NavLink className="logo" to="/">
            <span className="logo-mark">◈</span>
            Receipt<span>Brain</span>
          </NavLink>

          <div className="nav-links">
            {links.map(link => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  isActive ? 'active' : ''
                }
              >
                <span className="nav-icon">{link.icon}</span>
                {link.label}
              </NavLink>
            ))}
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Upload />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/manual" element={<ManualExpense />} />
            <Route path="/trends" element={<Trends />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/search" element={<Search />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
