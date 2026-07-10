export type Role = 'user' | 'ai';

export interface Message {
    id: string;
    role: Role;
    content: string;
    statusText?: string;
    isStreaming?: boolean;
}

// ----- Session types (used by Sidebar) -----

export interface SessionPreview {
    id: string;
    title: string;
    created_at: string;
    preview: string;
}

export interface SessionListResponse {
    sessions: SessionPreview[];
    total: number;
    limit: number;
    offset: number;
}

export interface SessionMessage {
    id: string;
    session_id: string;
    role: 'user' | 'ai';
    content: string;
    timestamp: string;
}

export interface SessionDetailResponse {
    id: string;
    title: string;
    created_at: string;
    messages: SessionMessage[];
}