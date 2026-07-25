
const express = require('express');
const cors = require('cors');
const Database = require('better-sqlite3');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

const db = new Database('votes.db');

db.exec(`
    CREATE TABLE IF NOT EXISTS designs (
        id TEXT PRIMARY KEY,
        theme TEXT, theme_cn TEXT, style TEXT, aspect TEXT, filename TEXT, votes INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        design_id TEXT, ip_hash TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(design_id, ip_hash)
    );
`);

const catalog = require('./catalog.json');
const insert = db.prepare('INSERT OR IGNORE INTO designs (id, theme, theme_cn, style, aspect, filename, votes) VALUES (?, ?, ?, ?, ?, ?, ?)');
for (const item of catalog) {
    insert.run(item.id, item.theme, item.theme_cn, item.style, item.aspect, item.filename, item.votes || 0);
}

app.get('/api/designs', (req, res) => {
    const designs = db.prepare('SELECT * FROM designs ORDER BY theme, style, aspect').all();
    res.json(designs);
});

app.get('/api/designs/:id', (req, res) => {
    const design = db.prepare('SELECT * FROM designs WHERE id = ?').get(req.params.id);
    if (!design) return res.status(404).json({error: 'Not found'});
    res.json(design);
});

app.post('/api/vote/:id', (req, res) => {
    const { id } = req.params;
    const ip = req.ip || req.connection.remoteAddress;
    const ipHash = Buffer.from(ip).toString('base64').slice(0, 16);
    
    const design = db.prepare('SELECT * FROM designs WHERE id = ?').get(id);
    if (!design) return res.status(404).json({error: 'Not found'});
    
    try {
        db.prepare('INSERT INTO votes (design_id, ip_hash) VALUES (?, ?)').run(id, ipHash);
        db.prepare('UPDATE designs SET votes = votes + 1 WHERE id = ?').run(id);
        const updated = db.prepare('SELECT votes FROM designs WHERE id = ?').get(id);
        res.json({votes: updated.votes, success: true});
    } catch (e) {
        if (e.code === 'SQLITE_CONSTRAINT_UNIQUE') {
            res.status(400).json({error: 'Already voted', votes: design.votes});
        } else {
            res.status(500).json({error: e.message});
        }
    }
});

app.get('/api/stats', (req, res) => {
    const totalDesigns = db.prepare('SELECT COUNT(*) as c FROM designs').get().c;
    const totalVotes = db.prepare('SELECT SUM(votes) as v FROM designs').get().v || 0;
    const byTheme = db.prepare('SELECT theme, theme_cn, COUNT(*) as count, SUM(votes) as votes FROM designs GROUP BY theme').all();
    res.json({totalDesigns, totalVotes, byTheme});
});

app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
