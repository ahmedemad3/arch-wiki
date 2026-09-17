export function authenticateJWT(req, res, next) { next(); }
export function requirePermission(perm: string) { return (req, res, next) => next(); }
