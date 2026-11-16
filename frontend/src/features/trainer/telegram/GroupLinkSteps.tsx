import { Copy } from 'lucide-react';
import { toast } from 'sonner';
import type { GroupCode } from '@/api/telegram';
import { Button } from '@/components/ui';
import { loc } from '@/i18n';

/** How to connect a player's Telegram group: create group -> add bot as admin -> send /link <code>. */
export function GroupLinkSteps({ code, botUsername = 'tahadi_coach_bot' }: { code: GroupCode; botUsername?: string }) {
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code.link_command);
      toast.success(loc('تم نسخ الأمر', 'Command copied'));
    } catch {
      toast.error(loc('تعذر النسخ، انسخه يدويًا', 'Could not copy, copy it manually'));
    }
  };
  const expires = new Date(code.expires_at * 1000).toLocaleDateString();
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-line bg-surface-2 p-4 text-sm">
      <ol className="flex list-decimal flex-col gap-1.5 ps-5">
        <li>{loc('في تيليجرام أنشئ مجموعة جديدة باسم اللاعب (مثل: تحدي – ياسر).', "In Telegram create a new group named after the player (e.g. Tahadi – Yasser).")}</li>
        <li>
          {loc('أضف البوت ', 'Add the bot ')}
          <span dir="ltr" className="font-semibold">@{botUsername}</span>
          {loc(' واجعله مشرفًا (Admin).', ' and make it an admin.')}
        </li>
        <li>{loc('أرسل هذا الأمر داخل المجموعة:', 'Send this command inside the group:')}</li>
      </ol>
      <div className="flex items-center gap-2">
        <code dir="ltr" className="min-w-0 flex-1 truncate rounded-lg bg-surface px-3 py-2 font-mono text-xs">{code.link_command}</code>
        <Button size="sm" variant="outline" icon={<Copy className="h-4 w-4" />} onClick={copy}>
          {loc('نسخ', 'Copy')}
        </Button>
      </div>
      <p className="text-xs text-muted">
        {loc(
          `بعدها يرسل لك البوت رابط دعوة المجموعة لترسله للاعب. الرمز صالح حتى ${expires}.`,
          `The bot then sends you the group invite link to share with the player. Valid until ${expires}.`,
        )}
      </p>
    </div>
  );
}
