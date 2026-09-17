import express from 'express';
import authRoutes from './routes/auth.routes.js';
import userRoutes from './routes/users.routes.js';

const app = express();
app.use(express.json());
app.use('/api/v1/auth', authRoutes);
app.use('/api/v1/users', userRoutes);

export default app;
