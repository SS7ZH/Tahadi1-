import { Copy, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import type { PlayerInvite } from '@/api/telegram';
import { Button } from '@/components/ui';
import { loc } from '@/i18n';

/** The player's personal link: the coach sends it, the player opens it and presses Start. */
export function PlayerLinkBox({ invite }: { invite: PlayerInvite }) {
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(invite.invite_url);
      toast.success(loc('تم نسخ الرابط', 'Link copied'));
    } catch {
      toast.error(loc('تعذر النسخ، انسخه يدويًا', 'Could not copy, copy it manually'));
    }
  };
  const expires = new Date(invite.expires_at * 1000).toLocaleDateString();
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-line bg-surface-2 p-4 text-sm">
      <p>
        {loc(
          'أرسل هذا الرابط للاعب (واتساب أو أي وسيلة). يفتحه ويضغط «Start» ويبدأ المحادثة مع البوت مباشرة، ورسائله وصوره وفيديوهاته تصلك في محادثتك مع البوت.',
          'Send this link to the player. He opens it, presses «Start» and chats with the bot right away; his messages, photos and videos reach you in your own chat with the bot.',
        )}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <code dir="ltr" className="min-w-0 flex-1 truncate rounded-lg bg-surface px-3 py-2 font-mono text-xs">{invite.invite_url}</code>
        <Button size="sm" variant="outline" icon={<Copy className="h-4 w-4" />} onClick={copy}>
          {loc('نسخ', 'Copy')}
        </Button>
        <Button size="sm" variant="ghost" icon={<ExternalLink className="h-4 w-4" />} onClick={() => window.open(invite.invite_url, '_blank', 'noopener')}>
          {loc('فتح', 'Open')}
        </Button>
      </div>
      <p className="text-xs text-muted">{loc(`الرابط خاص بهذا اللاعب وصالح حتى ${expires}.`, `This link is for this player only, valid until ${expires}.`)}</p>
    </div>
  );
}
