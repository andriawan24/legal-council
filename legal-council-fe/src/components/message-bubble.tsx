import { DeliberationMessage } from '@/types/legal-council';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { AgentAvatar } from './agent-avatar';

export const markdownComponents: Components = {
  ul: ({ ...props }) => <ul className='list-disc pl-4 mb-2' {...props} />,
  ol: ({ ...props }) => <ol className='list-decimal pl-4 mb-2' {...props} />,
  p: ({ ...props }) => <p className='mb-2 last:mb-0' {...props} />,
  strong: ({ ...props }) => <strong className='font-bold' {...props} />,
  table: ({ ...props }) => (
    <div className='my-2 w-full overflow-y-auto'>
      <table className='w-full text-sm' {...props} />
    </div>
  ),
  thead: ({ ...props }) => <thead className='border-b border-border' {...props} />,
  tbody: ({ ...props }) => <tbody className='[&_tr:last-child]:border-0' {...props} />,
  tr: ({ ...props }) => <tr className='border-b border-border/50 transition-colors' {...props} />,
  th: ({ ...props }) => (
    <th className='h-10 px-2 text-left align-middle font-medium text-muted-foreground' {...props} />
  ),
  td: ({ ...props }) => <td className='p-2 align-middle' {...props} />,
  blockquote: ({ ...props }) => (
    <blockquote className='mt-6 border-l-2 border-primary pl-6 italic' {...props} />
  ),
};

export function MessageBubble({ message }: { message: DeliberationMessage }) {
  const isUser = message.sender === 'user';
  const isSystem = message.sender === 'system';

  if (isSystem) {
    return (
      <div className='bg-secondary/50 rounded-lg p-4 mx-6 border border-border'>
        <div className='text-sm text-foreground'>
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {message.content}
          </ReactMarkdown>
        </div>
      </div>
    );
  }

  // We need to cast message.sender to the specific union type expected by AgentAvatar
  // assuming message.sender is 'strict' | 'humanist' | 'historian' | 'user' | 'system'
  const agentId = message.sender as 'strict' | 'humanist' | 'historian' | 'user' | 'system';

  return (
    <div className={`flex gap-3 mx-6 ${isUser ? 'flex-row-reverse' : ''}`}>
      <AgentAvatar agent={agentId} size='md' />
      <div className={`flex-1 max-w-[80%] ${isUser ? 'flex flex-col items-end' : ''}`}>
        <span className='text-xs text-muted-foreground mb-1 block'>{message.sender_name}</span>
        <div
          className={`rounded-lg p-3 ${
            isUser
              ? 'bg-primary text-primary-foreground rounded-tr-none'
              : 'bg-secondary rounded-tl-none'
          }`}
        >
          <div className={`text-sm ${isUser ? '' : 'text-foreground'}`}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {message.content}
            </ReactMarkdown>
          </div>
          {message.cited_articles && message.cited_articles.length > 0 && (
            <div className='mt-2 pt-2 border-t border-border/50'>
              <span className='text-xs text-muted-foreground'>Cited Articles: </span>
              <ul className={`text-xs ${isUser ? 'text-primary-foreground/80' : 'text-primary'} list-disc pl-4`}>
                {message.cited_articles.map((citation, idx) => (
                  <li key={idx}>{citation.full_citation || citation.article}</li>
                ))}
              </ul>
            </div>
          )}
           {message.referenced_precedents && message.referenced_precedents.length > 0 && (
            <div className='mt-2 pt-2 border-t border-border/50'>
              <span className='text-xs text-muted-foreground'>Precedents: </span>
              <ul className={`text-xs ${isUser ? 'text-primary-foreground/80' : 'text-primary'} list-disc pl-4`}>
                {message.referenced_precedents.map((precedent, idx) => (
                  <li key={idx}>{precedent.verdict_number}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
