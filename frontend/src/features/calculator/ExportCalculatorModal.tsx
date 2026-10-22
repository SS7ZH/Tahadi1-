import { useState } from 'react';
import type { Role } from '@/api/types';
import { Button, Input, Modal, Select } from '@/components/ui';
import { useClients } from '@/hooks/queries';
import { tr } from '@/i18n';

interface ExportCalculatorModalProps {
  open: boolean;
  onClose: () => void;
  userRole: Role;
  onExport: (names: { clientId?: number; clientName?: string; coachName?: string }) => Promise<void>;
  exporting: boolean;
}

export function ExportCalculatorModal({
  open,
  onClose,
  userRole,
  onExport,
  exporting,
}: ExportCalculatorModalProps) {
  const isTrainer = userRole === 'trainer';
  const isAdmin = userRole === 'admin';
  const clients = useClients(undefined);

  const [selectedClientId, setSelectedClientId] = useState<string>('');
  const [customClientName, setCustomClientName] = useState('');
  const [coachName, setCoachName] = useState('');

  const canSubmit = isTrainer
    ? !!selectedClientId || !!customClientName.trim()
    : isAdmin
    ? !!coachName.trim() && !!customClientName.trim()
    : true;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    await onExport({
      clientId: selectedClientId ? Number(selectedClientId) : undefined,
      clientName: customClientName.trim() || undefined,
      coachName: coachName.trim() || undefined,
    });
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={tr.pdf.calculatorExport}
      size="sm"
      footer={
        <div className="flex w-full items-center justify-between gap-2">
          <Button variant="ghost" onClick={onClose} disabled={exporting}>
            {tr.common.cancel}
          </Button>
          <Button loading={exporting} disabled={!canSubmit} onClick={handleSubmit}>
            {tr.pdf.exportPdf}
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        <p className="text-xs text-muted">{tr.pdf.calculatorSubtitle}</p>

        {isAdmin && (
          <Input
            label={tr.pdf.coachName}
            value={coachName}
            onChange={(e) => setCoachName(e.target.value)}
            required
            autoFocus
          />
        )}

        {isTrainer && (
          <Select
            label={tr.pdf.chooseClient}
            value={selectedClientId}
            onChange={(e) => {
              setSelectedClientId(e.target.value);
              if (e.target.value) setCustomClientName('');
            }}
          >
            <option value="">{tr.form.choose}</option>
            {clients.data?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.full_name}
              </option>
            ))}
          </Select>
        )}

        {(isAdmin || (isTrainer && !selectedClientId)) && (
          <Input
            label={isTrainer ? tr.pdf.orTypeClientName : tr.pdf.clientName}
            value={customClientName}
            onChange={(e) => setCustomClientName(e.target.value)}
            required={isAdmin || !selectedClientId}
          />
        )}
      </div>
    </Modal>
  );
}
