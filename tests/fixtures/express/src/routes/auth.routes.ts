import { Router } from 'express';
import { login, refresh, me } from '../controllers/auth.controller.js';
import { authenticateJWT } from '../middleware/auth.middleware.js';

const router = Router();

router.post('/login', login);
router.post('/refresh', refresh);
router.get('/me', authenticateJWT, me);

export default router;
