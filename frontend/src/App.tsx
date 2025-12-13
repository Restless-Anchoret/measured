import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import LogSession from './pages/LogSession';
import Sessions from './pages/Sessions';
import Projects from './pages/Projects';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/log-session" replace />} />
          <Route path="/log-session" element={<LogSession />} />
          <Route path="/sessions" element={<Sessions />} />
          <Route path="/projects" element={<Projects />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
