/**
 * DemoPage — واجهة مساعد المدرب وفحص الأداء الذكي
 *
 * تتضمن:
 *  - لوحة فحص أداء السكوات عبر الرؤية الحاسوبية (MediaPipe Pose)
 *  - لوحة متابعة المشترك، المخطط البياني، تحليل التقدم ومسودات الرد الآلية عبر تيليجرام
 */

import { useState } from 'react';
import { Sparkles } from 'lucide-react';
import { PageHeader } from '@/components/ui';
import { SquatChecker } from './SquatChecker';
import { CoachView } from './CoachView';
import { DEMO_CLIENTS } from './demoApi';

export function DemoPage() {
  const [activeClient, setActiveClient] = useState(DEMO_CLIENTS[0]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={
          <span className="flex items-center gap-2.5">
            <Sparkles className="h-6 w-6 text-primary" />
            مساعد المدرب وفحص الأداء الذكي
          </span>
        }
        subtitle="تحليل فوري لتكنيك السكوات بالرؤية الحاسوبية · متابعة تطور القياسات والردود الآلية عبر تيليجرام"
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* اللوحة الأولى: فحص أداء السكوات */}
        <SquatChecker selectedClient={activeClient} />

        {/* اللوحة الثانية: واجهة المدرب ومتابعة القياسات والردود */}
        <CoachView onClientChange={setActiveClient} />
      </div>
    </div>
  );
}
