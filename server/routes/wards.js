const { Router } = require('express');
const fs = require('fs');
const path = require('path');
const mongoose = require('mongoose');

const router = Router();

// Schemas (only used if Mongo is connected)
const GeometrySchema = new mongoose.Schema({
  type: { type: String, enum: ['Polygon', 'MultiPolygon'], required: true },
  coordinates: { type: Array, required: true }
});

const WardSchema = new mongoose.Schema({
  wardNumber: { type: Number, unique: true, required: true },
  wardName: { type: String, required: true },
  corporatorName: { type: String, required: true },
  geometry: { type: GeometrySchema, required: true }
});

const ProjectSchema = new mongoose.Schema({
  title: { type: String, required: true },
  wardNumber: { type: Number, index: true, required: true },
  status: { type: String, enum: ['active', 'completed', 'delayed'], required: true }
});

const Ward = mongoose.models.Ward || mongoose.model('Ward', WardSchema);
const Project = mongoose.models.Project || mongoose.model('Project', ProjectSchema);

function hasMongo() {
  return mongoose.connection.readyState === 1;
}

// Use real wards GeoJSON from project root /data/wards.geojson
const fileGeoPath = path.join(__dirname, '..', 'data', 'wards.geojson');


const fileStats = [
  { wardNumber: 1, wardName: 'Ward 1', corporatorName: 'Person A', total: 10, active: 5, completed: 4, delayed: 1 },
  { wardNumber: 2, wardName: 'Ward 2', corporatorName: 'Person B', total: 8, active: 2, completed: 6, delayed: 0 }
];

router.get('/geojson', async (_req, res) => {
  if (hasMongo()) {
    const wards = await Ward.find({}, { wardNumber: 1, wardName: 1, geometry: 1, _id: 0 }).lean();
    const features = wards.map((w) => ({
      type: 'Feature',
      properties: { wardNumber: w.wardNumber, wardName: w.wardName },
      geometry: w.geometry
    }));
    res.set('x-geojson-source', 'mongo');
    return res.json({ type: 'FeatureCollection', features });
  }

  if (fs.existsSync(fileGeoPath)) {
    const raw = JSON.parse(fs.readFileSync(fileGeoPath, 'utf8'));

    const features = raw.features.map((f) => ({
      type: 'Feature',
      properties: {
        wardNumber: Number(f.properties.note),   // converting "note" → wardNumber
        wardName: `Ward ${f.properties.note}`
      },
      geometry: f.geometry
    }));

    res.set('x-geojson-source', 'file');
    return res.json({
      type: 'FeatureCollection',
      features
    });
  }

  res.set('x-geojson-source', 'empty');
  return res.json({ type: 'FeatureCollection', features: [] });
});

router.get('/stats', async (_req, res) => {
  if (hasMongo()) {
    const agg = await Project.aggregate([
      {
        $group: {
          _id: '$wardNumber',
          total: { $sum: 1 },
          active: { $sum: { $cond: [{ $eq: ['$status', 'active'] }, 1, 0] } },
          completed: { $sum: { $cond: [{ $eq: ['$status', 'completed'] }, 1, 0] } },
          delayed: { $sum: { $cond: [{ $eq: ['$status', 'delayed'] }, 1, 0] } }
        }
      }
    ]);

    const wards = await Ward.find({}, { wardNumber: 1, wardName: 1, corporatorName: 1, _id: 0 }).lean();
    const byWard = new Map(wards.map((w) => [w.wardNumber, w]));

    const result = agg.map((a) => {
      const w = byWard.get(a._id) || { wardName: '', corporatorName: '' };
      return {
        wardNumber: a._id,
        wardName: w.wardName,
        corporatorName: w.corporatorName,
        total: a.total,
        active: a.active,
        completed: a.completed,
        delayed: a.delayed
      };
    });

    return res.json(result);
  }

  if (fs.existsSync(fileGeoPath)) {
    const raw = JSON.parse(fs.readFileSync(fileGeoPath, 'utf8'));

    const stats = raw.features.map((f) => {
      const wn = Number(f.properties.note);

      return {
        wardNumber: wn,
        wardName: `Ward ${wn}`,
        corporatorName: "Not Assigned",
        total: 0,
        active: 0,
        completed: 0,
        delayed: 0
      };
    });

    return res.json(stats);
  }

});

router.get('/:wardNumber', async (req, res) => {
  const wardNumber = Number(req.params.wardNumber);

  if (hasMongo()) {
    const ward = await Ward.findOne({ wardNumber }).lean();

    const stats = await Project.aggregate([
      { $match: { wardNumber } },
      {
        $group: {
          _id: '$wardNumber',
          total: { $sum: 1 },
          active: { $sum: { $cond: [{ $eq: ['$status', 'active'] }, 1, 0] } },
          completed: { $sum: { $cond: [{ $eq: ['$status', 'completed'] }, 1, 0] } },
          delayed: { $sum: { $cond: [{ $eq: ['$status', 'delayed'] }, 1, 0] } }
        }
      }
    ]);

    const s = stats[0] || { total: 0, active: 0, completed: 0, delayed: 0 };

    return res.json({
      wardNumber,
      wardName: ward?.wardName || '',
      corporatorName: ward?.corporatorName || '',
      total: s.total,
      active: s.active,
      completed: s.completed,
      delayed: s.delayed
    });
  }

  const fallback = fileStats.find((x) => x.wardNumber === wardNumber) || {
    wardNumber,
    wardName: '',
    corporatorName: '',
    total: 0,
    active: 0,
    completed: 0,
    delayed: 0
  };

  return res.json(fallback);
});

module.exports = router;
