import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { errorMessage } from '@/api/client';
import { telegramApi, type PlayerInvite } from '@/api/telegram';
import { Button, Input, Modal, Select } from '@/components/ui';
import { loc, tr } from '@/i18n';
import { PlayerLinkBox } from './PlayerLinkBox';

/** Add a player who only uses Telegram (no email, no password, no web login). */
export function TelegramPlayerModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [sex, setSex] = useState<'male' | 'female'>('male');
  const [goal, setGoal] = useState('fitness');
  const [created, setCreated] = useState<{ id: number; name: string; invite: PlayerInvite } | null>(null);

  const close = () => {
    setName('');
    setCreated(null);
    onClose();
  };

  const save = useMutation({
    mutationFn: () => telegramApi.createPlayer({ full_name: name.trim(), sex, goal }),
    onSuccess: async (r) => {
      setCreated({ id: r.client.id, name: r.client.full_name, invite: r });
      await qc.invalidateQueries({ queryKey: ['clients'] });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  return (
    <Modal
      open={open}
      onClose={close}
      title={created ? loc(`تمت إضافة ${created.name} ✅`, `${created.name} added ✅`) : loc('إضافة لاعب عبر تيليجرام', 'Add a Telegram player')}
      size="lg"
      footer={
        created ? (
          <>
            <Button variant="secondary" onClick={close}>{tr.common.close}</Button>
            <Button onClick={() => { close(); navigate(`/trainer/clients/${created.id}?tab=telegram`); }}>
              {loc('فتح صفحة اللاعب', "Open player's page")}
            </Button>
          </>
        ) : (
          <>
            <Button variant="secondary" onClick={close}>{tr.common.cancel}</Button>
            <Button loading={save.isPending} disabled={name.trim().length < 2} onClick={() => save.mutate()}>
              {tr.common.create}
            </Button>
          </>
        )
      }
    >
      {created ? (
        <PlayerLinkBox invite={created.invite} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          <p className="text-sm text-muted sm:col-span-2">
            {loc(
              'اللاعب لا يحتاج حسابًا ولا كلمة مرور: تحصل على رابط خاص به، يفتحه ويتحدث مع البوت مباشرة. البوت يسأله عن عمره وطوله في البداية.',
              'The player needs no account or password: you get a personal link, he opens it and chats with the bot directly. The bot asks his age and height at the start.',
            )}
          </p>
          <Input label={tr.client.fullName} value={name} onChange={(e) => setName(e.target.value)} />
          <Select label={tr.client.sex} value={sex} onChange={(e) => setSex(e.target.value as 'male' | 'female')}>
            <option value="male">{tr.sex.male}</option>
            <option value="female">{tr.sex.female}</option>
          </Select>
          <Select label={tr.client.goal} wrapperClassName="sm:col-span-2" value={goal} onChange={(e) => setGoal(e.target.value)}>
            {Object.entries(tr.goals).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </Select>
        </div>
      )}
    </Modal>
  );
}

