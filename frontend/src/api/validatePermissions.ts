import { redirect } from "@sveltejs/kit";
import type { MembershipRead, Permission } from "./types";

// Extended validatePermissions to support logical combinations of permissions
export const validatePermissions = (
    membership: Partial<MembershipRead> & Pick<MembershipRead, 'permissions'>,
    requiredPermissions: Permission[] | { and?: Permission[]; or?: Permission[] },
    redirectUrl?: string | URL
): boolean => {
    // Admin override
    if (membership.permissions.includes("administrator") || membership.is_owner) {
        return true;
    }

    // Handle logical combinations of permissions
    if (Array.isArray(requiredPermissions)) {
        // Default behavior: all permissions must be present (AND logic)
        if (!requiredPermissions.every(permission => membership.permissions.includes(permission))) {
            if (redirectUrl) {
                redirect(303, redirectUrl);
            }
            return false;
        }
    } else {
        const { and, or } = requiredPermissions;

        // Check AND conditions
        if (and && !and.every(permission => membership.permissions.includes(permission))) {
            if (redirectUrl) {
                redirect(303, redirectUrl);
            }
            return false;
        }

        // Check OR conditions
        if (or && !or.some(permission => membership.permissions.includes(permission))) {
            if (redirectUrl) {
                redirect(303, redirectUrl);
            }
            return false;
        }
    }

    return true;
};