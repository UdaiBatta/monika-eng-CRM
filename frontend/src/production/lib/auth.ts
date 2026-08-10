import { useQuery } from "@tanstack/react-query"

import { apiGet } from "./api"
import type { CurrentUser } from "./types"

export const currentUserQueryKey = ["auth", "me"] as const

export function useCurrentUser() {
  return useQuery({
    queryKey: currentUserQueryKey,
    queryFn: () => apiGet<CurrentUser>("/auth/me/"),
  })
}

export function hasPermission(user: CurrentUser | undefined, code: string) {
  return Boolean(user?.permissions?.includes(code))
}
