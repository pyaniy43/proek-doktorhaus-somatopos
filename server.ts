import express from "express";
import fs from "fs";
import path from "path";
import { createServer as createViteServer } from "vite";

const DB_FILE = path.resolve("db.json");

// Define structure
interface DbSchema {
    users: { name: string; password: string }[];
    history: any[];
}

// Initialize DB
const initDb = () => {
    if (!fs.existsSync(DB_FILE)) {
        fs.writeFileSync(DB_FILE, JSON.stringify({ users: [], history: [] }, null, 2));
    }
};
initDb();

const readDb = (): DbSchema => JSON.parse(fs.readFileSync(DB_FILE, "utf-8"));
const writeDb = (data: DbSchema) => fs.writeFileSync(DB_FILE, JSON.stringify(data, null, 2));

async function startServer() {
    const app = express();
    const PORT = 3000;

    app.use(express.json());

    // --- API ROUTES ---
    app.get("/api/db", (req, res) => {
        res.json(readDb());
    });

    app.post("/api/users", (req, res) => {
        const { name, password } = req.body;
        const db = readDb();
        if (!db.users.find(u => u.name === name)) {
            db.users.push({ name, password });
            writeDb(db);
        }
        res.json({ success: true });
    });

    app.post("/api/history", (req, res) => {
        const record = req.body;
        const db = readDb();
        db.history.unshift(record);
        writeDb(db);
        res.json({ success: true });
    });

    app.delete("/api/db", (req, res) => {
        const db = { users: [], history: [] };
        writeDb(db);
        res.json({ success: true });
    });

    // --- VITE MIDDLEWARE ---
    if (process.env.NODE_ENV !== "production") {
        const vite = await createViteServer({
            server: { middlewareMode: true },
            appType: "spa",
        });
        app.use(vite.middlewares);
    } else {
        const distPath = path.resolve('dist');
        app.use(express.static(distPath));
        app.get('*', (req, res) => {
            res.sendFile(path.join(distPath, 'index.html'));
        });
    }

    app.listen(PORT, "0.0.0.0", () => {
        console.log(`Server running on http://localhost:${PORT}`);
    });
}

startServer();
