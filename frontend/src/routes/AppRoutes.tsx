import { Route, Routes } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { PublicShell } from '@/components/PublicShell';
import { SiteContentPage } from '@/features/admin/SiteContentPage';
import { LandingPage } from '@/features/home/LandingPage';
import { AdminDashboard } from '@/features/admin/AdminDashboard';
import { AssignPage } from '@/features/admin/AssignPage';
import { ExercisesPage } from '@/features/admin/ExercisesPage';
import { PlansPage } from '@/features/admin/PlansPage';
import { TemplatesPage } from '@/features/admin/TemplatesPage';
import { SettingsPage } from '@/features/admin/SettingsPage';
import { UsersPage } from '@/features/admin/UsersPage';
import { LoginPage } from '@/features/auth/LoginPage';
import { NotFoundPage } from '@/features/auth/NotFoundPage';
import { ProfilePage } from '@/features/auth/ProfilePage';
import { CalculatorPage } from '@/features/calculator/CalculatorPage';
import { AskTrainerPage } from '@/features/client/AskTrainerPage';
import { HomePage } from '@/features/client/HomePage';
import { MyDocumentsPage } from '@/features/client/MyDocumentsPage';
import { MyHistoryPage } from '@/features/client/MyHistoryPage';
import { OnboardingPage } from '@/features/onboarding/OnboardingPage';
import { MyNutritionPage } from '@/features/client/MyNutritionPage';
import { MyProgramPage } from '@/features/client/MyProgramPage';
import { MyProgressPage } from '@/features/client/MyProgressPage';
import { ClientPage } from '@/features/trainer/ClientPage';
import { InboxPage } from '@/features/trainer/InboxPage';
import { TrainerDashboard } from '@/features/trainer/TrainerDashboard';
import { useAuth } from '@/hooks/useAuth';
import { FullScreenLoader, OnboardingGate, RequireRole } from './RequireRole';

/** Public pages: signed-in users keep the app layout (and onboarding gate), visitors get the public header/footer. */
function AppOrPublicLayout() {
  const { user, status } = useAuth();
  if (status === 'loading') return <FullScreenLoader />;
  if (!user) return <PublicShell />;
  return (
    <OnboardingGate>
      <Layout />
    </OnboardingGate>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<LandingPage />} />

      <Route path="/onboarding" element={<RequireRole roles={['client']}><OnboardingPage /></RequireRole>} />

      <Route element={<AppOrPublicLayout />}>
        <Route path="/calculator" element={<CalculatorPage />} />
      </Route>

      <Route
        element={
          <RequireRole>
            <OnboardingGate>
              <Layout />
            </OnboardingGate>
          </RequireRole>
        }
      >
        {/* shared */}
        <Route path="/profile" element={<ProfilePage />} />

        {/* admin */}
        <Route path="/admin" element={<RequireRole roles={['admin']}><AdminDashboard /></RequireRole>} />
        <Route path="/admin/users" element={<RequireRole roles={['admin']}><UsersPage /></RequireRole>} />
        <Route path="/admin/assign" element={<RequireRole roles={['admin']}><AssignPage /></RequireRole>} />
        <Route path="/admin/settings" element={<RequireRole roles={['admin']}><SettingsPage /></RequireRole>} />
        <Route path="/admin/plans" element={<RequireRole roles={['admin']}><PlansPage /></RequireRole>} />
        <Route path="/admin/templates" element={<RequireRole roles={['admin']}><TemplatesPage /></RequireRole>} />
        <Route path="/admin/site" element={<RequireRole roles={['admin']}><SiteContentPage /></RequireRole>} />
        <Route path="/admin/exercises" element={<RequireRole roles={['admin']}><ExercisesPage /></RequireRole>} />
        <Route path="/admin/questions" element={<RequireRole roles={['admin']}><InboxPage /></RequireRole>} />
        <Route path="/admin/clients/:clientId" element={<RequireRole roles={['admin']}><ClientPage /></RequireRole>} />

        {/* trainer */}
        <Route path="/trainer" element={<RequireRole roles={['trainer']}><TrainerDashboard /></RequireRole>} />
        <Route path="/trainer/questions" element={<RequireRole roles={['trainer']}><InboxPage /></RequireRole>} />
        <Route path="/trainer/clients/:clientId" element={<RequireRole roles={['trainer']}><ClientPage /></RequireRole>} />

        {/* client / player */}
        <Route path="/me" element={<RequireRole roles={['client']}><HomePage /></RequireRole>} />
        <Route path="/me/progress" element={<RequireRole roles={['client']}><MyProgressPage /></RequireRole>} />
        <Route path="/me/documents" element={<RequireRole roles={['client']}><MyDocumentsPage /></RequireRole>} />
        <Route path="/me/history" element={<RequireRole roles={['client']}><MyHistoryPage /></RequireRole>} />
        <Route path="/me/program" element={<RequireRole roles={['client']}><MyProgramPage /></RequireRole>} />
        <Route path="/me/nutrition" element={<RequireRole roles={['client']}><MyNutritionPage /></RequireRole>} />
        <Route path="/me/ask" element={<RequireRole roles={['client']}><AskTrainerPage /></RequireRole>} />

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
