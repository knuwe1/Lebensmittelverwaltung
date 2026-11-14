export type Role = 'admin' | 'member';

export interface User {
  id: string;
  username: string;
  display_name: string;
  role: Role;
  can_do_inventory: boolean;
  active: boolean;
}
