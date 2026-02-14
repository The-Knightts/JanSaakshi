const express = require('express');
const cors = require('cors');
const mongoose = require('mongoose');
const wardsRouter = require('./routes/wards');

const app = express();
app.use(cors());
app.use(express.json());

app.use('/api/wards', wardsRouter);

const PORT = process.env.PORT || 4000;
const MONGO_URI = process.env.MONGO_URI;

async function start() {
  if (MONGO_URI) {
    try {
      await mongoose.connect(MONGO_URI);
      // eslint-disable-next-line no-console
      console.log('MongoDB connected');
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn('MongoDB connection failed, continuing with file-backed data');
    }
  } else {
    // eslint-disable-next-line no-console
    console.warn('MONGO_URI not set, using file-backed data');
  }
  app.listen(PORT, () => {
    // eslint-disable-next-line no-console
    console.log(`API server on http://localhost:${PORT}`);
  });
}

start();

