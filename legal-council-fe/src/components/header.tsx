import { Scale } from 'lucide-react';

export function Header() {
  return (
    <header className='border-b border-border bg-card'>
      <div className='container mx-auto px-4 py-4 max-w-6xl'>
        <div className='flex items-center gap-3'>
          <div className='w-10 h-10 rounded-lg bg-primary flex items-center justify-center'>
            <Scale className='w-5 h-5 text-primary-foreground' />
          </div>
          <div>
            <h1 className='text-xl font-semibold text-foreground'>Legal Council</h1>
            <p className='text-sm text-muted-foreground'>Virtual Deliberation Room</p>
          </div>
        </div>
      </div>
    </header>
  );
}
