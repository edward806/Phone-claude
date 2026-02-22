const express = require('express');
const { config, validate } = require('./config');
const SessionService = require('./services/sessionService');
const voiceRoutes = require('./routes/voice');
const outboundRoutes = require('./routes/outbound');
const logger = require('./utils/logger');

async function createApp() {
  validate(config);

  const app = express();
  app.use(express.urlencoded({ extended: false }));
  app.use(express.json());

  app.use('/voice', voiceRoutes);
  app.use('/outbound', outboundRoutes);

  app.get('/health', (req, res) => res.json({ status: 'ok' }));

  return app;
}

async function main() {
  const app = await createApp();
  const session = new SessionService();
  await session.connect();

  app.listen(config.port, () => {
    logger.info(`Phone-claude listening on port ${config.port}`);
  });
}

if (require.main === module) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = { createApp };
