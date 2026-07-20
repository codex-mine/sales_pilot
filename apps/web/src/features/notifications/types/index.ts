// Mirrors the backend's app/schemas/notifications.py exactly (snake_case, same field names).

export interface NotificationResponse {
  id: string;
  notification_type: string;
  title: string;
  body: string | null;
  entity_type: string | null;
  entity_id: string | null;
  action_url: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface UnreadCountResponse {
  count: number;
}

export interface MarkAllReadResponse {
  marked_count: number;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface NotificationsQuery {
  unread_only?: boolean;
  page?: number;
  page_size?: number;
}
