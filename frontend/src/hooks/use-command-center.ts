import { create } from 'zustand';

export type CommandType = 
  | 'create_campaign' 
  | 'add_client' 
  | 'keyword_discovery' 
  | 'generate_report' 
  | 'citation_submission' 
  | null;

interface CommandState {
  activeCommand: CommandType;
  isOpen: boolean;
  context: any;
  openCommand: (type: CommandType, context?: any) => void;
  closeCommand: () => void;
}

export const useCommandCenter = create<CommandState>((set) => ({
  activeCommand: null,
  isOpen: false,
  context: null,
  openCommand: (type, context = null) => set({ activeCommand: type, isOpen: true, context }),
  closeCommand: () => set({ activeCommand: null, isOpen: false, context: null }),
}));
