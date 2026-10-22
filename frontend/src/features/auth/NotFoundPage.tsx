import { Compass } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button, Card, EmptyState } from '@/components/ui';
import { homePathFor, useCurrentUser } from '@/hooks/useAuth';
import { tr } from '@/i18n';

export function NotFoundPage() {
  const user = useCurrentUser();
  return (
    <Card>
      <EmptyState
        icon={<Compass className="h-6 w-6" />}
        title={tr.notFound.title}
        description={tr.notFound.text}
        action={
          <Link to={homePathFor(user.role)}>
            <Button>{tr.notFound.home}</Button>
          </Link>
        }
      />
    </Card>
  );
}
