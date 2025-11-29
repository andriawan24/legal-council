import { Gavel, Heart, BookOpen, User, Bot } from 'lucide-react';

interface AgentAvatarProps {
  agent: 'strict' | 'humanist' | 'historian' | 'user' | 'system';
  size?: 'sm' | 'md' | 'lg';
}

const AGENT_CONFIG = {
  strict: {
    icon: Gavel,
    bgClass: 'bg-agent-strict',
    label: 'A',
  },
  humanist: {
    icon: Heart,
    bgClass: 'bg-agent-humanist',
    label: 'B',
  },
  historian: {
    icon: BookOpen,
    bgClass: 'bg-agent-historian',
    label: 'C',
  },
  user: {
    icon: User,
    bgClass: 'bg-primary',
    label: 'U',
  },
  system: {
    icon: Bot,
    bgClass: 'bg-muted-foreground',
    label: 'S',
  },
};

const SIZE_CLASSES = {
  sm: 'w-6 h-6',
  md: 'w-8 h-8',
  lg: 'w-10 h-10',
};

const ICON_SIZES = {
  sm: 'w-3 h-3',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
};

export function AgentAvatar({ agent, size = 'md' }: AgentAvatarProps) {
  const config = AGENT_CONFIG[agent];
  const Icon = config.icon;

  return (
    <div
      className={`
        ${SIZE_CLASSES[size]} ${config.bgClass}
        rounded-full flex items-center justify-center shrink-0
      `}
    >
      <Icon className={`${ICON_SIZES[size]} text-white`} />
    </div>
  );
}
