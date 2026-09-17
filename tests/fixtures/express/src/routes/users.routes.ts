import { Router } from 'express';
import { list, getOne, create, remove } from '../controllers/users.controller.js';
import { authenticateJWT, requirePermission } from '../middleware/auth.middleware.js';

const router = Router();
router.use(authenticateJWT);

router.get('/', requirePermission('users:read'), list);
router.get('/:id', requirePermission('users:read'), getOne);
router.post('/', requirePermission('users:write'), create);
router.delete('/:id', requirePermission('users:delete'), remove);

export default router;
