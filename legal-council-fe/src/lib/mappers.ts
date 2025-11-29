import { DeliberationMessage, CouncilMemberRole } from '@/types/legal-council';

// Define the raw API message shape
interface ApiMessageSender {
  type: 'system' | 'user' | 'agent';
  role?: string;
  agent_id?: CouncilMemberRole;
}

interface ApiDeliberationMessage extends Omit<DeliberationMessage, 'sender'> {
  sender: ApiMessageSender | string; // Handle both for robustness
}

export function normalizeMessage(message: ApiDeliberationMessage | DeliberationMessage): DeliberationMessage {
  let senderId: string;

  if (typeof message.sender === 'string') {
    return message as DeliberationMessage;
  }

  const senderObj = message.sender as ApiMessageSender;

  switch (senderObj.type) {
    case 'system':
      senderId = 'system';
      break;
    case 'user':
      senderId = 'user';
      break;
    case 'agent':
      senderId = senderObj.agent_id || 'system'; // Fallback
      break;
    default:
      senderId = 'system';
  }

  return {
    ...message,
    sender: senderId as any,
    timestamp: new Date(message.timestamp), // Ensure date object
  };
}

export function normalizeMessages(messages: (ApiDeliberationMessage | DeliberationMessage)[]): DeliberationMessage[] {
  return messages.map(normalizeMessage);
}

