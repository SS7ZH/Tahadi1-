import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { AdminDashboard } from '@/features/admin/AdminDashboard';
import { AssignPage } from '@/features/admin/AssignPage';
import { ExercisesPage } from '@/features/admin/ExercisesPage';
import { SettingsPage } from '@/features/admin/SettingsPage';
import { UsersPage } from '@/features/admin/UsersPage';
import { LoginPage } from '@/features/auth/LoginPage';
import { NotFoundPage } from '@/features/auth/NotFoundPage';
import { ProfilePage } from '@/features/auth/ProfilePage';
import { CalculatorPage } from '@/features/calculator/CalculatorPage';
import { AskTrainerPage } from '@/features/client/AskTrainerPage';
import { MyHistoryPage } from '@/features/client/MyHistoryPage';
import { MyNutritionPage } from '@/features/client/MyNutritionPage';
import { MyProgramPage } from '@/features/client/MyProgramPage';
import { MyProgressPage } from '@/features/client/MyProgressPage';
import { ClientPage } from '@/features/trainer/ClientPage';
import { InboxPage } from '@/features/trainer/InboxPage';
import { TrainerDashboard } from '@/features/trainer/TrainerDashboard';
import { homePathFor, useAuth } from '@/hooks/useAuth';
import { FullScreenLoader, RequireRole } from './RequireRole';

function HomeRedirect() {
  const { user, status } = useAuth();
  if (status === 'loading') return <FullScreenLoader />;
  return <Navigate to={user ? homePathFor(user.role) : '/login'} replace />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<HomeRedirect />} />

      <Route
        element={
          <RequireRole>
            <Layout />
          </RequireRole>
        }
      >
        {/* shared */}
        <Route path="/calculator" element={<CalculatorPage />} />
        <Route path="/profile" element={<ProfilePage />} />

        {/* admin */}
        <Route path="/admin" element={<RequireRole roles={['admin']}><AdminDashboard /></RequireRole>} />
        <Route path="/admin/users" element={<RequireRole roles={['admin']}><UsersPage /></RequireRole>} />
        <Route path="/admin/assign" element={<RequireRole roles={['admin']}><AssignPage /></RequireRole>} />
        <Route path="/admin/settings" element={<RequireRole roles={['admin']}><SettingsPage /></RequireRole>} />
        <Route path="/admin/exercises" element={<RequireRole roles={['admin']}><ExercisesPage /></RequireRole>} />
        <Route path="/admin/questions" element={<RequireRole roles={['admin']}><InboxPage /></RequireRole>} />
        <Route path="/admin/clients/:clientId" element={<RequireRole roles={['admin']}><ClientPage /></RequireRole>} />

        {/* trainer */}
        <Route path="/trainer" element={<RequireRole roles={['trainer']}><TrainerDashboard /></RequireRole>} />
        <Route path="/trainer/questions" element={<RequireRole roles={['trainer']}><InboxPage /></RequireRole>} />
        <Route path="/trainer/clients/:clientId" element={<RequireRole roles={['trainer']}><ClientPage /></RequireRole>} />

        {/* client / player */}
        <Route path="/me" element={<RequireRole roles={['client']}><MyProgressPage /></RequireRole>} />
        <Route path="/me/history" element={<RequireRole roles={['client']}><MyHistoryPage /></RequireRole>} />
        <Route path="/me/program" element={<RequireRole roles={['client']}><MyProgramPage /></RequireRole>} />
        <Route path="/me/nutrition" element={<RequireRole roles={['client']}><MyNutritionPage /></RequireRole>} />
        <Route path="/me/ask" element={<RequireRole roles={['client']}><AskTrainerPage /></RequireRole>} />

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
