import { Compass } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button, Card, EmptyState } from '@/components/ui';
import { homePathFor, useCurrentUser } from '@/hooks/useAuth';
import { ar } from '@/i18n/ar';

export function NotFoundPage() {
  const user = useCurrentUser();
  return (
    <Card>
      <EmptyState
        icon={<Compass className="h-6 w-6" />}
        title={ar.notFound.title}
        description={ar.notFound.text}
        action={
          <Link to={homePathFor(user.role)}>
            <Button>{ar.notFound.home}</Button>
          </Link>
        }
      />
    </Card>
  );
}
