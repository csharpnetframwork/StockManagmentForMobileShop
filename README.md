# Mobile Shop Management – Streamlit (Supabase / PostgreSQL) v8

**Permanent data:** This build uses **PostgreSQL** (Supabase) instead of SQLite.

---
## 🔑 Default Admin Login
- **Username:** admin
- **Password:** vishal@7007

An admin user is auto-seeded *only if the `users` table is empty* at startup.

---
## ⚙️ Configuration (Streamlit Cloud)
Add this to **Secrets**:

```toml
[db]
url = "postgresql://postgres:YOUR-PASSWORD@db.ktufeagwjsmucvpoggvb.supabase.co:5432/postgres"
```

Replace `YOUR-PASSWORD` with your Supabase DB password.

---
## 🔁 Local Development (Optional)
You can set an env var instead of secrets:

**PowerShell (Windows):**
```powershell
$env:DB_URL="postgresql://postgres:YOUR-PASSWORD@db.ktufeagwjsmucvpoggvb.supabase.co:5432/postgres"
streamlit run app.py
```

**Linux/Mac:**
```bash
export DB_URL="postgresql://postgres:YOUR-PASSWORD@db.ktufeagwjsmucvpoggvb.supabase.co:5432/postgres"
streamlit run app.py
```

---
## 📦 Bulk Stock Upload (CSV)
Go to **Inventory → Upload Stock via CSV**.

Required columns:
`name,sku,category,price,qty`  
Optional: `imei`

Sample file included: `sample_stock.csv`.

---
## 🚀 Deploy on Streamlit Cloud
1. Push this folder to GitHub.
2. In Streamlit Cloud: New App → select repo → main branch → `app.py`.
3. Add Secrets (see above).
4. Deploy.

---
Generated: 2025-07-17T12:14:27
